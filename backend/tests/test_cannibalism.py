"""§AC Desperation cannibalism — the starving may eat the living.

Only true desperation unlocks it (sated/hungry never), the weak and enemy-clan
members are legitimate prey while healthy kin adults are not, kin-eating exiles
the slayer into an outcast band that the former clan now counts an enemy, and
every kill leaves a partial corpse.
"""

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import Simulation


def cann_cfg(**kw) -> Config:
    kw.setdefault("rivers_enabled", False)
    zeros = dict(
        seed=77,
        width=60.0,
        height=60.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        weather_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        shelter_enabled=False,
        sleep_enabled=False,
        territory_enabled=False,
        schism_enabled=False,
        culture_enabled=False,
        age_enabled=False,
        communication_enabled=False,
        knowledge_enabled=True,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(s: Simulation, cid: int) -> None:
    s.clans[cid] = {
        "name": f"Clan {cid}", "founder_id": cid, "born_tick": 0,
        "color": "#ffd166", "leader_id": None,
        "coalition_id": None, "larder": 0.0, "tribute_to": None,
    }
    # hand-registered clans must not collide with _new_clan's id counter
    # (the outcast band mints the next id when a kin-eater is exiled)
    s._next_clan_id = max(s._next_clan_id, cid + 1)


def spawn(s: Simulation, x, y, *, clan=None, energy=100.0, health=100.0):
    c = s.world.add(Creature(x=x, y=y, sides=4, energy=energy, health=health,
                             age=5000, lifespan=10000.0, speed=0.0))  # adult
    if clan is not None:
        c.clan_id = clan
    return c


def test_starving_eats_weak_enemy():
    s = Simulation(cann_cfg())
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)   # starving (≤15%)
    prey = spawn(s, 30.9, 30.0, clan=2, energy=40.0, health=30.0)  # wounded → weak
    make_clan(s, 1)
    make_clan(s, 2)

    s.step()

    assert prey.id not in s.world.entities
    assert s._death_counts.get("cannibalism") == 1
    # metabolism keeps ticking after the feed — allow a decay-sized slack
    assert eater.energy == pytest.approx(8.0 + s.config.cannibalism_energy, abs=0.5)
    assert eater.meals == 1
    kill = [e for e in s.history if e.type == "cannibalism"]
    assert kill and kill[0].payload["prey"] == prey.id and kill[0].payload["kin"] is False
    corpses = [e for e in s.world.entities.values() if e.kind == "corpse"]
    assert corpses and corpses[0].energy == pytest.approx(s.config.corpse_energy * 0.5)


def test_sated_and_hungry_never_eat_the_living():
    for energy in (80.0, 25.0):  # sated, hungry
        s = Simulation(cann_cfg())
        eater = spawn(s, 30.0, 30.0, clan=1, energy=energy)
        prey = spawn(s, 30.9, 30.0, clan=2, energy=40.0, health=10.0)  # very weak
        make_clan(s, 1)
        make_clan(s, 2)

        s.step()

        assert prey.id in s.world.entities  # the living stay living
        assert not [e for e in s.history if e.type == "cannibalism"]


def test_healthy_kin_adults_are_never_prey():
    s = Simulation(cann_cfg())
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)  # starving
    kin = spawn(s, 30.9, 30.0, clan=1, energy=90.0, health=100.0)  # healthy same-clan adult
    make_clan(s, 1)

    s.step()

    assert kin.id in s.world.entities  # never healthy kin adults


def test_enemy_hunting_needs_a_negative_relation():
    s = Simulation(cann_cfg(eat_kin_enabled=False))
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)
    stranger = spawn(s, 30.9, 30.0, clan=2, energy=80.0, health=95.0)  # healthy, neutral
    make_clan(s, 1)
    make_clan(s, 2)

    s.step()
    assert stranger.id in s.world.entities

    # declare rivalry: the healthy stranger is now fair game
    s.relations[s._relation_pair(1, 2)] = -60
    s.world.remove(eater.id)
    eater2 = spawn(s, 30.0, 30.0, clan=1, energy=8.0)
    s._refresh_cache()
    s.world.rebuild_index()

    s.step()
    assert stranger.id not in s.world.entities


def test_kin_eating_exiles_the_slayer():
    s = Simulation(cann_cfg(kin_stigma=90, relation_drift_rate=0))
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)
    kin = spawn(s, 30.9, 30.0, clan=1, energy=50.0, health=20.0)  # weak kin
    witness = spawn(s, 33.0, 31.0, clan=1)  # close enough to remember
    make_clan(s, 1)
    former_clans = len(s.clans)

    s.step()

    assert kin.id not in s.world.entities
    band = eater.clan_id
    assert band != 1 and band > 0  # cast out into a one-being outcast band
    assert s.clans[band]["leader_id"] == eater.id
    # stigma: former clan ↔ outcast band sink deep into hostility
    # (the same-caste diplomacy factor may soften by +1 on the same tick)
    score = s.relations[s._relation_pair(1, band)]
    assert score <= -(s.config.kin_stigma - 1)
    assert s._zone_of(score) == -1  # deep enough to cross the rivalry line
    exile = [e for e in s.history if e.type == "exile"]
    assert exile and exile[0].entity_id == eater.id and exile[0].payload["former_clan"] == 1
    # witnesses remember the outcast band as an enemy (§X knowledge)
    assert band in (witness.facts.get("enemies") or {})


def test_exile_disabled_keeps_the_slayer_in_the_clan():
    s = Simulation(cann_cfg(exile_on_kin_eat=False))
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)
    kin = spawn(s, 30.9, 30.0, clan=1, energy=50.0, health=20.0)
    make_clan(s, 1)

    s.step()

    assert kin.id not in s.world.entities
    assert eater.clan_id == 1  # shunned but not cast out
    assert any(e.type == "cannibalism" for e in s.history)
    assert not any(e.type == "exile" for e in s.history)


def test_cooldown_separates_desperate_kills():
    # tiny energy gain keeps the killer below the hunger gate after feeding;
    # corpses off so scavenging can't top the killer up above the gate either —
    # only the cooldown stands between kill one and kill two
    s = Simulation(cann_cfg(cannibalism_energy=5.0, corpses_enabled=False))
    eater = spawn(s, 30.0, 30.0, clan=1, energy=8.0)
    prey1 = spawn(s, 30.9, 30.0, clan=2, energy=40.0, health=10.0)
    prey2 = spawn(s, 29.4, 30.3, clan=3, energy=40.0, health=10.0)
    make_clan(s, 1)
    make_clan(s, 2)
    make_clan(s, 3)

    s.step()

    assert sum(1 for e in s.history if e.type == "cannibalism") == 1
    assert eater.cannibal_cooldown > 0
    assert prey1.id in s.world.entities and prey2.id not in s.world.entities

    kills = 1
    for _ in range(180):
        s.step()
        kills = sum(1 for e in s.history if e.type == "cannibalism")
        if kills >= 2:
            break
    assert kills >= 2  # once the cooldown passed, desperation struck again
    assert prey1.id not in s.world.entities


def test_cannibalism_law_roundtrip():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    client.headers["X-God-Key"] = "test-key"
    r = client.post(
        "/api/laws?persist=false",
        json={"cannibalism_energy": 60, "kin_stigma": 55,
              "cannibalism_hunger_ratio": 0.2},
    )
    assert r.status_code == 200
    laws = r.json()
    assert laws["cannibalism_energy"] == 60
    assert laws["kin_stigma"] == 55
    assert laws["cannibalism_hunger_ratio"] == 0.2
