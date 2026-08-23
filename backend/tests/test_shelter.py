"""Shelter tests: exposure, scarce beds and restful recovery."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def shelter_cfg(**kw) -> Config:
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
    assert out.energy < e_out - s.config.energy_decay_per_tick
    assert e_out - out.energy == pytest.approx(
        s.config.energy_decay_per_tick + s.config.exposure_drain
    )
    assert e_in - sheltered.energy == pytest.approx(s.config.energy_decay_per_tick)
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
    s.step()
    assert first.sleeping and first.indoors
    assert not second.sleeping and not second.indoors
    assert e_second - second.energy == pytest.approx(
        s.config.energy_decay_per_tick + s.config.exposure_drain
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
    """§L: capacity depends on SIZE — house_capacity counts beds in an 8x8 hall."""
    s = Simulation(shelter_cfg(seed=15, house_capacity=1))
    assert s._house_beds(House(x=0, y=0, size=6.0)) == 1   # int(36/64) -> floor 1
    assert s._house_beds(House(x=0, y=0, size=16.0)) == 4  # int(256/64)
    s2 = Simulation(shelter_cfg(seed=15, house_capacity=12))
    assert s2._house_beds(House(x=0, y=0, size=8.0)) == 12  # reference hall


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
    assert e_before - c.energy == pytest.approx(s.config.energy_decay_per_tick)
    assert c.health - h_before == pytest.approx(0.1)


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
    for _ in range(600):
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
