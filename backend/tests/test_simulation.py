"""Simulation core tests: determinism, boundaries, population, doors, hunger."""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food, House
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


def test_house_wall_blocks_entry():
    s = Simulation(minimal_cfg(seed=1))
    h = s.world.add(House(x=20.0, y=20.0, size=8.0))
    # approach the east wall head-on from outside
    c = s.world.add(Creature(x=26.0, y=20.0, angle=math.pi, speed=1.5, energy=100.0))
    for _ in range(6):
        s.step()
    assert c.x >= h.x + h.size / 2 - 0.01  # never got inside


def test_creature_enters_house_through_door():
    s = Simulation(minimal_cfg(seed=2, wander_turn=0.02))
    h = s.world.add(House(x=30.0, y=30.0, size=10.0, door_width=4.0))
    # approach the south door from below, heading north
    c = s.world.add(Creature(x=30.0, y=39.0, angle=-math.pi / 2, speed=2.0, energy=100.0))
    for _ in range(5):
        s.step()
    assert abs(c.x - h.x) < h.size / 2
    assert abs(c.y - h.y) < h.size / 2  # inside via the door


def test_creature_exits_house_through_door():
    s = Simulation(minimal_cfg(seed=3, wander_turn=0.02))
    h = s.world.add(House(x=30.0, y=30.0, size=10.0, door_width=4.0))
    # start at the centre heading south, straight through the door
    c = s.world.add(Creature(x=30.0, y=30.0, angle=math.pi / 2, speed=2.0, energy=100.0))
    for _ in range(6):
        s.step()
    assert c.y > h.y + h.size / 2  # made it outside through the south door


def test_interior_creature_blocked_by_walls():
    s = Simulation(minimal_cfg(seed=4, wander_turn=0.02))
    h = s.world.add(House(x=30.0, y=30.0, size=10.0, door_width=4.0))
    # start at centre heading west: hits the west wall from the inside
    c = s.world.add(Creature(x=30.0, y=30.0, angle=math.pi, speed=1.0, energy=100.0))
    for _ in range(8):
        s.step()
        assert c.x >= h.x - h.size / 2 - 0.01  # stayed inside


def test_door_width_scales_with_largest_creature():
    small = Simulation(
        minimal_cfg(num_women=5, num_houses=3, house_min_size=8.0, house_max_size=8.0)
    )
    big = Simulation(
        minimal_cfg(num_priests=2, num_houses=3, house_min_size=8.0, house_max_size=8.0)
    )
    doors_small = [h.door_width for h in small.world.entities.values() if h.kind == "house"]
    doors_big = [h.door_width for h in big.world.entities.values() if h.kind == "house"]
    assert min(doors_big) > max(doors_small)


def test_hunger_status_stages():
    s = Simulation(minimal_cfg(seed=5))
    c = s.world.add(Creature(x=10.0, y=10.0, energy=90.0))
    s.step()
    assert c.status == ""
    c.energy = 34.0  # <= hungry_ratio (0.35 * 100)
    s.step()
    assert c.status == "hungry"
    c.energy = 14.0  # <= starving_ratio (0.15 * 100)
    s.step()
    assert c.status == "starving"


def test_starving_creature_finds_food_beyond_normal_range():
    s = Simulation(minimal_cfg(width=60, height=60, seed=6))
    food = s.world.add(Food(x=48.0, y=30.0))  # 18 away: > perceive 12, < 12*1.6
    c = s.world.add(Creature(x=30.0, y=30.0, angle=0.0, speed=0.85, energy=10.0))
    s.step()
    assert c.status == "starving"
    for _ in range(40):
        s.step()
    assert food.id not in s.world.entities  # found and eaten
    assert c.energy > 20.0


def test_ticks_since_meal_resets_on_eating():
    s = Simulation(minimal_cfg(width=40, height=40, seed=7, num_food=1))
    food = next(e for e in s.world.entities.values() if e.kind == "food")
    c = s.world.add(Creature(x=(food.x + 0.1) % 40, y=food.y, energy=50.0))
    s.step()
    assert c.ticks_since_meal == 0
    assert c.meals == 1
    s.step()
    assert c.ticks_since_meal == 1


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
