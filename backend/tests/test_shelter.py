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
