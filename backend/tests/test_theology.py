"""§AP Unified Theology — the 8 Sacred Avatars of the Sphere, shrines,
tithes, faith miracles, temples, divine law resonance, holy synods and the
3D epiphany. Deterministic: hash-gates instead of rng draws."""

import pytest

import app.simulation as simmod
from app.config import Config
from app.entities import Creature, House
from app.simulation import (
    MIRACLE_FAITH_COST,
    SHRINE_AURA_RADIUS,
    TRUCE_TICKS,
    AVATARS,
    Simulation,
)


def _base_cfg() -> dict:
    """A living world: default densities on a small map (clans + houses spawn)."""
    return dict(
        seed=17, width=120.0, height=90.0,
        weather_enabled=False, birth_enabled=False, predation_enabled=False,
        war_enabled=False, disease_enabled=False, schism_enabled=False,
        culture_enabled=False, age_enabled=False,
    )


def th_cfg(**kw) -> Config:
    zeros = dict(
        seed=17,
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


def spawn(s: Simulation, x, y, *, clan=None, energy=90.0, sides=4):
    c = s.world.add(Creature(x=x, y=y, sides=sides, energy=energy,
                             age=1000, lifespan=20000.0, speed=0.0))
    if clan is not None:
        c.clan_id = clan
    return c


def make_faithful_clan(s: Simulation, cid: int, avatar: str, house: House | None) -> None:
    s.clans[cid] = {
        "name": f"Clan {cid}", "founder_id": cid, "born_tick": 0, "color": "#ffd166",
        "leader_id": None, "totem": avatar, "faith": 0.0, "shrine_level": 0,
        "larder": 0.0, "tribute_to": None, "coalition_id": None,
        "main_house_id": house.id if house else None,
        "history": [],
    }


# ----------------------------------------------------------------- Phase A

def test_every_clan_bears_a_sacred_avatar():
    s = Simulation(th_cfg())
    for info in s.clans.values():
        assert info["totem"] in AVATARS


def test_avatar_assignment_deterministic_per_seed():
    cfg_kw = dict(seed=5, width=120.0, height=90.0)  # default densities seed a real society
    a = Simulation(Config(**{**_base_cfg(), **cfg_kw}))
    b = Simulation(Config(**{**_base_cfg(), **cfg_kw}))
    ta = {cid: i["totem"] for cid, i in a.clans.items()}
    tb = {cid: i["totem"] for cid, i in b.clans.items()}
    assert ta == tb and len(ta) >= 2


def test_avatar_buff_vocabulary_is_wired():
    s = Simulation(th_cfg())
    strike = spawn(s, 10.0, 10.0, clan=1)
    scales = spawn(s, 12.0, 10.0, clan=2)
    monolith = spawn(s, 14.0, 10.0, clan=3)
    make_faithful_clan(s, 1, "Celestial Strike", None)
    make_faithful_clan(s, 2, "Cosmic Scales", None)
    make_faithful_clan(s, 3, "Indomitable Monolith", None)
    assert s._totem_stat(strike, "damage") == pytest.approx(0.25)
    assert s._totem_stat(monolith, "cold") == pytest.approx(0.40)
    assert s._totem_stat(scales, "lawful") == 1.0
    # plain clan: no buffs
    loner = spawn(s, 16.0, 10.0, clan=9)
    make_faithful_clan(s, 9, None, None)
    assert s._totem_stat(loner, "damage") == 0.0


# ----------------------------------------------------------------- Phase B

def _settlement(sim: Simulation, cid: int = 1, avatar="Radiant Circle"):
    h = House(x=30.0, y=30.0, size=8.0, door_width=4.0, door_side="south")
    h.clan_id = cid
    sim.world.add(h)
    make_faithful_clan(sim, cid, avatar, h)
    return h


def test_settled_clan_consecrates_shrine():
    s = Simulation(th_cfg())
    _settlement(s)
    spawn(s, 32.0, 30.0, clan=1)
    s._refresh_cache()
    s._update_faith()
    assert s.clans[1]["shrine_level"] == 1


def test_tithes_fill_the_faith_pool_at_dawn():
    """Tick 0 is exactly sunrise (tod 0.25): the devout tithe at the shrine."""
    s = Simulation(th_cfg())
    _settlement(s)
    devout = spawn(s, 33.0, 30.0, clan=1, energy=90.0)          # within aura (10u)
    priest = spawn(s, 31.0, 31.0, clan=1, energy=90.0, sides=24)  # Priest tithes double
    far = spawn(s, 60.0, 60.0, clan=1, energy=90.0)             # outside the aura
    poor = spawn(s, 33.0, 31.0, clan=1, energy=20.0)            # too lean to give
    s._refresh_cache()

    s._update_faith()

    faith = s.clans[1]["faith"]
    rate = s.config.tithe_rate * s.config.energy_max  # 4.0
    assert faith == pytest.approx(rate * 3, abs=0.6)  # 2 tithe + priest double
    assert devout.energy < 90.0 and priest.energy < priest.energy + 1
    assert far.energy == 90.0 and poor.energy == 20.0  # absent & exempt
    assert SHRINE_AURA_RADIUS > 3.0  # sanity: the aura covers the shrine yard


def test_seasonal_miracle_blooms_food_and_mends_the_flock():
    s = Simulation(th_cfg())
    _settlement(s)
    hurt = spawn(s, 32.0, 30.0, clan=1, energy=50.0)
    hurt.health = 40.0
    s._refresh_cache()
    s.clans[1]["faith"] = MIRACLE_FAITH_COST + 20.0
    s._last_season = "summer"  # current season is spring at tick 0

    food_before = sum(1 for e in s.world.entities.values() if e.kind == "food")
    s._update_faith()

    miracles = [e for e in s.history if e.type == "miracle"]
    assert miracles and miracles[0].payload["clan_id"] == 1
    food_after = sum(1 for e in s.world.entities.values() if e.kind == "food")
    assert food_after >= food_before + 3  # bounty bloomed around the shrine
    assert hurt.health > 40.0  # the flock was mended
    assert s.clans[1]["faith"] < MIRACLE_FAITH_COST  # the miracle was paid for


def test_high_faith_raises_a_temple():
    s = Simulation(th_cfg())
    _settlement(s)
    spawn(s, 32.0, 30.0, clan=1)
    s._refresh_cache()
    cost = s.config.temple_faith_cost
    s.clans[1]["faith"] = cost + 5.0

    s._update_faith()

    assert s.clans[1]["shrine_level"] == 2
    assert s.clans[1]["faith"] < cost  # spent on the works
    assert any(e.type == "temple" for e in s.history)


# ----------------------------------------------------------------- Phase C

def test_law_change_chimes_shrines_and_priests_preach():
    s = Simulation(th_cfg())
    _settlement(s)
    priest = spawn(s, 31.0, 31.0, clan=1, sides=24)
    layman = spawn(s, 32.0, 30.0, clan=1, energy=95.0)
    s._refresh_cache()
    s.clans[1]["shrine_level"] = 1
    energy_before = layman.energy

    s.on_law_change(["food_count", "war_enabled"])

    chimes = [sg for sg in s.signals if sg.get("kind") == "chime"]
    assert chimes and chimes[0]["clan_id"] == 1
    sermons = [e for e in s.history if e.type == "sermon"]
    assert sermons and sermons[0].entity_id == priest.id
    assert any(e.type == "resonance" for e in s.history)
    assert layman.energy > energy_before  # morale rally inside the aura


def test_doctrinal_kinship_draws_same_avatar_clans_together():
    s = Simulation(th_cfg(totems_enabled=True, relation_drift_rate=0))
    a = spawn(s, 10.0, 10.0, clan=1, sides=4)   # Gentleman
    b = spawn(s, 30.0, 10.0, clan=2, sides=3)   # Soldier — no same-caste bump
    make_faithful_clan(s, 1, "Radiant Circle", None)
    make_faithful_clan(s, 2, "Sacred Spiral", None)  # complementary aspect
    pair = s._relation_pair(1, 2)
    s.relations[pair] = 10
    s._relation_zones[pair] = 0

    s._update_relations()

    assert s.relations[pair] == 11  # doctrine pulls the faithful together (+1)


# ----------------------------------------------------------------- Phase D

def test_synod_unifies_clans_under_sacred_truce():
    s = Simulation(th_cfg())
    for cid in (1, 2):
        _settlement(s, cid=cid, avatar="Radiant Circle")
        p = spawn(s, 20.0 + cid * 5.0, 20.0, clan=cid, sides=24)
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -50

    s._hold_synod("Ice")

    assert s.relations[pair] > -50  # the clans warmed toward each other
    assert s.truce_ticks == TRUCE_TICKS
    synod = [e for e in s.history if e.type == "synod"]
    assert synod and sorted(synod[0].payload["clans"]) == [1, 2]


def test_sacred_truce_stops_war_but_only_while_it_lasts():
    from app.entities import Creature as C

    s = Simulation(th_cfg(war_enabled=True))
    a = spawn(s, 40.0, 40.0, clan=1, sides=3)
    b = spawn(s, 41.0, 40.0, clan=2, sides=3)  # within attack_radius
    make_faithful_clan(s, 1, "Radiant Circle", None)
    make_faithful_clan(s, 2, "Celestial Strike", None)
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -100
    s._relation_zones[pair] = -1

    s.truce_ticks = 5
    s.step()
    assert not [e for e in s.history if e.type == "war"]

    s.truce_ticks = 0
    s.step()
    assert [e for e in s.history if e.type == "war"]  # strife resumes after truce


# ----------------------------------------------------------------- Phase E

def test_epiphany_at_a_temple_stills_all_strife():
    s = Simulation(th_cfg(day_length=200))
    _settlement(s)
    elder = spawn(s, 32.0, 30.0, clan=1, sides=24)
    elder.age = 18000  # lifespan 20000 → stage "elder"
    s._refresh_cache()
    s.clans[1]["shrine_level"] = 2  # temple
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -30
    # find the deterministic day the epiphany fires for (seed, clan 1)
    dl = max(1, s.config.day_length)
    day_index = next(
        d for d in range(500)
        if (s.config.seed * 31 + 1 * 17 + d) % simmod.EPIPHANY_PERIODS_GAP == 0
    )
    s.tick = day_index * dl + 1

    s._maybe_epiphany()

    visions = [e for e in s.history if e.type == "epiphany"]
    assert visions and visions[0].entity_id == elder.id
    assert visions[0].payload["avatar"] == "Radiant Circle"
    assert s.truce_ticks == TRUCE_TICKS * 2
    assert elder.emote == "heal"


# ------------------------------------------------------------------ laws

def test_theology_laws_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    client.headers["X-God-Key"] = "test-key"
    r = client.post(
        "/api/laws?persist=false",
        json={"theology_enabled": False, "tithe_rate": 0.08,
              "temple_faith_cost": 250},
    )
    assert r.status_code == 200
    laws = r.json()
    assert laws["theology_enabled"] is False
    assert laws["tithe_rate"] == 0.08
    assert laws["temple_faith_cost"] == 250
