"""Performance & scale tests: spatial indexing, mate discovery, snapshot caching."""

import math
import time
import pytest

from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import Simulation
from app.world import World


def perf_cfg(**kw) -> Config:
    base = dict(
        seed=42,
        width=200.0,
        height=200.0,
        birth_enabled=True,
        adult_age=0.0,
        mate_radius=12.0,
        mate_energy_min=10.0,
        birth_rate=1.0,
        num_triangles=0,
        num_squares=0,
        num_pentagons=0,
        num_hexagons=0,
        num_priests=0,
        num_women=0,
        food_count=0,
        num_houses=0,
    )
    base.update(kw)
    return Config(**base)


def test_spatial_hash_preallocated_buckets_integrity():
    """Verify that World._buckets accurately partitions entities without dict tuple overhead."""
    cfg = perf_cfg(width=100.0, height=100.0)
    world = World(cfg)
    assert len(world._buckets) == world.cols * world.rows

    # Add entities in various quadrants
    c1 = world.add(Creature(x=5.0, y=5.0))
    c2 = world.add(Creature(x=95.0, y=95.0))
    c3 = world.add(Creature(x=50.0, y=50.0))

    world.rebuild_index()

    # Query near c1
    near_c1 = list(world.query_radius(5.0, 5.0, 10.0))
    assert c1 in near_c1
    assert c3 not in near_c1

    # Query with wrap-around across the edge (5.0, 5.0 to 95.0, 95.0 wrap distance is hypot(10, 10) ≈ 14.14)
    near_wrap = list(world.query_radius(5.0, 5.0, 15.0))
    assert c1 in near_wrap
    assert c2 in near_wrap


def test_spatial_hash_clamp_boundary_integrity():
    """Verify clamp boundary spatial partitioning."""
    cfg = perf_cfg(width=100.0, height=100.0, boundary="clamp")
    world = World(cfg)
    c1 = world.add(Creature(x=5.0, y=5.0))
    c2 = world.add(Creature(x=95.0, y=95.0))
    world.rebuild_index()

    # In clamp mode, 5,5 and 95,95 are distance ~127.28 apart (no wrap)
    near = list(world.query_radius(5.0, 5.0, 20.0))
    assert c1 in near
    assert c2 not in near


def test_reproduce_spatial_candidate_discovery():
    """Verify that spatial index-based mate discovery pairs close partners and produces offspring."""
    s = Simulation(perf_cfg(width=100.0, height=100.0, birth_rate=1.0, sex_ratio=1.0))
    father = s.world.add(Creature(x=20.0, y=20.0, shape="polygon", sides=4, energy=100.0, age=500, lifespan=1000))
    mother = s.world.add(Creature(x=22.0, y=20.0, shape="line", sides=2, energy=100.0, age=500, lifespan=1000))
    # A distant male outside mate_radius (12.0)
    distant_male = s.world.add(Creature(x=70.0, y=70.0, shape="polygon", sides=4, energy=100.0, age=500, lifespan=1000))

    s.world.rebuild_index()
    s._reproduce()

    children = [c for c in s.world.creatures() if c.generation == 1]
    assert len(children) == 1
    assert children[0].mother_id == mother.id
    assert children[0].father_id == father.id
    assert children[0].father_id != distant_male.id


def test_snapshot_terrain_caching():
    """Verify that static terrain is cached and correctly surfaced in snapshot payloads."""
    s = Simulation(perf_cfg(fertile_patches=2, rock_count=2))
    payload1 = s.snapshot_payload()
    payload2 = s.snapshot_payload()

    assert len(payload1["terrain_fertile"]) == 2
    assert len(payload1["terrain_rocks"]) == 2
    # Ensure they point to identical cached lists without re-allocating
    assert payload1["terrain_fertile"] is payload2["terrain_fertile"]
    assert payload1["terrain_rocks"] is payload2["terrain_rocks"]


def test_large_population_scale_throughput():
    """Benchmark high-population scale: 1000+ inhabitants step fast and deterministic."""
    cfg = perf_cfg(
        width=400.0,
        height=300.0,
        num_triangles=-1,
        num_squares=-1,
        num_pentagons=-1,
        num_hexagons=-1,
        num_priests=-1,
        num_women=-1,
        creature_density=0.01,  # ~1200 creatures
        carrying_capacity=2000,
        max_population=2500,
    )
    s = Simulation(cfg)
    initial_pop = len(s.world.creatures())
    assert initial_pop >= 500

    # Step simulation 10 times and verify smooth performance
    t0 = time.perf_counter()
    for _ in range(10):
        s.step()
    elapsed = time.perf_counter() - t0

    # 10 steps for 500-1000+ creatures must execute cleanly and fast
    assert elapsed < 3.5
    assert s.tick == 10
