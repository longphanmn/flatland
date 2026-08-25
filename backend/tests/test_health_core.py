"""§AT-4 H-0 — the health core: regeneration demands energy, weakness slows
the body, and sickly creatures cannot beget children."""

import math

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import HEALTH_SELF_DRAIN_RATE, Simulation


def health_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,  # eternal day: no sleep branches in these tests
        season_length=100000,
        weather_change_rate=0.0,
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


def test_regen_requires_energy_surplus():
    """Below 40% energy regen stalls; above it, wounds close."""
    s = Simulation(health_cfg())
    weak = s.world.add(Creature(x=10.0, y=10.0, energy=30.0, health=60.0))
    fed = s.world.add(Creature(x=200.0, y=200.0, energy=90.0, health=60.0))
    s.step()
    assert weak.health == pytest.approx(60.0)  # stalled: 30% < 40%
    assert fed.health == pytest.approx(60.05)  # + base regen × REGEN_OUTDOOR_MULT


def test_starving_body_drains_health():
    """Below 20% energy the body cannibalizes itself: −health each tick."""
    s = Simulation(health_cfg(lifespan_mult=100.0))
    c = s.world.add(Creature(x=50.0, y=50.0, energy=15.0, health=100.0, lifespan=100000.0))
    s.step()
    expected = 100.0 - HEALTH_SELF_DRAIN_RATE
    assert c.health == pytest.approx(expected)
    assert c.energy < 15.0  # metabolism ran too; drain is on top of it


def test_speed_penalty_by_health():
    """A wounded creature strides shorter: tiered multipliers, verified live."""
    assert Simulation._health_speed_mult(100.0) == 1.0
    assert Simulation._health_speed_mult(79.9) == 0.95
    assert Simulation._health_speed_mult(59.0) == 0.85
    assert Simulation._health_speed_mult(39.0) == 0.70
    assert Simulation._health_speed_mult(5.0) == 0.50

    # Integration: same caste, two grown adults, one gravely wounded.
    s = Simulation(health_cfg())
    from app.entities import traits_for
    speed = traits_for("Gentleman").speed
    fit = Creature(x=50.0, y=50.0, sides=4, angle=0.7, energy=90.0,
                   health=100.0, age=50000, lifespan=100000.0, speed=speed)
    hurt = Creature(x=150.0, y=150.0, sides=4, angle=0.7, energy=90.0,
                    health=10.0, age=50000, lifespan=100000.0, speed=speed)
    s.world.add(fit)
    s.world.add(hurt)
    fx, fy = fit.x, fit.y
    hx, hy = hurt.x, hurt.y
    s.step()
    d_fit = math.hypot(fit.x - fx, fit.y - fy)
    d_hurt = math.hypot(hurt.x - hx, hurt.y - hy)
    assert d_fit == pytest.approx(speed * 1.0, rel=1e-6)
    assert d_hurt == pytest.approx(speed * 0.5, rel=1e-6)


def test_sickly_creatures_cannot_mate():
    """Reproduction is blocked below 50 HP even with full energy nearby."""
    def births_with(health: float) -> int:
        s = Simulation(health_cfg(birth_enabled=True, adult_age=0.0, birth_rate=1.0))
        mother = Creature(shape="line", sides=2, x=100.0, y=100.0,
                          energy=100.0, health=health, age=40000,
                          lifespan=100000.0)
        father = Creature(shape="polygon", sides=4, x=101.0, y=101.0,
                          energy=100.0, health=health, age=40000,
                          lifespan=100000.0)
        s.world.add(mother)
        s.world.add(father)
        for _ in range(30):
            s.step()
        return sum(1 for e in s.history if e.type == "birth")

    assert births_with(100.0) > 0   # healthy pair breeds at once
    assert births_with(45.0) == 0   # sickly pair never does


def test_sleeping_heal_also_demands_energy():
    """Even tucked in bed, a body on fumes does not mend (§AT-4 H-0)."""
    s = Simulation(health_cfg(day_length=8, shelter_enabled=True, rest_recovery_mult=2.0))
    h = House(x=25.0, y=25.0, size=10.0)
    s.world.add(h)
    rested = s.world.add(Creature(x=25.0, y=25.0, energy=80.0, health=50.0, lifespan=100000.0))
    # 30% energy: above starving_ratio (sleeps) but below the 40% healing floor
    famished = s.world.add(Creature(x=25.5, y=25.0, energy=30.0, health=50.0, lifespan=100000.0))
    guard = 20
    while not s._is_night(s._time_of_day()) and guard:
        s.step()
        guard -= 1
    assert s._is_night(s._time_of_day())
    hr, hf = rested.health, famished.health
    s.step()
    assert rested.sleeping and famished.sleeping
    assert rested.health - hr == pytest.approx(0.3)      # 0.15 × rest_recovery_mult
    assert famished.health == pytest.approx(hf)          # no free healing
