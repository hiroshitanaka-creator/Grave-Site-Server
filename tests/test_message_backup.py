import sqlite3

import pytest

from src.messages.backup import backup
from src.messages.store import SQLiteMessageStore


def test_backup_restores_ids_revisions_and_unknown_state_without_overwriting(tmp_path):
    store = SQLiteMessageStore(tmp_path / "source.db")
    record = store.create({"message": "original", "calendar_id": "calendar"}, "request")
    store.revise(record["id"], {"message": "correction", "calendar_id": "calendar"}, 1)
    _, token = store.claim(record["id"])
    store.checkpoint(record["id"], token, drive_file_id="reserved", delivery_status="unknown")
    store.release(record["id"], token)
    destination = tmp_path / "backup.db"
    assert backup(store.path, destination) == 1
    restored = SQLiteMessageStore(destination).get(record["id"])
    assert restored == store.get(record["id"])
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT count(*) FROM revisions").fetchone()[0] == 2
    with pytest.raises(FileExistsError):
        backup(store.path, destination)
    assert SQLiteMessageStore(destination).get(record["id"]) == restored


def test_missing_backup_source_is_not_created(tmp_path):
    source = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        backup(source, tmp_path / "backup.db")
    assert not source.exists()
