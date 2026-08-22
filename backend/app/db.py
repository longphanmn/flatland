"""SQLite persistence: worlds, chronicle events, and god's law changes.

Deliberately uses the stdlib `sqlite3` behind a thin repository interface:
writes are tiny batches to a local file, so an ORM/async driver would add
loop-affinity hazards without benefit. Swap to SQLAlchemy/Postgres here when
the deployment needs it — callers only touch Database methods.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

from .config import Config
from .protocol import HistoryEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seed INTEGER NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    boundary TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    type TEXT NOT NULL,
    entity_id INTEGER,
    caste TEXT,
    cause TEXT,
    x REAL,
    y REAL,
    payload TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS law_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_world ON events(world_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: sqlite3.Connection | None = None
        # One connection shared across threads (event loop + test workers);
        # a plain lock serializes the tiny local writes.
        self._lock = threading.Lock()

    # ------------------------------------------------------------ lifecycle
    def connect(self) -> None:
        """Open (once) and migrate."""
        if self._conn is not None:
            return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def _require(self) -> sqlite3.Connection:
        self.connect()
        assert self._conn is not None
        return self._conn

    # --------------------------------------------------------------- worlds
    def new_world(self, cfg: Config) -> int:
        with self._lock:
            cur = self._require().execute(
                "INSERT INTO worlds(seed,width,height,boundary,started_at) VALUES (?,?,?,?,?)",
                (cfg.seed, cfg.width, cfg.height, cfg.boundary, _now()),
            )
            self._conn.commit()  # type: ignore[union-attr]
            return int(cur.lastrowid)

    def end_world(self, world_id: int) -> None:
        with self._lock:
            self._require().execute(
                "UPDATE worlds SET ended_at=? WHERE id=? AND ended_at IS NULL",
                (_now(), world_id),
            )
            self._conn.commit()  # type: ignore[union-attr]

    def worlds(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._require().execute(
                "SELECT * FROM worlds ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --------------------------------------------------------------- events
    def add_events(self, world_id: int, events: list[HistoryEvent]) -> None:
        if not events:
            return
        with self._lock:
            self._require().executemany(
                "INSERT INTO events(world_id,tick,type,entity_id,caste,cause,x,y,payload,created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        world_id,
                        e.tick,
                        e.type,
                        e.entity_id,
                        e.caste,
                        e.cause,
                        e.x,
                        e.y,
                        json.dumps(e.payload),
                        _now(),
                    )
                    for e in events
                ],
            )
            self._conn.commit()  # type: ignore[union-attr]

    def history(
        self, world_id: int, since_id: int = 0, limit: int = 500
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._require().execute(
                "SELECT * FROM events WHERE world_id=? AND id>? ORDER BY id LIMIT ?",
                (world_id, since_id, limit),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "tick": r["tick"],
                "type": r["type"],
                "entity_id": r["entity_id"],
                "caste": r["caste"],
                "cause": r["cause"],
                "x": r["x"],
                "y": r["y"],
                "payload": json.loads(r["payload"] or "{}"),
            }
            for r in rows
        ]

    def death_count(self, world_id: int) -> int:
        with self._lock:
            row = self._require().execute(
                "SELECT COUNT(*) AS n FROM events WHERE world_id=? AND type='death'",
                (world_id,),
            ).fetchone()
        return int(row["n"])

    # ----------------------------------------------------------------- laws
    def add_law_change(
        self, world_id: int, tick: int, name: str, value: Any
    ) -> None:
        with self._lock:
            self._require().execute(
                "INSERT INTO law_changes(world_id,tick,name,value,created_at) VALUES (?,?,?,?,?)",
                (world_id, tick, name, json.dumps(value), _now()),
            )
            self._conn.commit()  # type: ignore[union-attr]

    def law_changes(self, world_id: int, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._require().execute(
                "SELECT * FROM law_changes WHERE world_id=? ORDER BY id DESC LIMIT ?",
                (world_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
