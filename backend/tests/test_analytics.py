"""Unit tests for BD Analytics & Mutation Tracking."""
import pytest
from app.config import Config
from app.entities import Creature
from app.simulation import Simulation
from app.analytics import AnalyticsEngine, TelemetryRing, attach_to_sim

def test_telemetry_ring_mutation_buffers():
    cfg = Config(seed=42, num_triangles=2, num_squares=2, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    ring = TelemetryRing(maxlen=100)
    ring.push(1, sim)
    snap = ring.snapshot()
    assert "mutation_freq" in snap
    assert "avg_irregularity" in snap
    assert "max_generation" in snap
    assert "morph_lambda" in snap
    assert len(snap["mutation_freq"]) == 1

def test_generational_tracker_top_mutants_and_abbott():
    cfg = Config(seed=42, num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    c1 = sim.world.add(Creature(x=10, y=10, sides=3, irregularity=0.45, generation=2))
    c2 = sim.world.add(Creature(x=20, y=20, sides=5, irregularity=0.82, generation=3))
    c3 = sim.world.add(Creature(x=30, y=30, sides=4, irregularity=0.0, generation=1))
    
    eng = attach_to_sim(sim)
    eng.on_tick(sim)
    summary = eng.summary(sim)
    gen = summary["generational"]
    
    assert gen["mutation_freq"] == pytest.approx(2 / 3, 0.01)
    assert gen["max_generation"] == 3
    assert len(gen["top_mutants"]) == 2
    assert gen["top_mutants"][0]["id"] == c2.id
    assert gen["top_mutants"][0]["irregularity"] == 0.82
    assert gen["top_mutants"][1]["id"] == c1.id
    assert 3 in gen["abbott_ladder"]
    assert 5 in gen["abbott_ladder"]
    assert 4 in gen["abbott_ladder"]

def test_on_mutation_record():
    cfg = Config(seed=42, num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    c = sim.world.add(Creature(x=10, y=10, sides=7, irregularity=0.35, generation=4))
    eng = attach_to_sim(sim)
    eng.on_mutation(100, c, {"clan_name": "Test Clan", "clan_color": "#ff0000", "type": "asymmetry", "desc": "Gen 4 mutant"})
    
    summary = eng.summary(sim)
    muts = summary["generational"]["recent_mutations"]
    assert len(muts) == 1
    assert muts[0]["creature_id"] == c.id
    assert muts[0]["irregularity"] == 0.35
    assert muts[0]["generation"] == 4
    assert muts[0]["clan_name"] == "Test Clan"


def test_birth_velocity_and_death_velocity_rolling():
    cfg = Config(seed=42, num_triangles=2, num_squares=2, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    ring = TelemetryRing(maxlen=1000, window_ticks=600)

    # Initial tick
    sim.tick = 0
    sim.births = 0
    sim.deaths = 0
    ring.push(0, sim)
    assert ring.birth_velocity[-1] == 0.0
    assert ring.death_velocity[-1] == 0.0

    # Advance 600 ticks, with 6 births and 3 deaths distributed
    for t in range(1, 601):
        sim.tick = t
        if t % 100 == 0:
            sim.births += 1
        if t % 200 == 0:
            sim.deaths += 1
        ring.push(t, sim)

    # At tick 600: exactly 6 births in 600 ticks -> 6.0 births/min; 3 deaths -> 3.0 deaths/min
    assert ring.birth_velocity[-1] == pytest.approx(6.0, 0.01)
    assert ring.death_velocity[-1] == pytest.approx(3.0, 0.01)


def test_single_death_does_not_spike_to_600():
    cfg = Config(seed=42, num_triangles=2, num_squares=2, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    ring = TelemetryRing(maxlen=1000, window_ticks=600)

    # Run for 600 ticks with 0 events
    for t in range(600):
        sim.tick = t
        ring.push(t, sim)

    assert ring.death_velocity[-1] == 0.0

    # 1 single death occurs at tick 600
    sim.tick = 600
    sim.deaths = 1
    ring.push(600, sim)

    # Over the 600-tick window, 1 death = 1.0 death/min (NOT 600.0!)
    assert ring.death_velocity[-1] == pytest.approx(1.0, 0.01)


def test_simulation_birth_counter_and_velocity():
    cfg = Config(seed=42, num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    assert hasattr(sim, "births")
    assert sim.births == 0

    mother = sim.world.add(Creature(x=10, y=10, shape="line", sides=2, energy=50, clan_id=0))
    father = sim.world.add(Creature(x=10, y=10, shape="polygon", sides=3, energy=50, clan_id=0))

    sim.step()
    sim._birth(mother, father)
    sim.step()

    assert sim.births == 1
    assert getattr(sim, "_births", 0) == 1

    eng = attach_to_sim(sim)
    summary = eng.summary(sim)
    ring = summary["ring"]

    assert len(ring["birth_velocity"]) > 0
    # Velocity should be positive and non-zero after birth
    assert ring["birth_velocity"][-1] > 0.0


def test_telemetry_ring_resets_on_rewind():
    cfg = Config(seed=42, num_triangles=2, num_squares=0, num_pentagons=0, num_hexagons=0, food_count=0)
    sim = Simulation(cfg)
    ring = TelemetryRing(maxlen=1000, window_ticks=600)

    sim.tick = 500
    sim.births = 10
    sim.deaths = 5
    ring.push(500, sim)

    # Rewind tick and counters to simulate reset / snapshot load
    sim.tick = 10
    sim.births = 0
    sim.deaths = 0
    ring.push(10, sim)

    assert ring.birth_velocity[-1] == 0.0
    assert ring.death_velocity[-1] == 0.0

