"""§AQ PH-2 — the wind: a vector over the land; flame runs before it."""

import math

import pytest

from app.config import Config
from app.entities import Food
from app.simulation import (
    WIND_CALM_SPEED,
    WIND_SEASON_BIAS,
    WIND_STORM_SPEED,
    Simulation,
)


def wind_cfg(**kw) -> Config:
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
        war_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        schism_enabled=False,
        age_enabled=False,
        wildfire_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_wind_strength_follows_the_sky():
    """Storms howl, rain breathes, clear days barely stir the grass."""
    s = Simulation(wind_cfg(seed=5))
    assert s.wind_speed == pytest.approx(WIND_CALM_SPEED)
    s.weather = "storm"
    for _ in range(120):
        s._update_wind()
    assert s.wind_speed == pytest.approx(WIND_STORM_SPEED, abs=0.02)
    s.weather = "clear"
    for _ in range(200):
        s._update_wind()
    assert s.wind_speed == pytest.approx(WIND_CALM_SPEED, abs=0.02)
    # magnitude scales with storm severity vs rain
    s.weather = "rain"
    peak = 0.0
    for _ in range(60):
        s._update_wind()
        peak = max(peak, s.wind_speed)
    assert peak < WIND_STORM_SPEED


def test_new_weather_rerolls_direction_near_season_bias():
    """A changing sky re-rolls the bearing near the season's prevailing one."""
    s = Simulation(wind_cfg(seed=6, weather_enabled=True,
                            weather_change_rate=1.0))  # always turns
    s.tick = 0  # spring
    s._update_weather()  # guaranteed change
    diff_spring = (s.wind_angle - WIND_SEASON_BIAS["spring"] + math.pi) % (2 * math.pi) - math.pi
    assert abs(diff_spring) <= 1.0 + 1e-9
    # winter's prevailing bearing differs from spring's
    s2 = Simulation(wind_cfg(seed=6, season_length=1, weather_enabled=True,
                             weather_change_rate=1.0))
    for _ in range(3):
        s2.step()
    assert s2._season() == "winter"
    s2._update_weather()
    diff_winter = (s2.wind_angle - WIND_SEASON_BIAS["winter"] + math.pi) % (2 * math.pi) - math.pi
    assert abs(diff_winter) <= 1.0 + 1e-9


def test_fire_spreads_downwind():
    """Same seed, a wall of plants east and west of a blaze blowing east:
    more eastern plants catch before the smoke clears."""
    def burn_east_vs_west() -> tuple[int, int]:
        s = Simulation(wind_cfg(seed=8, food_count=25))  # bounty covers the field
        s.wind_angle = 0.0          # due east
        s.wind_speed = WIND_STORM_SPEED
        s.weather = "storm"
        west: list[Food] = []
        east: list[Food] = []
        for i in range(12):
            fw = Food(x=90.0 - 2.0 - i * 3.0, y=150.0, growth=1.0)   # upwind column
            fe = Food(x=90.0 + 2.0 + i * 3.0, y=150.0, growth=1.0)   # downwind column
            west.append(s.world.add(fw))
            east.append(s.world.add(fe))
        s.world.add(Food(x=90.0, y=150.0, growth=1.0))
        s.fires.append({"x": 90.0, "y": 150.0, "r": 2.5, "ttl": 10_000})
        for _ in range(16):
            s.step()
        alive_west = sum(1 for f in west if f.id in s.world.entities)
        alive_east = sum(1 for f in east if f.id in s.world.entities)
        return 12 - alive_west, 12 - alive_east

    burned_west, burned_east = burn_east_vs_west()
    assert burned_east > burned_west, (burned_east, burned_west)
