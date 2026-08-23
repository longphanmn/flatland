"""API tests: REST endpoints and WebSocket protocol (sim loop not running)."""

import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import DB, RT, SimEngine, RuntimeState, app, start_world
from app.simulation import Simulation


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = Config.from_env()  # discard any laws set by earlier tests
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()  # fresh DB world row per test
    yield


@pytest.fixture()
def client():
    # No context manager: lifespan (background tick loop) must NOT run here.
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    return c


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "tick" in body and "paused" in body


def test_get_config(client):
    cfg = client.get("/api/config").json()
    assert cfg["width"] > 0
    assert cfg["boundary"] in ("wrap", "clamp")
    assert "seed" in cfg


def test_state_and_control_flow(client):
    st = client.get("/api/state").json()
    assert st["type"] == "state"
    assert st["tick"] == 0

    r = client.post("/api/control", json={"action": "pause"})
    assert r.json()["paused"] is True

    r = client.post("/api/control", json={"action": "step"})
    assert r.json()["tick"] == 1

    r = client.post("/api/control", json={"action": "set_speed", "value": 25})
    assert r.json()["speed"] == 25

    r = client.post("/api/control", json={"action": "reset"})
    assert r.json()["tick"] == 0

    st = client.get("/api/state").json()
    assert st["tick"] == 0


def test_sim_engine_ticks_on_its_own_thread_and_lock_guards_reads():
    """The threaded engine advances the world while readers stay consistent."""
    rt = RuntimeState(Config(seed=5, num_houses=2))
    hub = __import__("app.main", fromlist=["Hub"]).Hub()
    engine = SimEngine(rt, hub)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        engine.start(loop=loop)
        deadline = time.monotonic() + 5.0
        while rt.sim.tick < 5 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert rt.sim.tick >= 5

        # a reader holding the lock sees an integral snapshot
        with rt.lock:
            snap = rt.sim.snapshot()
        assert snap.tick == rt.sim.tick

        # pause is honoured by the engine thread
        rt.paused = True
        frozen = rt.sim.tick
        time.sleep(0.2)
        assert rt.sim.tick == frozen
        rt.paused = False
    finally:
        engine.stop()
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=1)


def test_websocket_hello_then_state_then_step(client):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["width"] == RT.config.width

        state = ws.receive_json()
        assert state["type"] == "state"
        assert state["tick"] == 0

        ws.send_json({"action": "pause", "key": "test-key"})
        ws.send_json({"action": "step", "key": "test-key"})
        state2 = ws.receive_json()
        assert state2["tick"] == 1

        ws.send_json({"action": "reset", "key": "test-key"})
        state3 = ws.receive_json()
        assert state3["tick"] == 0


def test_presets_list_and_apply_all(client):
    """Verify all presets are exposed and can be applied cleanly."""
    r = client.get("/api/presets")
    assert r.status_code == 200
    presets = r.json()["presets"]
    assert "sustainable" in presets
    assert "chaos" in presets
    assert "extinction" in presets
    assert "boom" in presets

    for name in presets:
        resp = client.post(f"/api/presets/{name}?reset=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == name
        assert data["reset"] is True
        assert RT.sim.tick == 0

