"""§AQ PH-1 — hearths: warmth is infrastructure; radiant fire is double-edged.

Also covers the PH-2 wind ecology (seed drift + scent on the wind) and the
PH-5 neighbour ecology (root competition & plant symbiosis) shipped together
with hearths in the physics-ecosystem batch.
"""

import math

from app.config import Config
from app.entities import Corpse, Creature, Food, House
from app.simulation import (
    FIRE_HEAT,
    HEARTH_COMFORT_TEMP,
    INSULATION_BY_MATERIAL,
    SEASON_BASE_TEMP,
    Simulation,
)


def aq_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,  # eternal noon-ish
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
        agriculture_enabled=True,
        resource_sharing_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(s: Simulation, members: list[Creature]) -> int:
    cid = s._new_clan(members[0])
    for m in members:
        m.clan_id = cid
    s._refresh_cache()
    s.world.rebuild_index()
    return cid


def add_house(s: Simulation, x: float, y: float, clan_id: int = 0, material: str = "stone") -> House:
    h = s.world.add(House(x=x, y=y, size=8.0, material=material))
    h.clan_id = clan_id
    s._refresh_cache()
    s.world.rebuild_index()
    return h


# ---------------------------------------------------------------- hearths

def test_hearth_lights_from_larder_and_warms_the_roof():
    """A stocked larder + kin at home in winter → the hearth burns and the
    indoor air climbs past what insulation alone manages."""
    s = Simulation(aq_cfg(season_length=20000))
    s.tick = 3 * 20000 + 7  # deep winter (4th season), just after a refuel boundary
    kin = s.world.add(Creature(x=100.0, y=100.0, energy=90.0, lifespan=100000.0))
    cid = make_clan(s, [kin])
    h = add_house(s, 100.0, 100.0, clan_id=cid)
    s.clans[cid]["larder"] = 50.0
    assert not h.hearth_lit
    for _ in range(30):
        s.step()
    assert h.hearth_lit
    assert h.hearth_fuel > 0
    # lit hearth beats bare insulation toward HEARTH_COMFORT_TEMP
    amb = s.ambient_at(h.x, h.y)
    base = amb + (18.0 - amb) * INSULATION_BY_MATERIAL["stone"] * 1.0
    warm = s.indoor_ambient(h)
    assert warm > base + 3.0
    assert warm <= HEARTH_COMFORT_TEMP + 1e-6 or warm < HEARTH_COMFORT_TEMP + 5.0


def test_unfed_hearth_gutter_out():
    """An empty larder cannot keep the fire alive — the woodpile runs dry."""
    s = Simulation(aq_cfg())
    kin = s.world.add(Creature(x=60.0, y=60.0, energy=90.0, lifespan=100000.0))
    cid = make_clan(s, [kin])
    h = add_house(s, 60.0, 60.0, clan_id=cid)
    h.hearth_lit = True
    h.hearth_fuel = 20.0
    s.clans[cid]["larder"] = 0.0  # famine: nothing to burn
    for _ in range(25):
        s.step()
    assert not h.hearth_lit
    assert h.hearth_fuel == 0.0


def test_hearth_law_off_extinguishes_every_flame():
    """Withdraw the law and every lit hearth dies instantly."""
    s = Simulation(aq_cfg(hearths_enabled=False))
    kin = s.world.add(Creature(x=60.0, y=60.0, energy=90.0, lifespan=100000.0))
    cid = make_clan(s, [kin])
    h = add_house(s, 60.0, 60.0, clan_id=cid)
    h.hearth_lit = True
    h.hearth_fuel = 500.0
    s.step()
    assert not h.hearth_lit and h.hearth_fuel == 0.0


# ------------------------------------------------------- radiant fire

def test_fire_scalds_beyond_the_flame_core():
    """Heat radiation: a creature just outside the burn radius cooks slowly."""
    s = Simulation(aq_cfg(wildfire_enabled=True))
    victim = s.world.add(Creature(x=200.0, y=150.0, energy=90.0, lifespan=100000.0))
    victim.health = 100.0
    s.fires.append({"x": 206.0, "y": 150.0, "r": 2.0, "ttl": 40})  # core ends ~3.2 away
    d0 = victim.health
    for _ in range(10):
        if victim.id not in s.world.entities:
            break
        s.step()
    assert victim.health < d0 or s._death_counts.get("hyperthermia", 0) > 0


def test_fire_heat_field_reaches_the_ambient_grid():
    """Open flame dominates its neighbourhood on the heat field."""
    s = Simulation(aq_cfg())
    s.fires.append({"x": 200.0, "y": 150.0, "r": 3.0, "ttl": 30})
    far_before = s.ambient_at(360.0, 280.0)
    near_before = s.ambient_at(205.0, 152.0)
    for _ in range(12):
        s._update_temperature()
    near_after = s.ambient_at(205.0, 152.0)
    far_after = s.ambient_at(360.0, 280.0)
    assert near_after - near_before > 20.0  # pulled hard toward FIRE_HEAT
    assert abs(far_after - far_before) < 3.0  # the far field barely drifts


# --------------------------------------------- PH-2 wind seed & scent

def test_seed_drift_rides_downwind():
    """With a steady west wind most sprouts land east of the parent."""
    s = Simulation(aq_cfg(
        food_count=60,  # seasonal bounty headroom for the lone parent
        plant_spread_rate=1.0,
        plant_growth_rate=0.0,
        food_decay_enabled=False,
    ))
    # clear the seeded bounty — one lone parent on open ground
    for e in list(s.world.entities.values()):
        if isinstance(e, Food):
            s.world.remove(e.id)
    parent = s.world.add(Food(x=200.0, y=150.0, growth=1.0))
    s.wind_angle = 0.0  # wind blows +x (west → east)
    s.wind_speed = 1.0
    s.world.rebuild_index()
    downwind = 0
    n = 0
    tod_len = max(1, s.config.day_length)
    for i in range(120):
        s.tick = int(0.25 * tod_len) + i * 4  # re-center at noon each probe
        before = {e.id for e in s.world.entities.values() if isinstance(e, Food)}
        s._update_plants()
        after = {e.id for e in s.world.entities.values() if isinstance(e, Food)}
        for fid in after - before:
            f = s.world.entities.get(fid)
            if f is None:
                continue
            dx, _ = s.world.delta(f.x, f.y, parent.x, parent.y)  # sprout relative to parent
            n += 1
            if dx > 0:
                downwind += 1
    assert n >= 30, f"too few spreads observed ({n})"
    assert downwind / n > 0.55, f"only {downwind}/{n} sprouts went downwind"


def test_scent_carries_upwind_to_predator_nose():
    """A predator steers hard toward UPWIND prey beyond base sight range;
    the same gap downwind stays hidden (directional stealth layer)."""
    cfg = aq_cfg(predation_enabled=True, scent_enabled=True)
    assert cfg.hunt_radius < 11.0  # base nose cannot cover the 11-unit gap
    houses: list = []

    def probe(prey_dx: float) -> float:
        s = Simulation(cfg)
        s.wind_angle = 0.0  # west wind blowing +x
        s.wind_speed = 1.0
        pred = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                    lifespan=100000.0, angle=0.0))
        pred.is_predator = True
        prey = s.world.add(Creature(x=200.0 + prey_dx, y=150.0, energy=90.0,
                                    lifespan=100000.0))
        prey.is_predator = False
        s._refresh_cache()
        s.world.rebuild_index()
        for _ in range(6):
            if prey.id not in s.world.entities:
                break  # got close enough to bite — strongest possible signal
            s._update_creature(pred, houses, 0.5, False, 1.0, 1.0, {})
        # how closely does the hunter face its quarry (π = due west)?
        return abs((pred.angle - math.pi + math.pi) % (2 * math.pi) - math.pi)

    upwind_miss = probe(-11.0)   # scent blows from prey to predator's nose
    downwind_miss = probe(+11.0) # scent blows away from the predator
    assert upwind_miss < 0.7, f"upwind prey not tracked (miss {upwind_miss})"
    assert downwind_miss > 1.0, f"downwind prey somehow tracked (miss {downwind_miss})"


# ------------------------------------------------ PH-5 neighbour ecology

def grow_after_ticks(s: Simulation, f: Food, ticks: int) -> float:
    start = f.growth
    tod_len = max(1, s.config.day_length)
    for i in range(ticks):
        s.tick = int(0.25 * tod_len) + i  # eternal noon → full sun
        s._refresh_cache()
        s.world.rebuild_index()
        s._update_plants()
    return f.growth - start


def eco_sim(**kw) -> Simulation:
    return Simulation(aq_cfg(
        plant_spread_rate=0.0,
        food_decay_enabled=False,
        soil_depletion_enabled=False,
        plant_growth_rate=0.05,
        **kw,
    ))


def test_root_competition_stunts_sprouts_near_mature_plants():
    lone = eco_sim()
    a = lone.world.add(Food(x=100.0, y=100.0, growth=0.1))
    ga = grow_after_ticks(lone, a, 8)
    crowded = eco_sim()
    b = crowded.world.add(Food(x=100.0, y=100.0, growth=0.1))
    crowded.world.add(Food(x=102.0, y=100.0, growth=1.0))
    crowded.world.rebuild_index()
    gb = grow_after_ticks(crowded, b, 8)
    assert gb < ga * 0.9, f"crowded {gb} vs lone {ga}"


def test_mushrooms_fruit_where_things_die():
    lone = eco_sim()
    m = lone.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="mushroom"))
    gm = grow_after_ticks(lone, m, 8)
    rich = eco_sim()
    m2 = rich.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="mushroom"))
    rich.world.add(Corpse(x=102.0, y=100.0, ttl=500))
    rich.world.rebuild_index()
    gm2 = grow_after_ticks(rich, m2, 8)
    assert gm2 > gm * 1.25, f"corpse-fed {gm2} vs bare {gm}"


def test_poison_stunts_and_herbs_love_berries():
    clean = eco_sim()
    g = clean.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="grass"))
    gg = grow_after_ticks(clean, g, 8)
    toxic = eco_sim()
    g2 = toxic.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="grass"))
    toxic.world.add(Food(x=102.0, y=100.0, growth=1.0, variant="poisonous"))
    toxic.world.rebuild_index()
    gg2 = grow_after_ticks(toxic, g2, 8)
    assert gg2 < gg * 0.9

    lone_herb = eco_sim()
    h1 = lone_herb.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="medicinal_herb"))
    gh1 = grow_after_ticks(lone_herb, h1, 8)
    thicket = eco_sim()
    h2 = thicket.world.add(Food(x=100.0, y=100.0, growth=0.1, variant="medicinal_herb"))
    thicket.world.add(Food(x=102.0, y=100.0, growth=1.0, variant="berry"))
    thicket.world.rebuild_index()
    gh2 = grow_after_ticks(thicket, h2, 8)
    assert gh2 > gh1 * 1.15
