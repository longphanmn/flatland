"""§AQ PH-0 — foundational axioms: sunlight is the only income, every body
pays upkeep by its geometric complexity, and mending costs energy."""

import pytest

from app.config import Config
from app.entities import Creature, Food
from app.simulation import (
    HEALING_ENERGY_COST,
    METABOLIC_COST,
    Simulation,
)


def physics_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=1000,
        season_length=100000,
        weather_change_rate=0.0,
        weather_enabled=False,
        shelter_enabled=False,
        disease_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        schism_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def noon_step(s: Simulation) -> None:
    dl = max(1, s.config.day_length)
    s.tick = (s.tick // dl) * dl + dl // 4  # world starts at sunrise
    s.step()


def night_step(s: Simulation) -> None:
    dl = max(1, s.config.day_length)
    s.tick = (s.tick // dl) * dl + 3 * dl // 4  # midnight
    s.step()


def test_sun_factor_curve():
    s = Simulation(physics_cfg())
    assert s._sun_factor() >= 0.0
    dl = 1000
    s.tick = dl // 4          # noon (world starts at sunrise)
    assert s._sun_factor() == pytest.approx(1.0)
    s.tick = 3 * dl // 4      # midnight
    assert s._sun_factor() == 0.0
    s.tick = dl // 2          # sunset edge (tod 0.75)
    assert 0.0 < s._sun_factor() < 1.0


def test_plants_grow_in_sun_and_starve_in_the_dark():
    """No free energy at night: the same sprout grows fast at noon, not at all
    at midnight."""
    def growth_over(steps, phase) -> float:
        s = Simulation(physics_cfg(seed=3, plant_growth_rate=0.1,
                                   plant_variants_enabled=False,
                                   food_count=1))
        # the bounty is exactly our experimental plant — no law removals
        for e in [e for e in s.world.entities.values() if e.kind == "food"]:
            s.world.remove(e.id)
        plant = Food(x=50.0, y=50.0, growth=0.1)
        plant.variant = "grass"
        s.world.add(plant)
        stepper = noon_step if phase == "day" else night_step
        for _ in range(steps):
            assert plant.id in s.world.entities
            stepper(s)
        return plant.growth

    day_growth = growth_over(4, "day") - 0.1
    night_growth = growth_over(4, "night") - 0.1
    assert day_growth == pytest.approx(0.4, abs=0.01)   # four full-sun ticks
    assert night_growth == 0.0                          # the dark pays nothing


def test_metabolic_cost_by_caste():
    """More sides, more ceremony: a woman burns 1.5x what a soldier does."""
    assert METABOLIC_COST["Soldier"] == 1.0
    assert METABOLIC_COST["Gentleman"] == 1.1
    assert METABOLIC_COST["Professional"] == 1.2
    assert METABOLIC_COST["Noble"] == 1.3
    assert METABOLIC_COST["Priest"] == 1.5
    assert METABOLIC_COST["Woman"] == 1.5

    def burn(caste_args: dict) -> float:
        s = Simulation(physics_cfg(seed=5))
        from app.entities import max_hp_for
        c = Creature(x=50.0, y=50.0, energy=100.0, lifespan=100000.0,
                     health=max_hp_for(caste_args["caste"]), **caste_args)
        s.world.add(c)
        e0 = c.energy
        s.step()
        return e0 - c.energy

    woman_burn = burn(dict(shape="line", sides=2, caste="Woman"))
    soldier_burn = burn(dict(shape="polygon", sides=3, caste="Soldier"))
    assert woman_burn == pytest.approx(soldier_burn * 1.5, rel=1e-6)


def test_healing_costs_energy():
    """Regeneration converts energy into health — nothing is free."""
    def burn_with(health: float) -> tuple[float, float]:
        s = Simulation(physics_cfg(seed=7))
        c = Creature(x=50.0, y=50.0, shape="polygon", sides=3, angle=0.0,
                     energy=100.0, health=health, lifespan=100000.0)
        s.world.add(c)
        e0, h0 = c.energy, c.health
        s.step()
        return e0 - c.energy, c.health - h0

    burn_healthy, heal_healthy = burn_with(130.0)  # Soldier max HP pool: full
    burn_wounded, heal_wounded = burn_with(60.0)
    assert heal_healthy == pytest.approx(0.0)      # full health: no mend, no cost
    assert heal_wounded == pytest.approx(0.05)     # 0.1 base × REGEN_OUTDOOR_MULT
    assert burn_wounded == pytest.approx(
        burn_healthy + 0.05 * HEALING_ENERGY_COST, rel=1e-6
    )
