from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any


class CalendarExporterError(RuntimeError):
    """Google Calendar publish related errors."""


@dataclass(frozen=True)
class CalendarPublishResult:
    event_id: str
    html_link: str | None


def _build_calendar_service() -> Any:
    try:
        from googleapiclient.discovery import build
        from google.auth import default
    except ModuleNotFoundError as exc:
        raise CalendarExporterError(
            "Google Calendar 連携には google-api-python-client と google-auth のインストールが必要です。"
        ) from exc

    credentials, _ = default(scopes=["https://www.googleapis.com/auth/calendar.events"])
    return build("calendar", "v3", credentials=credentials)


def publish_daily_message(calendar_id: str, target_date: date, message: str) -> CalendarPublishResult:
    if not calendar_id.strip():
        raise CalendarExporterError("calendar_id は必須です。")

    if not message.strip():
        raise CalendarExporterError("message は空にできません。")

    service = _build_calendar_service()

    start_utc = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end_utc = start_utc + timedelta(days=1)

    event = {
        "summary": "Daily Diary Message",
        "description": message,
        "start": {"dateTime": start_utc.isoformat()},
        "end": {"dateTime": end_utc.isoformat()},
    }

    response = service.events().insert(calendarId=calendar_id, body=event).execute()
    return CalendarPublishResult(event_id=response["id"], html_link=response.get("htmlLink"))
import hashlib
import importlib.util
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SERVICE_ACCOUNT_JSON_ENV = "GOOGLE_SERVICE_ACCOUNT_JSON"
CALENDAR_ID_ENV = "GOOGLE_CALENDAR_ID"
CALENDAR_TIMEZONE_ENV = "CALENDAR_TIMEZONE"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarExporterError(RuntimeError):
    """Google Calendar export related errors."""


@dataclass(frozen=True)
class CalendarConfig:
    service_account_json: Path
    calendar_id: str
    timezone: str | None


@dataclass(frozen=True)
class EventUpsertResult:
    event_id: str
    calendar_id: str
    replaced_existing: bool


def load_calendar_config() -> CalendarConfig:
    service_account_json = os.getenv(SERVICE_ACCOUNT_JSON_ENV)
    calendar_id = os.getenv(CALENDAR_ID_ENV)
    timezone = os.getenv(CALENDAR_TIMEZONE_ENV)

    if not service_account_json:
        raise CalendarExporterError(
            f"環境変数 {SERVICE_ACCOUNT_JSON_ENV} が未設定です。サービスアカウントJSONへのパスを設定してください。"
        )

    json_path = Path(service_account_json)
    if not json_path.exists():
        raise CalendarExporterError(
            f"環境変数 {SERVICE_ACCOUNT_JSON_ENV} のファイルが見つかりません: {json_path}"
        )

    if not calendar_id:
        raise CalendarExporterError(
            f"環境変数 {CALENDAR_ID_ENV} が未設定です。保存先カレンダーIDを設定してください。"
        )

    return CalendarConfig(service_account_json=json_path, calendar_id=calendar_id, timezone=timezone)


def build_calendar_service(config: CalendarConfig) -> Any:
    if (
        importlib.util.find_spec("google.oauth2.service_account") is None
        or importlib.util.find_spec("googleapiclient.discovery") is None
    ):
        raise CalendarExporterError(
            "Google Calendar 連携には google-api-python-client と google-auth のインストールが必要です。"
        )

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_service_account_file(
        str(config.service_account_json),
        scopes=CALENDAR_SCOPES,
    )
    try:
        return build("calendar", "v3", credentials=credentials)
    except Exception as exc:
        raise CalendarExporterError(f"Calendar API クライアントの初期化に失敗しました: {exc}") from exc


def build_daily_event_payload(
    *,
    target_date: date,
    message: str,
    idempotency_key: str,
    summary: str = "Daily diary",
) -> dict[str, Any]:
    return {
        "summary": summary,
        "description": message,
        "start": {"date": target_date.isoformat()},
        "end": {"date": (target_date + timedelta(days=1)).isoformat()},
        "extendedProperties": {
            "private": {
                "idempotency_key": idempotency_key,
            }
        },
    }


def _build_idempotency_key(target_date: date, message: str) -> str:
    raw = f"{target_date.isoformat()}::{message}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _find_existing_event_id(
    service: Any,
    *,
    calendar_id: str,
    target_date: date,
    idempotency_key: str,
    timezone: str | None,
) -> str | None:
    list_params: dict[str, Any] = {
        "calendarId": calendar_id,
        "timeMin": f"{target_date.isoformat()}T00:00:00Z",
        "timeMax": f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00Z",
        "singleEvents": True,
        "privateExtendedProperty": f"idempotency_key={idempotency_key}",
        "maxResults": 1,
        "orderBy": "startTime",
    }
    if timezone:
        list_params["timeZone"] = timezone

    try:
        response = service.events().list(**list_params).execute()
    except Exception as exc:
        raise CalendarExporterError(f"既存イベントの検索に失敗しました: {exc}") from exc
    events = response.get("items", [])
    if not events:
        return None
    return events[0]["id"]


def upsert_daily_event(
    *,
    target_date: date,
    message: str,
    summary: str = "Daily diary",
) -> EventUpsertResult:
    config = load_calendar_config()
    service = build_calendar_service(config)

    idempotency_key = _build_idempotency_key(target_date, message)
    payload = build_daily_event_payload(
        target_date=target_date,
        message=message,
        idempotency_key=idempotency_key,
        summary=summary,
    )

    event_id = _find_existing_event_id(
        service,
        calendar_id=config.calendar_id,
        target_date=target_date,
        idempotency_key=idempotency_key,
        timezone=config.timezone,
    )

    if event_id:
        try:
            response = (
                service.events()
                .update(
                    calendarId=config.calendar_id,
                    eventId=event_id,
                    body=payload,
                )
                .execute()
            )
        except Exception as exc:
            raise CalendarExporterError(f"既存イベントの更新に失敗しました: {exc}") from exc
        return EventUpsertResult(
            event_id=response["id"],
            calendar_id=config.calendar_id,
            replaced_existing=True,
        )

    try:
        response = (
            service.events()
            .insert(
                calendarId=config.calendar_id,
                body=payload,
            )
            .execute()
        )
    except Exception as exc:
        raise CalendarExporterError(f"新規イベントの作成に失敗しました: {exc}") from exc
    return EventUpsertResult(
        event_id=response["id"],
        calendar_id=config.calendar_id,
        replaced_existing=False,
    )
