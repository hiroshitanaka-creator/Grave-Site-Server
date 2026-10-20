import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.router import message_service
from src.exporters.message_exporters import ExportFailure
from src.messages.service import MessageService
from src.messages.store import SQLiteMessageStore

VALID_BODY = {
    "recipient": "妻",
    "message": "今日もありがとう",
    "date": "2026-03-14",
    "request_id": "api-test-001",
}


@pytest.fixture
def context(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "test-calendar")
    service = MessageService(
        SQLiteMessageStore(tmp_path / "messages.db"), drive_enabled=False, calendar_enabled=False
    )
    app.dependency_overrides[message_service] = lambda: service
    with TestClient(
        app, headers={"X-API-Key": "test-key"}, raise_server_exceptions=False
    ) as client:
        yield client, service
    app.dependency_overrides.clear()


def test_save_and_read_all_fields(context):
    client, service = context
    body = {
        **VALID_BODY,
        "message": "  今日もありがとう\n",
        "tags": ["感謝"],
        "source": "cli",
        "memory_refs": ["diary:001"],
    }
    response = client.post("/actions/save-message", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["storage_type"] == "record"
    assert data["delivery_status"] == "disabled"
    content = client.get(f"/messages/{data['record_id']}").json()["content"]
    for key in ("recipient", "message", "date", "tags", "source", "memory_refs"):
        assert content[key] == body[key]
    assert len(service.store.records()) == 1


def test_same_day_different_recipient_and_retry_conflict(context):
    client, service = context
    first = client.post("/actions/save-message", json=VALID_BODY).json()
    second = client.post(
        "/actions/save-message",
        json={**VALID_BODY, "recipient": "家族", "request_id": "api-test-002"},
    ).json()
    assert first["record_id"] != second["record_id"]
    assert (
        client.post("/actions/save-message", json=VALID_BODY).json()["record_id"]
        == first["record_id"]
    )
    conflict = client.post("/actions/save-message", json={**VALID_BODY, "message": "変更"})
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "conflict"
    assert len(service.store.records()) == 2


def test_update_keeps_identity_and_checks_revision(context):
    client, _ = context
    first = client.post("/actions/save-message", json=VALID_BODY).json()
    body = {key: value for key, value in VALID_BODY.items() if key != "request_id"}
    edit = {**body, "message": "訂正", "expected_revision": 1}
    result = client.put(f"/messages/{first['record_id']}", json=edit)
    assert result.status_code == 200
    assert result.json()["record_id"] == first["record_id"]
    assert result.json()["revision"] == 2
    assert client.put(f"/messages/{first['record_id']}", json=edit).status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        {"recipient": ""},
        {"message": ""},
        {"message": " "},
        {"message": "a" * 1001},
        {"date": "not-a-date"},
        {"date": "20261020"},
        {"date": 0},
        {"date": "9999-12-31"},
        {"publish_at": "2026-10-20T01:00:00"},
        {"request_id": ""},
        {"tags": [" "]},
        {"unexpected": True},
    ],
)
def test_invalid_body(context, change):
    client, _ = context
    response = client.post("/actions/save-message", json={**VALID_BODY, **change})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert "input" not in response.json()


@pytest.mark.parametrize("key", ["recipient", "message", "date"])
def test_missing_required(context, key):
    client, _ = context
    assert (
        client.post(
            "/actions/save-message", json={k: v for k, v in VALID_BODY.items() if k != key}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("header", ["wrong", ""])
def test_wrong_key(context, header):
    client, service = context
    response = client.post("/actions/save-message", json=VALID_BODY, headers={"X-API-Key": header})
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert not service.store.records()


def test_missing_configuration_fails_closed(context, monkeypatch):
    client, service = context
    monkeypatch.delenv("API_KEY")
    assert client.post("/actions/save-message", json=VALID_BODY).status_code == 500
    assert not service.store.records()


def test_calendar_failure_visible_then_retry(context):
    client, service = context

    class Calendar:
        failing = True

        def publish(self, record):
            if self.failing:
                raise ExportFailure("calendar_403")
            return "calendar-id"

    calendar = Calendar()
    service.calendar, service.calendar_enabled = calendar, True
    first = client.post("/actions/save-message", json=VALID_BODY)
    assert first.status_code == 200
    data = first.json()
    assert data["saved"] and data["delivery_status"] == "failed"
    calendar.failing = False
    result = client.post(f"/messages/{data['record_id']}/retry").json()
    assert result["delivery_status"] == "published"
    assert result["calendar_event_id"] == "calendar-id"


def test_missing_record(context):
    client, _ = context
    assert client.get("/messages/msg-" + "0" * 32).status_code == 404


def test_unset_calendar_can_be_bound_but_existing_destination_cannot_move(context, monkeypatch):
    client, _ = context
    monkeypatch.delenv("GOOGLE_CALENDAR_ID")
    first = client.post("/actions/save-message", json=VALID_BODY).json()
    payload = {key: value for key, value in VALID_BODY.items() if key != "request_id"}
    edit = {**payload, "calendar_id": "test-calendar", "expected_revision": 1}
    fixed = client.put(f"/messages/{first['record_id']}", json=edit)
    assert fixed.status_code == 200
    assert fixed.json()["revision"] == 2
    edit.update(calendar_id="different-calendar", expected_revision=2)
    assert client.put(f"/messages/{first['record_id']}", json=edit).status_code == 409
