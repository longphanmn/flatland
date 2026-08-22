"""God screen tests: god sets laws of nature, never touches individual creatures."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import RT, app, start_world
from app.simulation import Simulation


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = Config.from_env()
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()
    yield


@pytest.fixture()
def client():
    # No context manager: lifespan (background tick loop) must NOT run here.
    return TestClient(app)


def test_get_laws_returns_current(client):
    laws = client.get("/api/laws").json()
    assert laws["food_count"] == Config().food_count
    assert laws["boundary"] == "wrap"
    assert laws["energy_decay_per_tick"] == pytest.approx(Config().energy_decay_per_tick)


def test_god_declares_famine_and_world_follows(client):
    r = client.post("/api/laws", json={"food_count": 5})
    assert r.status_code == 200
    assert r.json()["food_count"] == 5

    client.post("/api/control", json={"action": "step"})
    state = client.get("/api/state").json()
    foods = [e for e in state["entities"] if e["kind"] == "food"]
    assert len(foods) == 5


def test_god_declares_bounty_and_world_follows(client):
    client.post("/api/laws", json={"food_count": 60})
    client.post("/api/control", json={"action": "step"})
    state = client.get("/api/state").json()
    foods = [e for e in state["entities"] if e["kind"] == "food"]
    assert len(foods) == 60


def test_laws_survive_reset(client):
    client.post("/api/laws", json={"perceive_radius": 30.0})
    client.post("/api/control", json={"action": "reset"})
    assert client.get("/api/laws").json()["perceive_radius"] == 30.0
    assert client.get("/api/config").json()["perceive_radius"] == 30.0


def test_invalid_law_rejected(client):
    r = client.post("/api/laws", json={"energy_decay_per_tick": 99})
    assert r.status_code == 422
    # world unchanged
    assert client.get("/api/laws").json()["energy_decay_per_tick"] == pytest.approx(Config().energy_decay_per_tick)


def test_starving_ratio_above_hungry_rejected(client):
    r = client.post("/api/laws", json={"starving_ratio": 0.9, "hungry_ratio": 0.2})
    assert r.status_code == 422


def test_house_max_below_min_rejected(client):
    r = client.post("/api/laws", json={"house_min_size": 10.0, "house_max_size": 5.0})
    assert r.status_code == 422


def test_boundary_law_applies_live(client):
    client.post("/api/laws", json={"boundary": "clamp"})
    assert client.get("/api/config").json()["boundary"] == "clamp"


def test_partial_law_update_keeps_other_laws(client):
    before = client.get("/api/laws").json()
    client.post("/api/laws", json={"eat_radius": 2.5})
    after = client.get("/api/laws").json()
    assert after["eat_radius"] == pytest.approx(2.5)
    for key in ("food_count", "energy_max", "wander_turn"):
        assert after[key] == before[key]


def test_lifespan_mult_law_scales_new_creatures(client):
    client.post("/api/laws", json={"lifespan_mult": 0.5})
    client.post("/api/control", json={"action": "reset"})
    state = client.get("/api/state").json()
    lifespans = {e["lifespan"] for e in state["entities"] if e["kind"] == "creature"}
    # CASTE_LIFESPAN × 0.5 for every caste present in the initial population
    assert lifespans == {2400.0, 2700.0, 3000.0, 3300.0, 3600.0, 4500.0}


def test_deaths_appear_in_history_api(client):
    # famine + fast decay: starvation is inevitable under these laws
    client.post("/api/laws", json={"food_count": 0, "energy_decay_per_tick": 2.0})
    for _ in range(45):
        client.post("/api/control", json={"action": "step"})
    hist = client.get("/api/history").json()
    assert hist["total_deaths"] >= 1
    assert len(hist["events"]) >= 1
    ev = hist["events"][-1]
    assert ev["cause"] == "starvation"
    assert ev["type"] == "death"
    assert {"tick", "caste", "x", "y"} <= set(ev)
