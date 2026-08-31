"""Tests verifying neural network raycast perception, foraging inductive bias, and creature food gathering."""

import math
import pytest
from app.config import Config
from app.entities import Creature, Food
from app.simulation import Simulation
from app.agent_soa import AgentSoA
from app.evolution import init_genomes
from app.agent_pipeline import build_inputs_batch, _raycast_world
from app.neural_engine import forward_batch


def test_raycast_world_detects_food():
    """Verify _raycast_world detects food placed along the ray path."""
    cfg = Config(width=100.0, height=100.0, food_count=1)
    sim = Simulation(cfg)
    sim.world.entities.clear()
    f = Food(x=50.0, y=40.0, variant="berry", growth=1.0, cultivated=True)
    sim.world.add(f)
    sim.world.rebuild_index()

    dist, typ = _raycast_world(sim.world, (50.0, 50.0), -math.pi / 2, max_dist=32.0)
    assert typ == "food"
    assert dist == pytest.approx(10.0, abs=1.0)


def test_inductive_genome_produces_forward_drive():
    """Verify initial genomes produce forward thrust."""
    soa = AgentSoA(capacity=4)
    soa.add_agent(1, 50.0, 50.0, angle=0.0, energy=20.0, health=100.0)
    init_genomes(soa, scale=0.0)

    inputs = build_inputs_batch(soa)
    out, _ = forward_batch(inputs, soa.genomes[:1] if getattr(soa, "HAS_NUMPY", True) else [soa.genomes[0]])
    thrust = float(out[0, 0] if hasattr(out, "shape") else out[0][0])
    assert thrust > 0.5, "Hungry creature should have strong baseline forward thrust"


def test_creature_forages_and_eats_nearby_food():
    """Verify that a hungry creature with food nearby approaches, eats, and restores energy."""
    cfg = Config(width=100.0, height=100.0, food_count=1, birth_enabled=False)
    sim = Simulation(cfg)
    sim.world.entities.clear()

    # Place a hungry creature at (50, 50) with energy 30
    c = Creature(x=50.0, y=50.0, energy=30.0, health=100.0, angle=0.0)
    sim.world.add(c)

    # Place mature berry food 6 units away at (56, 50)
    f = Food(x=56.0, y=50.0, variant="berry", growth=1.0, cultivated=True)
    sim.world.add(f)

    # Step simulation 20 ticks
    for _ in range(20):
        sim.step()

    # Creature should have eaten the food and gained energy
    assert c.energy > 50.0, f"Creature should have consumed food and increased energy (got {c.energy})"
