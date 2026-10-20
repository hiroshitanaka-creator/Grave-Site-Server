import copy
from types import SimpleNamespace

import pytest

from src.exporters.message_exporters import (
    CalendarMessageExporter,
    DriveMessageExporter,
    ExportFailure,
)


class HttpError(Exception):
    def __init__(self, status):
        self.resp = SimpleNamespace(status=status)


class Operation:
    def __init__(self, callback):
        self.callback, self.headers = callback, {}

    def execute(self):
        return self.callback(self.headers)


class CalendarAPI:
    """A server state model: IDs, optimistic concurrency and post-write timeouts."""

    def __init__(self):
        self.data, self.writes = {}, 0
        self.timeout_once = False
        self.before_update = None

    def events(self):
        return self

    def get(self, *, calendarId, eventId):
        def execute(_):
            if (calendarId, eventId) not in self.data:
                raise HttpError(404)
            return copy.deepcopy(self.data[calendarId, eventId])

        return Operation(execute)

    def insert(self, *, calendarId, body):
        def execute(_):
            key = (calendarId, body["id"])
            if key in self.data:
                raise HttpError(409)
            self.writes += 1
            self.data[key] = {**copy.deepcopy(body), "etag": str(self.writes)}
            if self.timeout_once:
                self.timeout_once = False
                raise TimeoutError
            return self.data[key]

        return Operation(execute)

    def update(self, *, calendarId, eventId, body):
        def execute(headers):
            key = (calendarId, eventId)
            if self.before_update:
                callback, self.before_update = self.before_update, None
                callback()
            if headers.get("If-Match") != self.data[key]["etag"]:
                raise HttpError(412)
            self.writes += 1
            self.data[key] = {"id": eventId, **copy.deepcopy(body), "etag": str(self.writes)}
            return self.data[key]

        return Operation(execute)


class DriveAPI:
    def __init__(self):
        self.data, self.writes = {}, 0
        self.timeout_once = False
        self.next_id = 0

    def files(self):
        return self

    def generateIds(self, **kwargs):
        def execute(_):
            self.next_id += 1
            return {"ids": [f"reserved-{self.next_id}"]}

        return Operation(execute)

    def get(self, *, fileId, fields, supportsAllDrives):
        assert supportsAllDrives

        def execute(_):
            if fileId not in self.data:
                raise HttpError(404)
            return copy.deepcopy(self.data[fileId])

        return Operation(execute)

    def create(self, *, body, media_body, fields, supportsAllDrives):
        assert supportsAllDrives

        def execute(_):
            if body["id"] in self.data:
                raise HttpError(409)
            self.writes += 1
            self.data[body["id"]] = copy.deepcopy(body)
            if self.timeout_once:
                self.timeout_once = False
                raise TimeoutError
            return self.data[body["id"]]

        return Operation(execute)


@pytest.fixture
def record():
    return {
        "id": "msg-" + "1" * 32,
        "revision": 1,
        "request_id": "test",
        "created_at": 0,
        "payload": {
            "recipient": "family",
            "message": "hello",
            "date": "2026-10-20",
            "calendar_id": "test-calendar",
            "tags": [],
            "source": "test",
        },
    }


def test_calendar_timeout_reconciliation_and_correction(record):
    server = CalendarAPI()
    server.timeout_once = True
    exporter = CalendarMessageExporter(server)
    with pytest.raises(ExportFailure) as failure:
        exporter.publish(record)
    assert failure.value.unknown
    event_id = exporter.publish(record)
    assert server.writes == 1
    corrected = {**record, "revision": 2, "payload": {**record["payload"], "message": "corrected"}}
    assert exporter.publish(corrected) == event_id
    assert server.writes == 2 and len(server.data) == 1
    with pytest.raises(ExportFailure, match="stale_worker"):
        exporter.publish(record)


def test_calendar_etag_blocks_stale_inflight_update(record):
    server = CalendarAPI()
    exporter = CalendarMessageExporter(server)
    event_id = exporter.publish(record)
    second = {**record, "revision": 2, "payload": {**record["payload"], "message": "v2"}}
    third = {**record, "revision": 3, "payload": {**record["payload"], "message": "v3"}}
    server.before_update = lambda: exporter.publish(third)
    with pytest.raises(ExportFailure, match="stale_worker"):
        exporter.publish(second)
    assert server.data["test-calendar", event_id]["description"] == "v3"


def test_calendar_does_not_overwrite_human_edit(record):
    server = CalendarAPI()
    exporter = CalendarMessageExporter(server)
    event_id = exporter.publish(record)
    server.data["test-calendar", event_id]["description"] = "manually edited"
    with pytest.raises(ExportFailure, match="external_edit_conflict"):
        exporter.publish(record)


def test_drive_preallocated_id_and_immutable_versions(record):
    server = DriveAPI()
    exporter = DriveMessageExporter(server, "folder")
    record["drive_file_id"] = exporter.reserve_id()
    server.timeout_once = True
    with pytest.raises(ExportFailure) as failure:
        exporter.save(record)
    assert failure.value.unknown
    assert exporter.save(record) == record["drive_file_id"]
    assert server.writes == 1
    second = {
        **record,
        "revision": 2,
        "drive_file_id": exporter.reserve_id(),
        "payload": {**record["payload"], "message": "corrected"},
    }
    exporter.save(second)
    assert len(server.data) == 2
    assert server.data[record["drive_file_id"]]["name"].endswith("_v1.json")


def test_drive_id_collision_is_not_accepted_as_success(record):
    server = DriveAPI()
    exporter = DriveMessageExporter(server, "folder")
    record["drive_file_id"] = exporter.reserve_id()
    server.data[record["drive_file_id"]] = {"appProperties": {}, "parents": ["folder"]}
    with pytest.raises(ExportFailure, match="conflict"):
        exporter.save(record)
