"""§AT-1 — clan history is complete and queryable: paginated endpoint, the
clan's internal log, and a SQL-level clan filter over the durable chronicle."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.db import Database
from app.entities import Creature
from app.main import RT, app, start_world
from app.protocol import HistoryEvent
from app.simulation import Simulation


def fresh_runtime() -> None:
    RT.config = Config.from_env()
    RT.paused = True  # no engine thread in these tests
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()


def test_clan_history_endpoint_paginates():
    fresh_runtime()

    # fabricate one clan + 55 war events naming it as the loser ("a")
    s = RT.sim
    founder = s.world.add(Creature(x=100.0, y=100.0))
    cid = s._new_clan(founder)
    for i in range(55):
        s.history.append(
            HistoryEvent(
                type="war", tick=i + 1, entity_id=100 + i,
                payload={"a": cid, "b": cid + 1, "lethal": False},
            )
        )
    s._log_clan_history(cid, "war_declared", "test milestone")

    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"

    r = c.get(f"/api/clans/{cid}/history?page=0&size=50")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 55
    assert len(d["events"]) == 50
    assert d["has_more"] is True
    assert any(m["event"] == "war_declared" for m in d["log"])

    r2 = c.get(f"/api/clans/{cid}/history?page=1&size=50")
    d2 = r2.json()
    assert len(d2["events"]) == 5
    assert d2["has_more"] is False
    # newest first ordering across pages
    assert d["events"][0]["tick"] == 55
    assert d2["events"][0]["tick"] == 5


def test_history_db_filter_by_clan(tmp_path):
    """§AT-1: the durable chronicle stays queryable by clan after the
    in-memory deque rolls over."""
    db = Database(str(tmp_path / "t.db"))
    wid = db.new_world(Config(seed=1))
    events = [
        HistoryEvent(type="war", tick=1, entity_id=1,
                     payload={"a": 3, "b": 4, "lethal": True}),
        HistoryEvent(type="takeover", tick=2, entity_id=9,
                     payload={"invader_clan": 7, "victim_clan": 3}),
        HistoryEvent(type="birth", tick=3, entity_id=2,
                     payload={"mother": 10, "father": 11}),
        HistoryEvent(type="death", tick=4, entity_id=5,
                     payload={"clan_id": 3, "personal_name": "X"}),
    ]
    db.add_events(wid, events)
    got = db.history(wid, limit=100, clan_id=3)
    types = sorted(g["type"] for g in got)
    assert types == ["death", "takeover", "war"]
    assert db.history(wid, limit=100, clan_id=7)[0]["type"] == "takeover"
    assert db.history(wid, limit=100, clan_id=99) == []
    db.close()


def test_api_history_accepts_clan_filter():
    fresh_runtime()
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    r = c.get("/api/history?clan_id=1")
    assert r.status_code == 200
    body = r.json()
    for ev in body["events"]:
        payload = ev["payload"]
        named = [payload.get(k) for k in
                 ("a", "b", "clan_id", "parent", "new_clan",
                  "invader_clan", "victim_clan", "winner_clan", "loser_clan")]
        assert 1 in named
