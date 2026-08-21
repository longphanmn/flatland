"""Simulation core tests: determinism, boundaries, population, behaviour."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def minimal_cfg(**kw) -> Config:
    """Config with an empty world; tests spawn entities explicitly."""
    base = dict(
        num_triangles=0,
        num_squares=0,
        num_pentagons=0,
        num_hexagons=0,
        num_priests=0,
        num_women=0,
        num_food=0,
        num_houses=0,
    )
    base.update(kw)
    return Config(**base)


def test_determinism_same_seed():
    a = Simulation(Config(seed=123))
    b = Simulation(Config(seed=123))
    for _ in range(120):
        a.step()
        b.step()
    assert a.snapshot() == b.snapshot()


def test_different_seed_diverges():
    a = Simulation(Config(seed=1))
    b = Simulation(Config(seed=2))
    for _ in range(50):
        a.step()
        b.step()
    assert a.snapshot() != b.snapshot()


def test_initial_population_counts():
    cfg = Config(
        seed=5,
        num_triangles=3,
        num_squares=2,
        num_pentagons=1,
        num_hexagons=1,
        num_priests=1,
        num_women=2,
        num_food=9,
        num_houses=3,
    )
    snap = Simulation(cfg).snapshot()
    kinds = [e.kind for e in snap.entities]
    assert kinds.count("creature") == 10
    assert kinds.count("food") == 9
    assert kinds.count("house") == 3
    assert snap.population["Soldier"] == 3
    assert snap.population["Gentleman"] == 2
    assert snap.population["Professional"] == 1
    assert snap.population["Noble"] == 1
    assert snap.population["Priest"] == 1
    assert snap.population["Woman"] == 2


def test_wrap_boundary():
    s = Simulation(minimal_cfg(width=50, height=50, seed=1))
    c = s.world.add(Creature(x=49.7, y=25.0, angle=0.0, speed=0.8, energy=100.0))
    s.step()
    assert 0.0 <= c.x < 50.0
    assert c.x < 2.0  # wrapped past the east edge


def test_clamp_boundary_reflects_heading():
    s = Simulation(minimal_cfg(width=50, height=50, boundary="clamp", seed=1))
    c = s.world.add(Creature(x=49.8, y=25.0, angle=0.05, speed=0.8, energy=100.0))
    s.step()
    assert c.x <= 50.0
    assert abs(c.angle) > 3.0  # reflected: now heading west-ish


def test_starvation_removes_creature():
    s = Simulation(minimal_cfg(seed=1))
    c = s.world.add(Creature(x=10, y=10, energy=0.01))
    s.step()
    assert c.id not in s.world.entities


def test_eating_increases_energy_and_replenishes_food():
    s = Simulation(minimal_cfg(width=40, height=40, seed=3, num_food=1))
    food = next(e for e in s.world.entities.values() if e.kind == "food")
    c = s.world.add(Creature(x=(food.x + 0.1) % 40, y=food.y, energy=50.0))
    s.step()
    assert c.energy > 70.0  # 50 - decay + food gain
    foods = [e for e in s.world.entities.values() if e.kind == "food"]
    assert len(foods) == 1  # consumed one, replenished one


def test_house_blocks_movement():
    s = Simulation(minimal_cfg(seed=1))
    h = s.world.add(House(x=20.0, y=20.0, size=6.0))
    c = s.world.add(Creature(x=20.0, y=20.0, angle=0.0, speed=1.0, energy=100.0))
    s.step()
    d = s.world.distance(c.x, c.y, h.x, h.y)
    assert d >= h.size / 2 - 0.01
    assert c.id in s.world.entities


def test_food_count_stable_over_many_ticks():
    s = Simulation(Config(seed=9, width=60, height=60))
    for _ in range(30):
        s.step()
    foods = [e for e in s.world.entities.values() if e.kind == "food"]
    assert len(foods) == 24


def test_snapshot_roundtrip_via_protocol():
    s = Simulation(Config(seed=11))
    snap = s.snapshot()
    dumped = snap.model_dump(mode="json")
    assert dumped["type"] == "state"
    assert dumped["tick"] == s.tick
    assert len(dumped["entities"]) == 20 + 24 + 6
