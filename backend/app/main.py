"""FastAPI application: WebSocket state broadcast + control, REST helpers."""

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config import Config
from .protocol import ControlAction, ControlMessage, HelloMessage, StateMessage
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


CONFIG = Config.from_env()
RT = RuntimeState(CONFIG)
HUB = Hub()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(tick_loop(RT, HUB))
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


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
        RT.sim = Simulation(RT.config)
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
        width=CONFIG.width,
        height=CONFIG.height,
        boundary=CONFIG.boundary,
    ).model_dump(mode="json")


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
    return asdict(CONFIG)


@app.get("/api/state", response_model=StateMessage)
async def get_state() -> StateMessage:
    return RT.sim.snapshot()


@app.post("/api/control")
async def post_control(msg: ControlMessage) -> dict:
    return await apply_control(msg)
