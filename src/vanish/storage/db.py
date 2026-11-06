"""Encrypted SQLite store. OWNER: orchestrator.

Layout: each table has clear-text index columns (ids, enums, timestamps: no PII) plus
`data BLOB`, which is the AES-GCM-encrypted JSON of the full pydantic model. AAD binds each
blob to (table, id), so rows can't be swapped between tables or ids.

Public API (stable; other modules use only this):
    Store(path=None, cipher=None)
    .save_profile(p) / .get_profile(id) / .list_profiles() / .delete_profile(id)
    .get_status(pid, bid) / .save_status(st) / .list_statuses(pid=None)
    .save_listing(l) / .list_listings(pid, bid=None)
    .save_request(r) / .get_request(id) / .list_requests(pid=None, bid=None, status=None)
    .save_evidence(e, plaintext: bytes) / .read_evidence(e) / .list_evidence(pid, bid=None)
    .save_todo(t) / .list_todos(pid=None, open_only=True) / .complete_todo(id)
    .log(event)  (append-only) / .events(pid=None, bid=None, limit=500)
    .transaction()  context manager
"""
from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .. import paths
from ..crypto import Cipher
from ..models import (
    BrokerStatus, Event, Evidence, Listing, Profile, Request, RequestStatus, Todo, utcnow,
)

M = TypeVar("M", bound=BaseModel)

SCHEMA_VERSION = 1
_DDL = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS brokers (            -- snapshot of registry entries used in runs
  id TEXT PRIMARY KEY, registry_version TEXT, data TEXT NOT NULL);  -- public info, not PII
CREATE TABLE IF NOT EXISTS broker_status (
  profile_id TEXT NOT NULL, broker_id TEXT NOT NULL, state TEXT NOT NULL,
  updated_at TEXT NOT NULL, next_check_at TEXT, data BLOB NOT NULL,
  PRIMARY KEY (profile_id, broker_id));
CREATE TABLE IF NOT EXISTS listings_found (
  id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, broker_id TEXT NOT NULL,
  first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS requests (
  id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, broker_id TEXT NOT NULL, kind TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL, sent_at TEXT, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, broker_id TEXT NOT NULL, kind TEXT NOT NULL,
  created_at TEXT NOT NULL, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS todos (
  id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, broker_id TEXT, kind TEXT NOT NULL,
  created_at TEXT NOT NULL, done_at TEXT, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, ts TEXT NOT NULL,
  profile_id TEXT, broker_id TEXT, actor TEXT NOT NULL, action TEXT NOT NULL,
  from_state TEXT, to_state TEXT, data BLOB NOT NULL);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
  BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
  WHEN (SELECT v FROM meta WHERE k='allow_event_purge') IS NOT '1'
  BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE INDEX IF NOT EXISTS ix_listings_pb ON listings_found(profile_id, broker_id);
CREATE INDEX IF NOT EXISTS ix_requests_pb ON requests(profile_id, broker_id);
CREATE INDEX IF NOT EXISTS ix_events_pb ON events(profile_id, broker_id);
"""


def _ts(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


class Store:
    def __init__(self, path: Path | None = None, cipher: Cipher | None = None) -> None:
        self.path = path or paths.db_path()
        self._cipher = cipher or Cipher()
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_DDL)
        self._conn.execute(
            "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
        )
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    # ------------------------------------------------------------------ plumbing
    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            self._conn.execute("COMMIT")

    def _enc(self, table: str, key: str, model: BaseModel) -> bytes:
        return self._cipher.encrypt(model.model_dump_json().encode(), f"{table}:{key}".encode())

    def _dec(self, table: str, key: str, blob: bytes, cls: type[M]) -> M:
        return cls.model_validate_json(self._cipher.decrypt(blob, f"{table}:{key}".encode()))

    def _x(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, args)

    # ------------------------------------------------------------------ profiles
    def save_profile(self, p: Profile) -> None:
        p = p.model_copy(update={"updated_at": utcnow()})
        self._x(
            "INSERT INTO profiles VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "updated_at=excluded.updated_at, data=excluded.data",
            (p.id, _ts(p.created_at), _ts(p.updated_at), self._enc("profiles", p.id, p)),
        )

    def get_profile(self, pid: str) -> Profile | None:
        r = self._x("SELECT data FROM profiles WHERE id=?", (pid,)).fetchone()
        return self._dec("profiles", pid, r[0], Profile) if r else None

    def list_profiles(self) -> list[Profile]:
        rows = self._x("SELECT id, data FROM profiles ORDER BY created_at").fetchall()
        return [self._dec("profiles", i, d, Profile) for i, d in rows]

    def delete_profile(self, pid: str) -> None:
        """Hard-delete a person's PII. Events keep only ids (no PII) for the audit trail."""
        with self.transaction():
            for t in ("listings_found", "requests", "evidence", "todos", "broker_status"):
                self._conn.execute(f"DELETE FROM {t} WHERE profile_id=?", (pid,))
            self._conn.execute("DELETE FROM profiles WHERE id=?", (pid,))
        d = paths.evidence_dir() / pid
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file():
                    f.unlink()

    # ------------------------------------------------------------------ status
    def get_status(self, pid: str, bid: str) -> BrokerStatus:
        r = self._x(
            "SELECT data FROM broker_status WHERE profile_id=? AND broker_id=?", (pid, bid)
        ).fetchone()
        if not r:
            return BrokerStatus(profile_id=pid, broker_id=bid)
        return self._dec("broker_status", f"{pid}/{bid}", r[0], BrokerStatus)

    def save_status(self, st: BrokerStatus) -> None:
        k = f"{st.profile_id}/{st.broker_id}"
        self._x(
            "INSERT INTO broker_status VALUES (?,?,?,?,?,?) ON CONFLICT(profile_id, broker_id) "
            "DO UPDATE SET state=excluded.state, updated_at=excluded.updated_at, "
            "next_check_at=excluded.next_check_at, data=excluded.data",
            (st.profile_id, st.broker_id, st.state.value, _ts(st.updated_at),
             _ts(st.next_check_at), self._enc("broker_status", k, st)),
        )

    def list_statuses(self, pid: str | None = None) -> list[BrokerStatus]:
        q, a = "SELECT profile_id, broker_id, data FROM broker_status", ()
        if pid:
            q, a = q + " WHERE profile_id=?", (pid,)
        return [self._dec("broker_status", f"{p}/{b}", d, BrokerStatus)
                for p, b, d in self._x(q, a).fetchall()]

    # ------------------------------------------------------------------ listings
    def save_listing(self, li: Listing) -> None:
        self._x(
            "INSERT INTO listings_found VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "last_seen=excluded.last_seen, data=excluded.data",
            (li.id, li.profile_id, li.broker_id, _ts(li.first_seen), _ts(li.last_seen),
             self._enc("listings_found", li.id, li)),
        )

    def list_listings(self, pid: str, bid: str | None = None) -> list[Listing]:
        q, a = "SELECT id, data FROM listings_found WHERE profile_id=?", (pid,)
        if bid:
            q, a = q + " AND broker_id=?", (pid, bid)
        return [self._dec("listings_found", i, d, Listing) for i, d in self._x(q, a).fetchall()]

    # ------------------------------------------------------------------ requests
    def save_request(self, r: Request) -> None:
        self._x(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "status=excluded.status, sent_at=excluded.sent_at, data=excluded.data",
            (r.id, r.profile_id, r.broker_id, r.kind.value, r.status.value, _ts(r.created_at),
             _ts(r.sent_at), self._enc("requests", r.id, r)),
        )

    def get_request(self, rid: str) -> Request | None:
        row = self._x("SELECT data FROM requests WHERE id=?", (rid,)).fetchone()
        return self._dec("requests", rid, row[0], Request) if row else None

    def list_requests(self, pid: str | None = None, bid: str | None = None,
                      status: RequestStatus | None = None) -> list[Request]:
        q, a = "SELECT id, data FROM requests WHERE 1=1", []
        for col, val in (("profile_id", pid), ("broker_id", bid),
                         ("status", status.value if status else None)):
            if val:
                q += f" AND {col}=?"
                a.append(val)
        q += " ORDER BY created_at"
        return [self._dec("requests", i, d, Request) for i, d in self._x(q, tuple(a)).fetchall()]

    # ------------------------------------------------------------------ evidence
    def save_evidence(self, e: Evidence, plaintext: bytes) -> Evidence:
        """Encrypts `plaintext` to VANISH_HOME/evidence/<relpath>; sets sha256."""
        dest = paths.evidence_dir() / e.relpath
        sha = self._cipher.encrypt_file(plaintext, dest)
        e = e.model_copy(update={"sha256": sha})
        self._x(
            "INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?)",
            (e.id, e.profile_id, e.broker_id, e.kind.value, _ts(e.created_at),
             self._enc("evidence", e.id, e)),
        )
        return e

    def read_evidence(self, e: Evidence) -> bytes:
        return self._cipher.decrypt_file(paths.evidence_dir() / e.relpath)

    def list_evidence(self, pid: str, bid: str | None = None) -> list[Evidence]:
        q, a = "SELECT id, data FROM evidence WHERE profile_id=?", (pid,)
        if bid:
            q, a = q + " AND broker_id=?", (pid, bid)
        q += " ORDER BY created_at"
        return [self._dec("evidence", i, d, Evidence) for i, d in self._x(q, a).fetchall()]

    # ------------------------------------------------------------------ todos
    def save_todo(self, t: Todo) -> None:
        self._x(
            "INSERT INTO todos VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "done_at=excluded.done_at, data=excluded.data",
            (t.id, t.profile_id, t.broker_id, t.kind.value, _ts(t.created_at), _ts(t.done_at),
             self._enc("todos", t.id, t)),
        )

    def list_todos(self, pid: str | None = None, open_only: bool = True) -> list[Todo]:
        q, a = "SELECT id, data FROM todos WHERE 1=1", []
        if pid:
            q += " AND profile_id=?"
            a.append(pid)
        if open_only:
            q += " AND done_at IS NULL"
        q += " ORDER BY created_at"
        return [self._dec("todos", i, d, Todo) for i, d in self._x(q, tuple(a)).fetchall()]

    def complete_todo(self, tid: str) -> Todo | None:
        row = self._x("SELECT data FROM todos WHERE id=?", (tid,)).fetchone()
        if not row:
            return None
        t = self._dec("todos", tid, row[0], Todo).model_copy(update={"done_at": utcnow()})
        self.save_todo(t)
        return t

    # ------------------------------------------------------------------ events
    def log(self, ev: Event) -> None:
        self._x(
            "INSERT INTO events (id, ts, profile_id, broker_id, actor, action, from_state, "
            "to_state, data) VALUES (?,?,?,?,?,?,?,?,?)",
            (ev.id, _ts(ev.ts), ev.profile_id, ev.broker_id, ev.actor.value, ev.action,
             ev.from_state.value if ev.from_state else None,
             ev.to_state.value if ev.to_state else None, self._enc("events", ev.id, ev)),
        )

    def events(self, pid: str | None = None, bid: str | None = None,
               limit: int = 500) -> list[Event]:
        q, a = "SELECT id, data FROM events WHERE 1=1", []
        for col, val in (("profile_id", pid), ("broker_id", bid)):
            if val:
                q += f" AND {col}=?"
                a.append(val)
        q += " ORDER BY seq DESC LIMIT ?"
        a.append(limit)
        return [self._dec("events", i, d, Event) for i, d in self._x(q, tuple(a)).fetchall()]

    # ------------------------------------------------------------------ brokers snapshot
    def snapshot_brokers(self, registry_version: str, brokers_json: dict[str, str]) -> None:
        with self.transaction():
            for bid, data in brokers_json.items():
                self._conn.execute(
                    "INSERT OR REPLACE INTO brokers VALUES (?,?,?)", (bid, registry_version, data)
                )


def dumps(obj: object) -> str:
    return json.dumps(obj, default=str)
