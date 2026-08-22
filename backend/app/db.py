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
CREATE TABLE IF NOT EXISTS creatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    caste TEXT,
    clan_id INTEGER,
    generation INTEGER,
    mother_id INTEGER,
    father_id INTEGER,
    born_tick INTEGER,
    died_tick INTEGER
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_world ON events(world_id, id);
CREATE INDEX IF NOT EXISTS idx_creatures_world ON creatures(world_id, entity_id);
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

    # ------------------------------------------------------------- genealogy
    def genealogy_parents(
        self, world_id: int, entity_id: int
    ) -> tuple[dict | None, dict | None]:
        """(mother, father) minimal cards from the genealogy table, if recorded."""
        with self._lock:
            row = self._require().execute(
                "SELECT mother_id, father_id FROM creatures"
                " WHERE world_id=? AND entity_id=?",
                (world_id, entity_id),
            ).fetchone()
        if row is None:
            return None, None
        cards: dict[str, dict | None] = {"m": None, "f": None}
        for pid, which in ((row["mother_id"], "m"), (row["father_id"], "f")):
            if not pid:
                continue
            with self._lock:
                prow = self._require().execute(
                    "SELECT caste FROM creatures WHERE world_id=? AND entity_id=?",
                    (world_id, pid),
                ).fetchone()
            cards[which] = {
                "id": pid,
                "caste": prow["caste"] if prow else None,
            }
        return cards["m"], cards["f"]

    def genealogy_children(self, world_id: int, entity_id: int) -> list[dict]:
        with self._lock:
            rows = self._require().execute(
                "SELECT entity_id, caste FROM creatures WHERE world_id=?"
                " AND (mother_id=? OR father_id=?)",
                (world_id, entity_id, entity_id),
            ).fetchall()
        return [{"id": r["entity_id"], "caste": r["caste"]} for r in rows]

    def law_changes(self, world_id: int, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._require().execute(
                "SELECT * FROM law_changes WHERE world_id=? ORDER BY id DESC LIMIT ?",
                (world_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- genealogy
    def add_creature(
        self,
        world_id: int,
        entity_id: int,
        caste: str,
        clan_id: int,
        generation: int,
        mother_id: int,
        father_id: int,
        born_tick: int,
    ) -> None:
        with self._lock:
            self._require().execute(
                "INSERT INTO creatures(world_id,entity_id,caste,clan_id,generation,"
                "mother_id,father_id,born_tick,died_tick) VALUES (?,?,?,?,?,?,?,?,NULL)",
                (world_id, entity_id, caste, clan_id, generation,
                 mother_id or None, father_id or None, born_tick),
            )
            self._conn.commit()  # type: ignore[union-attr]

    def mark_death(self, world_id: int, entity_id: int, died_tick: int) -> None:
        with self._lock:
            cur = self._require().execute(
                "UPDATE creatures SET died_tick=? WHERE world_id=? AND entity_id=?"
                " AND died_tick IS NULL",
                (died_tick, world_id, entity_id),
            )
            if cur.rowcount == 0:  # founder with no birth record: insert minimal row
                self._require().execute(
                    "INSERT INTO creatures(world_id,entity_id,born_tick,died_tick)"
                    " VALUES (?,?,NULL,?)",
                    (world_id, entity_id, died_tick),
                )
            self._conn.commit()  # type: ignore[union-attr]

    # -------------------------------------------------------------- snapshots
    def save_snapshot(self, world_id: int, tick: int, payload: str) -> int:
        with self._lock:
            cur = self._require().execute(
                "INSERT INTO snapshots(world_id,tick,payload,created_at) VALUES (?,?,?,?)",
                (world_id, tick, payload, _now()),
            )
            self._conn.commit()  # type: ignore[union-attr]
            return int(cur.lastrowid)

    def list_snapshots(self, world_id: int, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._require().execute(
                "SELECT id,world_id,tick,created_at FROM snapshots"
                " WHERE world_id=? ORDER BY id DESC LIMIT ?",
                (world_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_snapshot(self, snapshot_id: int) -> dict | None:
        with self._lock:
            row = self._require().execute(
                "SELECT * FROM snapshots WHERE id=?", (snapshot_id,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        return d
