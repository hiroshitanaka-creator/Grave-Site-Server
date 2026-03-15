from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.exporters.drive_exporter import UploadResult

client = TestClient(app, raise_server_exceptions=False)

VALID_BODY = {
    "recipient": "妻",
    "message": "今日もありがとう",
    "date": "2026-03-14",
}


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


@patch("src.api.router._publish_to_calendar", return_value="cal-event-id")
@patch("src.api.router._save_to_drive", return_value="drive-file-id")
def test_save_message_returns_200(mock_drive, mock_cal):
    resp = client.post("/actions/save-message", json=VALID_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] is True
    assert data["storage_type"] == "document"
    assert data["record_id"] == "cal-event-id"  # calendar_event_id が優先


@patch("src.api.router._publish_to_calendar", return_value=None)
@patch("src.api.router._save_to_drive", return_value="drive-file-id")
def test_save_message_falls_back_to_drive_id_when_no_calendar(mock_drive, mock_cal):
    resp = client.post("/actions/save-message", json=VALID_BODY)
    assert resp.status_code == 200
    assert resp.json()["record_id"] == "drive-file-id"


@patch("src.api.router._publish_to_calendar", return_value=None)
@patch("src.api.router._save_to_drive", return_value="drive-file-id")
def test_save_message_accepts_optional_fields(mock_drive, mock_cal):
    body = {**VALID_BODY, "tags": ["感謝", "家族"], "source": "cli", "request_id": "req-001"}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# バリデーション（400系）
# ---------------------------------------------------------------------------


def test_save_message_rejects_missing_recipient():
    body = {k: v for k, v in VALID_BODY.items() if k != "recipient"}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


def test_save_message_rejects_missing_message():
    body = {k: v for k, v in VALID_BODY.items() if k != "message"}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


def test_save_message_rejects_missing_date():
    body = {k: v for k, v in VALID_BODY.items() if k != "date"}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


def test_save_message_rejects_invalid_date_format():
    body = {**VALID_BODY, "date": "not-a-date"}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


def test_save_message_rejects_empty_message():
    body = {**VALID_BODY, "message": ""}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


def test_save_message_rejects_message_over_1000_chars():
    body = {**VALID_BODY, "message": "a" * 1001}
    resp = client.post("/actions/save-message", json=body)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 認証（401系）
# ---------------------------------------------------------------------------


def test_save_message_rejects_wrong_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    resp = client.post(
        "/actions/save-message",
        json=VALID_BODY,
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


@patch("src.api.router._publish_to_calendar", return_value=None)
@patch("src.api.router._save_to_drive", return_value="file-id")
def test_save_message_accepts_correct_api_key(mock_drive, mock_cal, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "correct-key")
    resp = client.post(
        "/actions/save-message",
        json=VALID_BODY,
        headers={"X-API-Key": "correct-key"},
    )
    assert resp.status_code == 200


@patch("src.api.router._publish_to_calendar", return_value=None)
@patch("src.api.router._save_to_drive", return_value="file-id")
def test_save_message_returns_500_when_api_key_not_configured(
    mock_drive, mock_cal, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/actions/save-message", json=VALID_BODY)
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Drive エラー（500系）
# ---------------------------------------------------------------------------


@patch("src.api.router._save_to_drive")
def test_save_message_returns_500_on_drive_error(mock_drive):
    from fastapi import HTTPException

    mock_drive.side_effect = HTTPException(
        status_code=500, detail={"error": "storage_error", "message": "drive failed"}
    )
    resp = client.post("/actions/save-message", json=VALID_BODY)
    assert resp.status_code == 500
