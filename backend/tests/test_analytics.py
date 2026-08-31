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
