from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Security
from fastapi.security import APIKeyHeader

from src.api.models import (
    ErrorResponse,
    MessageResponse,
    SaveMessageRequest,
    SaveMessageResponse,
    UpdateMessageRequest,
)
from src.messages.service import MessageService, configured_service
from src.messages.store import RecordConflict, RecordNotFound, configured_store

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="ApiKeyAuth")


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    expected = os.getenv("API_KEY", "").strip()
    if not expected:
        raise HTTPException(
            500, detail={"error": "server_misconfigured", "message": "API_KEY is not configured"}
        )
    if api_key is None or not hmac.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(
            401, detail={"error": "unauthorized", "message": "Invalid or missing API key"}
        )


router = APIRouter(
    dependencies=[Depends(verify_api_key)],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
RecordId = Annotated[str, Path(pattern=r"^msg-[0-9a-f]{32}(?:[0-9a-f]{32})?$")]


def message_service() -> MessageService:
    try:
        return configured_service(configured_store())
    except Exception as exc:
        raise HTTPException(
            500,
            detail={
                "error": "server_misconfigured",
                "message": "Check message store configuration",
            },
        ) from exc


def response(record: dict) -> SaveMessageResponse:
    return SaveMessageResponse(
        saved=True,
        storage_type="record",
        record_id=record["id"],
        revision=record["revision"],
        storage_status="saved",
        processing=bool(record["lease_token"]),
        **{
            key: record[key]
            for key in (
                "drive_status",
                "delivery_status",
                "drive_file_id",
                "calendar_event_id",
                "drive_error",
                "delivery_error",
            )
        },
    )


@router.post(
    "/actions/save-message", response_model=SaveMessageResponse, operation_id="saveMessage"
)
def save_message(
    body: SaveMessageRequest, service: MessageService = Depends(message_service)
) -> SaveMessageResponse:
    payload = body.model_dump(mode="json", exclude={"request_id"})
    payload["calendar_id"] = payload["calendar_id"] or os.getenv("GOOGLE_CALENDAR_ID")
    record = service.store.create(payload, body.request_id)
    return response(service.process(record["id"]))


@router.get("/messages/{record_id}", response_model=MessageResponse, operation_id="getMessage")
def get_message(
    record_id: RecordId, service: MessageService = Depends(message_service)
) -> MessageResponse:
    record = service.store.get(record_id)
    return MessageResponse(
        **response(record).model_dump(), content=record["payload"], request_id=record["request_id"]
    )


@router.put(
    "/messages/{record_id}", response_model=SaveMessageResponse, operation_id="updateMessage"
)
def update_message(
    record_id: RecordId,
    body: UpdateMessageRequest,
    service: MessageService = Depends(message_service),
) -> SaveMessageResponse:
    current = service.store.get(record_id)
    payload = body.model_dump(mode="json", exclude={"expected_revision"})
    payload["calendar_id"] = payload["calendar_id"] or current["payload"]["calendar_id"]
    service.store.revise(record_id, payload, body.expected_revision)
    return response(service.process(record_id))


@router.post(
    "/messages/{record_id}/retry", response_model=SaveMessageResponse, operation_id="retryMessage"
)
def retry_message(
    record_id: RecordId, service: MessageService = Depends(message_service)
) -> SaveMessageResponse:
    return response(service.process(record_id))


def record_error(exc: RecordConflict | RecordNotFound) -> tuple[int, dict[str, str]]:
    if isinstance(exc, RecordNotFound):
        return 404, {"error": "not_found", "message": "Message does not exist"}
    return 409, {"error": "conflict", "message": str(exc)}
