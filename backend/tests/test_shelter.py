"""Shelter tests: exposure, scarce beds and restful recovery."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import HEALING_ENERGY_COST, METABOLIC_COST, OVERCROWD_DRAIN, Simulation


def shelter_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        day_length=8,  # nights at ticks where tod < .22 or > .78 (5,6,7 mod 8)
        adult_age=0.0,
        weather_change_rate=0.0,  # weather stays wherever the test pins it
    )
    zeros.update(kw)
    return Config(**zeros)


def test_rain_drains_the_outdoors_but_not_the_sheltered():
    s = Simulation(shelter_cfg(seed=11))
    out = s.world.add(Creature(x=10.0, y=10.0, energy=50.0))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    sheltered = s.world.add(Creature(x=25.0, y=25.0, energy=50.0))
    s.weather = "rain"
    e_out, e_in = out.energy, sheltered.energy
    s.step()
    # §AQ PH-0: upkeep scales with body complexity (default spawn = Gentleman)
    meta = METABOLIC_COST[out.caste]
    assert out.energy < e_out - s.config.energy_decay_per_tick
    assert e_out - out.energy == pytest.approx(
        s.config.energy_decay_per_tick * meta + s.config.exposure_drain
    )
    assert e_in - sheltered.energy == pytest.approx(s.config.energy_decay_per_tick * meta)
    states = {e.id: e for e in s.snapshot().entities}
    assert states[sheltered.id].indoors is True
    assert states[out.id].indoors is False


def test_house_capacity_overflows_into_the_rain():
    s = Simulation(shelter_cfg(seed=12, house_capacity=1))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    first = s.world.add(Creature(x=25.0, y=25.0, energy=50.0))
    second = s.world.add(Creature(x=25.0, y=26.0, energy=50.0))
    assert first.id < second.id
    for _ in range(5):
        s.step()
    assert s._is_night(s._time_of_day())
    e_second = second.energy
    h_second = second.health
    s.step()
    assert first.sleeping and first.indoors
    assert not second.sleeping and not second.indoors
    # §AT-4 H-2: the roof holds two bodies over one bed — the overflow body
    # grinds health down (overcrowding) and mending the grind costs energy.
    assert h_second - second.health == pytest.approx(0.0)  # drain is re-mended at full pool
    assert e_second - second.energy == pytest.approx(
        s.config.energy_decay_per_tick * METABOLIC_COST[second.caste]
        + s.config.exposure_drain
        + OVERCROWD_DRAIN * HEALING_ENERGY_COST  # 1 body over capacity
    )


def test_rest_recovery_mult_scales_indoor_healing():
    def night_gain(rest_recovery_mult: float) -> float:
        s = Simulation(shelter_cfg(seed=13, rest_recovery_mult=rest_recovery_mult))
        s.world.add(House(x=25.0, y=25.0, size=10.0))
        c = s.world.add(Creature(x=25.0, y=25.0, health=50.0))
        for _ in range(5):
            s.step()
        assert s._is_night(s._time_of_day())
        h_before = c.health
        s.step()
        assert c.sleeping
        return c.health - h_before

    gain_default = night_gain(2.0)
    gain_strong = night_gain(4.0)
    assert gain_default == pytest.approx(0.3)
    assert gain_strong == pytest.approx(0.6)
    assert gain_strong > gain_default


def test_house_beds_scale_with_floor_area():
    """§L: capacity depends on SIZE — house_capacity counts beds in an 8x8 hall, max 16."""
    s = Simulation(shelter_cfg(seed=15, house_capacity=1))
    assert s._house_beds(House(x=0, y=0, size=6.0)) == 1   # int(36/64) -> floor 1
    assert s._house_beds(House(x=0, y=0, size=16.0)) == 4  # int(256/64)
    s2 = Simulation(shelter_cfg(seed=15, house_capacity=12))
    assert s2._house_beds(House(x=0, y=0, size=6.0)) == 6   # small hut
    assert s2._house_beds(House(x=0, y=0, size=8.0)) == 12  # reference hall
    assert s2._house_beds(House(x=0, y=0, size=10.0)) == 16 # max house (raw 18 -> capped at 16)
    assert s2._house_beds(House(x=0, y=0, size=16.0)) == 16 # oversized hall capped at 16



def test_shelter_law_disabled_stops_sleep_and_exposure():
    s = Simulation(shelter_cfg(seed=14, shelter_enabled=False))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    c = s.world.add(Creature(x=25.0, y=25.0, energy=50.0, health=60.0))
    for _ in range(5):
        s.step()
        assert not c.sleeping
    assert s._is_night(s._time_of_day())
    s.weather = "rain"
    e_before, h_before = c.energy, c.health
    s.step()
    assert not c.sleeping
    # burn + the energy price of the 0.1 health regenerated this tick (§AQ PH-0)
    assert e_before - c.energy == pytest.approx(
        s.config.energy_decay_per_tick * METABOLIC_COST[c.caste]
        + 0.05 * HEALING_ENERGY_COST
    )
    assert c.health - h_before == pytest.approx(0.05)


def test_small_hut_cannot_hold_the_whole_clan_spill_to_next_roof():
    """A full hut must not swallow the clan: at most `house_beds` sleepers in
    the hut, and the spillover beds down in the next roof WITH space."""
    s = Simulation(shelter_cfg(seed=16, house_capacity=1, house_claim_enabled=False))
    hut = House(x=15.0, y=25.0, size=6.0)
    hall = House(x=55.0, y=25.0, size=16.0)
    s.world.add(hut)
    s.world.add(hall)

    def inside(c, h):
        return abs(c.x - h.x) < h.size / 2 - 0.3 and abs(c.y - h.y) < h.size / 2 - 0.3

    c1 = s.world.add(Creature(x=14.5, y=25.0, energy=100.0))
    c2 = s.world.add(Creature(x=15.5, y=25.0, energy=500.0, lifespan=100000.0))
    guard = 20
    while not s._is_night(s._time_of_day()) and guard:
        s.step()
        guard -= 1
    assert s._is_night(s._time_of_day())

    spilled_to_a_second_roof = False
    for _ in range(800):
        s.step()
        # capacity is law: never more sleepers in the hut than it has beds
        in_hut = [c for c in (c1, c2) if c.sleeping and inside(c, hut)]
        assert len(in_hut) <= s._house_beds(hut)
        if c1.sleeping and c2.sleeping:
            r1 = "hut" if inside(c1, hut) else ("hall" if inside(c1, hall) else None)
            r2 = "hut" if inside(c2, hut) else ("hall" if inside(c2, hall) else None)
            if r1 and r2 and r1 != r2:
                spilled_to_a_second_roof = True  # overflow found the hall
                break
    assert spilled_to_a_second_roof, (
        f"no spill: c1@({c1.x:.1f},{c1.y:.1f})sleep={c1.sleeping} "
        f"c2@({c2.x:.1f},{c2.y:.1f})sleep={c2.sleeping}"
    )


def test_sleeping_creature_does_not_move():
    """Rest means still: a sleeping body holds its exact position until dawn."""
    s = Simulation(shelter_cfg(seed=17))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    c = s.world.add(Creature(x=25.0, y=25.0, energy=100.0, lifespan=100000.0))
    guard = 20
    while not (c.sleeping) and guard:
        s.step()
        guard -= 1
    assert c.sleeping
    x0, y0 = c.x, c.y
    steps = 0
    while s._is_night((s.tick + 1 + 2) % 8 / 8) and steps < 6:  # while next tick stays dark
        s.step()
        assert c.sleeping
        assert (c.x, c.y) == (x0, y0)
        steps += 1
    assert steps >= 1


def test_clan_shelter_and_food_invasion():
    """A growing clan with shelter/food shortages invades rival shelter and plunders food."""
    s = Simulation(shelter_cfg(seed=18, house_claim_enabled=True))
    s.clans[1] = {"name": "Invaders", "color": "#ff0000", "main_house_id": 1, "granary": 0.0}
    s.clans[2] = {"name": "Defenders", "color": "#0000ff", "main_house_id": 2, "granary": 100.0}

    # Clan 1 has 1 house (1 bed) but 4 members (shortage!)
    h1 = s.world.add(House(x=20.0, y=20.0, size=6.0))
    h1.clan_id = 1
    h1.is_main = True
    invaders = [s.world.add(Creature(x=20.0, y=20.0, energy=40.0, clan_id=1)) for _ in range(4)]

    # Clan 2 has main house and a spare house with 1 member
    h2_main = s.world.add(House(x=80.0, y=80.0, size=6.0))
    h2_main.clan_id = 2
    h2_main.is_main = True
    h2_spare = s.world.add(House(x=30.0, y=20.0, size=6.0))
    h2_spare.clan_id = 2
    h2_spare.is_main = False
    s.world.add(Creature(x=80.0, y=80.0, energy=90.0, clan_id=2))

    s._refresh_cache()
    taken = s._try_house_takeover(1, invaders, [h1, h2_main, h2_spare])
    assert taken is not None
    assert taken.id == h2_spare.id
    assert taken.clan_id == 1
    assert s.clans[1]["granary"] > 0.0  # plundered food transferred
    assert s.clans[2]["granary"] < 100.0
