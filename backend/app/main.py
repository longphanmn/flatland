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
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from .config import Config
from .db import Database
from .protocol import ControlAction, ControlMessage, GodLaws, HelloMessage, StateMessage
from .entities import Creature
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
        # Baseline laws that survive Reset (Save). Apply mutates only self.config.
        self.saved_config = self.config


CONFIG = Config.from_env()
RT = RuntimeState(CONFIG)
HUB = Hub()
DB = Database(os.environ.get("FLATWORLD_DB", str(Path(__file__).resolve().parent.parent / "flatworld.db")))


def start_world() -> None:
    """Register a fresh world row and attach the durable event sink."""
    if RT.world_id is not None:
        DB.end_world(RT.world_id)
    RT.world_id = DB.new_world(RT.config)
    RT.sim.on_event = _on_event


def _on_event(e) -> None:
    """Durable sinks for chronicle events: events feed the genealogy table."""
    if RT.world_id is None:
        return
    DB.add_events(RT.world_id, [e])
    if e.type == "birth":
        DB.add_creature(
            RT.world_id,
            entity_id=e.entity_id,
            caste=e.caste or "",
            clan_id=int(e.payload.get("clan_id") or 0),
            generation=int(e.payload.get("generation") or 0),
            mother_id=int(e.payload.get("mother") or 0),
            father_id=int(e.payload.get("father") or 0),
            born_tick=e.tick,
        )
    elif e.type == "death":
        DB.mark_death(RT.world_id, e.entity_id, e.tick)


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
        # Save persists across worlds, Apply does not — use saved baseline.
        # The chronicle endures in the database.
        base = getattr(RT, "saved_config", RT.config)
        new_cfg = replace(base, seed=random.SystemRandom().randint(0, 2**31 - 1))
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
    "plant_growth_rate",
    "plant_spread_rate",
    "nutrient_cycle_rate",
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
    "cohesion_weight",
    "alignment_weight",
    "separation_weight",
    "flock_radius",
    "relation_drift_rate",
    "alliance_threshold",
    "rivalry_threshold",
    "door_clearance",
    "house_min_size",
    "house_max_size",
    "shelter_enabled",
    "exposure_drain",
    "house_capacity",
    "house_claim_enabled",
    "rest_recovery_mult",
    "house_decay_ticks",
    "predation_enabled",
    "predator_ratio",
    "hunt_radius",
    "bite_damage",
    "bite_cooldown",
    "energy_from_prey",
    "fear_radius",
    "war_enabled",
    "attack_radius",
    "attack_damage",
)


def get_laws() -> dict:
    return {name: getattr(RT.config, name) for name in LAW_FIELDS}


def apply_laws(laws: GodLaws, persist: bool = True) -> dict:
    """God sets the rules; the world and every creature must obey them.

    persist=True  → Save: current world + future worlds (Reset uses this baseline)
    persist=False → Apply: current world only (Reset reverts to saved baseline)
    """
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
    if persist:
        # also advance the saved baseline so next Reset inherits it
        if not hasattr(RT, "saved_config"):
            RT.saved_config = RT.config
        else:
            RT.saved_config = replace(RT.saved_config, **updates)
    if "house_claim_enabled" in updates:
        RT.sim._refresh_house_claims()
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
async def write_laws(laws: GodLaws, persist: bool = True) -> dict:
    """Set new laws of nature (god-writable).

    persist=true  (default) → Save: current + future worlds (Reset keeps it)
    persist=false → Apply: current world only (Reset reverts)
    """
    return apply_laws(laws, persist=persist)


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


@app.post("/api/snapshot")
async def take_snapshot() -> dict:
    """Freeze the current world state into the album (god's photo, not a hand)."""
    if RT.world_id is None:
        raise HTTPException(409, "no active world")
    payload = json.dumps(RT.sim.snapshot().model_dump(mode="json"), separators=(",", ":"))
    sid = DB.save_snapshot(RT.world_id, RT.sim.tick, payload)
    return {"id": sid, "tick": RT.sim.tick}


@app.get("/api/snapshots")
async def list_snapshots() -> dict:
    if RT.world_id is None:
        return {"snapshots": []}
    return {"snapshots": DB.list_snapshots(RT.world_id)}


@app.get("/api/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: int) -> dict:
    snap = DB.get_snapshot(snapshot_id)
    if snap is None or (RT.world_id is not None and snap["world_id"] != RT.world_id):
        raise HTTPException(404, "snapshot not found")
    return {"id": snap["id"], "tick": snap["tick"], "state": snap["payload"]}


def _kin_card(entity_id: int) -> dict:
    """Dossier card for a family-tree node (alive creatures preferred)."""
    ent = RT.sim.world.entities.get(entity_id)
    if ent is not None and isinstance(ent, Creature):
        return {
            "id": entity_id,
            "caste": ent.caste,
            "alive": True,
            "clan_color": RT.sim.clans.get(ent.clan_id, {}).get("color"),
        }
    return {"id": entity_id, "caste": None, "alive": False, "clan_color": None}


def _family_of(creature_id: int) -> dict:
    """Parents above, children below — live world first, genealogy to fill gaps."""
    mother = father = None
    children: dict[int, dict] = {}

    # Living children are visible to the world even if the subject is not.
    for other in RT.sim.world.creatures():
        if other.id != creature_id and creature_id in (other.mother_id, other.father_id):
            children[other.id] = _kin_card(other.id)

    ent = RT.sim.world.entities.get(creature_id)
    if isinstance(ent, Creature):
        if ent.mother_id:
            mother = _kin_card(ent.mother_id)
        if ent.father_id:
            father = _kin_card(ent.father_id)

    if RT.world_id is not None:
        gm, gf = DB.genealogy_parents(RT.world_id, creature_id)
        if mother is None and gm:
            mother = {**gm, "alive": False, "clan_color": None}
        if father is None and gf:
            father = {**gf, "alive": False, "clan_color": None}
        for kid in DB.genealogy_children(RT.world_id, creature_id):
            if kid["id"] not in children and kid["id"] != creature_id:
                children[kid["id"]] = {**kid, "alive": False, "clan_color": None}

    return {"mother": mother, "father": father, "children": list(children.values())}


@app.get("/api/creature/{creature_id}")
async def get_creature(creature_id: int) -> dict:
    """Live status + personal chronicle + family tree for one creature."""
    ent = RT.sim.world.entities.get(creature_id)
    entity = RT.sim._entity_state(ent).model_dump(mode="json") if ent else None
    events = (
        [
            e
            for e in DB.history(RT.world_id, since_id=0, limit=2000)
            if e["entity_id"] == creature_id
        ]
        if RT.world_id
        else []
    )
    return {"entity": entity, "events": events, "family": _family_of(creature_id)}


@app.get("/api/state", response_model=StateMessage)
async def get_state() -> StateMessage:
    return RT.sim.snapshot()


@app.get("/guide", response_class=HTMLResponse)
async def get_guide(format: str | None = None):
    """Living guide — backend-rendered, always matches the running code."""
    if format == "json":
        return JSONResponse(
            {
                "laws": list(GodLaws.model_fields.keys()),
                "routes": [getattr(r, "path", "") for r in app.routes],
            }
        )
    from .guide import build_guide_html

    return HTMLResponse(build_guide_html(app))


@app.post("/api/control")
async def post_control(msg: ControlMessage) -> dict:
    return await apply_control(msg)
