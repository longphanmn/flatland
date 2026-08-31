"""Tests for Density-Dependent Soft-Cap Damping Engine and population stabilization."""

import pytest

from app.config import Config
from app.density_damping import compute_xi, scales_for_xi, DensityDampingEngine
from app.entities import Creature
from app.simulation import Simulation


def test_compute_xi():
    assert compute_xi(50, 100, enabled=True) == 0.0
    assert compute_xi(100, 100, enabled=True) == 0.0
    assert compute_xi(120, 100, enabled=True) == pytest.approx(0.20)
    assert compute_xi(150, 100, enabled=True) == pytest.approx(0.50)
    # Disabled or invalid Kcap
    assert compute_xi(150, 100, enabled=False) == 0.0
    assert compute_xi(150, -1, enabled=True) == 0.0
    assert compute_xi(150, 0, enabled=True) == 0.0


def test_scales_for_xi():
    cfg = Config(damping_steepness=6.0, crowding_stress_mult=0.35, resource_strain_mult=1.2)

    s0 = scales_for_xi(0.0, cfg)
    assert s0["birth_rate_eff"] == 1.0
    assert s0["birth_cost_eff"] == 1.0
    assert s0["cooldown_eff"] == 1.0
    assert s0["decay_eff"] == 1.0
    assert s0["growth_eff"] == 1.0

    # At xi = 0.10 (+10% overshoot), immediate suppression slope
    s1 = scales_for_xi(0.10, cfg)
    assert s1["birth_rate_eff"] < 0.70  # strong linear suppression
    assert s1["birth_cost_eff"] > 1.10
    assert s1["cooldown_eff"] > 1.30
    assert s1["decay_eff"] > 1.03

    # At xi = 0.50 (+50% overshoot), heavy suppression
    s5 = scales_for_xi(0.50, cfg)
    assert s5["birth_rate_eff"] < 0.10  # heavy suppression
    assert s5["decay_eff"] > 1.20
    assert s5["growth_eff"] < 0.70


def test_density_damping_engine():
    cfg = Config(carrying_capacity=100, soft_cap_enabled=True)
    engine = DensityDampingEngine(cfg)

    xi, scales = engine.update(120, 10)
    assert xi == pytest.approx(0.20)
    assert "birth_rate_eff" in scales
    assert engine.last_xi == xi


def test_reproduction_hard_ceiling():
    """Verify that births are completely halted at or above max_population."""
    cfg = Config(
        seed=42,
        width=50.0,
        height=50.0,
        birth_enabled=True,
        adult_age=0.0,
        mate_radius=10.0,
        mate_energy_min=10.0,
        birth_rate=1.0,
        carrying_capacity=20,
        max_population=20,
        soft_cap_enabled=True,
        num_triangles=0,
        num_squares=0,
        num_pentagons=0,
        num_hexagons=0,
        num_priests=0,
        num_women=0,
        food_count=0,
        num_houses=0,
    )
    sim = Simulation(cfg)

    # Spawn 10 males and 10 females = 20 creatures (at max_population)
    for i in range(10):
        sim.world.add(Creature(x=25.0 + i*0.1, y=25.0, energy=100.0, age=100, lifespan=5000))
        sim.world.add(Creature(x=25.0 + i*0.1, y=25.0, shape="line", sides=2, energy=100.0, age=100, lifespan=5000))

    assert len(sim.world.creatures()) == 20
    sim._reproduce()
    # No babies should be born because pop == max_pop
    assert len(sim.world.creatures()) == 20
