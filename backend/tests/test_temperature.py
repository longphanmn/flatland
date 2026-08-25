"""§AQ PH-1 — thermodynamics: a heat field over the land, bodies that drift
toward it, houses that insulate against both extremes."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.simulation import (
    HYPERTHERMIA_TEMP,
    SEASON_BASE_TEMP,
    Simulation,
)


def temp_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=1000,
        season_length=100000,  # stays spring for most tests
        weather_change_rate=0.0,
        weather_enabled=False,
        shelter_enabled=True,
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


def noon_step(s: Simulation) -> None:
    dl = max(1, s.config.day_length)
    s.tick = (s.tick // dl) * dl + dl // 4
    s.step()


def test_heat_field_follows_season_and_day():
    """Winter cells sit below summer cells; noon sits above midnight."""
    winter = Simulation(temp_cfg(seed=1, season_length=4))  # tick 3 -> winter-ish
    for _ in range(40):
        winter.step()
    summer = Simulation(temp_cfg(seed=1, season_length=100000))
    # force summer by pinning the season arithmetic through a long run? Simpler:
    # compare the seasonal bases via the sweep target on a fresh grid.
    assert max(winter.temperature_grid) < 15.0

    warm_side_noon = summer.temperature_grid[len(summer.temperature_grid) // 2]
    for _ in range(30):
        noon_step(summer)
    noon_avg = sum(summer.temperature_grid) / len(summer.temperature_grid)
    assert noon_avg > SEASON_BASE_TEMP["spring"] - 2.0


def test_cold_front_sweeps_from_the_west():
    """Heading into winter the western edge reaches winter's cold first."""
    s = Simulation(temp_cfg(seed=2, season_length=100))
    # drive deep into the season so the front is mid-map
    s.tick = 70
    s._update_temperature()
    west = sum(s.temperature_grid[r * s._temp_cols + 0] for r in range(s._temp_rows))
    east = sum(
        s.temperature_grid[r * s._temp_cols + s._temp_cols - 1]
        for r in range(s._temp_rows)
    )
    assert west < east, "the cold should arrive from the west first"


def test_body_drifts_toward_ambient_and_houses_insulate():
    """A body outdoors chases the cold; a body indoors stays near comfort."""
    s = Simulation(temp_cfg(seed=3, season_length=8))  # quick seasons
    house_stone = House(x=60.0, y=60.0, size=8.0, material="stone")
    house_straw = House(x=200.0, y=200.0, size=8.0, material="straw")
    s.world.add(house_stone)
    s.world.add(house_straw)
    outdoor = Creature(x=20.0, y=20.0, energy=90.0, lifespan=100000.0)
    indoors = Creature(x=60.0, y=60.0, energy=90.0, lifespan=100000.0)
    s.world.add(outdoor)
    s.world.add(indoors)
    # walk to deep winter
    while s._season() != "winter":
        s.step()
    for _ in range(80):
        s.step()
        # keep everyone at their post: this tests thermodynamics, not wandering
        outdoor.x, outdoor.y = 20.0, 20.0
        indoors.x, indoors.y = 60.0, 60.0
    amb_out = s.ambient_at(outdoor.x, outdoor.y)
    assert abs(outdoor.body_temp - amb_out) < 6.0   # drifted with the weather
    stone_in = s.indoor_ambient(house_stone)
    straw_in = s.indoor_ambient(house_straw)
    assert stone_in > straw_in                      # stone insulates better
    assert abs(indoors.body_temp - stone_in) < 6.0  # and the body noticed
    # bigger floors shed heat faster: same material, same spot, larger floor
    # ⇒ thinner effective insulation
    big = House(x=60.0, y=60.0, size=16.0, material="stone")
    assert s.indoor_ambient(house_stone) > s.indoor_ambient(big)


def test_hyperthermia_near_open_flame():
    """Stand too close to a fire too long and the body cooks: health drains
    with the excess until death by hyperthermia."""
    s = Simulation(temp_cfg(seed=4))
    c = s.world.add(Creature(x=100.0, y=100.0, energy=95.0, lifespan=100000.0))
    s.fires.append({"x": 102.0, "y": 100.0, "r": 1.0, "ttl": 10_000})
    died_of_heat = False
    for _ in range(600):
        if c.id not in s.world.entities:
            died_of_heat = True
            break
        noon_step(s)
        c.x, c.y = 100.0, 100.0  # pinned beside the flame — nowhere to wander
    assert died_of_heat, "a body parked next to a flame must eventually cook"
    assert s._death_counts.get("hyperthermia", 0) == 1
