import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.messages.store import LeaseLost, RecordConflict, SQLiteMessageStore, configured_store


@pytest.fixture
def payload():
    return {
        "recipient": "family",
        "message": "hello",
        "date": "2026-10-20",
        "tags": ["thanks"],
        "source": "test",
        "calendar_id": "test-calendar",
        "publish_at": None,
        "memory_refs": ["ref:1"],
    }


def test_concurrent_creation_is_unique_and_conflicts_do_not_overwrite(tmp_path, payload):
    path = tmp_path / "messages.db"
    store = SQLiteMessageStore(path)

    def create(_):
        return SQLiteMessageStore(path).create(payload, "same-request")["id"]

    with ThreadPoolExecutor(max_workers=8) as workers:
        ids = list(workers.map(create, range(24)))
    assert len(set(ids)) == 1
    assert len(store.records()) == 1
    with pytest.raises(RecordConflict):
        store.create({**payload, "recipient": "someone else"}, "same-request")
    assert store.get(ids[0])["payload"] == payload


def test_content_revisions_and_restart(tmp_path, payload):
    path = tmp_path / "messages.db"
    store = SQLiteMessageStore(path)
    record = store.create(payload, "original")
    updated = store.revise(record["id"], {**payload, "message": "corrected"}, 1)
    assert updated["revision"] == 2
    with sqlite3.connect(path) as conn:
        versions = [
            json.loads(row[0])["payload"]["message"]
            for row in conn.execute("SELECT body FROM revisions ORDER BY revision")
        ]
    assert versions == ["hello", "corrected"]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from src.messages.store import SQLiteMessageStore; "
            "print(SQLiteMessageStore(sys.argv[1]).get(sys.argv[2])['payload']['message'])",
            str(path),
            record["id"],
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(__import__("pathlib").Path(__file__).resolve().parents[1]),
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "corrected"


def test_lease_fencing_and_recovery(tmp_path, payload, monkeypatch):
    store = SQLiteMessageStore(tmp_path / "state.db")
    record = store.create(payload, "one")
    monkeypatch.setattr("src.messages.store.time.time", lambda: 100)
    _, first = store.claim(record["id"], lease_seconds=10)
    with pytest.raises(RecordConflict):
        store.claim(record["id"])
    with pytest.raises(RecordConflict):
        store.revise(record["id"], {**payload, "message": "new"}, 1)
    monkeypatch.setattr("src.messages.store.time.time", lambda: 111)
    _, second = store.claim(record["id"])
    with pytest.raises(LeaseLost):
        store.checkpoint(record["id"], first, delivery_status="published")
    with pytest.raises(LeaseLost):
        store.release(record["id"], first)
    store.checkpoint(record["id"], second, delivery_status="unknown")
    store.release(record["id"], second)


def test_no_key_creates_distinct_records(tmp_path, payload):
    store = SQLiteMessageStore(tmp_path / "state.db")
    assert store.create(payload, None)["id"] != store.create(payload, None)["id"]


def test_cloud_run_refuses_ephemeral_sqlite(monkeypatch):
    monkeypatch.setenv("MESSAGE_STORE", "sqlite")
    monkeypatch.setenv("K_SERVICE", "test")
    with pytest.raises(ValueError, match="ephemeral"):
        configured_store()


def test_new_request_does_not_overwrite_same_day(tmp_path, payload):
    store = SQLiteMessageStore(tmp_path / "state.db")
    a = store.create(payload, "a")
    b = store.create({**payload, "recipient": "B", "message": "B text"}, "b")
    assert a["id"] != b["id"]
    assert store.get(a["id"])["payload"] == payload
