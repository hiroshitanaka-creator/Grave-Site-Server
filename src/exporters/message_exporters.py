"""Idempotent external projections of durable messages, separate from diary exports."""

from __future__ import annotations

import io
import os
from datetime import date, timedelta
from typing import Any

from src.exporters.google_credentials import build_google_service, http_status
from src.messages.store import Record, canonical, fingerprint


class ExportFailure(RuntimeError):
    def __init__(self, code: str, *, unknown: bool = False):
        super().__init__(code)
        self.unknown = unknown


def _failure(provider: str, exc: Exception, *, writing: bool = False) -> ExportFailure:
    status = http_status(exc)
    # No raw provider errors: URLs, credentials and message content can appear in them.
    return ExportFailure(
        f"{provider}_{status or type(exc).__name__}",
        unknown=writing and (status is None or status >= 500 or status == 408),
    )


def export_document(record: Record) -> Record:
    return {
        "schema_version": 2,
        "record_id": record["id"],
        "revision": record["revision"],
        "request_id": record["request_id"],
        "created_at": record["created_at"],
        **record["payload"],
    }


class DriveMessageExporter:
    def __init__(self, service: Any = None, folder_id: str | None = None):
        self._service = service
        self.folder_id = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

    @property
    def service(self):
        if not self.folder_id:
            raise ExportFailure("GOOGLE_DRIVE_FOLDER_ID_missing")
        if self._service is None:
            try:
                self._service = build_google_service(
                    "drive",
                    "v3",
                    ["https://www.googleapis.com/auth/drive.file"],
                )
            except Exception as exc:
                raise _failure("drive_config", exc) from exc
        return self._service

    def reserve_id(self) -> str:
        try:
            return (
                self.service.files()
                .generateIds(count=1, space="drive", type="files")
                .execute()["ids"][0]
            )
        except ExportFailure:
            raise
        except Exception as exc:
            raise _failure("drive_reserve", exc) from exc

    def save(self, record: Record) -> str:
        file_id = record["drive_file_id"]
        document = export_document(record)
        properties = {
            "grave_record": record["id"],
            "revision": str(record["revision"]),
            "payload_hash": fingerprint(document),
        }
        files = self.service.files()
        try:
            existing = files.get(
                fileId=file_id, fields="id,appProperties,trashed,parents", supportsAllDrives=True
            ).execute()
        except Exception as exc:
            if http_status(exc) != 404:
                raise _failure("drive_lookup", exc) from exc
        else:
            if (
                existing.get("appProperties") != properties
                or existing.get("trashed")
                or self.folder_id not in existing.get("parents", [])
            ):
                raise ExportFailure("drive_existing_file_conflict")
            return file_id

        try:
            from googleapiclient.http import MediaIoBaseUpload

            media = MediaIoBaseUpload(
                io.BytesIO(canonical(document).encode()),
                mimetype="application/json",
                resumable=False,
            )
        except ImportError as exc:
            raise ExportFailure("google_dependencies_missing") from exc
        try:
            files.create(
                body={
                    "id": file_id,
                    "name": f"message_{record['id']}_v{record['revision']}.json",
                    "parents": [self.folder_id],
                    "appProperties": properties,
                },
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()
        except Exception as exc:
            if http_status(exc) == 409:
                # Do not retry create with a different ID. Verify the already-created object.
                try:
                    existing = files.get(
                        fileId=file_id,
                        fields="id,appProperties,trashed,parents",
                        supportsAllDrives=True,
                    ).execute()
                except Exception as lookup_exc:
                    raise ExportFailure(
                        "drive_create_conflict_unresolved", unknown=True
                    ) from lookup_exc
                if (
                    existing.get("appProperties") == properties
                    and not existing.get("trashed")
                    and self.folder_id in existing.get("parents", [])
                ):
                    return file_id
                raise ExportFailure("drive_existing_file_conflict") from exc
            raise _failure("drive_create", exc, writing=True) from exc
        return file_id


class CalendarMessageExporter:
    def __init__(self, service: Any = None):
        self._service = service

    @property
    def service(self):
        if self._service is None:
            try:
                self._service = build_google_service(
                    "calendar",
                    "v3",
                    ["https://www.googleapis.com/auth/calendar.events"],
                )
            except Exception as exc:
                raise _failure("calendar_config", exc) from exc
        return self._service

    def publish(self, record: Record) -> str:
        payload = record["payload"]
        calendar_id = payload["calendar_id"]
        if not calendar_id:
            raise ExportFailure("GOOGLE_CALENDAR_ID_missing")
        event_id = "grave" + fingerprint(record["id"])
        properties = {
            "grave_record": record["id"],
            "revision": str(record["revision"]),
            "payload_hash": fingerprint(payload),
        }
        target_date = date.fromisoformat(payload["date"])
        body = {
            "summary": f"Message for {payload['recipient']}",
            "description": payload["message"],
            "start": {"date": target_date.isoformat()},
            "end": {"date": (target_date + timedelta(days=1)).isoformat()},
            "extendedProperties": {"private": properties},
        }
        events = self.service.events()
        for _ in range(3):
            try:
                existing = events.get(calendarId=calendar_id, eventId=event_id).execute()
            except Exception as exc:
                if http_status(exc) != 404:
                    raise _failure("calendar_lookup", exc) from exc
                existing = None
            if existing is not None:
                old = existing.get("extendedProperties", {}).get("private", {})
                if old.get("grave_record") != record["id"] or existing.get("status") == "cancelled":
                    raise ExportFailure("calendar_existing_event_conflict")
                try:
                    old_revision = int(old.get("revision", "0"))
                except ValueError as exc:
                    raise ExportFailure("calendar_invalid_revision") from exc
                if old_revision > record["revision"]:
                    raise ExportFailure("calendar_stale_worker")
                if old == properties:
                    if all(existing.get(key) == value for key, value in body.items()):
                        return event_id
                    # A human edit is not silently overwritten by an identical retry.
                    raise ExportFailure("calendar_external_edit_conflict")
                if old_revision == record["revision"]:
                    raise ExportFailure("calendar_revision_conflict")
                if not existing.get("etag"):
                    raise ExportFailure("calendar_missing_etag")
                operation = events.update(calendarId=calendar_id, eventId=event_id, body=body)
                operation.headers["If-Match"] = existing["etag"]
            else:
                operation = events.insert(calendarId=calendar_id, body={"id": event_id, **body})
            try:
                operation.execute()
                return event_id
            except Exception as exc:
                if http_status(exc) in {409, 412}:
                    continue  # Re-read ID/version/ETag instead of blind overwrite.
                raise _failure("calendar_write", exc, writing=True) from exc
        raise ExportFailure("calendar_concurrent_update", unknown=True)
