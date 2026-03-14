from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

SERVICE_ACCOUNT_JSON_ENV = "GOOGLE_SERVICE_ACCOUNT_JSON"
DRIVE_FOLDER_ID_ENV = "GOOGLE_DRIVE_FOLDER_ID"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveExporterError(RuntimeError):
    """Google Drive export related errors."""


@dataclass(frozen=True)
class DriveConfig:
    service_account_json: Path
    drive_folder_id: str


@dataclass(frozen=True)
class UploadResult:
    file_id: str
    file_name: str
    replaced_existing: bool


def build_daily_filename(target_date: date, extension: str) -> str:
    clean_ext = extension.lower().lstrip(".")
    if clean_ext not in {"csv", "json"}:
        raise ValueError("extension は csv または json を指定してください")
    return f"diary_{target_date.isoformat()}.{clean_ext}"


def load_drive_config() -> DriveConfig:
    service_account_json = os.getenv(SERVICE_ACCOUNT_JSON_ENV)
    drive_folder_id = os.getenv(DRIVE_FOLDER_ID_ENV)

    if not service_account_json:
        raise DriveExporterError(
            f"環境変数 {SERVICE_ACCOUNT_JSON_ENV} が未設定です。サービスアカウントJSONへのパスを設定してください。"
        )

    json_path = Path(service_account_json)
    if not json_path.exists():
        raise DriveExporterError(
            f"環境変数 {SERVICE_ACCOUNT_JSON_ENV} のファイルが見つかりません: {json_path}"
        )

    if not drive_folder_id:
        raise DriveExporterError(
            f"環境変数 {DRIVE_FOLDER_ID_ENV} が未設定です。アップロード先フォルダIDを設定してください。"
        )

    return DriveConfig(service_account_json=json_path, drive_folder_id=drive_folder_id)


def _build_drive_service(config: DriveConfig) -> Any:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ModuleNotFoundError as exc:
        raise DriveExporterError(
            "Google Drive 連携には google-api-python-client と google-auth のインストールが必要です。"
        ) from exc

    credentials = Credentials.from_service_account_file(str(config.service_account_json), scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=credentials)


def _find_existing_file_id(service: Any, folder_id: str, file_name: str) -> str | None:
    query = (
        f"name = '{file_name}' and '{folder_id}' in parents "
        "and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
    )
    response = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)", pageSize=1)
        .execute()
    )
    files = response.get("files", [])
    if not files:
        return None
    return files[0]["id"]


def upload_daily_file(local_path: Path, target_date: date, extension: str) -> UploadResult:
    """Upload CSV/JSON to Google Drive with a fixed name pattern.

    Policy: if same file name exists in target folder, update content in-place (overwrite).
    """

    if not local_path.exists():
        raise DriveExporterError(f"アップロード対象ファイルが見つかりません: {local_path}")

    config = load_drive_config()
    drive_service = _build_drive_service(config)

    file_name = build_daily_filename(target_date, extension)
    mime_type, _ = mimetypes.guess_type(file_name)
    media_mime = mime_type or "application/octet-stream"

    try:
        from googleapiclient.http import MediaFileUpload
    except ModuleNotFoundError as exc:
        raise DriveExporterError(
            "Google Drive 連携には google-api-python-client のインストールが必要です。"
        ) from exc

    media = MediaFileUpload(str(local_path), mimetype=media_mime, resumable=False)
    existing_file_id = _find_existing_file_id(drive_service, config.drive_folder_id, file_name)

    if existing_file_id:
        response = (
            drive_service.files()
            .update(fileId=existing_file_id, media_body=media, fields="id, name")
            .execute()
        )
        return UploadResult(
            file_id=response["id"],
            file_name=response["name"],
            replaced_existing=True,
        )

    metadata = {"name": file_name, "parents": [config.drive_folder_id]}
    response = (
        drive_service.files()
        .create(body=metadata, media_body=media, fields="id, name")
        .execute()
    )
    return UploadResult(
        file_id=response["id"],
        file_name=response["name"],
        replaced_existing=False,
    )
