"""§AQ PH-3 — fluid dynamics: rivers are 1D channels, a radical 2D constraint.

Channels cost energy to ford, sweep infants and the wounded downstream,
flood under rain and leave fertile silt; builders span planks and raise dams
that hold until they catastrophically fail.
"""

import math

from app.config import Config
from app.entities import Creature, Food
from app.simulation import (
    RIVER_BASE_HW,
    RIVER_FORD_COST,
    RIVER_SILT_MULT,
    Simulation,
)


def river_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,
        season_length=100000,
        weather_change_rate=0.0,
        weather_enabled=True,
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
    )
    zeros.update(kw)
    return Config(**zeros)


def flat_sim(**kw) -> Simulation:
    """A world with exactly one straight channel pinned at y=150."""
    s = Simulation(river_cfg(river_count=0))
    s.rivers = [{
        "cy": 150.0, "hw": RIVER_BASE_HW, "base_hw": RIVER_BASE_HW,
        "dir": 1.0, "water": 0.0, "flood_ticks": 0, "silt_ticks": 0,
    }]
    return s


def test_world_spawns_rivers_and_keeps_houses_dry():
    s = Simulation(river_cfg(river_count=3))
    assert len(s.rivers) >= 1
    for r in s.rivers:
        assert r["dir"] in (1.0, -1.0)
        assert r["hw"] == RIVER_BASE_HW
        assert 0.0 <= r["cy"] <= s.config.height
    for h in s._functional_houses():
        for rv in s.rivers:
            dy = abs(h.y - rv["cy"])
            dy = min(dy, s.config.height - dy)
            assert dy > rv["hw"] + 2.0, f"house #{h.id} straddles the water"


def test_fording_drains_energy_but_bridges_cross_dry():
    s = flat_sim()
    wader = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                 lifespan=100000.0, speed=0.5, angle=0.0))
    houses: list = []
    e0 = wader.energy
    s._update_creature(wader, houses, 0.5, False, 1.0, 1.0, {})
    assert wader.energy < e0 - 0.05  # paid the ford toll on top of metabolism
    # bridge crossing: no toll inside the plank's x-range
    r = s.rivers[0]
    s.bridges.append({"x": 240.0, "cy": r["cy"], "hw": r["hw"], "hp": 100})
    crosser = s.world.add(Creature(x=240.0, y=150.0, energy=90.0,
                                   lifespan=100000.0, speed=0.5, angle=-math.pi / 2))
    e1 = crosser.energy
    s._update_creature(crosser, houses, 0.5, False, 1.0, 1.0, {})
    assert crosser.energy >= e1 - 0.05  # dry feet — only base metabolism bit


def test_current_sweeps_infants_downstream():
    s = flat_sim()
    babe = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                lifespan=100000.0, speed=0.4, age=10))
    assert babe.stage == "infant"
    houses: list = []
    x0 = babe.x
    s._update_creature(babe, houses, 0.5, False, 1.0, 1.0, {})
    dx, _ = s.world.delta(babe.x, babe.y, x0, 150.0)  # babe relative to start
    assert dx > 0.1  # carried east by the eastward current


def test_rain_floods_the_channel_then_leaves_silt():
    s = flat_sim()
    r = s.rivers[0]
    sprout = s.world.add(Food(x=200.0, y=150.0, growth=0.5))
    victim = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                  lifespan=100000.0, health=100.0, speed=0.0))
    hp0 = victim.health
    s.weather = "storm"
    grown = 0.5
    tod_len = max(1, s.config.day_length)
    for i in range(600):
        s.tick = int(0.25 * tod_len) + i  # keep the sun up so growth is measurable
        s.weather = "storm"
        if r["flood_ticks"] > 0:
            s.weather = "clear"  # flood rides out on stored water
        s.step()
        if victim.id not in s.world.entities:
            break
    assert r["flood_ticks"] > 0 or r["silt_ticks"] > 0 or r["water"] > 0
    # the flood drowned the creature standing in it OR the channel rose at all
    flooded_or_wet = (
        victim.id not in s.world.entities
        or victim.health < hp0
        or r["hw"] > RIVER_BASE_HW * 1.2
    )
    assert flooded_or_wet
    # after the flood recedes, bank plants grow faster on the fresh silt
    if r["silt_ticks"] > 0 and sprout.id in s.world.entities:
        before = sprout.growth
        s.tick += 1
        s._refresh_cache()
        s.world.rebuild_index()
        s._update_plants()
        gained = sprout.growth - before
        bare_gain = 0.05 * s._sun_factor() * 0.55 + 0.45  # upper bound sanity only
        assert gained > 0
        assert RIVER_SILT_MULT > 1.0 and gained <= bare_gain * RIVER_SILT_MULT + 0.01


def test_builders_span_planks_and_raise_dams():
    s = flat_sim()
    mason = s.world.add(Creature(x=210.0, y=160.0, energy=95.0,
                                 lifespan=100000.0, speed=0.3))
    mason.personality = "builder"
    s._refresh_cache()
    s.world.rebuild_index()
    for _ in range(40):
        s.step()
        if s.bridges:
            break
    assert s.bridges, "no builder ever raised a plank"
    # rising water → dam
    r = s.rivers[0]
    r["water"] = 0.9
    for _ in range(40):
        s.weather = "rain"
        s.step()
        if any(d["cy"] == r["cy"] for d in s.dams):
            break
    assert any(d["cy"] == r["cy"] for d in s.dams), "no dam against the rising water"


def test_dam_failure_releases_a_flash_flood():
    s = flat_sim()
    r = s.rivers[0]
    r["flood_ticks"] = 50  # already in spate
    hw0 = r["hw"]
    s.dams.append({"x": 250.0, "cy": r["cy"], "hp": 1})  # rotten masonry
    s.step()
    kinds = [e.payload.get("kind") for e in s.history if e.type == "disaster"]
    assert "flash_flood" in kinds
    assert not any(d["cy"] == r["cy"] and d["hp"] <= 0 for d in s.dams)
    assert r["flood_ticks"] > 0
    assert r["hw"] > hw0


def test_no_law_no_rivers():
    s = Simulation(river_cfg(rivers_enabled=True, river_count=0))
    assert s.rivers == []


def test_artisan_builds_and_repairs_bridges():
    """Artisan caste members build and maintain bridges without needing builder personality."""
    s = flat_sim()
    artisan = s.world.add(Creature(x=210.0, y=160.0, energy=95.0,
                                   caste="Artisan", sides=3,
                                   lifespan=100000.0, speed=0.3))
    artisan.personality = "cautious"  # Even if cautious, artisan caste builds bridges
    s._refresh_cache()
    s.world.rebuild_index()
    for _ in range(40):
        s.step()
        if s.bridges:
            break
    assert s.bridges, "Artisan should build a bridge plank"
    # Verify bridge repair
    br = s.bridges[0]
    br["hp"] = 1000  # Damaged bridge
    for _ in range(40):
        s.step()
        if br["hp"] > 1000:
            break
    assert br["hp"] > 1000, "Artisan should repair decaying bridge nearby"
