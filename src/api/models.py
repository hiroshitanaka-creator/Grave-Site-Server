from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SaveMessageRequest(BaseModel):
    recipient: str = Field(min_length=1, description="Message recipient name")
    message: str = Field(min_length=1, max_length=1000, description="Message body")
    date: datetime.date = Field(description="Delivery or record date (YYYY-MM-DD)")
    tags: list[str] = Field(default_factory=list, description="Optional labels")
    source: str = Field(default="gpts-actions", description="Message source channel")
    request_id: str | None = Field(default=None, description="Optional idempotency key")


class SaveMessageResponse(BaseModel):
    saved: bool
    storage_type: Literal["document", "spreadsheet"]
    record_id: str


class ErrorResponse(BaseModel):
    error: str
    message: str | None = None
