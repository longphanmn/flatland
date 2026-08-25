"""§AN Communication, language & diplomacy — every caste has a voice.

Priest liturgy calms the panicked; women's peace-hums part the crowd;
soldiers' war-chirps rally allies onto a flagged target; touching vertices
in peace builds trust and elders bless the young with skill; foragers drop
scent trails home and violent deaths leave danger scent; emissaries carry
treaties, boundary stones ring at trespassers, tribute rides in couriers'
panniers, allied neighbours found markets and trade caravans, isolated
clans drift apart in dialect, and priests proclaim the turning season.
"""

import pytest

from app.config import Config
from app.entities import Corpse, Creature, House
from app.simulation import (
    ENVOY_RELATION_BOOST,
    PREPARED_TICKS,
    SCENT_TTL,
    Simulation,
)


def dip_cfg(**kw) -> Config:
    kw.setdefault("rivers_enabled", False)
    zeros = dict(
        seed=11, width=90.0, height=90.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        weather_enabled=False,
        age_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        schism_enabled=False,
        culture_enabled=False,
        plant_growth_rate=0.0,
        plant_spread_rate=0.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(sim: Simulation, cid: int, house: House | None = None) -> None:
    sim.clans[cid] = {
        "name": f"Clan {cid}", "founder_id": None, "born_tick": 0,
        "color": "#fff", "totem": None, "leader_id": None,
        "governance": "republic",
        "bylaws": {"rationing": False, "martial_law": False, "sanctuary": "open"},
        "task_board": {"priority": "balanced", "harvester_weight": 1.0, "guard_weight": 1.0},
        "specialization": {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34},
        "culture": "Test Rite", "culture_id": cid, "coalition_id": None,
        "larder": 0.0, "granary": 0.0, "harvest_total": 0.0, "feast_until": 0,
        "dialect": 0.0, "tribute_to": None,
        "main_house_id": house.id if house else None,
        "faith": 0.0, "shrine_level": 0, "history": [],
    }
    if house is not None:
        house.clan_id = cid


def add_creature(sim: Simulation, x: float, y: float, clan_id: int = 0, **kw) -> Creature:
    c = sim.world.add(Creature(x=x, y=y, clan_id=clan_id, energy=kw.pop("energy", 90.0), **kw))
    sim._init_creature_evolution(c)
    return c


# ------------------------------------------------- Phase A: caste voices

def test_priest_chant_calms_the_panicked(monkeypatch):
    import app.simulation as sim_mod
    monkeypatch.setattr(sim_mod, "CHANT_CHANCE", 1.0)
    s = Simulation(dip_cfg())
    priest = add_creature(s, 30.0, 30.0, clan_id=1, sides=24, shape="polygon", caste="Priest")
    kin = add_creature(s, 33.0, 30.0, clan_id=1)
    kin.panic_ticks = 20  # the leader just died

    for _ in range(6):
        s.step()
        if kin.calm_ticks > 0:
            break

    assert any(sg["kind"] == "chant" for sg in s.signals), "the liturgy rang out"
    assert kin.panic_ticks == 0, "panic drains away under the chant"
    assert kin.calm_ticks > 0


def test_womans_peace_hum_parts_the_crowd():
    s = Simulation(dip_cfg(seed=5))
    woman = add_creature(s, 40.0, 40.0, sides=2, shape="line", caste="Woman", clan_id=1)
    woman.trait = None
    hums = 0
    for _ in range(400):
        s.step()
        hums = sum(1 for sg in s.signals if sg["kind"] == "hum")
        if hums:
            break
    assert hums, "moving women emit their law-mandated peace-hum"


def test_war_chirp_rallies_allied_soldiers(monkeypatch):
    import app.simulation as sim_mod
    monkeypatch.setattr(sim_mod, "WARCHIRP_CHANCE", 1.0)
    s = Simulation(dip_cfg(predation_enabled=True))
    scout_threat = add_creature(s, 60.0, 60.0, sides=3, shape="polygon", caste="Soldier")  # enemy
    chirper = add_creature(s, 30.0, 30.0, clan_id=1, sides=3, shape="polygon", caste="Soldier")
    ally = add_creature(s, 34.0, 30.0, clan_id=1, sides=3, shape="polygon", caste="Soldier")
    # give the chirper a threat to flag: an enemy within fear radius
    enemy = add_creature(s, 27.0, 27.0, clan_id=2, sides=3, shape="polygon", caste="Soldier")
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -100

    for _ in range(8):
        s.step()
        wars = [sg for sg in s.signals if sg["kind"] == "war"]
        if wars:
            break

    assert wars, "the engaging soldier blows the war signal"
    tx, ty = wars[-1]["threat_x"], wars[-1]["threat_y"]
    d_before = s.world.distance(ally.x, ally.y, tx, ty)
    for _ in range(10):
        s.step()
    d_after = s.world.distance(ally.x, ally.y, tx, ty)
    assert d_after < d_before or ally.clan_id != 1 or ally.id not in s.world.entities, \
        "allied soldiers converge on the flagged target"


# --------------------------------------------- Phase B: touch & scent

def test_greeting_builds_trust_and_elder_blesses_the_young():
    s = Simulation(dip_cfg(seed=9))
    house = House(x=50.0, y=50.0, size=6.0)
    elder = add_creature(s, 20.0, 20.0, clan_id=1, sides=4, shape="polygon", caste="Gentleman")
    child = add_creature(s, 21.0, 20.0, clan_id=1, sides=3, shape="polygon", caste="Soldier", age=400)
    elder.age = 4600  # ≥75% of the 6000-tick lifespan → stage 'elder'
    child.speed = 0.05  # keep them within touch range
    elder.skills["farming"] = 5.0
    before_trust = child.trust.get(elder.id, 0.0)

    # land exactly on the greeting cadence for the elder's id
    fire_tick = (-(elder.id)) % 29
    while fire_tick <= s.tick:
        fire_tick += 29
    s.tick = fire_tick
    assert (s.tick + elder.id) % 29 == 0
    s.step()

    assert child.trust.get(elder.id, 0.0) >= before_trust + 2.0, "touching vertices binds"
    assert child.skills.get("farming", 0.0) > 0.0, "the elder's blessing passes skill"


def test_forager_scent_trail_is_dropped_and_followed(monkeypatch):
    import app.simulation as sim_mod
    from app.entities import Food
    monkeypatch.setattr(sim_mod, "TRAIL_DROP_CHANCE", 1.0)
    s = Simulation(dip_cfg(communication_enabled=True, food_call_rate=0.0, food_count=1))
    finder = add_creature(s, 40.0, 40.0, clan_id=1, energy=95.0)  # well-fed forager
    grain = s.world.add(Food(x=41.0, y=40.0, growth=1.0, variant="grain"))

    for _ in range(6):
        s.step()
        trails = [sg for sg in s.signals if sg["kind"] == "trail"]
        if trails:
            break
    assert trails, "a rich find leaves a breadcrumb trail"
    assert trails[-1]["ttl"] <= SCENT_TTL
    fx, fy = trails[-1]["food_x"], trails[-1]["food_y"]

    # a starving clan-mate follows the trail to the marked patch
    hungry = add_creature(s, float(fx) + 6.0, float(fy), clan_id=1, energy=10.0)
    hungry.x, hungry.y = fx + 6.0, fy
    d_before = s.world.distance(hungry.x, hungry.y, fx, fy)
    for _ in range(12):
        s.step()
        if hungry.id not in s.world.entities:
            break
    else:
        assert s.world.distance(hungry.x, hungry.y, fx, fy) < d_before or hungry.meals > 0, \
            "hungry kin walk the scent line home"


def test_violent_death_leaves_danger_scent_and_the_young_learn_it():
    s = Simulation(dip_cfg(predation_enabled=True, knowledge_enabled=True))
    wolf = add_creature(s, 30.0, 30.0, sides=3, shape="polygon")
    wolf.is_predator = True
    wolf.caste = "Predator"
    prey = add_creature(s, 31.0, 30.0, clan_id=1, health=10.0)
    juvenile = add_creature(s, 32.0, 31.0, clan_id=1, age=600)

    s.world.rebuild_index()
    s._refresh_cache()
    s._kill(prey, "predation")

    assert any(sg["kind"] == "danger_scent" for sg in s.signals), "the death site reeks"
    juvenile._learn_dummy = None
    # hearing pass: run one tick so the juvenile processes the marker
    s.tick += 1
    s._refresh_cache()
    s.world.rebuild_index()
    danger_fact = juvenile.facts.get("danger")
    # direct hearing via signal processing needs the full update path:
    for _ in range(2):
        s.signals.append({"x": 31.0, "y": 30.0, "kind": "danger_scent",
                          "sender": 0, "clan_id": 1, "ttl": 300})
        s.step()
        fact = juvenile.facts.get("danger") if juvenile.id in s.world.entities else None
        if fact is not None:
            break
    assert juvenile.facts.get("danger") is not None or fact is not None, \
        "the young learn to shun ambush grounds"


# ------------------------------------- Phase C: envoys, stones, couriers

def test_peace_envoy_delivered_warms_relations():
    s = Simulation(dip_cfg())
    ha = House(x=30.0, y=30.0, size=6.0)
    hb = House(x=60.0, y=60.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)
    make_clan(s, 2, hb)
    herald = add_creature(s, 59.0, 59.5, clan_id=1)  # arrived at the rival seat
    herald.mission = {"type": "peace", "target_clan": 2,
                      "x": 60.0, "y": 60.0, "deadline": s.tick + 100}
    pair = s._relation_pair(1, 2)
    before = s.relations.get(pair, 0)
    s._refresh_cache()

    s._update_diplomacy()

    assert herald.mission is None
    assert s.relations.get(pair, 0) >= min(100, before + ENVOY_RELATION_BOOST) - 1
    envys = [e for e in s.history if e.type == "peace_envoy"]
    assert envys and envys[0].payload.get("banner") == "📜"


def test_envoy_mission_steers_the_herald():
    s = Simulation(dip_cfg())
    herald = add_creature(s, 20.0, 20.0, clan_id=1)
    herald.mission = {"type": "peace", "target_clan": 2,
                      "x": 40.0, "y": 20.0, "deadline": s.tick + 500}
    d_before = s.world.distance(herald.x, herald.y, 40.0, 20.0)
    for _ in range(10):
        s.step()
        if herald.id not in s.world.entities:
            break
    d_after = s.world.distance(herald.x, herald.y, 40.0, 20.0)
    assert d_after < d_before, "the banner walks toward the rival house"


def test_boundary_stone_rings_at_trespassers():
    s = Simulation(dip_cfg(trespass_decay=1.0))
    ha = House(x=30.0, y=30.0, size=6.0)
    s.world.add(ha)
    make_clan(s, 1, ha)
    s._set_main_house_for_clan(1, ha)  # raises the boundary stone
    assert any(st["clan_id"] == 1 for st in s.boundary_stones), "the stone stands"
    stone = next(st for st in s.boundary_stones if st["clan_id"] == 1)

    trespasser = add_creature(s, stone["x"] + 1.0, stone["y"], clan_id=2)
    s.world.rebuild_index()
    s._refresh_cache()
    s._update_territory()

    chimes = [sg for sg in s.signals if sg["kind"] == "chime"]
    assert chimes, "trespass rings the warning"
    # throttled: no second chime inside the gap
    s._update_territory()
    assert sum(1 for sg in s.signals if sg["kind"] == "chime") == len(chimes)


def test_tribute_rides_in_a_courier():
    s = Simulation(dip_cfg(tribute_enabled=True, resource_sharing_enabled=True))
    ha = House(x=30.0, y=30.0, size=6.0)
    hb = House(x=70.0, y=70.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)  # protector
    make_clan(s, 2, hb)  # vassal
    vassal = add_creature(s, 71.0, 71.0, clan_id=2, energy=95.0)
    s.clans[2]["tribute_to"] = 1
    s.clans[2]["larder"] = 50.0
    s.clans[2]["granary"] = 40.0
    s.tick = (s.tick // 240 + 1) * 240  # land on the tribute interval
    s._refresh_cache()

    s._update_larders()

    tributes = [e for e in s.history if e.type == "tribute"]
    assert tributes, "the vassal pays"
    assert s.clans[1]["granary"] > 0.0, "grain travels to the suzerain granary"
    assert any(sg["kind"] == "courier" for sg in s.signals), "the courier is seen"


# ------------------------------------------- Phase D: markets & caravans

def test_allied_neighbours_found_a_market_and_barter():
    s = Simulation(dip_cfg(markets_enabled=True, granaries_enabled=True))
    ha = House(x=30.0, y=30.0, size=6.0)
    hb = House(x=38.0, y=38.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)
    make_clan(s, 2, hb)
    add_creature(s, 31.0, 31.0, clan_id=1)
    add_creature(s, 39.0, 39.0, clan_id=2)
    pair = s._relation_pair(1, 2)
    s.relations[pair] = s.config.alliance_threshold  # sworn friends
    s.clans[1]["granary"] = 100.0
    s.clans[2]["granary"] = 10.0
    s.tick = (s.tick // 480 + 1) * 480
    s._refresh_cache()

    s._update_diplomacy()

    assert pair in s.markets, "trading partners raise a neutral post"
    assert any(e.type == "market" for e in s.history)

    s.tick += 240  # barter cadence
    s._update_diplomacy()
    ga, gb = s.clans[1]["granary"], s.clans[2]["granary"]
    assert abs(ga - gb) < abs(100.0 - 10.0), "surplus flows to the leaner store"


def test_caravan_carries_goods_and_news():
    s = Simulation(dip_cfg(markets_enabled=True))
    ha = House(x=20.0, y=20.0, size=6.0)
    hb = House(x=80.0, y=80.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)
    make_clan(s, 2, hb)
    add_creature(s, 21.0, 21.0, clan_id=1, age=2500)   # adult
    add_creature(s, 81.0, 81.0, clan_id=2, age=2500)   # adult
    s.clans[1]["granary"] = 30.0
    s.clans[2]["granary"] = 0.0
    s.tick = (s.tick // 2400 + 1) * 2400
    s._refresh_cache()

    s._update_diplomacy()

    caravans = [e for e in s.history if e.type == "caravan"]
    assert caravans, "peddlers set out between settlements"
    assert s.clans[2]["granary"] > 0.0, "rare goods change hands"
    assert s.relations.get(s._relation_pair(1, 2), 0) > 0


# ------------------------------- Phase E: omens, murals, archaeology

def test_priests_proclaim_the_turning_season():
    s = Simulation(dip_cfg(omens_enabled=True, theology_enabled=False))
    ha = House(x=30.0, y=30.0, size=6.0)
    s.world.add(ha)
    make_clan(s, 1, ha)
    s.clans[1]["shrine_level"] = 1
    priest = add_creature(s, 31.0, 31.0, clan_id=1, sides=24, shape="polygon", caste="Priest")
    flock = add_creature(s, 33.0, 31.0, clan_id=1)
    s._omen_season = "winter"  # actual season differs → a turn is due
    s._refresh_cache()

    s._update_diplomacy()

    omens = [e for e in s.history if e.type == "omen"]
    assert omens, "the priest beheld the turning of the season"
    assert any(sg["kind"] == "omen" for sg in s.signals)
    # the flock heeds it on the next hearing pass
    for _ in range(3):
        s.step()
        if flock.prepared_ticks > 0:
            break
    assert flock.prepared_ticks > 0, "worshippers prepare for what comes"


def test_dialect_drifts_apart_in_isolation_converges_among_allies():
    s = Simulation(dip_cfg(dialect_drift_enabled=True))
    make_clan(s, 1)
    make_clan(s, 2)
    make_clan(s, 3)
    s.relations[s._relation_pair(1, 2)] = 60  # allies: converge
    s.clans[1]["dialect"] = 0.4
    s.clans[2]["dialect"] = -0.4
    s._omen_season = "winter"  # force the season-turn branch
    s._refresh_cache()

    s._update_diplomacy()

    d1, d2, d3 = (s.clans[c]["dialect"] for c in (1, 2, 3))
    assert abs(d1 - d2) < 0.8, "shared tongue among allies"
    assert d3 != 0.0, "isolated clans drift off their own way"


def test_murals_record_the_great_days():
    s = Simulation(dip_cfg())
    h = House(x=30.0, y=30.0, size=6.0)
    s.world.add(h)
    make_clan(s, 1, h)
    assert h.murals == 0
    s._log_clan_history(1, "war_declared", "Declared war on the neighbours")
    s._log_clan_history(1, "banquet", "Feasted the whole vale")
    assert h.murals == 2, "artisans paint each milestone on the walls"


def test_ruin_archaeology_recovers_lost_knowledge():
    s = Simulation(dip_cfg(knowledge_enabled=True))
    ruin = House(x=40.0, y=40.0, size=8.0, is_ruin=True)
    s.world.add(ruin)
    digger = add_creature(s, 42.0, 40.0)
    digger.personality = "explorer"  # evolution rolls personalities randomly
    fire_tick = (7 - digger.id) % 23   # (tick + id) % 23 == 7
    while fire_tick <= s.tick:
        fire_tick += 23
    s.tick = fire_tick
    s.world.rebuild_index()
    s._refresh_cache()

    s.step()

    assert digger.skills.get("farming", 0.0) > 0.0, "old walls teach old tricks"
    assert digger.facts.get("food") is not None, "lore of the old farms surfaces"


# ------------------------------------------------------------------ laws

def test_diplomacy_laws_roundtrip(client):
    r = client.post(
        "/api/laws?persist=false",
        json={
            "vocalizations_enabled": False,
            "scent_enabled": False,
            "envoys_enabled": False,
            "markets_enabled": False,
            "omens_enabled": False,
            "dialect_drift_enabled": False,
        },
    )
    assert r.status_code == 200
    laws = r.json()
    for key in ("vocalizations_enabled", "scent_enabled", "envoys_enabled",
                "markets_enabled", "omens_enabled", "dialect_drift_enabled"):
        assert laws[key] is False


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    return c
