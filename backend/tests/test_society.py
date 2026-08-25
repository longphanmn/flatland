"""§I society tests: flocking instincts and clan relations."""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food
from app.simulation import Simulation


def social_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        weather_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def kin_pair(sim: Simulation, clan: int) -> tuple[Creature, Creature]:
    """Two same-clan creatures facing away from each other."""
    a = sim.world.add(Creature(x=25.0, y=25.0, sides=4, angle=0.0, energy=100.0,
                               clan_id=clan, lifespan=10000.0))
    b = sim.world.add(Creature(x=35.0, y=25.0, sides=4, angle=math.pi, energy=100.0,
                               clan_id=clan, lifespan=10000.0))
    return a, b


def test_relations_drift_toward_neutrality():
    s = Simulation(social_cfg(seed=1, relation_drift_rate=2))
    pair = (1, 2)
    s.relations[pair] = -6
    for _ in range(4):
        s._update_relations()
    assert s.relations.get(pair, 0) == pytest.approx(0)  # drift clamps at 0, never overshoots
    for _ in range(5):
        s._update_relations()
    assert s.relations.get(pair, 0) == 0  # never overshoots into the opposite sign
    assert pair not in s.relations  # AA: neutral pairs are forgotten, not hoarded


def test_shared_feasting_bonds_clans_and_forges_alliance():
    s = Simulation(social_cfg(seed=2, flock_radius=10.0, alliance_threshold=2,
                              relation_drift_rate=0))
    # two clanless-by-config creatures; assign clans manually (1 and 2)
    a = s.world.add(Creature(x=20.0, y=20.0, sides=4, angle=0.0, energy=40.0,
                             clan_id=1))
    b = s.world.add(Creature(x=21.0, y=20.0, shape="line", sides=2, angle=0.0,
                             energy=40.0, clan_id=2))
    # one meal each, side by side
    s.world.add(Food(x=20.3, y=20.0, growth=1.0))
    s.world.add(Food(x=21.3, y=20.0, growth=1.0))
    s.step()
    assert a.meals == 1 and b.meals == 1
    assert s.relations[(1, 2)] == 2  # feasting together forged a bond
    ev = [e for e in s.history if e.type == "alliance"]
    assert len(ev) == 1 and ev[0].payload["a"] == 1 and ev[0].payload["b"] == 2


def test_cohesion_pulls_kin_together():
    def world(weight: float):
        s = Simulation(social_cfg(seed=3, cohesion_weight=weight))
        a, b = kin_pair(s, clan=1)
        return s, a, b

    s1, a1, b1 = world(2.0)
    s0, a0, b0 = world(0.0)  # control: no flock instinct
    for _ in range(12):
        s1.step()
        s0.step()
    gap_cohesion = s1.distance(a1.x, a1.y, b1.x, b1.y)
    gap_control = s0.distance(a0.x, a0.y, b0.x, b0.y)
    assert gap_cohesion < gap_control


def test_separation_pushes_overlapping_bodies_apart():
    def world(weight: float):
        s = Simulation(social_cfg(seed=4, separation_weight=weight,
                                  energy_decay_per_tick=0.0))
        a = s.world.add(Creature(x=25.0, y=25.0, sides=4, angle=0.0,
                                 energy=100.0, speed=0.5, lifespan=100000.0,
                                 age=1000))
        b = s.world.add(Creature(x=25.6, y=25.1, sides=4, angle=math.pi,
                                 energy=100.0, speed=0.5, lifespan=100000.0,
                                 age=1000))
        return s, a, b

    s_on, a_on, b_on = world(2.0)
    s_off, a_off, b_off = world(0.0)
    for _ in range(8):
        s_on.step()
        s_off.step()
    d_on = s_on.distance(a_on.x, a_on.y, b_on.x, b_on.y)
    d_off = s_off.distance(a_off.x, a_off.y, b_off.x, b_off.y)
    assert d_on > d_off  # personal space won


def test_alignment_converges_headings():
    def world(weight: float):
        s = Simulation(social_cfg(seed=5, alignment_weight=weight,
                                  cohesion_weight=0.0, separation_weight=0.0,
                                  flock_radius=10.0, energy_decay_per_tick=0.0))
        a = s.world.add(Creature(x=24.0, y=25.0, sides=4, angle=0.7,
                                 energy=100.0, speed=0.55, lifespan=100000.0,
                                 age=1000))
        b = s.world.add(Creature(x=26.0, y=25.0, sides=4, angle=-0.7,
                                 energy=100.0, speed=0.55, lifespan=100000.0,
                                 age=1000))
        return s, a, b

    s_on, a_on, b_on = world(2.0)
    s_off, a_off, b_off = world(0.0)
    start_diff = abs(((a_on.angle - b_on.angle + math.pi) % (2 * math.pi)) - math.pi)
    for _ in range(10):
        s_on.step()
        s_off.step()

    def heading_gap(sa: float, sb: float) -> float:
        return abs(((sa - sb + math.pi) % (2 * math.pi)) - math.pi)

    assert heading_gap(a_on.angle, b_on.angle) < heading_gap(a_off.angle, b_off.angle)
    assert start_diff > 0.5


def test_relations_travel_in_snapshot():
    s = Simulation(social_cfg(seed=6))
    s.relations[(1, 2)] = -70
    snap = s.snapshot()
    assert {"a": 1, "b": 2, "score": -70} in snap.relations


def test_rivalry_event_when_scores_crash():
    s = Simulation(social_cfg(seed=7, rivalry_threshold=-50, relation_drift_rate=0))
    s.relations[(2, 3)] = -49
    s._bump_relation(3, 2, -5)  # -54: crosses the rivalry line
    for _ in range(2):  # drift is off; the zone check runs in relations update
        s._update_relations()
    riv = [e for e in s.history if e.type == "rivalry"]
    assert len(riv) >= 1 and riv[0].payload["score"] <= -50
