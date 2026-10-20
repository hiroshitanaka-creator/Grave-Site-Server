"""Save first, then project to Drive and Calendar with durable checkpoints."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from src.exporters.message_exporters import (
    CalendarMessageExporter,
    DriveMessageExporter,
    ExportFailure,
)
from src.messages.store import MessageStore, Record, RecordConflict

logger = logging.getLogger(__name__)


def enabled(variable: str) -> bool:
    value = os.getenv(variable, "true").lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{variable} must be true or false")
    return value == "true"


def is_due(record: Record, now: datetime | None = None) -> bool:
    scheduled = record["payload"].get("publish_at")
    return scheduled is None or datetime.fromisoformat(scheduled) <= (
        now or datetime.now(timezone.utc)
    )


class MessageService:
    def __init__(
        self,
        store: MessageStore,
        drive: Any = None,
        calendar: Any = None,
        *,
        drive_enabled: bool = True,
        calendar_enabled: bool = True,
    ):
        self.store = store
        self.drive = drive if drive is not None else DriveMessageExporter()
        self.calendar = calendar if calendar is not None else CalendarMessageExporter()
        self.drive_enabled = drive_enabled
        self.calendar_enabled = calendar_enabled

    def process(self, record_id: str, *, now: datetime | None = None) -> Record:
        try:
            record, token = self.store.claim(record_id)
        except RecordConflict:
            return self.store.get(record_id)
        try:
            for stage, on, complete in [
                ("drive", self.drive_enabled, "saved"),
                ("delivery", self.calendar_enabled, "published"),
            ]:
                status_key = f"{stage}_status"
                error_key = f"{stage}_error"
                if record[status_key] == complete:
                    continue
                if not on:
                    if record[status_key] == "pending":
                        record = self.store.checkpoint(record_id, token, **{status_key: "disabled"})
                    continue
                if stage == "delivery" and not is_due(record, now):
                    record = self.store.checkpoint(record_id, token, delivery_status="pending")
                    continue
                was_unknown = record[status_key] == "unknown"
                try:
                    if stage == "drive" and not record["drive_file_id"]:
                        reserved = self.drive.reserve_id()
                        record = self.store.checkpoint(record_id, token, drive_file_id=reserved)
                    # If killed after this checkpoint, restart must reconcile the same provider ID.
                    record = self.store.checkpoint(
                        record_id, token, **{status_key: "unknown", error_key: None}
                    )
                    provider_id = (
                        self.drive.save(record)
                        if stage == "drive"
                        else self.calendar.publish(record)
                    )
                except ExportFailure as exc:
                    # A previously uncertain write must remain uncertain until provider reconciliation.
                    status = "unknown" if exc.unknown or was_unknown else "failed"
                    record = self.store.checkpoint(
                        record_id, token, **{status_key: status, error_key: str(exc)}
                    )
                else:
                    id_key = "drive_file_id" if stage == "drive" else "calendar_event_id"
                    record = self.store.checkpoint(
                        record_id,
                        token,
                        **{
                            status_key: complete,
                            id_key: provider_id,
                            error_key: None,
                        },
                    )
                logger.info(
                    "delivery record=%s revision=%s stage=%s status=%s",
                    record_id,
                    record["revision"],
                    stage,
                    record[status_key],
                )
        finally:
            # Storage errors intentionally propagate; never report a fictitious success.
            # The previous unknown checkpoint and fixed provider ID allow recovery.
            self.store.release(record_id, token)
        return self.store.get(record_id)


def configured_service(store: MessageStore) -> MessageService:
    return MessageService(
        store, drive_enabled=enabled("DRIVE_ENABLED"), calendar_enabled=enabled("CALENDAR_ENABLED")
    )
