"""Atomic record/revision storage; no external API calls inside transactions."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

Record = dict[str, Any]
Mutation = Callable[[Record | None], Record]


class RecordNotFound(LookupError):
    pass


class RecordConflict(ValueError):
    pass


class LeaseLost(RecordConflict):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class MessageStore:
    """Subclasses must implement serializable per-record mutations."""

    def _mutate(self, record_id: str, mutation: Mutation) -> Record:
        raise NotImplementedError

    def get(self, record_id: str) -> Record:
        raise NotImplementedError

    def records(self) -> list[Record]:
        raise NotImplementedError

    def create(self, payload: Record, request_id: str | None) -> Record:
        digest = fingerprint(payload)
        record_id = "msg-" + (fingerprint(request_id) if request_id else uuid.uuid4().hex)
        now = time.time()

        def mutation(current: Record | None) -> Record:
            if current is not None:
                if current["request_hash"] != digest:
                    raise RecordConflict("request_id already exists with different content")
                return current
            return {
                "id": record_id,
                "request_id": request_id,
                "request_hash": digest,
                "revision": 1,
                "payload": payload,
                "created_at": now,
                "updated_at": now,
                "drive_status": "pending",
                "delivery_status": "pending",
                "drive_file_id": None,
                "calendar_event_id": None,
                "drive_error": None,
                "delivery_error": None,
                "lease_token": None,
                "lease_until": 0.0,
            }

        return self._mutate(record_id, mutation)

    def revise(self, record_id: str, payload: Record, expected_revision: int) -> Record:
        def mutation(current: Record | None) -> Record:
            if current is None:
                raise RecordNotFound(record_id)
            if current["revision"] != expected_revision:
                raise RecordConflict("revision changed; read the record before editing")
            if current["lease_token"]:
                raise RecordConflict("delivery in progress; reconcile/retry before editing")
            # A missing destination cannot have received an event; allow explicit repair.
            # Moving an already-bound destination needs a separate migration.
            if (
                current["payload"]["calendar_id"] is not None
                and payload["calendar_id"] != current["payload"]["calendar_id"]
            ):
                raise RecordConflict("calendar_id is immutable; moving an event needs a migration")
            if payload == current["payload"]:
                return current
            current.update(
                payload=payload,
                revision=current["revision"] + 1,
                updated_at=time.time(),
                drive_status="pending",
                delivery_status="pending",
                drive_file_id=None,
                drive_error=None,
                delivery_error=None,
            )
            return current

        return self._mutate(record_id, mutation)

    def claim(self, record_id: str, *, lease_seconds: float = 300) -> tuple[Record, str]:
        now, token = time.time(), uuid.uuid4().hex

        def mutation(current: Record | None) -> Record:
            if current is None:
                raise RecordNotFound(record_id)
            if current["lease_token"] and current["lease_until"] > now:
                raise RecordConflict("delivery already in progress")
            current.update(lease_token=token, lease_until=now + lease_seconds)
            return current

        return self._mutate(record_id, mutation), token

    def checkpoint(self, record_id: str, token: str, **changes: Any) -> Record:
        allowed = {
            "drive_status",
            "delivery_status",
            "drive_file_id",
            "calendar_event_id",
            "drive_error",
            "delivery_error",
        }
        if not changes.keys() <= allowed:
            raise ValueError("invalid checkpoint fields")

        def mutation(current: Record | None) -> Record:
            if current is None or current["lease_token"] != token:
                raise LeaseLost("worker lease was replaced")
            if current["lease_until"] <= time.time():
                raise LeaseLost("worker lease expired; retry to reconcile")
            current.update(changes, updated_at=time.time())
            return current

        return self._mutate(record_id, mutation)

    def release(self, record_id: str, token: str) -> Record:
        def mutation(current: Record | None) -> Record:
            if current is None or current["lease_token"] != token:
                raise LeaseLost("worker lease was replaced")
            current.update(lease_token=None, lease_until=0.0)
            return current

        return self._mutate(record_id, mutation)


class SQLiteMessageStore(MessageStore):
    """Durable on one host/local POSIX disk. Not a shared Cloud Run database."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, body TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS revisions (id TEXT, revision INTEGER, "
                "body TEXT NOT NULL, PRIMARY KEY(id, revision));"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _mutate(self, record_id: str, mutation: Mutation) -> Record:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT body FROM messages WHERE id=?", (record_id,)).fetchone()
            record = mutation(json.loads(row[0]) if row else None)
            body = canonical(record)
            conn.execute(
                "INSERT INTO messages VALUES (?,?) ON CONFLICT(id) "
                "DO UPDATE SET body=excluded.body",
                (record_id, body),
            )
            conn.execute(
                "INSERT INTO revisions VALUES (?,?,?) ON CONFLICT(id,revision) "
                "DO UPDATE SET body=excluded.body",
                (record_id, record["revision"], body),
            )
            conn.commit()
            return copy.deepcopy(record)
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get(self, record_id: str) -> Record:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT body FROM messages WHERE id=?", (record_id,)).fetchone()
        if row is None:
            raise RecordNotFound(record_id)
        return json.loads(row[0])

    def records(self) -> list[Record]:
        with closing(self._connect()) as conn:
            return [
                json.loads(row[0]) for row in conn.execute("SELECT body FROM messages ORDER BY id")
            ]


class FirestoreMessageStore(MessageStore):
    """Optional multi-instance Cloud Run backend; never provisions a database."""

    def __init__(
        self, project: str, collection: str = "grave_messages", database: str = "(default)"
    ):
        from google.cloud import firestore

        self.client = firestore.Client(project=project, database=database)
        self.collection = self.client.collection(collection)

    def _mutate(self, record_id: str, mutation: Mutation) -> Record:
        from google.cloud import firestore

        ref = self.collection.document(record_id)

        @firestore.transactional
        def transact(transaction):
            snapshot = ref.get(transaction=transaction)
            record = mutation(json.loads(snapshot.get("body")) if snapshot.exists else None)
            # One blob field avoids Firestore's nested-field/index limits for arbitrary user tags.
            body = {"body": canonical(record)}
            transaction.set(ref, body)
            transaction.set(ref.collection("revisions").document(str(record["revision"])), body)
            return record

        return transact(self.client.transaction())

    def get(self, record_id: str) -> Record:
        snapshot = self.collection.document(record_id).get()
        if not snapshot.exists:
            raise RecordNotFound(record_id)
        return json.loads(snapshot.get("body"))

    def records(self) -> list[Record]:
        return [json.loads(snapshot.get("body")) for snapshot in self.collection.stream()]


def configured_store() -> MessageStore:
    backend = os.getenv("MESSAGE_STORE", "sqlite")
    if backend == "sqlite":
        if os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"):
            raise ValueError("Cloud Run requires MESSAGE_STORE=firestore; local disk is ephemeral")
        return SQLiteMessageStore(os.getenv("MESSAGE_DB_PATH", "data/messages.sqlite3"))
    if backend == "firestore":
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        if not project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for Firestore")
        return FirestoreMessageStore(
            project,
            os.getenv("FIRESTORE_COLLECTION", "grave_messages"),
            os.getenv("FIRESTORE_DATABASE", "(default)"),
        )
    raise ValueError("MESSAGE_STORE must be sqlite or firestore")
