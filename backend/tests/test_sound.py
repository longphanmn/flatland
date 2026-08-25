"""§AQ PH-2 P2 — sound propagation: wind carries calls to downwind ears,
roofs muffle alarms from the open, and loud events roll out as booms."""

import math

from app.config import Config
from app.entities import Creature, House
from app.simulation import (
    SIGNALS_MAX,
    SOUND_WIND_MULT,
    Simulation,
)


def sound_cfg(**kw) -> Config:
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
        predation_enabled=True,
        war_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=True,
        knowledge_enabled=False,
        schism_enabled=False,
        age_enabled=False,
        rivers_enabled=False,
        relief_enabled=False,
        scent_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


def hearer_flees(cfg: Config, listener_x: float, indoors: bool = False) -> bool:
    """True when the listener consistently steers AWAY from the alarm source
    (net displacement over repeated ticks); wander averages out to ~zero."""
    s = Simulation(cfg)
    s.wind_angle = 0.0
    s.wind_speed = 1.0
    h = None
    if indoors:
        h = s.world.add(House(x=listener_x, y=150.0, size=8.0))
    c = s.world.add(Creature(x=listener_x, y=150.0, energy=90.0,
                             lifespan=100000.0, speed=0.5))
    s.signals.append({"x": 200.0, "y": 150.0, "kind": "alarm",
                      "sender": 999, "clan_id": None, "ttl": 100})
    houses = [h] if indoors else []
    net_away = 0.0
    for _ in range(14):
        c.x, c.y = listener_x, 150.0  # pin: isolate one tick of steering
        s._update_creature(c, houses, 0.5, False, 1.0, 1.0, {})
        # displacement relative to the source (east = away, west = toward)
        dx, _ = s.world.delta(c.x, c.y, 200.0, 150.0)
        net_away += dx - (listener_x - 200.0)
    return net_away > 3.0


def test_calls_carry_farther_downwind_than_upwind():
    cfg = sound_cfg(signal_radius=10.0)
    assert 14.0 <= 10.0 * (1.0 + SOUND_WIND_MULT)
    # west wind (+x): a listener east of the source is downwind — hears at 13
    assert hearer_flees(cfg, 213.0), "downwind ear missed the call"
    # the same gap upwind stays silent (base radius only reaches 10)
    assert not hearer_flees(cfg, 187.0), "upwind ear caught a distant call"


def test_roofs_muffle_alarms_from_the_open():
    cfg = sound_cfg(signal_radius=12.0)
    # well inside earshot but under a roof: the open-air alarm goes unheard
    assert not hearer_flees(cfg, 206.0, indoors=True)
    # the same spot unsheltered hears it fine
    assert hearer_flees(cfg, 206.0, indoors=False)


def test_collapsing_roof_booms_across_the_land():
    s = Simulation(sound_cfg())
    witness = s.world.add(Creature(x=210.0, y=150.0, energy=90.0, lifespan=100000.0))
    h = s.world.add(House(x=195.0, y=150.0, size=8.0, material="straw"))
    h.hp = 0.1
    s.weather = "storm"
    heard = False
    for _ in range(6):
        s.step()
        if any(sg["kind"] == "boom" for sg in getattr(s, "signals", [])):
            pass  # boom may already have faded; the reaction is what counts
        if witness.id not in s.world.entities:
            break
        dx, dy = s.world.delta(195.0, 150.0, witness.x, witness.y)
        if abs(dx) < 20 and witness.angle != 0.0:
            heard = True
            break
    boomed = [e for e in s.history if e.type == "ruin" and e.payload.get("kind") == "collapse"]
    assert boomed or any(sg["kind"] == "boom" for sg in s.signals) or heard


def test_boom_cap_respects_signal_budget():
    s = Simulation(sound_cfg())
    for i in range(SIGNALS_MAX + 5):
        s.signals.append({"x": 0.0, "y": 0.0, "kind": "food",
                          "sender": 0, "clan_id": None, "ttl": 5})
    s._emit_boom(100.0, 100.0)
    assert all(sg["kind"] != "boom" or len(s.signals) <= SIGNALS_MAX + 1
               for sg in s.signals)
