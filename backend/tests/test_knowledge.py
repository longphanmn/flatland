"""§X Communication II — knowledge, teaching & mobbing.

Creatures learn typed facts from experience (food spots, danger zones, enemy
clans, safe roofs), teach their clan via knowledge signals (rumors arrive at
half confidence per hop), and rally to a clan-mate's help call to mob the
attacker. The union of member knowledge surfaces as the clan's memory.
"""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import Simulation


def know_cfg(**kw) -> Config:
    kw.setdefault("rivers_enabled", False)
    zeros = dict(
        seed=12,
        width=60.0,
        height=60.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        weather_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        communication_enabled=True,
        knowledge_enabled=True,
        knowledge_ttl=600,
        knowledge_share_rate=1.0,
        perceive_radius=20.0,
        signal_radius=15.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def clan_of(sim: Simulation, *creatures: Creature, cid: int = 1) -> None:
    for c in creatures:
        c.clan_id = cid
    sim.clans[cid] = {
        "name": "Test Clan", "founder_id": creatures[0].id, "born_tick": 0,
        "color": "#ffd166", "leader_id": creatures[0].id,
        "specialization": {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34},
        "culture": "Test Rite", "culture_id": cid,
    }


def test_learns_food_and_danger_from_experience():
    s = Simulation(know_cfg(predation_enabled=True))
    c = s.world.add(Creature(x=20.0, y=30.0, angle=0.0, energy=100.0, age=1000, lifespan=10000.0))
    meal = s.world.add(Food(x=24.0, y=30.0, growth=1.0))  # within sight
    hunter = s.world.add(Creature(x=16.0, y=30.0, sides=6, caste="Predator",
                                  is_predator=True, energy=100.0, lifespan=100000.0,
                                  speed=0.0, clan_id=0))
    for _ in range(4):
        if c.id not in s.world.entities:
            break
        s.step()

    food_fact = c.facts.get("food")
    assert food_fact is not None and "x" in food_fact  # saw the plant
    # fleeing outranks eating while the hunter watches — both facts still land:
    danger_fact = c.facts.get("danger")
    assert danger_fact is not None and "x" in danger_fact  # …and the predator

def test_knowledge_fades_after_ttl():
    s = Simulation(know_cfg(knowledge_ttl=50))
    c = s.world.add(Creature(x=20.0, y=30.0, angle=0.0, energy=100.0, age=1000, lifespan=10000.0))
    s.world.add(Food(x=24.0, y=30.0, growth=1.0))
    s.step()
    assert c.facts.get("food") is not None
    s.tick += 51  # fast-forward past the ttl
    assert s._fact_fresh(c, "food") is None  # the memory faded


def test_teaching_shares_food_fact_at_half_confidence():
    # B is outside its own sight of the meal but inside A's voice
    s = Simulation(know_cfg(perceive_radius=8.0, signal_radius=15.0))
    a = s.world.add(Creature(x=20.0, y=30.0, angle=0.0, energy=100.0, age=1000, lifespan=10000.0))
    b = s.world.add(Creature(x=32.0, y=30.0, shape="line", sides=2, angle=math.pi,
                             energy=100.0, age=1000, lifespan=10000.0))
    clan_of(s, a, b)
    s.world.add(Food(x=22.0, y=30.0, growth=1.0))  # only A sees this

    for _ in range(6):
        s.step()
        if "food" in b.facts:
            break
    heard = b.facts.get("food")
    assert heard is not None  # A taught B
    assert heard["conf"] <= 0.5  # rumor: half confidence per hop
    assert abs(heard["x"] - 22.0) < 3.0  # points at the real meal


def test_rumor_confidence_halves_each_hop():
    s = Simulation(know_cfg(perceive_radius=8.0, signal_radius=14.0))
    a = s.world.add(Creature(x=10.0, y=30.0, angle=0.0, energy=100.0, age=1000, lifespan=10000.0))
    b = s.world.add(Creature(x=18.0, y=30.0, shape="line", sides=2, angle=0.0,
                             energy=100.0, age=1000, lifespan=10000.0))
    c2 = s.world.add(Creature(x=26.0, y=30.0, sides=5, angle=math.pi,
                              energy=100.0, age=1000, lifespan=10000.0))
    clan_of(s, a, b, c2)
    s.world.add(Food(x=12.0, y=30.0, growth=1.0))  # only A sees it

    hops = 0
    for _ in range(40):
        s.step()
        hops += 1
        if "food" in c2.facts:
            break
    far = c2.facts.get("food")
    assert far is not None  # the fact travelled two hops
    assert far["conf"] <= 0.25  # halved twice — vaguer than firsthand


def test_war_loser_learns_enemy_clan():
    s = Simulation(know_cfg(war_enabled=True, attack_damage=10.0,
                            rivalry_threshold=-50, relation_drift_rate=0))
    a = s.world.add(Creature(x=30.0, y=30.0, sides=4, energy=100.0, health=100.0,
                             age=5000, lifespan=20000.0))
    rival = s.world.add(Creature(x=30.6, y=30.0, sides=4, energy=100.0, health=100.0,
                                 age=5000, lifespan=20000.0))
    clan_of(s, a, cid=1)
    rival.clan_id = 2
    s.clans[2] = {"name": "Foes", "founder_id": rival.id, "born_tick": 0,
                  "color": "#06d6a0", "leader_id": rival.id}
    s.relations[(1, 2)] = -80  # rivals → war on contact

    s.step()
    enemies_a = a.facts.get("enemies") or {}
    enemies_r = rival.facts.get("enemies") or {}
    assert 2 in enemies_a  # loser learned who struck
    assert 1 in enemies_r  # winner did too
    memory = s.clan_knowledge()
    assert 2 in memory[1]["enemy_clans"] and 1 in memory[2]["enemy_clans"]


def test_help_call_mobilises_clan_and_softens_blows():
    def world(with_defenders: bool):
        s = Simulation(know_cfg(war_enabled=True, attack_damage=25.0,
                                rivalry_threshold=-50, relation_drift_rate=0,
                                help_radius=12.0, defense_weight=1.0))
        victim = s.world.add(Creature(x=30.0, y=30.0, sides=3, energy=100.0, health=100.0,
                                      age=5000, lifespan=20000.0))
        attacker = s.world.add(Creature(x=31.0, y=30.0, sides=4, energy=100.0, health=100.0,
                                        age=5000, lifespan=20000.0))
        clan_of(s, victim, cid=1)
        attacker.clan_id = 2
        s.clans[2] = {"name": "R", "founder_id": attacker.id, "born_tick": 0,
                      "color": "#06d6a0", "leader_id": attacker.id}
        s.relations[(1, 2)] = -80
        mates: list[Creature] = []
        if with_defenders:
            for i in range(3):
                m = s.world.add(Creature(x=26 + i * 1.2, y=27.0, sides=3, energy=100.0,
                                         health=100.0, age=5000, lifespan=20000.0))
                m.clan_id = 1
                mates.append(m)
        return s, victim, attacker, mates

    s_alone, v_alone, _, _ = world(False)
    s_mob, v_mob, atk, mates = world(True)

    saw_help_call = False
    for _ in range(3):
        s_alone.step()
        s_mob.step()
        saw_help_call = saw_help_call or any(
            sg.get("kind") == "help" for sg in s_mob.signals
        )
        if v_alone.id not in s_alone.world.entities and v_mob.id not in s_mob.world.entities:
            break

    assert saw_help_call  # the wounded creature called its clan to arms

    # defenders near the fight soften the blows: the mobbed victim keeps more skin
    if v_alone.id in s_alone.world.entities and v_mob.id in s_mob.world.entities:
        assert v_mob.health > v_alone.health
    # and at least one defender converged on the attacker
    assert any(
        m.id in s_mob.world.entities
        and s_mob.distance(m.x, m.y, atk.x, atk.y) < 6.0
        for m in mates
    )


def test_safe_roof_learned_while_sleeping():
    s = Simulation(know_cfg(day_length=40))
    c = s.world.add(Creature(x=25.0, y=25.0, angle=0.0, energy=90.0, age=1000, lifespan=20000.0))
    house = House(x=25.0, y=25.0, size=9.0, door_width=3.0, door_side="south")
    house.clan_id = 0
    s.world.add(house)

    for _ in range(45):
        s.step()
        if c.facts.get("safe"):
            break
    safe = c.facts.get("safe")
    assert safe is not None  # sheltered → knows a roof
    assert abs(safe["x"] - 25.0) < 2.0 and abs(safe["y"] - 25.0) < 2.0


def test_knowledge_laws_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    client.headers["X-God-Key"] = "test-key"
    r = client.post(
        "/api/laws?persist=false",
        json={"knowledge_share_rate": 0.2, "defense_weight": 1.5,
              "knowledge_ttl": 900, "help_radius": 20},
    )
    assert r.status_code == 200
    laws = r.json()
    assert laws["knowledge_share_rate"] == 0.2
    assert laws["defense_weight"] == 1.5
    assert laws["knowledge_ttl"] == 900
    assert laws["help_radius"] == 20
