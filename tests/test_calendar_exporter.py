from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.exporters.calendar_exporter import (
    CALENDAR_ID_ENV,
    CALENDAR_TIMEZONE_ENV,
    SERVICE_ACCOUNT_JSON_ENV,
    CalendarExporterError,
    CalendarPublishResult,
    EventUpsertResult,
    _build_idempotency_key,
    _find_existing_event_id,
    build_daily_event_payload,
    load_calendar_config,
    publish_daily_message,
    upsert_daily_event,
)


# ---------------------------------------------------------------------------
# load_calendar_config
# ---------------------------------------------------------------------------


def test_load_calendar_config_requires_service_account_json(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(SERVICE_ACCOUNT_JSON_ENV, raising=False)
    monkeypatch.setenv(CALENDAR_ID_ENV, "cal@example.com")

    with pytest.raises(CalendarExporterError, match=SERVICE_ACCOUNT_JSON_ENV):
        load_calendar_config()


def test_load_calendar_config_requires_calendar_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(SERVICE_ACCOUNT_JSON_ENV, "/path/to/sa.json")
    monkeypatch.delenv(CALENDAR_ID_ENV, raising=False)

    with pytest.raises(CalendarExporterError, match=CALENDAR_ID_ENV):
        load_calendar_config()


def test_load_calendar_config_calendar_id_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(SERVICE_ACCOUNT_JSON_ENV, "/path/to/sa.json")
    monkeypatch.delenv(CALENDAR_ID_ENV, raising=False)

    config = load_calendar_config(calendar_id_override="override@example.com")
    assert config.calendar_id == "override@example.com"


def test_load_calendar_config_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(SERVICE_ACCOUNT_JSON_ENV, "/sa.json")
    monkeypatch.setenv(CALENDAR_ID_ENV, "cal@group.calendar.google.com")
    monkeypatch.setenv(CALENDAR_TIMEZONE_ENV, "Asia/Tokyo")

    config = load_calendar_config()
    assert config.calendar_id == "cal@group.calendar.google.com"
    assert config.timezone == "Asia/Tokyo"
    assert config.service_account_json == "/sa.json"


# ---------------------------------------------------------------------------
# build_daily_event_payload
# ---------------------------------------------------------------------------


def test_build_daily_event_payload_structure():
    payload = build_daily_event_payload(
        target_date=date(2026, 3, 14),
        message="今日は良い日だった",
        idempotency_key="abc123",
        summary="テスト日記",
    )
    assert payload["start"] == {"date": "2026-03-14"}
    assert payload["end"] == {"date": "2026-03-15"}
    assert payload["description"] == "今日は良い日だった"
    assert payload["summary"] == "テスト日記"
    assert payload["extendedProperties"]["private"]["idempotency_key"] == "abc123"


def test_build_daily_event_payload_default_summary():
    payload = build_daily_event_payload(
        target_date=date(2026, 3, 14),
        message="msg",
        idempotency_key="key",
    )
    assert payload["summary"] == "Daily diary"


# ---------------------------------------------------------------------------
# _build_idempotency_key
# ---------------------------------------------------------------------------


def test_build_idempotency_key_is_deterministic():
    key1 = _build_idempotency_key(date(2026, 3, 14), "hello")
    key2 = _build_idempotency_key(date(2026, 3, 14), "hello")
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex


def test_build_idempotency_key_differs_for_different_input():
    key1 = _build_idempotency_key(date(2026, 3, 14), "hello")
    key2 = _build_idempotency_key(date(2026, 3, 15), "hello")
    assert key1 != key2


# ---------------------------------------------------------------------------
# _find_existing_event_id
# ---------------------------------------------------------------------------


def test_find_existing_event_id_returns_none_when_no_events():
    service = MagicMock()
    service.events().list().execute.return_value = {"items": []}

    result = _find_existing_event_id(
        service,
        calendar_id="cal@example.com",
        target_date=date(2026, 3, 14),
        idempotency_key="abc",
        timezone=None,
    )
    assert result is None


def test_find_existing_event_id_returns_id_when_found():
    service = MagicMock()
    service.events().list().execute.return_value = {"items": [{"id": "event-xyz"}]}

    result = _find_existing_event_id(
        service,
        calendar_id="cal@example.com",
        target_date=date(2026, 3, 14),
        idempotency_key="abc",
        timezone="Asia/Tokyo",
    )
    assert result == "event-xyz"


def test_find_existing_event_id_raises_on_api_error():
    service = MagicMock()
    service.events().list().execute.side_effect = RuntimeError("API down")

    with pytest.raises(CalendarExporterError, match="既存イベントの検索に失敗しました"):
        _find_existing_event_id(
            service,
            calendar_id="cal@example.com",
            target_date=date(2026, 3, 14),
            idempotency_key="abc",
            timezone=None,
        )


# ---------------------------------------------------------------------------
# upsert_daily_event — 新規挿入
# ---------------------------------------------------------------------------


def _make_service_mock(existing_event_id: str | None = None, insert_id: str = "new-event-id"):
    service = MagicMock()
    service.events().list().execute.return_value = (
        {"items": [{"id": existing_event_id}]} if existing_event_id else {"items": []}
    )
    service.events().insert().execute.return_value = {"id": insert_id}
    service.events().update().execute.return_value = {"id": existing_event_id or ""}
    return service


@patch("src.exporters.calendar_exporter.build_calendar_service")
@patch("src.exporters.calendar_exporter.load_calendar_config")
def test_upsert_daily_event_inserts_when_no_existing(
    mock_config, mock_service, monkeypatch: pytest.MonkeyPatch
):
    mock_config.return_value = MagicMock(
        calendar_id="cal@example.com", timezone=None, service_account_json="/sa.json"
    )
    service = _make_service_mock(existing_event_id=None, insert_id="new-id")
    mock_service.return_value = service

    result = upsert_daily_event(
        target_date=date(2026, 3, 14),
        message="テストメッセージ",
    )

    assert isinstance(result, EventUpsertResult)
    assert result.replaced_existing is False
    assert result.event_id == "new-id"


@patch("src.exporters.calendar_exporter.build_calendar_service")
@patch("src.exporters.calendar_exporter.load_calendar_config")
def test_upsert_daily_event_updates_when_existing(mock_config, mock_service):
    mock_config.return_value = MagicMock(
        calendar_id="cal@example.com", timezone=None, service_account_json="/sa.json"
    )
    service = _make_service_mock(existing_event_id="old-event-id")
    mock_service.return_value = service

    result = upsert_daily_event(
        target_date=date(2026, 3, 14),
        message="テストメッセージ",
    )

    assert result.replaced_existing is True


@patch("src.exporters.calendar_exporter.build_calendar_service")
@patch("src.exporters.calendar_exporter.load_calendar_config")
def test_upsert_daily_event_raises_on_insert_failure(mock_config, mock_service):
    mock_config.return_value = MagicMock(
        calendar_id="cal@example.com", timezone=None, service_account_json="/sa.json"
    )
    service = MagicMock()
    service.events().list().execute.return_value = {"items": []}
    service.events().insert().execute.side_effect = RuntimeError("insert failed")
    mock_service.return_value = service

    with pytest.raises(CalendarExporterError, match="新規イベントの作成に失敗しました"):
        upsert_daily_event(target_date=date(2026, 3, 14), message="msg")


@patch("src.exporters.calendar_exporter.build_calendar_service")
@patch("src.exporters.calendar_exporter.load_calendar_config")
def test_upsert_daily_event_raises_on_update_failure(mock_config, mock_service):
    mock_config.return_value = MagicMock(
        calendar_id="cal@example.com", timezone=None, service_account_json="/sa.json"
    )
    service = MagicMock()
    service.events().list().execute.return_value = {"items": [{"id": "existing"}]}
    service.events().update().execute.side_effect = RuntimeError("update failed")
    mock_service.return_value = service

    with pytest.raises(CalendarExporterError, match="既存イベントの更新に失敗しました"):
        upsert_daily_event(target_date=date(2026, 3, 14), message="msg")


# ---------------------------------------------------------------------------
# publish_daily_message — backward-compat wrapper
# ---------------------------------------------------------------------------


@patch("src.exporters.calendar_exporter.upsert_daily_event")
def test_publish_daily_message_returns_publish_result(mock_upsert):
    mock_upsert.return_value = EventUpsertResult(
        event_id="evt-123", calendar_id="cal@example.com", replaced_existing=False
    )

    result = publish_daily_message(
        calendar_id="cal@example.com",
        target_date=date(2026, 3, 14),
        message="Hello",
    )

    assert isinstance(result, CalendarPublishResult)
    assert result.event_id == "evt-123"
    assert result.html_link is None
    mock_upsert.assert_called_once_with(
        target_date=date(2026, 3, 14),
        message="Hello",
        calendar_id="cal@example.com",
    )
