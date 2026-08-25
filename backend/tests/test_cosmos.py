"""§AQ PH-8/9/10 — seismic waves, electrostatics & cosmology.

Earthquakes with high-caste early warning, finite-speed news, lightning
strikes, the priest's bio-electric calm, totem resonance, hidden anomaly
zones, the law-change shimmer, roof shadow and the dawn sun edge.
"""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import (
    ANOMALY_RADIUS,
    HEAT_STROKE_TICKS,
    HYPOTHERMIA_TEMP,
    LAW_WAVE_TICKS,
    PRIEST_AURA_RADIUS,
    QUAKE_WARN_TICKS,
    SIGNALS_MAX,
    TORPOR_BURN_MULT,
    Simulation,
)


def cosmos_cfg(**kw) -> Config:
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
        communication_enabled=True,
        knowledge_enabled=False,
        schism_enabled=False,
        age_enabled=False,
        rivers_enabled=False,
        relief_enabled=False,
        theology_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


# ------------------------------------------------------------- PH-8 seismic

def test_earthquake_shakes_bodies_and_stone():
    s = Simulation(cosmos_cfg(earthquake_enabled=True, earthquake_rate=1.0,
                              structural_enabled=True))
    victim = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                  lifespan=100000.0, health=50.0, speed=0.0))
    h = s.world.add(House(x=210.0, y=150.0, size=8.0, material="wood"))
    h.hp = 60.0
    rock = {"x": 190.0, "y": 150.0, "r": 3.0}
    s.rocks.append(rock)
    s._refresh_cache()
    s.world.rebuild_index()
    s._do_earthquake(200.0, 150.0, 7.0)
    kinds = [e.payload.get("kind") for e in s.history if e.type == "disaster"]
    assert "earthquake" in kinds
    assert victim.health < 50.0 or victim.id not in s.world.entities
    assert h.hp < 60.0 or h.is_ruin  # weakened roofs fall
    assert rock not in s.rocks or len(s.rocks) > 1  # stone cracks or thrusts


def test_high_castes_feel_the_quake_coming():
    s = Simulation(cosmos_cfg(earthquake_enabled=True, earthquake_rate=1.0))
    elder = s.world.add(Creature(x=205.0, y=150.0, sides=5, caste="Professional",
                                 energy=90.0, lifespan=100000.0))
    peasant = s.world.add(Creature(x=195.0, y=150.0, sides=3, caste="Soldier",
                                   energy=90.0, lifespan=100000.0))
    s._refresh_cache()
    s.world.rebuild_index()
    s.pending_quake = {"x": 200.0, "y": 150.0, "mag": 6.0,
                       "hit_tick": s.tick + QUAKE_WARN_TICKS, "warned": False}
    s._update_seismic()  # warning phase
    assert elder.panic_ticks > 0, "the Professional never felt the deep hum"
    assert peasant.panic_ticks == 0, "the Soldier felt it too early"
    assert s.pending_quake is not None  # the shock itself still pending
    s.tick = s.pending_quake["hit_tick"]
    s._update_seismic()
    assert s.pending_quake is None  # the quake landed


def test_news_travels_at_finite_speed():
    cfg = cosmos_cfg(signal_speed=8.0, signal_radius=30.0)
    s = Simulation(cfg)
    far = s.world.add(Creature(x=226.0, y=150.0, energy=90.0,
                               lifespan=100000.0, speed=0.6))
    s.signals.append({"x": 200.0, "y": 150.0, "kind": "alarm", "sender": 0,
                      "clan_id": None, "ttl": 30, "born_tick": s.tick})
    houses: list = []
    # the wavefront (speed 8) needs 4 ticks to cover the 26-unit gap:
    # pinned updates show stillness first, consistent flight once it lands
    def pinned_away() -> float:
        far.x, far.y = 226.0, 150.0
        s._update_creature(far, houses, 0.5, False, 1.0, 1.0, {})
        dx, _ = s.world.delta(far.x, far.y, 200.0, 150.0)
        return dx - 26.0

    early = sum(pinned_away() for _ in range(3))
    s.tick += 4
    late = sum(pinned_away() for _ in range(6))
    assert early < 1.0, "the far ear reacted before the wavefront arrived"
    assert late > 1.0, "the alarm never landed" 


# ---------------------------------------------------------- PH-9 electrostatics

def test_lightning_strikes_kill_and_scorch():
    s = Simulation(cosmos_cfg(weather_enabled=True, lightning_enabled=True,
                              lightning_strike_rate=1.0, wildfire_enabled=False))
    unlucky = s.world.add(Creature(x=100.0, y=100.0, energy=90.0,
                                   lifespan=100000.0, speed=0.0))
    s.weather = "storm"
    s._rand_pos = lambda: (100.0, 100.0)  # aim the sky
    s._refresh_cache()
    s.world.rebuild_index()
    s._update_lightning()
    kinds = [e.payload.get("kind") for e in s.history if e.type == "disaster"]
    assert "lightning" in kinds
    assert s.lightning, "no bolt visual"
    assert unlucky.id not in s.world.entities
    assert s._death_counts.get("lightning", 0) >= 1


def test_priest_aura_calms_the_nearby():
    s = Simulation(cosmos_cfg())
    priest = s.world.add(Creature(x=200.0, y=150.0, sides=24, caste="Priest",
                                  energy=90.0, lifespan=100000.0))
    flock = s.world.add(Creature(x=203.0, y=150.0, energy=90.0, lifespan=100000.0))
    cid = s._new_clan(priest)
    priest.clan_id = cid
    flock.clan_id = cid
    s.clans[cid]["faith"] = 100.0
    s._refresh_cache()
    s.world.rebuild_index()
    near = s._effective_fear_radius(flock)
    far_body = s.world.add(Creature(x=260.0, y=150.0, energy=90.0, lifespan=100000.0))
    far_body.clan_id = cid
    s._refresh_cache()
    far_r = s._effective_fear_radius(far_body)
    assert near < far_r, "the priest's field calms nobody"


def test_totem_resonance_and_rival_interference():
    s = Simulation(cosmos_cfg())
    c1 = s._new_clan(None)
    c2 = s._new_clan(None)
    s.clans[c1]["totem"] = "Wolf"
    s.clans[c2]["totem"] = "Wolf"
    s.clans[c1]["shrine_level"] = 1
    s.clans[c2]["shrine_level"] = 1
    # co-located shrines via main houses
    h1 = s.world.add(House(x=100.0, y=100.0, size=8.0))
    h2 = s.world.add(House(x=108.0, y=100.0, size=8.0))
    h1.clan_id, h2.clan_id = c1, c2
    s._set_main_house_for_clan(c1, h1)
    s._set_main_house_for_clan(c2, h2)
    s.clans[c1]["main_house_id"] = h1.id
    s.clans[c2]["main_house_id"] = h2.id
    s.relations[(c1, c2)] = 60  # allies
    s._totem_mult_cache = {}
    m_allied = s._totem_mult(c1)
    assert m_allied > 1.0, "same-god allied shrines never resonated"
    # now rivals
    s.relations[(c1, c2)] = -80
    s._totem_mult_cache = {}
    m_rival = s._totem_mult(c1)
    assert m_rival < m_allied, "rival proximity failed to dim the aura"


def test_anomalies_bend_physics_and_get_discovered():
    s = Simulation(cosmos_cfg(anomaly_count=0))
    s.anomalies = [{"x": 200.0, "y": 150.0, "kind": "fertile",
                    "discovered": False}]
    # fertile ground grows strange and lush
    sprout = s.world.add(Food(x=200.0, y=150.0, growth=0.1))
    stray = s.world.add(Food(x=330.0, y=270.0, growth=0.1))
    tod_len = max(1, s.config.day_length)
    s.tick = int(0.25 * tod_len)
    s._refresh_cache()
    s.world.rebuild_index()
    s._update_plants()
    assert sprout.growth > stray.growth
    # a skilled forager walking in discovers it
    forager = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                   lifespan=100000.0))
    forager.skills["foraging"] = 5.0
    s._refresh_cache()
    s.world.rebuild_index()
    s._update_anomaly_discovery()
    assert s.anomalies[0]["discovered"]
    kinds = [e.type for e in s.history]
    assert "anomaly" in kinds


def test_law_change_sends_a_shimmer_wave():
    s = Simulation(cosmos_cfg())
    assert s.law_wave is None
    s.on_law_change(["food_count"])
    assert s.law_wave is not None
    front0 = s._law_wave_front()
    s.tick += LAW_WAVE_TICKS // 2
    front1 = s._law_wave_front()
    assert front1 > front0  # the front sweeps west → east
    s.tick += LAW_WAVE_TICKS
    s._update_law_wave()
    assert s.law_wave is None  # the shimmer fades


def test_roof_shade_and_dawn_sun_edge():
    s = Simulation(cosmos_cfg(anomaly_count=0))
    h = s.world.add(House(x=200.0, y=150.0, size=8.0, material="stone"))
    shaded = s.world.add(Food(x=200.0 - 8.0 - 4.0, y=150.0, growth=0.1))  # west of roof
    open_sky = s.world.add(Food(x=260.0, y=150.0, growth=0.1))
    tod_len = max(1, s.config.day_length)
    s.tick = int(0.25 * tod_len)  # noon: full shadow cast
    s._refresh_cache()
    s.world.rebuild_index()
    s._update_plants()
    assert shaded.growth < open_sky.growth
    # dawn rim: a sprout at the east rim at sunrise outgrows a midland twin
    s2 = Simulation(cosmos_cfg(anomaly_count=0))
    rim = s2.world.add(Food(x=s2.config.width - 6.0, y=150.0, growth=0.1))
    mid = s2.world.add(Food(x=200.0, y=150.0, growth=0.1))
    s2.tick = int(0.24 * max(1, s2.config.day_length))  # just after sunrise
    s2._refresh_cache()
    s2.world.rebuild_index()
    s2._update_plants()
    assert rim.growth >= mid.growth
