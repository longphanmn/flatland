"""§AB Politics — coalitions, leader agency, resource sharing, betrayal.

Leaders propose blocs and turn on allies; strike one coalition member and
every mate turns on you; the settlement larder buffers famine; vassals pay
tribute; the unhappy defect to healthier banners. God sees plots, never vetoes.
"""

import pytest

import app.simulation as simmod
from app.config import Config
from app.entities import Creature, House
from app.simulation import GRANARY_WITHDRAW_RATE, REPUBLIC_LARDER_EFF, Simulation


def pol_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        seed=31,
        width=80.0,
        height=80.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        weather_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        shelter_enabled=False,
        territory_enabled=False,
        schism_enabled=False,
        culture_enabled=False,
        age_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(s: Simulation, cid: int, leader: Creature | None = None) -> None:
    s.clans[cid] = {
        "name": f"Clan {cid}", "founder_id": leader.id if leader else cid,
        "born_tick": 0, "color": "#ffd166",
        "leader_id": leader.id if leader else None,
        "coalition_id": None, "larder": 0.0, "tribute_to": None,
    }


def spawn(s: Simulation, x, y, *, clan=None, energy=100.0, trait=None, health=100.0, sides=4):
    c = s.world.add(Creature(x=x, y=y, sides=sides, energy=energy, health=health,
                             age=1000, lifespan=20000.0, speed=0.0, trait=trait))
    if clan is not None:
        c.clan_id = clan
    return c


def test_coalition_forms_and_dissolves_when_soured(monkeypatch):
    monkeypatch.setattr(simmod, "COALITION_FORM_CHANCE", 1.0)
    s = Simulation(pol_cfg(relation_drift_rate=0))
    a = spawn(s, 20.0, 20.0, clan=1)
    b = spawn(s, 40.0, 20.0, clan=2)
    make_clan(s, 1, a)
    make_clan(s, 2, b)
    s.relations[s._relation_pair(1, 2)] = 60
    s._relation_zones[s._relation_pair(1, 2)] = 1

    s.step()

    assert len(s.coalitions) == 1
    coal = next(iter(s.coalitions.values()))
    assert sorted(coal["members"]) == [1, 2]
    formed = [e for e in s.history if e.type == "coalition_formed"]
    assert formed and sorted(formed[0].payload["members"]) == [1, 2]
    assert s._clan_coalition[1] == s._clan_coalition[2]

    # relations sour below the friendship floor → the bloc dissolves
    pair = s._relation_pair(1, 2)
    s.relations[pair] = 0
    s.step()
    assert not s.coalitions
    assert 1 not in s._clan_coalition and 2 not in s._clan_coalition
    assert any(e.type == "coalition_dissolved" for e in s.history)


def test_strike_one_member_every_mate_turns_on_you():
    s = Simulation(pol_cfg())
    a = spawn(s, 20.0, 20.0, clan=1)
    b = spawn(s, 40.0, 20.0, clan=2)
    foe = spawn(s, 60.0, 20.0, clan=3)
    make_clan(s, 1, a)
    make_clan(s, 2, b)
    make_clan(s, 3, foe)
    # clan 1 sits in a bloc with clan 2
    s.coalitions[1] = {"name": "Pact", "leader_clan": 1, "members": [1, 2], "born_tick": 0}
    s._clan_coalition[1] = 1
    s._clan_coalition[2] = 1
    s.clans[1]["coalition_id"] = 1
    s.clans[2]["coalition_id"] = 1

    before = s.relations.get(s._relation_pair(3, 2), 0)
    s._mobilise_coalition(3, 1)

    assert s.relations[s._relation_pair(3, 2)] == before - 12


def test_paranoid_leader_betrays_ally(monkeypatch):
    monkeypatch.setattr(simmod, "LEADER_DECISION_CHANCE", 1.0)
    s = Simulation(pol_cfg(betrayal_enabled=True, relation_drift_rate=0))
    leader = spawn(s, 20.0, 20.0, clan=1, trait="paranoid")
    victim = spawn(s, 40.0, 20.0, clan=2)
    make_clan(s, 1, leader)
    make_clan(s, 2, victim)
    s.relations[s._relation_pair(1, 2)] = 60
    s._relation_zones[s._relation_pair(1, 2)] = 1

    s.step()

    betrayals = [e for e in s.history if e.type == "betrayal"]
    assert betrayals and betrayals[0].payload["a"] == 1 and betrayals[0].payload["b"] == 2
    assert s.relations[s._relation_pair(1, 2)] <= 60 - 95 + 5  # slammed toward hostility


def test_weakened_peaceful_leader_sues_for_peace(monkeypatch):
    """§AS L-4: close chiefs sign at once; far chiefs send a herald."""
    monkeypatch.setattr(simmod, "LEADER_DECISION_CHANCE", 1.0)
    # — face to face within TALK_RADIUS: immediate treaty —
    s = Simulation(pol_cfg(relation_drift_rate=0))
    leader = spawn(s, 20.0, 20.0, clan=1, trait="peaceful", energy=100.0)
    strong = spawn(s, 23.0, 20.0, clan=2)
    backup = spawn(s, 24.0, 20.0, clan=2)
    make_clan(s, 1, leader)
    make_clan(s, 2, strong)
    s.relations[s._relation_pair(1, 2)] = -80
    s._relation_zones[s._relation_pair(1, 2)] = -1

    s.step()

    peace = [e for e in s.history if e.type == "peace"]
    assert peace and peace[0].payload["a"] == 1 and peace[0].payload["b"] == 2
    assert s.relations[s._relation_pair(1, 2)] >= -80 + 60 - 5

    # — chiefs far apart: a herald is dispatched with the terms —
    monkeypatch.setattr(simmod, "LEADER_DECISION_CHANCE", 1.0)
    s2 = Simulation(pol_cfg(relation_drift_rate=0, envoys_enabled=True))
    l2 = spawn(s2, 20.0, 20.0, clan=1, trait="peaceful", energy=100.0)
    subject = spawn(s2, 21.0, 21.0, clan=1)  # an adult subject carries the banner
    subject.age = 6000
    strong2 = spawn(s2, 40.0, 20.0, clan=2)
    backup2 = spawn(s2, 41.0, 20.0, clan=2)
    make_clan(s2, 1, l2)
    make_clan(s2, 2, strong2)
    s2.relations[s2._relation_pair(1, 2)] = -80
    s2._relation_zones[s2._relation_pair(1, 2)] = -1

    s2.step()

    heralded = any(
        isinstance(m, dict) and m.get("type") == "peace" and m.get("target_clan") == 2
        for c_ in s2.world.creatures()
        if (m := getattr(c_, "mission", None))
    )
    assert heralded, "distant peace rides with a herald"
    assert not [e for e in s2.history if e.type == "peace"], "no instant treaty afar"


def test_bold_leader_declares_war_on_remembered_enemy(monkeypatch):
    monkeypatch.setattr(simmod, "LEADER_DECISION_CHANCE", 1.0)
    s = Simulation(pol_cfg(knowledge_enabled=True, relation_drift_rate=0,
                           rivalry_threshold=-50))
    leader = spawn(s, 20.0, 20.0, clan=1, trait="bold")
    enemy = spawn(s, 40.0, 20.0, clan=2)
    make_clan(s, 1, leader)
    make_clan(s, 2)  # leaderless rival: nobody answers the declaration this tick
    # the clan remembers clan 2 struck them (§X memory feeds the declaration)
    leader.facts["enemies"] = {2: {"tick": s.tick, "conf": 1.0}}

    s.step()

    assert s.relations.get(s._relation_pair(1, 2), 0) <= -45


def test_war_declared_once_per_enemy(monkeypatch):
    """§AB fix: a leader must not re-declare war on the same clan.

    With the default rivalry threshold, one declaration (−50) leaves the pair
    in the neutral zone — before the fix every later decision roll logged
    another "Declared war" against the same enemy.
    """
    monkeypatch.setattr(simmod, "LEADER_DECISION_CHANCE", 1.0)
    s = Simulation(pol_cfg(knowledge_enabled=True, relation_drift_rate=0))
    leader = spawn(s, 20.0, 20.0, clan=1, trait="bold")
    enemy = spawn(s, 40.0, 20.0, clan=2, sides=3)  # different caste: no diplomacy bumps
    make_clan(s, 1, leader)
    make_clan(s, 2)
    leader.facts["enemies"] = {2: {"tick": s.tick, "conf": 1.0}}

    for _ in range(10):
        s.step()

    decls = [h for h in s.clans[1]["history"] if h.get("event") == "war_declared"]
    assert len(decls) == 1
    assert s.relations.get(s._relation_pair(1, 2), 0) <= -45


def test_larder_stores_surplus_from_the_well_fed():
    s = Simulation(pol_cfg(resource_sharing_enabled=True))
    house = House(x=25.0, y=25.0, size=9.0, door_width=3.0, door_side="south")
    house.clan_id = 1
    s.world.add(house)
    full = spawn(s, 25.0, 25.0, clan=1, energy=92.0)  # ratio 0.92 > 0.75
    make_clan(s, 1, full)
    s.tick = 1  # dodge the tribute interval branch

    s._refresh_cache()
    s._update_politics()

    assert s.clans[1]["larder"] > 0  # surplus reached the settlement store
    assert full.energy < 92.0  # the depositor paid for it


def test_starving_members_withdraw_from_the_larder():
    s = Simulation(pol_cfg(resource_sharing_enabled=True))
    house = House(x=25.0, y=25.0, size=9.0, door_width=3.0, door_side="south")
    house.clan_id = 1
    s.world.add(house)
    starved = spawn(s, 25.0, 25.0, clan=1, energy=8.0)  # ratio ≤ starving_ratio
    make_clan(s, 1, starved)
    s.clans[1]["larder"] = 50.0
    s.tick = 1

    s._refresh_cache()
    s._update_politics()

    # §AS L-5: republics portion stores at 1.25× efficiency (3.75/tick)
    assert starved.energy == pytest.approx(8.0 + GRANARY_WITHDRAW_RATE * REPUBLIC_LARDER_EFF, abs=0.01)
    assert s.clans[1]["larder"] == pytest.approx(50.0 - GRANARY_WITHDRAW_RATE * REPUBLIC_LARDER_EFF, abs=0.01)


def test_vassal_pays_tribute_to_protector():
    s = Simulation(pol_cfg(tribute_enabled=True))
    vassal = spawn(s, 20.0, 20.0, clan=1)
    protector = spawn(s, 40.0, 20.0, clan=2)
    make_clan(s, 1, vassal)
    make_clan(s, 2, protector)
    s.clans[1]["tribute_to"] = 2
    s.clans[1]["larder"] = 100.0
    s.clans[2]["larder"] = 0.0
    s.tick = 480  # multiple of TRIBUTE_INTERVAL

    s._refresh_cache()
    s._update_larders()

    assert s.clans[1]["larder"] == 70.0
    assert s.clans[2]["larder"] == 30.0
    tribute = [e for e in s.history if e.type == "tribute"]
    assert tribute and tribute[0].payload["from"] == 1 and tribute[0].payload["to"] == 2


def test_unhappy_members_defect_to_healthier_banner(monkeypatch):
    monkeypatch.setattr(simmod, "DEFECT_CHANCE", 1.0)
    s = Simulation(pol_cfg(defection_enabled=True))
    sad = spawn(s, 30.0, 30.0, clan=1, energy=5.0)  # starving AND clan 1 is roofless
    happy = spawn(s, 32.0, 30.0, clan=2, energy=95.0)
    mate = spawn(s, 33.0, 30.0, clan=2, energy=90.0)
    make_clan(s, 1, sad)
    make_clan(s, 2, happy)
    s.world.rebuild_index()  # direct _update_* calls need a fresh spatial hash
    s._refresh_cache()

    s._update_defection()

    assert sad.clan_id == 2
    defects = [e for e in s.history if e.type == "defection"]
    assert defects and defects[0].entity_id == sad.id
    assert defects[0].payload["from"] == 1 and defects[0].payload["to"] == 2


def test_coalition_mates_share_signals_like_kin():
    s = Simulation(pol_cfg(communication_enabled=True, knowledge_enabled=True))
    a = spawn(s, 20.0, 20.0, clan=1)
    b = spawn(s, 24.0, 20.0, clan=2)
    make_clan(s, 1, a)
    make_clan(s, 2, b)
    s.coalitions[1] = {"name": "Pact", "leader_clan": 1, "members": [1, 2], "born_tick": 0}
    s._clan_coalition[1] = 1
    s._clan_coalition[2] = 1

    def _is_kin(sender_clan, hearer):
        kin = sender_clan == hearer.clan_id
        ca = s._coalition_of(sender_clan) if sender_clan else None
        cb = s._coalition_of(hearer.clan_id) if hearer.clan_id else None
        return kin or (ca is not None and ca == cb)

    assert _is_kin(1, b)  # coalition-mates count as kin for hearing


def test_politics_law_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    client.headers["X-God-Key"] = "test-key"
    r = client.post(
        "/api/laws?persist=false",
        json={"coalition_threshold": 55, "coalition_min_size": 3,
              "larder_capacity": 500, "aid_rate": 0.2},
    )
    assert r.status_code == 200
    laws = r.json()
    assert laws["coalition_threshold"] == 55
    assert laws["coalition_min_size"] == 3
    assert laws["larder_capacity"] == 500
    assert laws["aid_rate"] == 0.2
