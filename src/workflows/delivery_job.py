"""One bounded delivery pass, suitable for Cloud Run Jobs or a local scheduler."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.api.models import SaveMessageRequest
from src.messages.service import MessageService, configured_service, is_due
from src.messages.store import configured_store


def run_pending(
    service: MessageService, *, dry_run: bool = False, limit: int = 100, now: datetime | None = None
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    counts = {"selected": 0, "completed": 0, "failed": 0, "busy": 0}
    # Oldest checkpoint first: repeatedly failing low IDs must not starve other records.
    for record in sorted(
        service.store.records(), key=lambda item: (item["updated_at"], item["id"])
    ):
        drive_done = record["drive_status"] == "saved" or not service.drive_enabled
        calendar_done = record["delivery_status"] == "published" or not service.calendar_enabled
        if drive_done and (calendar_done or not is_due(record, now)):
            continue
        if counts["selected"] >= limit:
            break
        counts["selected"] += 1
        if dry_run:
            continue
        try:
            result = service.process(record["id"], now=now)
            if result["lease_token"]:
                counts["busy"] += 1
            elif result["drive_status"] in {"failed", "unknown"} or result["delivery_status"] in {
                "failed",
                "unknown",
            }:
                counts["failed"] += 1
            else:
                counts["completed"] += 1
        except Exception:
            logging.getLogger(__name__).error("delivery interrupted record=%s", record["id"])
            counts["failed"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Inspect only; no delivery or record updates"
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--enqueue", type=Path, help="Save one message JSON without external publication"
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        store = configured_store()
        if args.enqueue:
            import os

            body = SaveMessageRequest.model_validate_json(args.enqueue.read_text(encoding="utf-8"))
            payload = body.model_dump(mode="json", exclude={"request_id"})
            payload["calendar_id"] = payload["calendar_id"] or os.getenv("GOOGLE_CALENDAR_ID")
            if args.dry_run:
                print(json.dumps({"valid": True, "enqueued": False}))
                return 0
            record = store.create(payload, body.request_id)
            print(json.dumps({"record_id": record["id"], "enqueued": True}))
            return 0
        result = run_pending(configured_service(store), dry_run=args.dry_run, limit=args.limit)
        print(json.dumps(result))
        return 1 if result["failed"] or result["busy"] else 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": type(exc).__name__,
                    "message": "Check configuration and input; no success was recorded",
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
