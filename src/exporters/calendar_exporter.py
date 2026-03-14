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
