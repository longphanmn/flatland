"""API tests: REST endpoints and WebSocket protocol (sim loop not running)."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import RT, app
from app.simulation import Simulation


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = Config.from_env()  # discard any laws set by earlier tests
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    yield


@pytest.fixture()
def client():
    # No context manager: lifespan (background tick loop) must NOT run here.
    return TestClient(app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


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


def test_websocket_hello_then_state_then_step(client):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert hello["width"] == RT.config.width

        state = ws.receive_json()
        assert state["type"] == "state"
        assert state["tick"] == 0

        ws.send_json({"action": "pause"})
        ws.send_json({"action": "step"})
        state2 = ws.receive_json()
        assert state2["tick"] == 1

        ws.send_json({"action": "reset"})
        state3 = ws.receive_json()
        assert state3["tick"] == 0
