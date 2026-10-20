from __future__ import annotations

import datetime
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must contain non-whitespace characters")
    return value


Label = Annotated[str, Field(min_length=1, max_length=200), AfterValidator(nonblank)]


class MessageContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)
    date: datetime.date
    tags: list[Label] = Field(default_factory=list, max_length=100)
    source: str = Field(default="gpts-actions", min_length=1, max_length=100)
    calendar_id: str | None = Field(default=None, min_length=1, max_length=500)
    publish_at: datetime.datetime | None = Field(
        default=None, description="Earliest Calendar publication time; explicit timezone required."
    )
    memory_refs: list[Label] = Field(
        default_factory=list,
        max_length=100,
        description="Provenance references only; no automatic retrieval.",
    )

    @field_validator("recipient", "message", "source", "calendar_id")
    @classmethod
    def nonblank_text(cls, value):
        return nonblank(value) if value is not None else value

    @field_validator("date", mode="before")
    @classmethod
    def strict_date(cls, value):
        if isinstance(value, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date must be YYYY-MM-DD")
        if isinstance(value, (int, float, datetime.datetime)):
            raise ValueError("date must be YYYY-MM-DD")
        return value

    @field_validator("date")
    @classmethod
    def calendar_end_date(cls, value):
        if value == datetime.date.max:
            raise ValueError("date must allow a following day for an all-day Calendar event")
        return value

    @field_validator("publish_at")
    @classmethod
    def aware_schedule(cls, value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("publish_at must include a timezone offset")
            return value.astimezone(datetime.timezone.utc)
        return value


class SaveMessageRequest(MessageContent):
    request_id: Label | None = Field(
        default=None, description="Persist and reuse this key when retrying a request."
    )


class UpdateMessageRequest(MessageContent):
    expected_revision: int = Field(ge=1)


class SaveMessageResponse(BaseModel):
    saved: bool
    storage_type: Literal["record"]
    record_id: str
    revision: int
    storage_status: Literal["saved"]
    drive_status: Literal["pending", "saved", "failed", "unknown", "disabled"]
    delivery_status: Literal["pending", "published", "failed", "unknown", "disabled"]
    drive_file_id: str | None
    calendar_event_id: str | None
    drive_error: str | None
    delivery_error: str | None
    processing: bool


class MessageResponse(SaveMessageResponse):
    content: MessageContent
    request_id: str | None


class ErrorResponse(BaseModel):
    error: str
    message: str
