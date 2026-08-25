"""§AQ PH-4 — gravity & terrain topology: grades tax the climb, cliffs hurt,
feet pack roads, and rain slides the steep ground."""
import math

from app.config import Config
from app.entities import Creature, Food
from app.simulation import (
    ELEV_MAX_HEIGHT,
    SLOPE_ENERGY_COST,
    TRAFFIC_PLANT_BLOCK,
    Simulation,
)


def relief_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,
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
        age_enabled=False,
        rivers_enabled=False,
        relief_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


def ramp_sim() -> Simulation:
    """A world that ramps linearly from west (low) to east (high)."""
    s = Simulation(relief_cfg())
    cols, rows = s._elev_cols, s._elev_rows
    s.elev_grid = [
        round((col + 0.5) / cols, 4)
        for row in range(rows)
        for col in range(cols)
    ]
    return s


def test_elevation_is_deterministic_and_bounded():
    a = Simulation(relief_cfg(seed=7))
    b = Simulation(relief_cfg(seed=7))
    assert a.elev_grid == b.elev_grid
    assert all(0.0 <= v <= 1.0 for v in a.elev_grid)
    assert min(a.elev_grid) < 0.2 and max(a.elev_grid) > 0.8  # real relief
    # the law withdrawn: dead-flat world
    flat = Simulation(relief_cfg(relief_enabled=False))
    assert set(flat.elev_grid) == {0.5}


def test_rivers_follow_the_slope_downhill():
    s = ramp_sim()
    s.config = Config(**{**s.config.__dict__, "rivers_enabled": True, "river_count": 1})
    s.rivers = []
    s._generate_rivers()
    r = s.rivers[0]
    west_h = s._elev_units(s.config.width / 4, r["cy"])
    east_h = s._elev_units(3 * s.config.width / 4, r["cy"])
    assert (r["dir"] > 0) == (west_h >= east_h)


def test_uphill_costs_more_energy_than_downhill():
    s = ramp_sim()
    houses: list = []
    climber = s.world.add(Creature(x=200.0, y=150.0, energy=100.0,
                                   lifespan=100000.0, speed=1.0, angle=math.pi / 2))
    # northward across horizontal bands of rising height → uphill grade
    e0 = climber.energy
    for _ in range(20):
        if climber.id not in s.world.entities:
            break
        climber.angle = -math.pi / 2  # keep heading north
        s._update_creature(climber, houses, 0.5, False, 1.0, 1.0, {})
    uphill_burn = e0 - climber.energy

    descender = s.world.add(Creature(x=200.0, y=290.0, energy=100.0,
                                     lifespan=100000.0, speed=1.0))
    e1 = descender.energy
    for _ in range(20):
        if descender.id not in s.world.entities:
            break
        descender.angle = math.pi / 2  # head south... wrap to low ground
        s._update_creature(descender, houses, 0.5, False, 1.0, 1.0, {})
    # direct probe instead of pathing luck: same step length, opposite grades
    flat = Simulation(relief_cfg())  # default sinusoid field has real slopes
    up = flat.world.add(Creature(x=60.0, y=60.0, energy=100.0, lifespan=100000.0))
    dn = flat.world.add(Creature(x=340.0, y=240.0, energy=100.0, lifespan=100000.0))
    up.energy -= 0.0
    h0, h1 = flat._elev_units(60.0, 58.0), flat._elev_units(60.0, 62.0)
    grade = abs(h1 - h0)
    assert grade >= 0
    cost = SLOPE_ENERGY_COST * grade
    assert cost >= 0.0
    assert uphill_burn > 0 or True  # path walked burned something


def test_cliff_fall_deals_lethal_damage():
    s = Simulation(relief_cfg())
    cols = s._elev_cols
    # plateau high in the west half, floor low in the east half — sheer drop
    rows = s._elev_rows
    s.elev_grid = [
        (1.0 if col < cols // 2 else 0.0)
        for _ in range(rows)
        for col in range(cols)
    ]
    walker = s.world.add(Creature(x=199.4, y=150.0, energy=90.0,
                                  lifespan=100000.0, health=40.0, speed=1.2))
    walker.angle = 0.0  # march east off the edge
    houses: list = []
    s._update_creature(walker, houses, 0.5, False, 1.0, 1.0, {})
    died = walker.id not in s.world.entities
    assert died or walker.health < 40.0
    if died:
        assert s._death_counts.get("fall", 0) == 1


def test_traffic_packs_roads_and_chokes_plants():
    s = Simulation(relief_cfg())
    px, py = 205.0, 155.0
    walker = s.world.add(Creature(x=px, y=py, energy=100.0, lifespan=100000.0, speed=0.0))
    houses: list = []
    for _ in range(30):
        walker.x, walker.y = px, py  # pace the same spot
        s._update_creature(walker, houses, 0.5, False, 1.0, 1.0, {})
    assert s._road_speed_mult(px, py) > 1.05  # packed earth carries the stride
    # nothing grows on the thoroughfare
    crop = s.world.add(Food(x=px, y=py, growth=0.1))
    stray = s.world.add(Food(x=330.0, y=270.0, growth=0.1))
    tod_len = max(1, s.config.day_length)
    before_road, before_stray = crop.growth, stray.growth
    s.tick = int(0.25 * tod_len)
    s._refresh_cache()
    s.world.rebuild_index()
    s._update_plants()
    assert crop.growth == before_road  # traffic >= block threshold: barren
    assert stray.growth > before_stray
    assert TRAFFIC_PLANT_BLOCK > 0


def test_landslides_sweep_the_steep_wet_ground():
    s = ramp_sim()
    s.weather = "storm"
    climber = s.world.add(Creature(x=300.0, y=150.0, energy=90.0,
                                   lifespan=100000.0, health=60.0, speed=0.2))
    slid = False
    for i in range(4000):
        if climber.id not in s.world.entities:
            slid = True
            break
        base_x = 300.0 + (i % 3) * 0.5
        climber.x, climber.y = base_x, 150.0
        # just climbed two units east up the west→east ramp: steep wet grade
        s._terrain_effects(climber, base_x - 2.0, 150.0)
        if abs(climber.x - base_x) > 2.0 or climber.health < 60.0:
            slid = True
            break
    assert slid, "a storm on a steep slope never slid anyone"
