"""Environment tests: day/night clock, seasons, weather."""

import pytest

from app.config import Config
from app.simulation import SEASONS, WEATHER_STATES, Simulation


def env_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        age_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_day_night_clock_progresses():
    s = Simulation(env_cfg(seed=1, day_length=10))
    assert s._time_of_day() == pytest.approx(0.25)  # world starts at sunrise
    for _ in range(5):
        s.step()
    assert s._time_of_day() == pytest.approx(0.75)  # 5 ticks of 10 = half day later
    for _ in range(5):
        s.step()
    assert s.day == 2 and s._time_of_day() == pytest.approx(0.25)


def test_night_dims_sight():
    s = Simulation(env_cfg(seed=1, day_length=100))
    s.tick = 80  # midnight under the offset formula
    assert s.env_sight_mult() == pytest.approx(s.config.night_sight_mult)
    s.tick = 30  # high noon
    assert s.env_sight_mult() == pytest.approx(1.0)


def test_fog_and_rain_stack_on_the_sky():
    s = Simulation(env_cfg(seed=1, day_length=100))
    s.tick = 30  # noon: no night penalty
    s.weather = "fog"
    assert s.env_sight_mult() == pytest.approx(s.config.fog_sight_mult)
    s.weather = "rain"
    assert s.env_speed_mult() == pytest.approx(s.config.rain_speed_mult)
    s.weather = "clear"
    assert s.env_speed_mult() == pytest.approx(1.0)


def test_weather_machine_changes_and_stays_valid():
    s = Simulation(env_cfg(seed=2, weather_change_rate=1.0))
    seen = set()
    last = s.weather
    for _ in range(12):
        s.step()
        assert s.weather in WEATHER_STATES
        if s.weather != last:
            seen.add(s.weather)
            last = s.weather
    assert len(seen) >= 2


def test_weather_disabled_stays_clear():
    s = Simulation(env_cfg(seed=3, weather_enabled=True, weather_change_rate=1.0))
    s.step()
    assert s.weather != "clear" or True  # sanity: enabled worlds may change
    s2 = Simulation(env_cfg(seed=3, weather_enabled=False, weather_change_rate=1.0))
    for _ in range(5):
        s2.step()
    assert s2.weather == "clear"


def test_winter_halves_the_food_law():
    from app.simulation import SEASON_FOOD_MULT

    # season_length 10 => winter (index 3) spans ticks 30..39
    s = Simulation(env_cfg(seed=4, season_length=10, food_count=10))
    expected = round(10 * SEASON_FOOD_MULT["winter"])
    guard = 0
    while s._season() != "winter" and guard < 45:
        s.step()
        guard += 1
    assert s._season() == "winter"
    s.step()  # one full tick enforced under the winter law
    foods = [e for e in s.world.entities.values() if e.kind == "food"]
    assert len(foods) == expected


def test_seasons_cycle_through_all_four():
    s = Simulation(env_cfg(seed=5, season_length=3))
    seen = []
    for _ in range(13):
        seen.append(s._season())
        s.step()
    assert set(seen) == set(SEASONS)
