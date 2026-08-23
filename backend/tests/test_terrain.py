"""Terrain tests: fertile patches bias food; rocks block movement."""

import math

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import Simulation


def terrain_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_terrain_generated_with_explicit_counts():
    s = Simulation(terrain_cfg(seed=1, fertile_patches=3, rock_count=2))
    assert len(s.fertile) == 3
    assert len(s.rocks) == 2
    for p in s.fertile + s.rocks:
        assert 0 <= p["x"] <= s.config.width and 0 <= p["y"] <= s.config.height


def test_auto_terrain_scales_with_area():
    small = Simulation(terrain_cfg(seed=2, width=100.0, height=100.0))
    big = Simulation(terrain_cfg(seed=2, width=400.0, height=400.0))
    assert len(big.fertile) >= len(small.fertile)
    assert len(big.rocks) >= len(small.rocks)


def test_food_prefers_fertile_ground():
    from dataclasses import replace

    # one huge patch covering most of a 100x100 world
    s = Simulation(
        terrain_cfg(seed=3, width=100.0, height=100.0, fertile_patches=1,
                    food_count=0)
    )
    s.fertile = [{"x": 50.0, "y": 50.0, "r": 45.0}]
    s.config = replace(s.config, food_count=40)
    s._enforce_food_law()
    foods = [e for e in s.world.entities.values() if e.kind == "food"]
    assert len(foods) == 40
    inside = sum(
        1
        for f in foods
        if math.hypot(f.x - 50.0, f.y - 50.0) <= 45.0
    )
    assert inside >= int(0.85 * 40)  # ~70% biased + most strays land inside anyway


def test_rocks_block_movement():
    s = Simulation(terrain_cfg(seed=4, width=60.0, height=60.0))
    s.rocks = [{"x": 30.0, "y": 30.0, "r": 5.0}]
    c = s.world.add(Creature(x=20.0, y=30.0, angle=0.0, speed=1.0, energy=100.0))
    for _ in range(10):
        s.step()
        d = s.world.distance(c.x, c.y, 30.0, 30.0)
        assert d >= 5.0 + c.radius - 0.05  # never inside the stone


def test_terrain_in_snapshot():
    s = Simulation(terrain_cfg(seed=5, fertile_patches=2, rock_count=1))
    snap = s.snapshot()
    assert len(snap.terrain_fertile) == 2
    assert len(snap.terrain_rocks) == 1
