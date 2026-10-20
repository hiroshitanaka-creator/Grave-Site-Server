from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event

import pytest

from src.exporters.message_exporters import ExportFailure
from src.messages.service import MessageService
from src.messages.store import SQLiteMessageStore
from src.workflows.delivery_job import run_pending


class Drive:
    def __init__(self):
        self.ids, self.objects = [], {}
        self.timeout_after_write = False

    def reserve_id(self):
        value = f"file-{len(self.ids) + 1}"
        self.ids.append(value)
        return value

    def save(self, record):
        self.objects[record["drive_file_id"]] = record["payload"].copy()
        if self.timeout_after_write:
            self.timeout_after_write = False
            raise ExportFailure("drive_timeout", unknown=True)
        return record["drive_file_id"]


class Calendar:
    def __init__(self):
        self.events, self.calls = {}, 0
        self.failure = None

    def publish(self, record):
        self.calls += 1
        if self.failure:
            raise self.failure
        self.events[record["id"]] = record["payload"].copy()
        return record["id"]


@pytest.fixture
def context(tmp_path):
    store = SQLiteMessageStore(tmp_path / "state.db")
    record = store.create(
        {
            "recipient": "A",
            "message": "hello",
            "date": "2026-10-20",
            "calendar_id": "test-calendar",
            "publish_at": None,
        },
        "one",
    )
    drive, calendar = Drive(), Calendar()
    return store, record, drive, calendar, MessageService(store, drive, calendar)


def test_ambiguous_drive_write_reuses_reserved_id_after_restart(context):
    store, record, drive, calendar, service = context
    drive.timeout_after_write = True
    result = service.process(record["id"])
    assert result["drive_status"] == "unknown"
    assert result["delivery_status"] == "published"
    restarted = MessageService(SQLiteMessageStore(store.path), drive, calendar)
    assert restarted.process(record["id"])["drive_status"] == "saved"
    assert len(drive.ids) == len(drive.objects) == 1
    assert calendar.calls == 1


def test_delivery_failure_can_retry_without_drive_upload(context):
    _, record, drive, calendar, service = context
    calendar.failure = ExportFailure("calendar_403")
    first = service.process(record["id"])
    assert first["delivery_status"] == "failed"
    assert first["drive_status"] == "saved"
    calendar.failure = None
    assert service.process(record["id"])["delivery_status"] == "published"
    assert len(drive.ids) == 1


def test_provider_success_then_checkpoint_failure_recovers(context, monkeypatch):
    store, record, drive, calendar, service = context
    original = store.checkpoint

    def fail_final(record_id, token, **changes):
        if changes.get("delivery_status") == "published":
            raise OSError("simulated disk failure")
        return original(record_id, token, **changes)

    monkeypatch.setattr(store, "checkpoint", fail_final)
    with pytest.raises(OSError):
        service.process(record["id"])
    assert store.get(record["id"])["delivery_status"] == "unknown"
    restarted = MessageService(SQLiteMessageStore(store.path), drive, calendar)
    assert restarted.process(record["id"])["delivery_status"] == "published"
    assert len(calendar.events) == 1


def test_parallel_workers_do_not_publish_twice(context):
    store, record, drive, calendar, service = context
    entered, release = Event(), Event()
    original = calendar.publish

    def slow_publish(item):
        entered.set()
        assert release.wait(5)
        return original(item)

    calendar.publish = slow_publish
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(service.process, record["id"])
        assert entered.wait(5)
        other = MessageService(SQLiteMessageStore(store.path), drive, calendar)
        assert other.process(record["id"])["lease_token"]
        release.set()
        assert first.result()["delivery_status"] == "published"
    assert calendar.calls == 1


def test_scheduled_job_timezone_and_dry_run(context):
    store, record, _, calendar, service = context
    payload = {**record["payload"], "publish_at": "2026-10-20T09:00:00+09:00"}
    store.revise(record["id"], payload, 1)
    early = datetime(2026, 10, 19, 23, 59, tzinfo=timezone.utc)
    service.process(record["id"], now=early)
    assert calendar.calls == 0
    due = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
    assert run_pending(service, dry_run=True, now=due)["selected"] == 1
    assert calendar.calls == 0
    assert run_pending(service, now=due)["completed"] == 1
    assert calendar.calls == 1
    assert run_pending(service, now=due)["selected"] == 0


def test_job_continues_independent_messages(context):
    store, record, _, calendar, service = context
    other = store.create({**record["payload"], "recipient": "B"}, "two")
    original = calendar.publish

    def publish(item):
        if item["id"] == record["id"]:
            raise ExportFailure("calendar_403")
        return original(item)

    calendar.publish = publish
    result = run_pending(service)
    assert result["failed"] == result["completed"] == 1
    assert store.get(other["id"])["delivery_status"] == "published"


def test_disabled_provider_keeps_uncertain_previous_outcome(context):
    _, record, _, calendar, service = context
    calendar.failure = ExportFailure("calendar_timeout", unknown=True)
    assert service.process(record["id"])["delivery_status"] == "unknown"
    service.calendar_enabled = False
    assert service.process(record["id"])["delivery_status"] == "unknown"


def test_job_limit_does_not_starve_messages_after_permanent_failure(context):
    store, record, _, calendar, service = context
    other = store.create({**record["payload"], "recipient": "B"}, "two")
    calendar.failure = ExportFailure("calendar_403")
    assert run_pending(service, limit=1)["failed"] == 1
    calendar.failure = None
    assert run_pending(service, limit=1)["completed"] == 1
    assert store.get(other["id"])["delivery_status"] == "published"
