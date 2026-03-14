from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Any


@dataclass(slots=True)
class DiaryEmbeddingRecord:
    """Embedded representation tied to existing diary output IDs."""

    id: str
    summary: str
    source: str
    vector: list[float]


def resolve_record_id(raw_row: dict[str, Any], index: int) -> str:
    """Prefer explicit IDs from existing exports, fallback to deterministic hash."""

    for key in ("id", "record_id", "entry_id"):
        value = raw_row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    base = "|".join(
        [
            str(raw_row.get("date") or date.today().isoformat()),
            str(raw_row.get("entry") or ""),
            str(raw_row.get("summary") or ""),
            str(index),
        ]
    )
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"auto-{digest}"
