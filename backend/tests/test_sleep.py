"""Night rest tests: creatures shelter indoors after dark."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def sleep_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        day_length=8,  # nights at ticks where tod < .22 or > .78 (5,6,7 mod 8)
        adult_age=0.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_creatures_sleep_inside_houses_at_night():
    s = Simulation(sleep_cfg(seed=1))
    h = s.world.add(House(x=25.0, y=25.0, size=10.0))
    c = s.world.add(Creature(x=25.0, y=26.0, energy=50.0))
    # tick 0 is sunrise; walk until the first night tick
    slept_ticks = 0
    energy_before_night = c.energy
    for i in range(8):
        s.step()
        if s._is_night(s._time_of_day()):
            if not c.sleeping:
                # walk it indoors manually and confirm next night tick sleeps
                c.x, c.y = 25.0, 25.0
                s.step()
            if c.sleeping:
                slept_ticks += 1
                break
    assert slept_ticks == 1
    assert c.sleeping


def test_sleeping_halves_hunger():
    """Non-vacuous: hard-precondition a night tick indoors, then assert the halved loss."""
    s = Simulation(sleep_cfg(seed=2))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    c = s.world.add(Creature(x=25.0, y=25.0, energy=50.0))
    guard = 0
    while not s._is_night(s._time_of_day()) and guard < 10:
        s.step()  # stay day; the house keeps them centred
        guard += 1
    assert s._is_night(s._time_of_day())
    e_before = c.energy
    s.step()  # the first night tick
    assert c.sleeping is True and c.indoors is True
    loss = e_before - c.energy
    assert loss == pytest.approx(
        s.config.energy_decay_per_tick * s.config.sleep_energy_mult, abs=0.01
    )


def test_no_house_no_sleep():
    s = Simulation(sleep_cfg(seed=3))
    c = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    for _ in range(9):
        s.step()
        assert not c.sleeping


def test_day_wakes_the_sleeper():
    s = Simulation(sleep_cfg(seed=4))
    s.world.add(House(x=25.0, y=25.0, size=10.0))
    c = s.world.add(Creature(x=25.0, y=25.0, energy=50.0))
    saw_sleep = False
    for _ in range(16):  # two full days
        s.step()
        if c.sleeping:
            saw_sleep = True
        elif saw_sleep and not s._is_night(s._time_of_day()):
            break
    assert saw_sleep  # slept at night...
    assert not c.sleeping  # ...and daylight woke them
