from __future__ import annotations

import json
import os
import tempfile
import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader

from src.api.models import SaveMessageRequest, SaveMessageResponse

API_KEY_ENV = "API_KEY"
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

router = APIRouter()


def _verify_api_key(api_key: str | None) -> None:
    expected = os.getenv(API_KEY_ENV, "").strip()
    if not expected:
        raise HTTPException(
            status_code=500,
            detail={"error": "server_misconfigured", "message": f"{API_KEY_ENV} is not configured"},
        )
    if api_key != expected:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid or missing API key"})


def _save_to_drive(target_date: datetime.date, message: str, record_id_hint: str | None) -> str:
    """メッセージをJSONファイルとしてDriveにアップロードし、file_id を返す。"""
    try:
        from src.exporters.drive_exporter import DriveExporterError, upload_daily_file
    except ImportError:
        raise HTTPException(status_code=500, detail={"error": "internal_error", "message": "drive_exporter unavailable"})

    payload = {
        "date": target_date.isoformat(),
        "message": message,
        **({"request_id": record_id_hint} if record_id_hint else {}),
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8", delete=False
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = Path(tmp.name)

    try:
        result = upload_daily_file(tmp_path, target_date, "json")
    except DriveExporterError as exc:
        raise HTTPException(status_code=500, detail={"error": "storage_error", "message": str(exc)})
    finally:
        tmp_path.unlink(missing_ok=True)

    return result.file_id


def _publish_to_calendar(target_date: datetime.date, message: str) -> str | None:
    """Calendarに終日イベントを配信する。環境変数未設定の場合はスキップしてNoneを返す。"""
    if not os.getenv("GOOGLE_CALENDAR_ID") and not os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return None

    try:
        from src.exporters.calendar_exporter import CalendarExporterError, upsert_daily_event
    except ImportError:
        return None

    try:
        result = upsert_daily_event(target_date=target_date, message=message)
        return result.event_id
    except CalendarExporterError:
        return None  # Calendar失敗はDrive保存成功を妨げない


@router.post(
    "/actions/save-message",
    response_model=SaveMessageResponse,
    responses={
        400: {"model": None},
        401: {"model": None},
        500: {"model": None},
    },
)
def save_message(
    body: SaveMessageRequest,
    api_key: str | None = Security(_api_key_header),
) -> SaveMessageResponse:
    """故人のメッセージをDriveに保存し、Calendarに終日イベントとして配信する。"""
    _verify_api_key(api_key)

    file_id = _save_to_drive(body.date, body.message, body.request_id)
    calendar_event_id = _publish_to_calendar(body.date, body.message)

    record_id = calendar_event_id or file_id

    return SaveMessageResponse(
        saved=True,
        storage_type="document",
        record_id=record_id,
    )
