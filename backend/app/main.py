"""FastAPI application: WebSocket state broadcast + control, REST helpers."""

import asyncio
import json
import os
import random
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict, replace
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config import Config
from .db import Database
from .protocol import ControlAction, ControlMessage, GodLaws, HelloMessage, StateMessage
from .simulation import Simulation

MIN_SPEED = 0.5  # ticks per second
MAX_SPEED = 120.0


class Hub:
    """Tracks connected WebSocket clients and broadcasts snapshots."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, payload: dict) -> None:
        if not self.clients:
            return
        text = json.dumps(payload, separators=(",", ":"))
        dead: list[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class RuntimeState:
    """Shared mutable runtime: current simulation, pause flag, ticks/sec."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.sim = Simulation(self.config)
        self.paused = False
        self.speed = self.config.tick_rate
        self.world_id: int | None = None


CONFIG = Config.from_env()
RT = RuntimeState(CONFIG)
HUB = Hub()
DB = Database(os.environ.get("FLATWORLD_DB", str(Path(__file__).resolve().parent.parent / "flatworld.db")))


def start_world() -> None:
    """Register a fresh world row and attach the durable event sink."""
    if RT.world_id is not None:
        DB.end_world(RT.world_id)
    RT.world_id = DB.new_world(RT.config)
    RT.sim.on_event = lambda e: DB.add_events(RT.world_id, [e])


@asynccontextmanager
async def lifespan(_: FastAPI):
    DB.connect()
    start_world()
    task = asyncio.create_task(tick_loop(RT, HUB))
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    if RT.world_id is not None:
        DB.end_world(RT.world_id)
    DB.close()


app = FastAPI(title="Flatland World Simulation", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------- loop
async def tick_loop(rt: RuntimeState, hub: Hub) -> None:
    loop = asyncio.get_running_loop()
    while True:
        interval = 1.0 / max(rt.speed, MIN_SPEED)
        started = loop.time()
        if not rt.paused:
            rt.sim.step()
            await hub.broadcast(rt.sim.snapshot().model_dump(mode="json"))
        elapsed = loop.time() - started
        await asyncio.sleep(max(0.0, interval - elapsed))


# ------------------------------------------------------------------ control
async def apply_control(msg: ControlMessage) -> dict:
    if msg.action is ControlAction.PAUSE:
        RT.paused = True
    elif msg.action is ControlAction.RESUME:
        RT.paused = False
    elif msg.action is ControlAction.STEP:
        RT.sim.step()
        await HUB.broadcast(RT.sim.snapshot().model_dump(mode="json"))
    elif msg.action is ControlAction.RESET:
        # A new world is born with fresh laws of chance: a new random seed.
        # The chronicle endures in the database.
        new_cfg = replace(RT.config, seed=random.SystemRandom().randint(0, 2**31 - 1))
        RT.config = new_cfg
        RT.sim = Simulation(new_cfg, history=RT.sim.history)
        start_world()
        await HUB.broadcast(RT.sim.snapshot().model_dump(mode="json"))
    elif msg.action is ControlAction.SET_SPEED:
        if msg.value is not None:
            RT.speed = min(MAX_SPEED, max(MIN_SPEED, float(msg.value)))
    return {
        "ok": True,
        "paused": RT.paused,
        "speed": RT.speed,
        "tick": RT.sim.tick,
    }


def hello_payload() -> dict:
    return HelloMessage(
        seed=CONFIG.seed,
        tick_rate=RT.speed,
        width=RT.config.width,
        height=RT.config.height,
        boundary=RT.config.boundary,
    ).model_dump(mode="json")


# --------------------------------------------------------------------- laws
LAW_FIELDS = (
    "boundary",
    "food_count",
    "energy_max",
    "energy_decay_per_tick",
    "energy_from_food",
    "hungry_ratio",
    "starving_ratio",
    "perceive_radius",
    "eat_radius",
    "wander_turn",
    "steer_turn",
    "hungry_perceive_mult",
    "desperate_perceive_mult",
    "desperate_speed_mult",
    "lifespan_mult",
    "birth_enabled",
    "adult_age",
    "mate_radius",
    "mate_energy_min",
    "birth_rate",
    "sex_ratio",
    "mutation_rate",
    "max_sides",
    "birth_energy_cost",
    "reproduction_cooldown",
    "carrying_capacity",
    "max_population",
    "euthanasia_threshold",
    "disease_enabled",
    "disease_outbreak_rate",
    "disease_rate",
    "disease_radius",
    "disease_energy_drain",
    "recovery_rate",
    "disease_lethality",
    "day_length",
    "season_length",
    "night_sight_mult",
    "weather_enabled",
    "weather_change_rate",
    "fog_sight_mult",
    "rain_speed_mult",
    "storm_wander_bonus",
    "door_clearance",
    "house_min_size",
    "house_max_size",
)


def get_laws() -> dict:
    return {name: getattr(RT.config, name) for name in LAW_FIELDS}


def apply_laws(laws: GodLaws) -> dict:
    """God sets the rules; the world and every creature must obey them."""
    updates = {
        k: v for k, v in laws.model_dump(exclude_unset=True).items() if v is not None
    }
    if updates:
        hungry = updates.get("hungry_ratio", RT.config.hungry_ratio)
        starving = updates.get("starving_ratio", RT.config.starving_ratio)
        if starving > hungry:
            raise HTTPException(422, "starving_ratio must be <= hungry_ratio")
        hmin = updates.get("house_min_size", RT.config.house_min_size)
        hmax = updates.get("house_max_size", RT.config.house_max_size)
        if hmax < hmin:
            raise HTTPException(422, "house_max_size must be >= house_min_size")
    cfg = replace(RT.config, **updates)
    RT.config = cfg
    RT.sim.config = cfg  # the living world follows the new law immediately
    RT.sim.world.config = cfg
    if updates and RT.world_id is not None:
        for name, value in updates.items():
            DB.add_law_change(RT.world_id, RT.sim.tick, name, value)
    return get_laws()


# ---------------------------------------------------------------- websocket
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await HUB.connect(ws)
    try:
        await ws.send_json(hello_payload())
        await ws.send_json(RT.sim.snapshot().model_dump(mode="json"))
        while True:
            raw = await ws.receive_json()
            try:
                msg = ControlMessage.model_validate(raw)
            except ValidationError:
                continue
            await apply_control(msg)
    except WebSocketDisconnect:
        pass
    finally:
        HUB.disconnect(ws)


# --------------------------------------------------------------------- rest
@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/api/config")
async def get_config() -> dict:
    return asdict(RT.config)


@app.get("/api/laws")
async def read_laws() -> dict:
    """Current laws of nature (god-readable)."""
    return get_laws()


@app.post("/api/laws")
async def write_laws(laws: GodLaws) -> dict:
    """Set new laws of nature (god-writable). Applies to the live world."""
    return apply_laws(laws)


@app.get("/api/history")
async def get_history(since: int = 0, limit: int = 500) -> dict:
    """The durable chronicle for the current world (paginated by event id)."""
    limit = max(1, min(limit, 2000))
    return {
        "world_id": RT.world_id,
        "total_deaths": DB.death_count(RT.world_id) if RT.world_id else 0,
        "events": DB.history(RT.world_id, since_id=since, limit=limit) if RT.world_id else [],
    }


@app.get("/api/worlds")
async def get_worlds() -> dict:
    """All world runs recorded in the database (newest first)."""
    return {"worlds": DB.worlds()}


@app.get("/api/creature/{creature_id}")
async def get_creature(creature_id: int) -> dict:
    """Live status + personal chronicle for one creature."""
    ent = RT.sim.world.entities.get(creature_id)
    entity = Simulation._entity_state(ent).model_dump(mode="json") if ent else None
    events = (
        [
            e
            for e in DB.history(RT.world_id, since_id=0, limit=2000)
            if e["entity_id"] == creature_id
        ]
        if RT.world_id
        else []
    )
    return {"entity": entity, "events": events}


@app.get("/api/state", response_model=StateMessage)
async def get_state() -> StateMessage:
    return RT.sim.snapshot()


@app.post("/api/control")
async def post_control(msg: ControlMessage) -> dict:
    return await apply_control(msg)
