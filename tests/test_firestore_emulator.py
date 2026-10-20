"""Opt-in integration gate. Never points at a production Firestore endpoint."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.messages.store import FirestoreMessageStore, RecordConflict


@pytest.mark.firestore
def test_firestore_transaction_contract():
    host = os.getenv("FIRESTORE_EMULATOR_HOST", "")
    if not host.startswith(("localhost:", "127.0.0.1:")):
        pytest.skip(
            "local Firestore emulator not configured; cloud adapter not integration-verified"
        )
    store = FirestoreMessageStore("demo-grave-site", "test_" + uuid.uuid4().hex)
    body = {"message": "test", "calendar_id": "calendar"}
    with ThreadPoolExecutor(max_workers=4) as workers:
        records = list(workers.map(lambda _: store.create(body, "same"), range(8)))
    assert len({record["id"] for record in records}) == 1
    record = records[0]
    with pytest.raises(RecordConflict):
        store.create({**body, "message": "different"}, "same")
    _, lease = store.claim(record["id"])
    with pytest.raises(RecordConflict):
        store.claim(record["id"])
    store.checkpoint(record["id"], lease, delivery_status="unknown")
    store.release(record["id"], lease)
    assert store.get(record["id"])["delivery_status"] == "unknown"
    assert store.revise(record["id"], {**body, "message": "changed"}, 1)["revision"] == 2
