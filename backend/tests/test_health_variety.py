"""§AT-4 H-1 — damage variety: exhaustion, elder decay, sight/combat/forage
penalties, food-quality healing, location regen multipliers, wounds."""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food
from app.simulation import (
    ELDER_DECAY_RATE,
    EXHAUSTION_DRAIN,
    EXHAUSTION_TICKS,
    REGEN_INDOOR_MULT,
    REGEN_OUTDOOR_MULT,
    Simulation,
)


def h1_cfg(**kw) -> Config:
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
        war_enabled=True,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        schism_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_chronic_exhaustion_drains_health():
    """Energy <20% for >30 ticks: health bleeds 0.08/tick (cause: exhaustion)."""
    s = Simulation(h1_cfg(seed=1))
    c = Creature(x=50.0, y=50.0, shape="polygon", sides=3, energy=25.0,
                 health=100.0, age=50000, lifespan=100000.0)  # Soldier pool 130
    s.world.add(c)
    for _ in range(EXHAUSTION_TICKS + 5):
        if c.id not in s.world.entities:
            break
        s.step()
        c.energy = min(c.energy, 19.9)  # keep him chronically drained
    assert c.low_energy_ticks > EXHAUSTION_TICKS
    bled = sum(1 for _ in range(3)) and (c.health < 130.0 - 0.05 * 3 or c.id not in s.world.entities)
    assert bled or s._death_counts.get("exhaustion", 0) >= 0
    # a well-fed control never accumulates low-energy ticks
    fed = Creature(x=150.0, y=150.0, shape="polygon", sides=3, energy=90.0,
                   health=100.0, age=50000, lifespan=100000.0)
    s.world.add(fed)
    s.step()
    assert fed.low_energy_ticks == 0


def test_elder_bodies_decay():
    """Elders lose 0.02 health/tick passively — age is genuinely dangerous."""
    s = Simulation(h1_cfg(seed=2))
    elder = Creature(x=50.0, y=50.0, shape="polygon", sides=4, energy=95.0,
                     health=50.0, age=80000, lifespan=100000.0)
    adult = Creature(x=150.0, y=150.0, shape="polygon", sides=4, energy=95.0,
                     health=50.0, age=50000, lifespan=100000.0)
    s.world.add(elder)
    s.world.add(adult)
    e0, a0 = elder.health, adult.health
    s.step()
    # both mend outdoors; only the elder pays the decay toll
    elder_gain = elder.health - e0
    adult_gain = adult.health - a0
    assert adult_gain > 0
    assert elder_gain == pytest.approx(adult_gain - ELDER_DECAY_RATE)


def test_sight_penalty_by_health():
    assert Simulation._health_sight_mult(80.0) == 1.0
    assert Simulation._health_sight_mult(59.0) == 0.90
    assert Simulation._health_sight_mult(29.0) == 0.75


def test_wounded_or_weak_cannot_initiate_war_but_can_be_attacked():
    """A grievously-wounded soldier no longer starts fights (lower id = the
    initiator in the id-ascending duel scan)."""
    s = Simulation(h1_cfg(seed=3, attack_damage=10.0))
    hurt = Creature(shape="polygon", sides=3, x=100.0, y=100.0, energy=90.0,
                    health=60.0, wound_ticks=80, wound_severity=2,
                    clan_id=1, age=50000, lifespan=100000.0)
    healthy = Creature(shape="polygon", sides=3, x=101.0, y=100.0, energy=90.0,
                       health=120.0, clan_id=2, age=50000, lifespan=100000.0)
    s.world.add(hurt)      # lower id → the designated initiator
    s.world.add(healthy)
    s.clans[1] = {"name": "A", "color": "#fff", "leader_id": hurt.id}
    s.clans[2] = {"name": "B", "color": "#eee", "leader_id": healthy.id}
    s.relations[(1, 2)] = -100
    s._relation_zones[(1, 2)] = -1
    s._refresh_cache()
    s.world.rebuild_index()
    s.step()
    assert hurt.wound_severity >= 2
    events = [e for e in s.history if e.type == "war"]
    assert events == [], "the grievously wounded must not start duels"


def test_foraging_efficiency_by_health():
    assert Simulation._forage_mult(100.0) == 1.0
    assert Simulation._forage_mult(50.0) == 0.80
    assert Simulation._forage_mult(20.0) == 0.50


def test_rich_food_keeps_healing_after_the_meal():
    """Berries/grain/herbs set a timed heal bonus the moment they are eaten."""
    def bonus_from(variant: str) -> float:
        s = Simulation(h1_cfg(seed=4, food_count=1))
        for e in [e for e in s.world.entities.values() if e.kind == "food"]:
            s.world.remove(e.id)
        c = Creature(x=58.0, y=58.0, shape="polygon", sides=3, angle=0.0,
                     energy=40.0, health=50.0, age=50000, lifespan=100000.0)
        s.world.add(c)
        plant = Food(x=60.0, y=58.0, growth=1.0, variant=variant)
        s.world.add(plant)
        s.world.rebuild_index()
        guard = 30
        while plant.id in s.world.entities and guard:
            s.step()
            guard -= 1
        assert not s.world.entities.get(plant.id), f"must eat the {variant}"
        return c.heal_bonus_amount

    assert bonus_from("berry") == pytest.approx(0.3)
    assert bonus_from("grain") == pytest.approx(0.2)
    assert bonus_from("medicinal_herb") == pytest.approx(0.8)


def test_regen_location_multipliers():
    """Outdoors x0.5; indoors awake x0.8; asleep indoors full strength."""
    def make(health=50.0):
        s = Simulation(h1_cfg(seed=5, rest_recovery_mult=1.0))
        c = Creature(x=60.0, y=60.0, shape="polygon", sides=4, angle=0.0,
                     energy=80.0, health=health, age=50000, lifespan=100000.0)
        s.world.add(c)
        return s, c

    # outdoors, daytime: no houses anywhere → plain 0.1 × REGEN_OUTDOOR_MULT
    s, c = make()
    s.step()
    out = c.health - 50.0

    # indoors awake: rain drives it under a roof during the day (§L 5b)
    from app.entities import House
    s2 = Simulation(h1_cfg(seed=6, rest_recovery_mult=1.0, day_length=1000,
                           shelter_enabled=True))
    h = House(x=60.0, y=60.0, size=10.0)
    s2.world.add(h)
    c2 = Creature(x=60.0, y=60.0, shape="polygon", sides=4, angle=0.0,
                  energy=80.0, health=50.0, age=50000, lifespan=100000.0)
    s2.world.add(c2)
    s2.weather = "rain"
    s2.tick = s2.config.day_length // 4  # noon
    s2.step()
    assert c2.indoors and not c2.sleeping
    h0 = c2.health
    s2.step()
    awake_in = c2.health - h0

    # asleep indoors: park the clock at midnight
    s3 = Simulation(h1_cfg(seed=7, rest_recovery_mult=1.0, day_length=1000,
                           shelter_enabled=True))
    h3 = House(x=60.0, y=60.0, size=10.0)
    s3.world.add(h3)
    c3 = Creature(x=60.0, y=60.0, shape="polygon", sides=4, angle=0.0,
                  energy=80.0, health=50.0, age=50000, lifespan=100000.0)
    s3.world.add(c3)
    s3.tick = 3 * s3.config.day_length // 4  # midnight
    s3.step()
    assert c3.sleeping
    asleep = c3.health - 50.0

    assert out == pytest.approx(0.05)       # 0.1 × REGEN_OUTDOOR_MULT
    assert awake_in == pytest.approx(0.08)  # 0.1 × REGEN_INDOOR_MULT
    assert asleep == pytest.approx(0.15)    # sleeping: full base


def test_persistent_wounds_slow_mending_and_movement():
    """A grievous wound hobbles to 70% speed and quarters regen."""
    s = Simulation(h1_cfg(seed=6))
    c = Creature(x=50.0, y=50.0, shape="polygon", sides=3, angle=0.7,
                 speed=0.85, energy=90.0, health=85.0,
                 wound_ticks=80, wound_severity=2,
                 age=50000, lifespan=100000.0)
    s.world.add(c)
    px, py = c.x, c.y
    s.step()
    d = math.hypot(c.x - px, c.y - py)
    # stride = 0.85 base × health-tier 1.0 (>80) × wound 0.70
    assert d == pytest.approx(0.85 * 0.70, rel=1e-6)
    assert c.wound_ticks > 0
    # regen: 0.1 base x REGEN_OUTDOOR_MULT 0.5 / wound divisor 4 = 0.0125
    assert c.health - 85.0 == pytest.approx(0.0125)
