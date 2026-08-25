"""FastAPI application: WebSocket state broadcast + control, REST helpers — Developer: Long Phan <long@minhnhan.in>."""

import asyncio
import json
import os
import random
import sys
import threading
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import ValidationError

from .auth import PasskeyAuth, SetupPasskey, require_god
from .config import Config
from .db import CLAN_PAYLOAD_KEYS, Database
from .protocol import ControlAction, ControlMessage, GodLaws, HelloMessage, StateMessage
from .entities import Creature
from .simulation import Simulation, glyph_for, personal_name_for, variation_for

MIN_SPEED = 0.5  # ticks per second
MAX_SPEED = 120.0

# AA: C-extension JSON for the ~30 Hz broadcast (GIL-releasing encode);
# falls back to stdlib when orjson is not installed.
try:
    import orjson

    def _dumps(payload: dict) -> str:
        return orjson.dumps(payload).decode("utf-8")
except ModuleNotFoundError:  # pragma: no cover - fallback envs

    def _dumps(payload: dict) -> str:
        return json.dumps(payload, separators=(",", ":"))


class Hub:
    """Tracks connected WebSocket clients and broadcasts snapshots.

    A half-dead client (phone slept, NAT dropped, proxy closed) makes
    `send_text` block forever — that used to park the whole tick loop at
    the broadcast await while HTTP stayed fine (world frozen, ok:true,
    nothing logged). Now every send gets a timeout; wedged clients are
    dropped and the world keeps ticking.
    """

    SEND_TIMEOUT = 5.0  # seconds a client may take per frame before we cut it

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def _send(self, ws: WebSocket, text: str) -> None:
        try:
            await asyncio.wait_for(ws.send_text(text), timeout=self.SEND_TIMEOUT)
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, payload: dict) -> None:
        if not self.clients:
            return
        text = _dumps(payload)
        # Concurrent fan-out: one slow client costs nobody else its timeout.
        await asyncio.gather(
            *(self._send(ws, text) for ws in list(self.clients)),
            return_exceptions=True,
        )


class RuntimeState:
    """Shared mutable runtime: current simulation, pause flag, ticks/sec.

    `lock` guards every touch of the live simulation. Since the tick engine
    runs on its own thread, REST/WS handlers must hold it while reading or
    mutating world state so nobody ever sees a half-advanced tick.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.sim = Simulation(self.config)
        self.paused = False
        self.speed = self.config.tick_rate
        self.world_id: int | None = None
        # Last failed tick (if any), sticky for diagnosis — surfaced via
        # /healthz so a sick world is visible without ssh-ing into the box.
        self.last_tick_error: str | None = None
        self.tick_failures = 0
        # Baseline laws that survive Reset (Save). Apply mutates only self.config.
        self.saved_config = self.config
        self.current_preset: str | None = "sustainable"
        self.lock = threading.RLock()
        # Tick timing ring buffer for /healthz diagnostics (true rate vs target)
        self._tick_times: list[float] = []  # monotonic timestamps of last 50 ticks
        self._tick_durs: list[float] = []  # durations (ms) of last 50 steps


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
    """Durable sinks for chronicle events: events feed the genealogy table.

    AA: blooms stay in the in-memory chronicle only — high-frequency,
    low-value, so they never cost a DB write. §AE withers are throttled
    the same way.
    AD: writes append to the Database RAM buffer (OS-log); the writer daemon
    drains it every 5s — the sim thread never blocks on SQLite.
    """
    if RT.world_id is None or e.type in ("bloom", "wither"):
        return
    wid = RT.world_id
    DB.log_event(wid, e)
    if e.type == "birth":
        DB.log_birth(
            wid,
            entity_id=e.entity_id,
            caste=e.caste or "",
            clan_id=int(e.payload.get("clan_id") or 0),
            generation=int(e.payload.get("generation") or 0),
            mother_id=int(e.payload.get("mother") or 0),
            father_id=int(e.payload.get("father") or 0),
            born_tick=e.tick,
        )
    elif e.type == "death":
        DB.log_death(wid, e.entity_id, e.tick)


# --------------------------------------------------------------------- loop
def advance_world(rt: RuntimeState, hub: Hub | None = None, force_keyframe: bool = False) -> dict | None:
    """Advance the world one tick (caller holds rt.lock).

    Returns the snapshot payload to broadcast (keyframe or delta), or None when throttled/failed.
    A plain function so tests can drive ticks without the engine thread.
    """
    if rt.paused:
        return None
    t0 = time.monotonic()
    try:
        # AD: chronicle/genealogy writes land in the RAM buffer; the writer
        # daemon commits them off-thread — step() never waits on SQLite.
        rt.sim.step()
        # World End / Extinction: if all creatures die (tick > 30), pause ticking automatically
        if rt.sim.tick > 30 and len(rt.sim.world.creatures()) == 0:
            rt.paused = True
    except Exception as exc:
        # The world must never die silently: one failed tick is logged
        # loudly and skipped — the loop keeps turning (a frozen tick
        # used to look like a crash and needed a restart to fix).
        rt.tick_failures += 1
        rt.last_tick_error = f"{type(exc).__name__}: {exc}"
        print(
            f"\n[tick-engine] step() FAILED at tick={rt.sim.tick}: {rt.last_tick_error} — skipping\n",
            flush=True,
        )
        traceback.print_exc()
        sys.stdout.flush()
        return None
    finally:
        # Record timing for /healthz even when step succeeded (or failed)
        dur_ms = (time.monotonic() - t0) * 1000.0
        try:
            rt._tick_durs.append(dur_ms)
            rt._tick_times.append(time.monotonic())
            if len(rt._tick_durs) > 50:
                rt._tick_durs.pop(0)
                rt._tick_times.pop(0)
            # Warn when a single tick overruns the target interval
            interval_ms = 1000.0 / max(rt.speed, MIN_SPEED)
            if dur_ms > interval_ms * 1.2:
                print(f"[tick-engine] overrun tick={rt.sim.tick} dur={dur_ms:.1f}ms > interval={interval_ms:.1f}ms (speed={rt.speed})", flush=True)
        except Exception:
            pass
    # If a hub is passed and has no active listeners, skip snapshot payload serialization
    if hub is not None and not hub.clients:
        return None
    # Throttle broadcast to ~20 Hz when tick rate is high
    every = max(1, int(round(rt.speed / 20))) if rt.speed > 20 else 1
    if every > 1 and rt.sim.tick % every != 0:
        return None

    # Phase 1 AJ: Broadcast full keyframe every 60 ticks (~2-3s) or when forced/uninitialized;
    # otherwise broadcast lightweight delta payload (85-95% bandwidth reduction).
    if force_keyframe or rt.sim.tick % 60 == 0 or not getattr(rt.sim, "_last_broadcast_state", None):
        return rt.sim.snapshot_payload()
    return rt.sim.snapshot_delta_payload()



class SimEngine:
    """Owns a dedicated OS thread that advances the world.

    Ticks used to run on the asyncio loop: a slow HTTP client or a big JSON
    broadcast stalled the simulation and vice versa. Now the sim paces itself
    on its own thread, DB writes ride along off-loop, and snapshots serialize
    here — the event loop only ships finished payloads. Shared state crosses
    threads strictly under `rt.lock`.
    """

    def __init__(self, rt: RuntimeState, hub: "Hub") -> None:
        self.rt = rt
        self.hub = hub
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self._loop = loop or asyncio.get_running_loop()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="tick-engine", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        assert self._loop is not None
        stop = self._stop
        while not stop.is_set():
            interval = 1.0 / max(self.rt.speed, MIN_SPEED)
            started = time.monotonic()
            payload = None
            with self.rt.lock:
                if not self.rt.paused:
                    payload = advance_world(self.rt, self.hub)
            if payload is not None:
                asyncio.run_coroutine_threadsafe(
                    self.hub.broadcast(payload), self._loop
                )
            elapsed = time.monotonic() - started
            stop.wait(max(0.0, interval - elapsed))


def _try_restore_snapshot() -> bool:
    """Restore same world across backend code deploys (no Reset).

    `deploy.sh` saves `GET /api/state` to `~/app/fl/snapshot.json` before
    killing the old backend. On next start we rehydrate `RT.sim` from that
    payload so tick+entities survive the restart — same world, same tick.
    """
    path = os.environ.get("FLATWORLD_RESTORE_SNAPSHOT", str(Path.home() / "app" / "fl" / "snapshot.json"))
    p = Path(path)
    if not p.exists():
        return False
    try:
        raw = p.read_text()
        data = json.loads(raw)
        if data.get("type") != "state" or "entities" not in data:
            return False
        # Rebuild simulation in-place
        from .entities import Corpse, Creature, Food, House
        # Clear existing
        RT.sim.world.entities.clear()
        RT.sim.world._next_id = 1
        # Also clear cached buckets will be rebuilt on next step
        max_id = 0
        for ent in data["entities"]:
            kind = ent.get("kind")
            eid = int(ent.get("id", 0))
            max_id = max(max_id, eid)
            if kind == "creature":
                c = Creature(
                    shape=ent.get("shape") or "polygon",
                    sides=int(ent.get("sides") or 4),
                    x=float(ent.get("x") or 0),
                    y=float(ent.get("y") or 0),
                    angle=float(ent.get("angle") or 0),
                    speed=0.6,
                    energy=float(ent.get("energy") or 80),
                    caste=ent.get("caste") or "",
                    radius=float(ent.get("radius") or 0),
                    age=int(ent.get("age") or 0),
                    lifespan=float(ent.get("lifespan") or 0),
                    generation=int(ent.get("generation") or 0),
                    clan_id=int(ent.get("clan_id") or 0),
                )
                # preserve extra fields if present
                for k in ("mother_id", "father_id", "health", "infected", "sleeping", "indoors", "status", "chill"):
                    if k in ent and ent[k] is not None:
                        setattr(c, k, ent[k])
                c.id = eid
                RT.sim.world.entities[eid] = c
            elif kind == "food":
                f = Food(x=float(ent.get("x") or 0), y=float(ent.get("y") or 0), growth=float(ent.get("growth") or 0.15), variant=ent.get("variant") or "grass")
                # preserve mature_ticks if present
                if "mature_ticks" in ent:
                    f.mature_ticks = int(ent["mature_ticks"])
                f.id = eid
                RT.sim.world.entities[eid] = f
            elif kind == "house":
                h = House(x=float(ent.get("x") or 0), y=float(ent.get("y") or 0), size=float(ent.get("size") or 6), door_width=float(ent.get("door_width") or 4), door_side=ent.get("door_side") or "south")
                for k in ("clan_id", "clan_color", "is_main", "is_ruin", "abandoned_ticks"):
                    if k in ent:
                        setattr(h, k, ent[k])
                h.id = eid
                RT.sim.world.entities[eid] = h
            elif kind == "corpse":
                co = Corpse(x=float(ent.get("x") or 0), y=float(ent.get("y") or 0), ttl=int(ent.get("ttl") or 600), energy=float(ent.get("energy") or 25))
                co.id = eid
                RT.sim.world.entities[eid] = co
        RT.sim.world._next_id = max_id + 1
        # Restore tick and meta
        RT.sim.tick = int(data.get("tick") or 0)
        if "clans" in data and isinstance(data["clans"], dict):
            # server keys are strings
            restored_clans: dict[int, dict] = {}
            for k, v in data["clans"].items():
                try:
                    restored_clans[int(k)] = dict(v)
                except Exception:
                    continue
            RT.sim.clans = restored_clans
            # repair _next_clan_id
            if restored_clans:
                RT.sim._next_clan_id = max(restored_clans.keys()) + 1
        if "relations" in data and isinstance(data["relations"], list):
            RT.sim.relations = {(int(r["a"]), int(r["b"])): int(r["score"]) for r in data["relations"] if "a" in r and "b" in r}
        if "signals" in data:
            RT.sim.signals = list(data["signals"])
        if "fires" in data:
            RT.sim.fires = list(data["fires"])
        # Rebuild index for next step
        RT.sim.world.rebuild_index()
        RT.sim._refresh_cache()
        print(f"[restore] loaded snapshot tick={RT.sim.tick} entities={len(RT.sim.world.entities)} clans={len(RT.sim.clans)} from {p}", flush=True)
        # Hotfix live world for N150: reduce query radii and heavy subsystems when pop >800
        c_count = len([e for e in RT.sim.world.entities.values() if e.kind == "creature"])
        if c_count > 800:
            # Apply cheaper laws in-place without POST (preserves tick) — keep most restrictive
            new_cfg = replace(
                RT.config,
                perceive_radius=min(RT.config.perceive_radius, 12.0),
                signal_radius=min(RT.config.signal_radius, 6.0),
                knowledge_enabled=False,
                schism_enabled=False,
                help_call_enabled=False,
                war_enabled=False,
                predation_enabled=False,
                territory_enabled=False,
                carrying_capacity=min(RT.config.carrying_capacity if RT.config.carrying_capacity>0 else 1200, 1200),
                max_population=min(RT.config.max_population if RT.config.max_population>0 else 1300, 1300),
                plant_growth_rate=min(RT.config.plant_growth_rate, 0.03),
                birth_rate=min(RT.config.birth_rate, 0.20),
                food_count=min(RT.config.food_count, 350),
                cannibalism_enabled=False,
                exile_on_kin_eat=False,
            )
            RT.config = new_cfg
            RT.sim.config = new_cfg
            RT.sim.world.config = new_cfg
            print(f"[restore] hotfix {c_count}c: perceive {new_cfg.perceive_radius} signal {new_cfg.signal_radius} cap {new_cfg.carrying_capacity}/{new_cfg.max_population} for 10t/s", flush=True)
        # Move aside so next start is fresh unless explicitly re-saved
        try:
            p.rename(p.with_suffix(".loaded"))
        except Exception:
            pass
        return True
    except Exception as exc:
        print(f"[restore] failed {exc}", flush=True)
        traceback.print_exc()
        return False


@asynccontextmanager
async def lifespan(_: FastAPI):
    DB.connect()
    # Try to keep same world across deploys
    restored = _try_restore_snapshot()
    if not restored:
        start_world()
    else:
        # reuse existing world_id row, attach event sink
        if RT.world_id is None:
            # find latest world row
            try:
                rows = DB.worlds()
                if rows:
                    RT.world_id = rows[0]["id"]
            except Exception:
                pass
        if RT.world_id is None:
            start_world()
        else:
            RT.sim.on_event = _on_event
            print(f"[restore] continuing world_id={RT.world_id} tick={RT.sim.tick}", flush=True)
    engine = SimEngine(RT, HUB)
    engine.start()
    yield
    engine.stop()
    if RT.world_id is not None:
        DB.end_world(RT.world_id)
    DB.close()


app = FastAPI(
    title="Flatland World Simulation",
    version="0.1.2",
    description="Flatland — 2D world simulation by Long Phan <long@minhnhan.in>",
    contact={"name": "Long Phan", "email": "long@minhnhan.in", "url": "https://minhnhan.in"},
    lifespan=lifespan,
)
AUTH = PasskeyAuth(DB)
app.state.god_auth = AUTH
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://world.minhnhan.in",
        "https://world.minhnhan.in",
    ],
    allow_origin_regex="https?://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ control
async def apply_control(msg: ControlMessage) -> dict:
    payload = None  # snapshots broadcast after the lock is released
    with RT.lock:
        if msg.action is ControlAction.PAUSE:
            RT.paused = True
        elif msg.action is ControlAction.RESUME:
            RT.paused = False
        elif msg.action is ControlAction.STEP:
            RT.sim.step()
            payload = RT.sim.snapshot_payload()
        elif msg.action is ControlAction.RESET:
            # A new world is born with fresh laws of chance: a new random seed.
            # Save persists across worlds, Apply does not — use saved baseline.
            # The chronicle endures in the database.
            base = getattr(RT, "saved_config", RT.config)
            new_cfg = replace(base, seed=random.SystemRandom().randint(0, 2**31 - 1))
            RT.config = new_cfg
            RT.sim = Simulation(new_cfg, history=RT.sim.history)
            RT.paused = False
            start_world()
            payload = RT.sim.snapshot_payload()
        elif msg.action is ControlAction.SET_SPEED:
            if msg.value is not None:
                RT.speed = min(MAX_SPEED, max(MIN_SPEED, float(msg.value)))
    if payload is not None:
        await HUB.broadcast(payload)
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
    "plant_variants_enabled",
    "poison_rate",
    "beast_ratio",
    "diet_strictness",
    "territory_enabled",
    "territory_radius",
    "trespass_decay",
    "totems_enabled",
    "succession_enabled",
    "max_clans",
    "schism_enabled",
    "schism_threshold",
    "schism_min_pop",
    "communication_enabled",
    "signal_radius",
    "food_call_rate",
    "alarm_call_rate",
    "knowledge_enabled",
    "knowledge_ttl",
    "knowledge_share_rate",
    "help_call_enabled",
    "help_radius",
    "defense_weight",
    "age_enabled",
    "age_length",
    "culture_enabled",
    "culture_spread_rate",
    "trait_mutation_rate",
    "wildfire_enabled",
    "fire_rate",
    "fire_spread_rate",
    "disaster_enabled",
    "disaster_rate",
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
    "food_giveup_ticks",
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
    "rain_growth_mult",
    "fog_mushroom_mult",
    "storm_plant_damage",
    "weather_sickness_enabled",
    "chill_rate",
    "chill_threshold",
    "chill_drain",
    "wet_disease_mult",
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
    "winter_food_mult",
    "coalitions_enabled",
    "coalition_threshold",
    "coalition_min_size",
    "leader_decisions_enabled",
    "resource_sharing_enabled",
    "larder_capacity",
    "aid_rate",
    "tribute_enabled",
    "betrayal_enabled",
    "defection_enabled",
    "cannibalism_enabled",
    "cannibalism_hunger_ratio",
    "cannibalism_energy",
    "eat_enemy_enabled",
    "eat_kin_enabled",
    "kin_stigma",
    "exile_on_kin_eat",
    "food_decay_enabled",
    "food_lifespan_ticks",
    "theology_enabled",
    "tithe_rate",
    "temple_faith_cost",
)


# --- T: presets ----------------------------------------------------------------
# Recalculated for the 400x300 default map (pop ~156, schism/comm/war enabled, war rare).
# Area-tuned numbers scale x3 from the 200x200 baseline: food bounty and population
# Recalculated for high-scale population on modern / low-end CPUs (e.g., Intel N150).
# Area-tuned numbers support 2000-4000+ active inhabitants with 60 FPS batched rendering.
PRESETS: dict[str, dict] = {
    "balance": dict(
        # The Goldilocks condition: gentle harmony for steady 500-800 population multi-generational flourishing.
        food_count=220,
        plant_growth_rate=0.045,
        plant_spread_rate=0.006,
        winter_food_mult=0.70,
        poison_rate=0.008,
        perceive_radius=16.0,
        energy_decay_per_tick=0.025,
        carrying_capacity=600,
        max_population=800,
        disease_enabled=True,
        disease_outbreak_rate=0.00006,
        disease_rate=0.035,
        disease_energy_drain=0.05,
        recovery_rate=0.03,
        disease_lethality=0.18,
        war_enabled=True,
        attack_damage=32.0,
        predation_enabled=True,
        predator_ratio=0.02,
        bite_damage=28.0,
        bite_cooldown=15,
        fear_radius=12.0,
        relation_drift_rate=2.2,
        rivalry_threshold=-80,
        alliance_threshold=60,
        trespass_decay=0.15,
        house_capacity=10,
        season_length=12000,
        schism_enabled=True,
        schism_threshold=0.6,
        schism_min_pop=8,
        communication_enabled=True,
        knowledge_enabled=True,
        help_call_enabled=True,
        cannibalism_enabled=True,
        cannibalism_hunger_ratio=0.12,
        cannibalism_energy=35.0,
        eat_enemy_enabled=True,
        eat_kin_enabled=True,
        kin_stigma=35,
        exile_on_kin_eat=True,
        food_decay_enabled=True,
        food_lifespan_ticks=8000,
        wildfire_enabled=True,
        fire_rate=0.00008,
        fire_spread_rate=0.035,
        disaster_enabled=True,
        disaster_rate=0.00004,
        age_enabled=True,
        culture_enabled=True,
        shelter_enabled=True,
        exposure_drain=0.025,
        rest_recovery_mult=2.0,
        adult_age=220.0,
        birth_rate=0.28,
        birth_energy_cost=20.0,
        reproduction_cooldown=200,
    ),
    "sustainable": dict(
        food_count=450,  # generous food for a thriving multi-generational civilization
        plant_growth_rate=0.06,
        plant_spread_rate=0.008,
        winter_food_mult=0.75,
        poison_rate=0.0,
        perceive_radius=18,
        energy_decay_per_tick=0.025,
        carrying_capacity=2200,  # soft cap for steady flourishing
        max_population=3000,  # hard cap
        disease_enabled=True,
        disease_outbreak_rate=0.0001,
        disease_rate=0.05,
        disease_energy_drain=0.08,
        recovery_rate=0.025,
        disease_lethality=0.25,
        war_enabled=True,
        attack_damage=40,  # wound, rare (default 45)
        predation_enabled=True,
        predator_ratio=0.03,
        bite_damage=40,
        bite_cooldown=12,
        relation_drift_rate=2.8,  # calm society
        rivalry_threshold=-85,
        trespass_decay=0.0,
        house_capacity=16,
        season_length=14400,
        schism_enabled=True,
        schism_threshold=0.55,
        schism_min_pop=7,
        communication_enabled=True,
    ),
    "chaos": dict(
        food_count=320,
        plant_growth_rate=0.04,
        plant_spread_rate=0.006,
        winter_food_mult=0.5,
        poison_rate=0.03,
        perceive_radius=20,
        energy_decay_per_tick=0.045,
        carrying_capacity=800,
        max_population=1200,
        disease_enabled=True,
        disease_outbreak_rate=0.002,
        disease_rate=0.12,
        disease_energy_drain=0.25,
        recovery_rate=0.005,
        disease_lethality=0.7,
        war_enabled=True,
        attack_damage=100,
        predation_enabled=True,
        predator_ratio=0.12,
        bite_damage=100,
        bite_cooldown=6,
        relation_drift_rate=0.4,
        rivalry_threshold=-20,
        trespass_decay=1.5,
        house_capacity=8,
        season_length=2400,
        wildfire_enabled=True,
        fire_rate=0.001,
        disaster_enabled=True,
        disaster_rate=0.001,
        schism_enabled=True,
        age_enabled=True,
    ),
    "extinction": dict(
        food_count=100,
        plant_growth_rate=0.02,
        plant_spread_rate=0.003,
        winter_food_mult=0.3,
        poison_rate=0.05,
        perceive_radius=14,
        energy_decay_per_tick=0.08,
        carrying_capacity=250,
        max_population=400,
        disease_enabled=True,
        disease_outbreak_rate=0.001,
        disease_rate=0.15,
        recovery_rate=0.003,
        disease_lethality=0.8,
        war_enabled=True,
        attack_damage=100,
        predation_enabled=True,
        predator_ratio=0.15,
        bite_damage=100,
        relation_drift_rate=0.3,
        rivalry_threshold=-30,
        trespass_decay=2.0,
        house_capacity=4,
        exposure_drain=0.15,
        storm_plant_damage=0.08,
        season_length=6000,
    ),
    "boom": dict(
        food_count=650,
        plant_growth_rate=0.08,
        plant_spread_rate=0.012,
        winter_food_mult=0.85,
        poison_rate=0.0,
        perceive_radius=20,
        energy_decay_per_tick=0.02,
        carrying_capacity=3500,  # massive population boom test
        max_population=5000,
        birth_rate=0.55,
        adult_age=100,
        mate_radius=12,
        mate_energy_min=15,
        birth_energy_cost=10,
        reproduction_cooldown=80,
        house_capacity=20,
        relation_drift_rate=3.0,
        rivalry_threshold=-95,
        trespass_decay=0.0,
        disease_enabled=False,
        war_enabled=False,
        season_length=14400,
        communication_enabled=True,
    ),
}


def detect_current_preset() -> str | None:
    current_laws = get_laws()
    for name, p_laws in PRESETS.items():
        if all(current_laws.get(k) == v for k, v in p_laws.items()):
            return name
    for name, p_laws in PRESETS.items():
        if (
            current_laws.get("food_count") == p_laws.get("food_count")
            and current_laws.get("carrying_capacity") == p_laws.get("carrying_capacity")
            and current_laws.get("max_population") == p_laws.get("max_population")
        ):
            return name
    return getattr(RT, "current_preset", "balance")


def get_laws() -> dict:
    laws = {name: getattr(RT.config, name) for name in LAW_FIELDS}
    return laws


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
    with RT.lock:
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
        # §AP Divine Law Resonance: the shrines chime, the priests preach.
        if updates:
            try:
                RT.sim.on_law_change(sorted(updates.keys()))
            except Exception:
                pass  # theology must never reject a law
        if updates and RT.world_id is not None:
            for name, value in updates.items():
                DB.add_law_change(RT.world_id, RT.sim.tick, name, value)
    return get_laws()


# ---------------------------------------------------------------- websocket
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await HUB.connect(ws)
    try:
        # A client that accepts the socket but never reads must not leak a
        # hung handler task — bound the handshake sends like broadcasts.
        await asyncio.wait_for(ws.send_json(hello_payload()), timeout=HUB.SEND_TIMEOUT)
        with RT.lock:
            snap = RT.sim.snapshot_payload()
        await asyncio.wait_for(
            ws.send_json(snap),
            timeout=HUB.SEND_TIMEOUT,
        )
        while True:
            raw = await ws.receive_json()
            try:
                msg = ControlMessage.model_validate(raw)
            except ValidationError:
                continue
            # God control over the socket needs the passkey too (pause/step/
            # reset are as much a hand on the world as any law).
            if not AUTH.verify(raw.get("key")):
                configured = AUTH.configured()
                await asyncio.wait_for(
                    ws.send_json(
                        {
                            "type": "auth_error",
                            "error": "god_key_not_configured" if not configured else "god_key_required",
                            "detail": (
                                "no god passkey exists yet — POST /api/auth/setup first"
                                if not configured
                                else "valid passkey required (key field) to control the world"
                            ),
                        }
                    ),
                    timeout=HUB.SEND_TIMEOUT,
                )
                continue
            await apply_control(msg)
    except WebSocketDisconnect:
        pass
    finally:
        HUB.disconnect(ws)


# --------------------------------------------------------------------- rest
@app.get("/healthz")
async def healthz() -> dict:
    # True rate from ring buffer (wall-clock)
    avg_dur = round(sum(RT._tick_durs) / len(RT._tick_durs), 2) if RT._tick_durs else 0.0
    max_dur = round(max(RT._tick_durs), 2) if RT._tick_durs else 0.0
    actual_tps = 0.0
    if len(RT._tick_times) >= 2:
        span = RT._tick_times[-1] - RT._tick_times[0]
        if span > 0:
            actual_tps = round((len(RT._tick_times) - 1) / span, 2)
    out: dict = {
        "ok": True,
        "tick": RT.sim.tick,
        "paused": RT.paused,
        "speed_target": RT.speed,
        "actual_tps": actual_tps,
        "avg_tick_ms": avg_dur,
        "max_tick_ms": max_dur,
        "interval_ms": round(1000.0 / max(RT.speed, MIN_SPEED), 1),
        "clients": len(HUB.clients),
        "db_pending": DB.pending,  # §AD ops still in the RAM log
        "creatures": len(RT.sim.world.creatures()),
    }
    if RT.last_tick_error:
        out["ok"] = False
        out["last_tick_error"] = RT.last_tick_error
    if avg_dur > out["interval_ms"] * 1.1:
        out["overrun"] = True
    return out


@app.get("/api/version")
async def get_version() -> dict:
    """Version + git revision for footer display."""
    import subprocess

    version = "0.1.2"
    revision = ""
    # try pyproject
    try:
        import tomllib

        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            version = data.get("project", {}).get("version", version)
    except Exception:
        try:
            import pathlib
            txt = pathlib.Path("pyproject.toml").read_text()
            for line in txt.splitlines():
                if line.strip().startswith("version"):
                    # version = "0.1.2"
                    parts = line.split("=")
                    if len(parts) == 2:
                        version = parts[1].strip().strip('"').strip("'")
        except Exception:
            pass
    # git revision
    try:
        revision = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=".", timeout=2).decode().strip()
    except Exception:
        try:
            revision = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], timeout=2).decode().strip()
        except Exception:
            revision = "dev"
    return {
        "version": version,
        "revision": revision,
        "developer": "Long Phan",
        "email": "long@minhnhan.in",
        "contact": "long@minhnhan.in",
    }


@app.get("/api/config")
async def get_config() -> dict:
    return asdict(RT.config)


@app.get("/api/laws")
async def read_laws() -> dict:
    """Current laws of nature (god-readable)."""
    return get_laws()


# --------------------------------------------------------------------- auth
@app.get("/api/auth/status")
async def auth_status() -> dict:
    """Whether a god passkey exists (public — lets the client ask to enroll)."""
    return {"configured": AUTH.configured()}


@app.post("/api/auth/setup")
async def auth_setup(body: SetupPasskey) -> dict:
    """First-time enrollment: register the god passkey (only before one exists)."""
    try:
        AUTH.setup(body.passkey)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(409, {"error": "god_key_already_configured", "detail": str(exc)}) from exc
    return {"ok": True, "configured": True}


@app.post("/api/laws", dependencies=[Depends(require_god)])
async def write_laws(laws: GodLaws, persist: bool = True) -> dict:
    """Set new laws of nature (god-writable).

    persist=true  (default) → Save: current + future worlds (Reset keeps it)
    persist=false → Apply: current world only (Reset reverts)
    """
    return apply_laws(laws, persist=persist)


@app.get("/api/presets")
async def list_presets() -> dict:
    """List available law presets (sustainable is the 1000-day world)."""
    return {
        "presets": list(PRESETS.keys()),
        "details": PRESETS,
        "current": detect_current_preset(),
    }


@app.post("/api/presets/{name}", dependencies=[Depends(require_god)])
async def apply_preset(name: str, persist: bool = True, reset: bool = False) -> dict:
    """Apply a named preset bundle. reset=true also resets the world with new laws."""
    if name not in PRESETS:
        raise HTTPException(404, f"preset {name!r} not found — {list(PRESETS.keys())}")
    RT.current_preset = name
    laws = GodLaws.model_validate(PRESETS[name])
    result = apply_laws(laws, persist=persist)
    if reset:
        # reuse RESET logic: new seed, new world
        base = getattr(RT, "saved_config", RT.config) if persist else RT.config
        new_cfg = replace(base, seed=random.SystemRandom().randint(0, 2**31 - 1))
        RT.config = new_cfg
        RT.sim = Simulation(new_cfg, history=RT.sim.history)
        RT.paused = False
        start_world()
        await HUB.broadcast(RT.sim.snapshot_payload())
    return {"preset": name, "laws": result, "reset": reset}


@app.get("/api/history")
async def get_history(
    since: int = 0,
    limit: int = 500,
    type: str | None = None,
    entity_id: int | None = None,
    clan_id: int | None = None,
) -> dict:
    """The durable chronicle for the current world (paginated by event id).

    §AT-1: `clan_id=N` filters at the SQL level — events whose payload names
    the clan (a/b/clan_id/conquest/schism/takeover pairs) stay queryable even
    after they rolled off the in-memory chronicle."""
    # AD: drain the RAM log so a fresh reader sees the full tail
    # (the flush runs here, on the HTTP thread — never on the sim thread).
    DB.flush()
    limit = max(1, min(limit, 2000))
    return {
        "world_id": RT.world_id,
        "total_deaths": DB.death_count(RT.world_id) if RT.world_id else 0,
        "events": DB.history(
            RT.world_id,
            since_id=since,
            limit=limit,
            type_filter=type,
            entity_id=entity_id,
            clan_id=clan_id,
        )
        if RT.world_id
        else [],
    }


@app.get("/api/clans/{clan_id}/history")
async def get_clan_history(clan_id: int, page: int = 0, size: int = 50) -> dict:
    """§AT-1: the FULL filtered event stream for a clan — paginated over the
    in-memory chronicle (newest page first), plus the clan's own internal log
    (leader changes, takeovers, wars, schisms)."""
    with RT.lock:
        if clan_id not in RT.sim.clans:
            raise HTTPException(404, "clan not found")
        size = max(1, min(size, 200))
        page = max(0, page)
        matching = [
            e for e in RT.sim.history
            if any(e.payload.get(k) == clan_id for k in CLAN_PAYLOAD_KEYS)
        ]
        matching.reverse()  # newest first
        start = page * size
        slice_ = matching[start:start + size]
        return {
            "clan_id": clan_id,
            "page": page,
            "size": size,
            "total": len(matching),
            "has_more": start + size < len(matching),
            "events": [e.model_dump(mode="json") for e in slice_],
            # the clan's internal milestone log (capped at 30 in-memory)
            "log": RT.sim.clans[clan_id].get("history", []),
        }


@app.get("/api/worlds")
async def get_worlds() -> dict:
    """All world runs recorded in the database (newest first)."""
    DB.flush()  # AD: fresh reads of the world ledger
    return {"worlds": DB.worlds()}


@app.get("/api/clans/{clan_id}")
async def get_clan(clan_id: int) -> dict:
    """Single clan details with members and history."""
    with RT.lock:
        return _clan_details(clan_id)


def _clan_details(clan_id: int) -> dict:
    if clan_id not in RT.sim.clans:
        raise HTTPException(404, "clan not found")
    info = RT.sim.clans[clan_id]
    # members
    members = []
    for c in RT.sim.world.creatures():
        if c.clan_id == clan_id:
            members.append({
                "id": c.id,
                "caste": c.caste,
                "sex": c.sex,
                "age": c.age,
                "lifespan": c.lifespan,
                "stage": c.stage,
                "energy": round(c.energy, 1),
                "health": round(c.health, 1),
                "status": c.status,
                "personal_name": __import__('app.simulation', fromlist=['personal_name_for']).personal_name_for(c.id, RT.sim.config.seed, c.generation),
                "glyph": __import__('app.simulation', fromlist=['glyph_for']).glyph_for(c.id, RT.sim.config.seed, c.generation),
            })
    # houses — a clan can have multiple houses, strictly one main house
    clan_houses = []
    main_house = None
    valid_clan_houses = [
        ent for ent in RT.sim.world.entities.values()
        if ent.kind == "house" and getattr(ent, "clan_id", 0) == clan_id and not getattr(ent, "is_ruin", False)
    ]
    main_hid = info.get("main_house_id")
    if valid_clan_houses and (not main_hid or not any(h.id == main_hid for h in valid_clan_houses)):
        main_hid = valid_clan_houses[0].id
        info["main_house_id"] = main_hid

    for ent in valid_clan_houses:
        is_main = (ent.id == main_hid)
        ent.is_main = is_main
        h_obj = {
            "id": ent.id,
            "x": round(ent.x, 2),
            "y": round(ent.y, 2),
            "size": getattr(ent, "size", 0),
            "is_main": is_main,
            "is_ruin": False,
            "clan_color": getattr(ent, "clan_color", None),
        }
        clan_houses.append(h_obj)
        if is_main:
            main_house = h_obj

    # war record
    wins = sum(1 for e in RT.sim.history if e.type == "war" and int(e.payload.get("b", 0) or 0) == clan_id)
    losses = sum(1 for e in RT.sim.history if e.type == "war" and int(e.payload.get("a", 0) or 0) == clan_id)
    # recent events for this clan
    clan_events = [e for e in RT.sim.history if (e.payload.get("a") == clan_id or e.payload.get("b") == clan_id or e.payload.get("clan_id") == clan_id) ][-20:]
    return {
        "id": clan_id,
        "name": info.get("name"),
        "color": info.get("color"),
        "totem": info.get("totem"),
        "founder_id": info.get("founder_id"),
        "leader_id": info.get("leader_id"),
        "born_tick": info.get("born_tick"),
        "population": len(members),
        "house": main_house,
        "houses": clan_houses,
        "main_house_id": main_house["id"] if main_house else None,
        "war_wins": wins,
        "war_losses": losses,
        "territory_radius": RT.sim.config.territory_radius if RT.sim.config.territory_enabled else None,
        "specialization": info.get("specialization"),
        "culture": info.get("culture"),
        "members": members,
        "events": [e.model_dump(mode="json") for e in clan_events],
        "history": info.get("history", []),
        "coalition_id": info.get("coalition_id"),  # §AB
        "larder": round(float(info.get("larder", 0.0)), 1),  # §AB clan store
        "tribute_to": info.get("tribute_to"),  # §AB subjugation
        "faith": round(float(info.get("faith", 0.0)), 1),  # §AP clan faith pool
        "shrine_level": int(info.get("shrine_level", 0)),  # §AP shrine/temple
        "governance": info.get("governance", "republic"),  # §AL
        "bylaws": info.get("bylaws", {}),  # §AL
        "task_board": info.get("task_board", {}),  # §AL
    }



@app.get("/api/clans")
async def get_clans() -> dict:
    """Clan roster with lineage, territory and war record."""
    with RT.lock:
        return _clans_payload()


def _clans_payload() -> dict:
    # live clan dict + live population + house territory + war history
    # N150: limit to top 100 alive clans to avoid 1.5MB/5s at 4000 clans
    war_wins: dict[int, int] = {}
    war_losses: dict[int, int] = {}
    for e in RT.sim.history:
        if e.type == "war":
            a = int(e.payload.get("a", 0) or 0)
            b = int(e.payload.get("b", 0) or 0)
            if b:
                war_wins[b] = war_wins.get(b, 0) + 1
            if a:
                war_losses[a] = war_losses.get(a, 0) + 1
    # houses by clan
    houses_by_clan: dict[int, dict] = {}
    for ent in RT.sim.world.entities.values():
        if ent.kind == "house" and getattr(ent, "clan_id", 0):
            houses_by_clan[ent.clan_id] = {"x": ent.x, "y": ent.y, "size": getattr(ent, "size", 0), "is_ruin": getattr(ent, "is_ruin", False)}
    # single pass for population count across all clans
    pop_by_clan: dict[int, int] = {}
    for c in RT.sim._get_creatures():
        if c.clan_id:
            pop_by_clan[c.clan_id] = pop_by_clan.get(c.clan_id, 0) + 1
    # §X clan memory — only for top 50 alive clans to avoid 4000× overhead
    alive_cids = [cid for cid, pop in pop_by_clan.items() if pop > 0]
    alive_cids.sort(key=lambda cid: -pop_by_clan.get(cid, 0))
    top_cids = set(alive_cids[:50])
    knowledge_by_clan = {}
    if RT.sim.config.knowledge_enabled and top_cids:
        # compute only for top 50, not all 4000
        all_know = RT.sim.clan_knowledge()
        knowledge_by_clan = {cid: all_know.get(cid) for cid in top_cids if cid in all_know}
    clans = []
    for cid, info in RT.sim.clans.items():
        pop = pop_by_clan.get(cid, 0)
        if pop == 0:
            continue  # skip ghost clans (exile/schism remnants) — saves 1.5MB
        if cid not in top_cids and len(clans) >= 100:
            continue
        house = houses_by_clan.get(cid)
        clans.append({
            "id": cid,
            "name": info.get("name"),
            "color": info.get("color"),
            "totem": info.get("totem"),
            "founder_id": info.get("founder_id"),
            "leader_id": info.get("leader_id"),
            "born_tick": info.get("born_tick"),
            "population": pop,
            "house": house,
            "war_wins": war_wins.get(cid, 0),
            "war_losses": war_losses.get(cid, 0),
            "territory_radius": RT.sim.config.territory_radius if RT.sim.config.territory_enabled else None,
            "specialization": info.get("specialization"),
            "culture": info.get("culture"),
            "culture_id": info.get("culture_id"),
            "knowledge": knowledge_by_clan.get(cid),
            "coalition_id": info.get("coalition_id"),  # §AB
            "larder": round(float(info.get("larder", 0.0)), 1),  # §AB clan store
            "tribute_to": info.get("tribute_to"),  # §AB subjugation
            "faith": round(float(info.get("faith", 0.0)), 1),  # §AP clan faith pool
            "shrine_level": int(info.get("shrine_level", 0)),  # §AP shrine/temple
            "governance": info.get("governance", "republic"),  # §AL
            "bylaws": info.get("bylaws", {}),  # §AL
            "task_board": info.get("task_board", {}),  # §AL
        })

    # sort by population desc and cap at 100
    clans.sort(key=lambda c: (-c["population"], c["id"]))
    clans = clans[:100]
    return {"clans": clans, "tick": RT.sim.tick}

@app.get("/api/plots")
async def get_plots() -> dict:
    """Upcoming war/schism as progress — god's foreshadowing."""
    with RT.lock:
        return {"plots": RT.sim.get_plots(), "tick": RT.sim.tick}


def _kin_card(entity_id: int) -> dict:

    """Dossier card for a family-tree node (alive creatures preferred)."""
    seed = RT.sim.config.seed if hasattr(RT.sim, "config") else RT.config.seed
    ent = RT.sim.world.entities.get(entity_id)
    if ent is not None and isinstance(ent, Creature):
        v = variation_for(entity_id, seed)
        return {
            "id": entity_id,
            "caste": ent.caste,
            "alive": True,
            "clan_color": RT.sim.clans.get(ent.clan_id, {}).get("color"),
            "personal_name": personal_name_for(entity_id, seed, ent.generation),
            "glyph": glyph_for(entity_id, seed, ent.generation),
            "hue_shift": v["hue_shift"],
            "scale_jitter": v["scale_jitter"],
            "angle_jitter": v["angle_jitter"],
        }
    # dead or archived — compute deterministic name via genealogy generation if available
    # try DB to get generation
    gen = 0
    if RT.world_id is not None:
        try:
            # quick lookup: genealogy_parents gives child's generation via creatures table
            for tbl in ("creatures",):
                pass
        except Exception:
            pass
    # fallback deterministic with gen 0 (still unique)
    v = variation_for(entity_id, seed)
    return {
        "id": entity_id,
        "caste": None,
        "alive": False,
        "clan_color": None,
        "personal_name": personal_name_for(entity_id, seed, gen),
        "glyph": glyph_for(entity_id, seed, gen),
        "hue_shift": v["hue_shift"],
        "scale_jitter": v["scale_jitter"],
        "angle_jitter": v["angle_jitter"],
    }


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
    DB.flush()  # AD: genealogy + chronicle must include the RAM tail
    with RT.lock:
        return _creature_dossier(creature_id)


def _creature_dossier(creature_id: int) -> dict:
    ent = RT.sim.world.entities.get(creature_id)
    if ent is not None:
        entity = RT.sim._entity_payload(ent)
    elif RT.world_id is not None:
        # deceased: synthesize minimal dossier from genealogy so name/glyph still show
        try:
            row = DB._require().execute(
                "SELECT caste, clan_id, generation, born_tick FROM creatures WHERE world_id=? AND entity_id=?",
                (RT.world_id, creature_id),
            ).fetchone()
        except Exception:
            row = None
        if row is not None:
            gen = int(row["generation"] or 0)
            clan_id = int(row["clan_id"] or 0)
            v = variation_for(creature_id, RT.sim.config.seed)
            entity = {
                "id": creature_id,
                "kind": "creature",
                "x": 0.0,
                "y": 0.0,
                "angle": 0.0,
                "caste": row["caste"],
                "clan_id": clan_id or None,
                "clan_color": RT.sim.clans.get(clan_id, {}).get("color") if clan_id else None,
                "clan_name": RT.sim.clans.get(clan_id, {}).get("name") if clan_id else None,
                "clan_totem": RT.sim.clans.get(clan_id, {}).get("totem") if clan_id else None,
                "generation": gen,
                "born_tick": row["born_tick"],
                "personal_name": personal_name_for(creature_id, RT.sim.config.seed, gen),
                "glyph": glyph_for(creature_id, RT.sim.config.seed, gen),
                "hue_shift": v["hue_shift"],
                "scale_jitter": v["scale_jitter"],
                "angle_jitter": v["angle_jitter"],
                "sex": "female" if row["caste"] == "Woman" else "male" if row["caste"] else None,
            }
        else:
            entity = None
    else:
        entity = None
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
    with RT.lock:
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


@app.get("/wiki", response_class=HTMLResponse)
async def get_wiki():
    """Wiki — richer guide with presets, sustainability, playground."""
    from .wiki import build_wiki_html

    return HTMLResponse(build_wiki_html(app))


@app.get("/api/wiki")
async def get_wiki_json():
    """Structured wiki data for frontend Wiki.tsx."""
    from .wiki import get_wiki_json as _get

    return _get(app)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots_txt():
    """Robots.txt for SEO."""
    return PlainTextResponse(
        "User-agent: *\nAllow: /\nAllow: /wiki\nAllow: /guide\nAllow: /docs\n\nSitemap: https://world.minhnhan.in/sitemap.xml\n",
        media_type="text/plain",
    )


@app.get("/sitemap.xml", response_class=HTMLResponse)
async def get_sitemap_xml():
    """Sitemap.xml for SEO."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://world.minhnhan.in/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://world.minhnhan.in/wiki</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://world.minhnhan.in/guide</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://world.minhnhan.in/docs</loc>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
</urlset>"""
    return HTMLResponse(content=xml_content, media_type="application/xml")


@app.get("/docs/god-laws.md", response_class=PlainTextResponse)
async def get_god_laws_md():
    """Serve the markdown docs for god laws — used by wiki + GodPanel hints."""
    candidates = [
        Path("docs/god-laws.md"),
        Path("../docs/god-laws.md"),
        Path(__file__).resolve().parent.parent.parent / "docs" / "god-laws.md",
        Path(__file__).resolve().parent.parent / "public" / "docs" / "god-laws.md",
        Path("frontend/public/docs/god-laws.md"),
        Path("../frontend/public/docs/god-laws.md"),
    ]
    for p in candidates:
        try:
            if p.exists():
                return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")
        except Exception:
            continue
    raise HTTPException(404, "god-laws.md not found")


@app.post("/api/control", dependencies=[Depends(require_god)])
async def post_control(msg: ControlMessage) -> dict:
    return await apply_control(msg)
