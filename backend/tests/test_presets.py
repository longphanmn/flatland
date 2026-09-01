"""Comprehensive and deep behavioral tests for world simulation presets on new world logic."""

import pytest
from dataclasses import replace
from fastapi.testclient import TestClient

from app.config import Config
from app.main import PRESETS, RT, app, detect_current_preset, start_world
from app.protocol import GodLaws
from app.simulation import Simulation


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = replace(Config.from_env(), age_enabled=False)
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()
    yield


@pytest.fixture()
def client():
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    return c


def test_all_presets_defined_and_valid():
    """Verify all curated presets are present, valid under GodLaws, and comprehensive."""
    expected_presets = {"balance", "sustainable", "chaos", "extinction", "boom", "theocracy", "warlords"}
    assert set(PRESETS.keys()) == expected_presets

    for name, p_laws in PRESETS.items():
        validated = GodLaws.model_validate(p_laws)
        dumped = validated.model_dump(exclude_unset=True)
        assert len(dumped) >= 50, f"Preset {name} should be comprehensively configured with all world laws"


def test_preset_application_and_detection(client):
    """Applying any preset should update config, persist it, and detect_current_preset should identify it."""
    for name in ["sustainable", "chaos", "extinction", "boom", "theocracy", "warlords", "balance"]:
        resp = client.post(f"/api/presets/{name}?persist=true&reset=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["preset"] == name
        assert data["reset"] is True
        assert detect_current_preset() == name


def test_preset_transition_hygiene(client):
    """Switching between extreme presets (Chaos -> Sustainable -> Boom -> Extinction -> Balance)
    must cleanly override all relevant laws without leaking settings from prior presets."""
    # 1. Apply Chaos
    client.post("/api/presets/chaos?persist=true&reset=true")
    assert RT.config.cannibalism_enabled is True
    assert RT.config.wildfire_enabled is True
    assert RT.config.earthquake_enabled is True
    assert RT.config.attack_damage == 60.0

    # 2. Transition to Sustainable
    client.post("/api/presets/sustainable?persist=true&reset=true")
    assert RT.config.cannibalism_enabled is False
    assert RT.config.wildfire_enabled is False
    assert RT.config.earthquake_enabled is False
    assert RT.config.attack_damage == 25.0
    assert RT.config.trespass_decay == 0.15

    # 3. Transition to Boom
    client.post("/api/presets/boom?persist=true&reset=true")
    assert RT.config.war_enabled is False
    assert RT.config.disease_enabled is False
    assert RT.config.predation_enabled is False
    assert RT.config.birth_rate == 0.18

    # 4. Transition to Extinction
    client.post("/api/presets/extinction?persist=true&reset=true")
    assert RT.config.food_count == 120
    assert RT.config.energy_decay_per_tick == 0.04
    assert RT.config.exposure_drain == 0.08
    assert RT.config.cannibalism_enabled is True

    # 5. Transition to Balance
    client.post("/api/presets/balance?persist=true&reset=true")
    assert RT.config.food_count == 380
    assert RT.config.carrying_capacity == 400
    assert RT.config.war_enabled is True
    assert RT.config.attack_damage == 30.0


def test_balance_deep_lifecycle(client):
    """Balance Goldilocks: multi-generational stability with active ecology and civilization."""
    resp = client.post("/api/presets/balance?persist=true&reset=true")
    assert resp.status_code == 200

    for _ in range(250):
        RT.sim.step()

    creatures = [e for e in RT.sim.world.entities.values() if getattr(e, "kind", "") == "creature"]
    assert len(creatures) > 50, "Balance world should sustain a thriving population"
    assert len(RT.sim.clans) > 0, "Clans should be active"


def test_sustainable_deep_peace_and_theology(client):
    """Sustainable preset: peace, agriculture, granary stores, faith, and high stability."""
    resp = client.post("/api/presets/sustainable?persist=true&reset=true")
    assert resp.status_code == 200

    for _ in range(250):
        RT.sim.step()

    creatures = [e for e in RT.sim.world.entities.values() if getattr(e, "kind", "") == "creature"]
    assert len(creatures) > 50, "Sustainable world should flourish"
    # Zero cannibalism deaths
    assert RT.sim._death_counts.get("cannibalism", 0) == 0


def test_chaos_deep_turmoil(client):
    """Chaos preset: high mortality, violent encounters, disease, and disaster potential."""
    resp = client.post("/api/presets/chaos?persist=true&reset=true")
    assert resp.status_code == 200

    for _ in range(250):
        RT.sim.step()

    # The world must withstand turmoil without crashing
    assert RT.sim.tick == 250


def test_extinction_deep_pressure(client):
    """Extinction preset: extreme famine pressure, high metabolic decay, and harsh mortality."""
    resp = client.post("/api/presets/extinction?persist=true&reset=true")
    assert resp.status_code == 200

    for _ in range(250):
        RT.sim.step()

    assert RT.sim.tick == 250
    # Starvation/exhaustion or exposure deaths should be recorded under severe conditions
    total_deaths = sum(RT.sim._death_counts.values())
    assert total_deaths > 0, "Extinction conditions should register death pressure"


def test_boom_deep_expansion(client):
    """Boom preset: rapid births, abundant resources, zero war/disease lead to rapid population expansion."""
    resp = client.post("/api/presets/boom?persist=true&reset=true")
    assert resp.status_code == 200

    initial_pop = len([e for e in RT.sim.world.entities.values() if getattr(e, "kind", "") == "creature"])

    for _ in range(250):
        RT.sim.step()

    final_pop = len([e for e in RT.sim.world.entities.values() if getattr(e, "kind", "") == "creature"])
    assert final_pop > initial_pop, "Boom world should experience rapid population growth"
    # Zero war or disease deaths
    assert RT.sim._death_counts.get("war", 0) == 0
    assert RT.sim._death_counts.get("disease", 0) == 0
    assert RT.sim._death_counts.get("predation", 0) == 0
