"""Database layer tests: durable chronicle, worlds, and law history."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.db import Database
from app.main import DB, RT, _on_event, app, start_world
from app.protocol import HistoryEvent
from app.simulation import Simulation


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = Config.from_env()
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def test_world_row_created_and_listed(client):
    worlds = client.get("/api/worlds").json()["worlds"]
    assert len(worlds) >= 1
    assert worlds[0]["ended_at"] is None  # current world is still open
    assert worlds[0]["width"] == RT.config.width


def test_reset_closes_old_world_row(client):
    old_id = RT.world_id
    client.post("/api/control", json={"action": "reset"})
    assert RT.world_id != old_id
    rows = {w["id"]: w for w in client.get("/api/worlds").json()["worlds"]}
    assert rows[old_id]["ended_at"] is not None
    assert rows[RT.world_id]["ended_at"] is None


def test_death_event_persisted(client):
    # famine + fast decay: starvation is inevitable under these laws
    client.post("/api/laws", json={"food_count": 0, "energy_decay_per_tick": 2.0})
    for _ in range(45):
        client.post("/api/control", json={"action": "step"})
    hist = client.get("/api/history").json()
    assert hist["world_id"] == RT.world_id
    assert hist["total_deaths"] >= 1
    deaths = [e for e in hist["events"] if e["type"] == "death"]
    assert deaths and deaths[-1]["cause"] == "starvation"


def test_history_persists_across_reopen(client):
    wid = RT.world_id
    DB.add_events(wid, [HistoryEvent(tick=7, entity_id=1, caste="Noble", cause="starvation", x=1.0, y=2.0)])
    # simulate a restart: a brand-new Database instance over the same file
    fresh = Database(DB.path)
    try:
        rows = fresh.history(wid)
        assert any(e["tick"] == 7 and e["caste"] == "Noble" for e in rows)
        assert fresh.death_count(wid) >= 1
    finally:
        fresh.close()


def test_history_pagination(client):
    wid = RT.world_id
    DB.add_events(
        wid,
        [
            HistoryEvent(tick=t, entity_id=t, caste="Soldier", cause="starvation", x=0.0, y=0.0)
            for t in range(1, 6)
        ],
    )
    all_ids = [e["id"] for e in client.get("/api/history?limit=2000").json()["events"]]
    assert len(all_ids) >= 5
    page = client.get(f"/api/history?since={all_ids[-3]}&limit=2").json()["events"]
    assert [e["id"] for e in page] == all_ids[-2:]


def test_law_changes_recorded(client):
    r = client.post("/api/laws", json={"food_count": 5, "boundary": "clamp"})
    assert r.status_code == 200
    conn = sqlite3.connect(DB.path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT name FROM law_changes WHERE world_id=? ORDER BY id", (RT.world_id,)
        ).fetchall()
    finally:
        conn.close()
    names = [r["name"] for r in rows]
    assert sorted(names) == ["boundary", "food_count"]


def test_creature_endpoint_status_and_history(client):
    from app.entities import Creature

    c = RT.sim.world.add(Creature(x=5.0, y=5.0, sides=4, energy=77.0))
    DB.add_events(
        RT.world_id,
        [
            HistoryEvent(tick=1, entity_id=c.id, caste="Gentleman", cause="",
                         x=5.0, y=5.0,
                         payload={"mother": 2, "father": 3, "generation": 1},
                         type="birth"),
        ],
    )
    data = client.get(f"/api/creature/{c.id}").json()
    assert data["entity"]["caste"] == "Gentleman"
    assert data["entity"]["energy"] == pytest.approx(77.0)
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "birth"
    assert data["events"][0]["payload"]["mother"] == 2

    # unknown / dead creature: entity null, chronicle still answers
    DB.add_events(
        RT.world_id,
        [HistoryEvent(tick=2, entity_id=c.id, caste="Gentleman", cause="starvation", x=5.0, y=5.0)],
    )
    RT.sim.world.remove(c.id)
    data = client.get(f"/api/creature/{c.id}").json()
    assert data["entity"] is None
    assert len(data["events"]) == 2


def test_genealogy_table_written(client):
    from app.entities import Creature

    # a birth writes the lineage row; a death closes it
    c = RT.sim.world.add(Creature(x=5.0, y=5.0, sides=4, energy=100.0))
    DB.add_events(
        RT.world_id,
        [
            HistoryEvent(
                type="birth", tick=3, entity_id=c.id, caste="Gentleman",
                x=5.0, y=5.0,
                payload={"mother": 2, "father": 1, "generation": 4, "clan_id": 7},
            )
        ],
    )
    _on_event(HistoryEvent(
        type="birth", tick=3, entity_id=c.id, caste="Gentleman",
        x=5.0, y=5.0,
        payload={"mother": 2, "father": 1, "generation": 4, "clan_id": 7},
    ))
    conn = sqlite3.connect(DB.path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM creatures WHERE world_id=? AND entity_id=?",
            (RT.world_id, c.id),
        ).fetchone()
        assert row is not None
        assert row["mother_id"] == 2 and row["father_id"] == 1
        assert row["generation"] == 4 and row["clan_id"] == 7
        assert row["died_tick"] is None

        RT.sim._kill(c, "starvation")  # records death via on_event too
        row = conn.execute(
            "SELECT died_tick FROM creatures WHERE world_id=? AND entity_id=?",
            (RT.world_id, c.id),
        ).fetchone()
        assert row["died_tick"] is not None
    finally:
        conn.close()


def test_events_survive_world_reset_in_db(client):
    wid_before = RT.world_id
    DB.add_events(wid_before, [HistoryEvent(tick=1, entity_id=9, caste="Priest", cause="old_age", x=5.0, y=5.0)])
    client.post("/api/control", json={"action": "reset"})
    # new world's history starts empty...
    assert client.get("/api/history").json()["total_deaths"] == 0
    # ...but the old world's chronicle is still queryable in the database
    assert DB.death_count(wid_before) >= 1
