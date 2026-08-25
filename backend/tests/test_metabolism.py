"""§AQ PH-7 — metabolic extremes: cold-torpor shutdown and heat prostration."""

import math

from app.config import Config
from app.entities import Creature
from app.simulation import (
    HEAT_STROKE_TICKS,
    HYPOTHERMIA_TEMP,
    TORPOR_BURN_MULT,
    Simulation,
)


def meta_cfg(**kw) -> Config:
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
        relief_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def freeze_world(s: Simulation) -> None:
    s.temperature_grid = [-6.0] * len(s.temperature_grid)


def test_torpor_shuts_the_body_down_in_killing_cold():
    s = Simulation(meta_cfg())
    freeze_world(s)
    assert s.ambient_at(200.0, 150.0) < HYPOTHERMIA_TEMP
    body = s.world.add(Creature(x=200.0, y=150.0, energy=5.0,
                                lifespan=100000.0, speed=0.8))
    assert body.energy / 100.0 <= 0.10
    houses: list = []
    e0 = body.energy
    x0 = body.x
    s._update_creature(body, houses, 0.5, False, 1.0, 1.0, {})
    # still, and burning at a fraction of the awake rate
    assert body.x == x0
    burn = e0 - body.energy
    assert burn <= 0.025 * TORPOR_BURN_MULT * 1.5 + 1e-9
    # a fed body in the same cold keeps moving
    hale = s.world.add(Creature(x=210.0, y=150.0, energy=90.0,
                                lifespan=100000.0, speed=0.8))
    h0 = hale.x
    s._update_creature(hale, houses, 0.5, False, 1.0, 1.0, {})
    assert hale.x != h0


def test_warm_air_releases_the_torpid():
    s = Simulation(meta_cfg())
    body = s.world.add(Creature(x=200.0, y=150.0, energy=5.0,
                                lifespan=100000.0, speed=0.8))
    houses: list = []
    x0 = body.x
    s._update_creature(body, houses, 0.5, False, 1.0, 1.0, {})
    assert body.x != x0  # mild air: no torpor


def test_heat_stroke_drops_the_body_until_it_cools():
    s = Simulation(meta_cfg())
    cooked = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                  lifespan=100000.0, speed=0.8))
    cooked.body_temp = 42.0
    cooked.health = 90.0
    cooked.heat_stroke_ticks = HEAT_STROKE_TICKS
    houses: list = []
    x0 = cooked.x
    s._update_creature(cooked, houses, 0.5, False, 1.0, 1.0, {})
    assert cooked.x == x0  # prostrate: refuses to move
    assert cooked.emote == "sleep"
    # cooling below the hysteresis releases it (the reset lands late in the
    # tick: the first update clears the counter, the second walks again)
    cooked.body_temp = 28.0
    s._update_creature(cooked, houses, 0.5, False, 1.0, 1.0, {})
    assert cooked.heat_stroke_ticks == 0
    x1 = cooked.x
    s._update_creature(cooked, houses, 0.5, False, 1.0, 1.0, {})
    assert cooked.x != x1
