"""§H Plant ecosystem tests: growth, spread, nutrient cycle, winter die-back."""

import pytest

from app.config import Config
from app.entities import Creature, Food
from app.simulation import NUTRIENT_BOOST, SEASON_FOOD_MULT, Simulation


def plants_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, weather_enabled=False,
        age_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def foods(sim: Simulation) -> list:
    return [e for e in sim.world.entities.values() if e.kind == "food"]


def day_step(sim: Simulation) -> None:
    """§AQ PH-0: park the clock at high noon so this step gets full sun —
    keeps exact-arithmetic growth tests deterministic. (World starts at
    sunrise: noon sits at tick ≡ day_length/4.)"""
    dl = max(1, sim.config.day_length)
    sim.tick = (sim.tick // dl) * dl + dl // 4
    sim.step()


def test_same_seed_determinism_including_plants():
    kw = dict(
        seed=99, num_triangles=4, num_women=3, food_count=8,
        plant_growth_rate=0.05, plant_spread_rate=0.05,
    )
    a = Simulation(plants_cfg(**kw))
    b = Simulation(plants_cfg(**kw))
    for _ in range(300):
        a.step()
        b.step()

    def state(s: Simulation):
        return [
            (round(e.x, 6), round(e.y, 6), round(getattr(e, "growth", -1.0), 6))
            for e in sorted(s.world.entities.values(), key=lambda e: e.id)
        ]

    assert state(a) == state(b)
    assert [e.type for e in a.history] == [e.type for e in b.history]


def test_growth_reaches_one_and_stops_with_single_bloom():
    s = Simulation(plants_cfg(seed=7, food_count=3, plant_growth_rate=0.1, plant_variants_enabled=False))
    for f in foods(s):  # a young meadow: watch it ripen together
        f.growth = 0.5
        f.variant = "grass"
    for _ in range(6):  # 0.5 + 5 * 0.1 crosses 1.0 here (noon sun)
        day_step(s)
    assert len(foods(s)) == 3
    assert all(f.growth == pytest.approx(1.0) for f in foods(s))
    blooms = [e for e in s.history if e.type == "bloom"]
    assert len(blooms) == 3
    assert all({"x", "y"} <= set(b.payload) for b in blooms)
    for _ in range(10):  # mature plants stop growing, never re-bloom
        day_step(s)
    assert all(f.growth == pytest.approx(1.0) for f in foods(s))
    assert len([e for e in s.history if e.type == "bloom"]) == 3
    snap = s.snapshot()
    growths = [e.growth for e in snap.entities if e.kind == "food"]
    assert len(growths) == 3 and all(g == pytest.approx(1.0) for g in growths)


def test_immature_plant_feeds_less_than_mature():
    def meal_energy(growth: float) -> float:
        s = Simulation(plants_cfg(seed=5, plant_variants_enabled=False))
        s.world.add(Food(x=20.0, y=20.0, growth=growth, variant="grass"))
        eater = s.world.add(
            Creature(x=19.0, y=20.0, sides=4, angle=0.0, speed=0.55,
                     energy=40.0, lifespan=100000.0)
        )
        s.step()
        return eater.energy

    mature = meal_energy(1.0)
    young = meal_energy(0.25)
    # same seed => identical metabolism; only the harvest differs. The plant
    # grows one tick's worth before being eaten, hence 0.25 + growth_rate
    # (the step runs at whatever sun that tick provides — identical in both).
    s_probe = Simulation(plants_cfg(seed=5, plant_variants_enabled=False))
    expected = Config().energy_from_food * (
        1 - min(1.0, 0.25 + Config().plant_growth_rate * s_probe._sun_factor())
    )
    assert mature - young == pytest.approx(expected)


def test_spread_fills_only_below_seasonal_target():
    s = Simulation(plants_cfg(seed=11, food_count=6, plant_growth_rate=1.0,
                              plant_spread_rate=1.0))
    target = round(6 * SEASON_FOOD_MULT[s._season()])
    for _ in range(2):
        day_step(s)
    parents = foods(s)
    assert len(parents) == target and all(p.growth >= 1.0 for p in parents)

    # open one gap below the seasonal bounty: spread must refill it
    gone = parents[0]
    s.world.remove(gone.id)
    day_step(s)
    survivors = {f.id for f in foods(s)} - {gone.id} - {
        f.id for f in foods(s) if f.growth < 1.0
    }
    fresh = [f for f in foods(s) if f.id not in survivors and f.id != gone.id]
    assert len(foods(s)) == target
    assert len(fresh) == 1
    assert fresh[0].growth == pytest.approx(0.15)  # sprouts from the parent...
    near = min(
        s.world.distance(fresh[0].x, fresh[0].y, p.x, p.y)
        for p in parents[1:]
    )
    assert near <= 6.0  # ...nearby, not on random fertile ground

    # saturated land: at target, spread adds nothing more
    for _ in range(25):
        day_step(s)
    assert len(foods(s)) == target


def test_corpse_decay_boosts_nearby_plant_growth():
    from dataclasses import replace
    s = Simulation(plants_cfg(seed=21, corpse_ttl=2, nutrient_cycle_rate=1.0,
                              food_count=0, plant_variants_enabled=False))  # no auto-spawned plants
    # our two hand-placed sprouts ARE the seasonal bounty (target = 2)
    s.config = replace(s.config, food_count=2)
    s.world.add(Creature(x=20.0, y=20.0, energy=0.01))  # starves at once
    near = s.world.add(Food(x=26.0, y=20.0, growth=0.2, variant="grass"))   # in fertiliser reach…
    far = s.world.add(Food(x=80.0, y=80.0, growth=0.2, variant="grass"))     # …far one is not
    for _ in range(3):
        day_step(s)
    assert not any(e.kind == "corpse" for e in s.world.entities.values())
    grown = NUTRIENT_BOOST * s.config.nutrient_cycle_rate
    # §AM: the dead also enrich the soil grid, so the near plant grows at
    # least bare sun+water plus the direct nutrient gift; the far one,
    # whose own cell only depletes as it grows, never beats bare growth.
    assert near.growth >= 0.2 + 3 * s.config.plant_growth_rate + grown  # fertilised
    assert far.growth <= 0.2 + 3 * s.config.plant_growth_rate  # too far to feel it
    assert near.growth > far.growth


def test_winter_dieback_removes_youngest_first():
    s = Simulation(plants_cfg(seed=31, season_length=8, food_count=10,
                              plant_growth_rate=0.0, plant_spread_rate=0.0))
    for _ in range(20):  # spring -> summer -> autumn
        s.step()
    assert s._season() == "autumn"
    meadow = foods(s)
    assert len(meadow) == 10
    for i, f in enumerate(meadow):  # an uneven meadow: young shoots to elders
        f.growth = round(0.1 + 0.08 * i, 3)
    pre_avg = sum(f.growth for f in meadow) / len(meadow)
    baseline = sorted((f.growth for f in meadow), reverse=True)

    guard = 0
    while s._season() != "winter" and guard < 20:
        s.step()
        guard += 1
    s.step(); s.step()  # spend two full winter ticks under the shrunken bounty
    assert s._season() == "winter"
    survivors = foods(s)
    assert len(survivors) == round(10 * SEASON_FOOD_MULT["winter"])
    avg = sum(f.growth for f in survivors) / len(survivors)
    assert avg >= pre_avg  # the young were culled first
    # nothing among the youngest half of the original meadow survives…
    weakest_survivor = min(f.growth for f in survivors)
    assert weakest_survivor >= sorted(baseline)[len(baseline) // 2]
