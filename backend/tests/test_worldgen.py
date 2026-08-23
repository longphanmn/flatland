"""World generation tests: density scaling, jitter, reset reseeding."""

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
    return TestClient(app)


def creature_count(s: Simulation) -> int:
    return len(s.world.creatures())


def test_auto_population_scales_with_map_area():
    small = Simulation(Config(seed=5, width=100.0, height=100.0))
    big = Simulation(Config(seed=5, width=200.0, height=200.0))
    # 4x the area -> roughly 4x the creatures (jitter aside)
    assert creature_count(big) >= 2 * max(1, creature_count(small))


def test_jitter_varies_worlds_across_seeds():
    totals = {
        creature_count(Simulation(Config(seed=seed))) for seed in (1, 2, 3, 4, 5)
    }
    assert len(totals) >= 3, f"expected variety across seeds, got {totals}"


def test_auto_counts_stay_within_variance_band():
    cfg = Config(seed=7)  # 200x200, creature_density 0.0013 => target 52 ±25%
    s = Simulation(cfg)
    n = creature_count(s)
    target = int(cfg.width * cfg.height * cfg.creature_density)
    assert target * 0.75 - 8 <= n <= target * 1.25 + 8  # band widened for share rounding


def test_explicit_overrides_beat_densities():
    s = Simulation(Config(seed=8, num_triangles=3, num_squares=0, num_priests=0))
    castes = [c.caste for c in s.world.creatures()]
    assert len(castes) == 3
    assert castes.count("Soldier") == 3


def test_pyramid_shape_fewer_priests_than_soldiers():
    for seed in range(4):
        s = Simulation(Config(seed=seed))
        castes = [c.caste for c in s.world.creatures()]
        assert castes.count("Priest") <= castes.count("Soldier")


def test_reset_rolls_a_fresh_seed(client):
    seed_before = RT.config.seed
    r = client.post("/api/control", json={"action": "reset"})
    assert r.status_code == 200
    state = client.get("/api/state").json()
    assert state["seed"] == RT.config.seed
    assert state["seed"] != seed_before or seed_before == 0  # fresh chance
    # the new world row records the new seed
    worlds = client.get("/api/worlds").json()["worlds"]
    assert worlds[0]["seed"] == state["seed"]


def test_same_seed_same_world_even_after_rescale():
    a = Simulation(Config(seed=123))
    b = Simulation(Config(seed=123))
    assert a.snapshot() == b.snapshot()
