from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io
import json
from typing import Iterable, Mapping, Sequence


OUTPUT_COLUMNS = ["date", "entry", "mood_tag", "topic_tag", "summary"]


@dataclass(frozen=True)
class ParseResult:
    entries: list[str]
    errors: list[str]


def parse_entries(raw_items: Sequence[object]) -> ParseResult:
    """Normalize and validate diary entries.

    - Non-string inputs are treated as invalid input.
    - Empty/whitespace-only strings are ignored as empty lines.
    """
    entries: list[str] = []
    errors: list[str] = []

    for idx, item in enumerate(raw_items):
        if not isinstance(item, str):
            errors.append(f"line {idx + 1}: invalid type={type(item).__name__}")
            continue

        normalized = item.strip()
        if not normalized:
            errors.append(f"line {idx + 1}: empty line")
            continue

        if any(ord(char) < 32 and char != "\t" for char in normalized):
            errors.append(f"line {idx + 1}: invalid characters")
            continue

        entries.append(normalized)

    return ParseResult(entries=entries, errors=errors)


def parse_text_block(text: str) -> ParseResult:
    return parse_entries(text.splitlines())


def generate_mood_tag(entry: str) -> str:
    if any(word in entry for word in ["嬉しい", "楽しい", "最高", "よかった"]):
        return "positive"
    if any(word in entry for word in ["怒", "悲しい", "不安", "つらい"]):
        return "negative"
    if "成長" in entry or "頑張" in entry:
        return "motivated"
    return "neutral"


def generate_topic_tag(entry: str) -> str:
    topics: list[str] = []
    if any(word in entry for word in ["会社", "上司", "仕事", "会議"]):
        topics.append("work")
    if any(word in entry for word in ["家族", "友達", "恋人"]):
        topics.append("relationship")
    if any(word in entry for word in ["勉強", "学習", "読書"]):
        topics.append("learning")
    if any(word in entry for word in ["健康", "運動", "睡眠"]):
        topics.append("health")

    return ", ".join(topics) if topics else "daily-life"


def generate_summary(entry: str) -> str:
    text = entry.replace("\n", " ").strip()
    return text[:30]


def analyze_entry(entry: str, today: str) -> dict[str, str]:
    return {
        "date": today,
        "entry": entry,
        "mood_tag": generate_mood_tag(entry),
        "topic_tag": generate_topic_tag(entry),
        "summary": generate_summary(entry),
    }


def process_entries(entries: Iterable[str], today: str | None = None) -> list[dict[str, str]]:
    resolved_date = today or date.today().isoformat()
    return [analyze_entry(entry, resolved_date) for entry in entries]


def _normalize_date_value(value: object) -> str:
    if not isinstance(value, str):
        return ""

    normalized = value.strip()
    if not normalized:
        return ""

    try:
        date.fromisoformat(normalized)
    except ValueError:
        return ""

    return normalized


def normalize_output_record(record: Mapping[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for column in OUTPUT_COLUMNS:
        value = record.get(column, "")
        if column == "date":
            normalized[column] = _normalize_date_value(value)
        elif value is None:
            normalized[column] = ""
        else:
            normalized[column] = str(value).strip()

    return normalized


def normalize_output_records(records: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    return [normalize_output_record(record) for record in records]


def render_csv(records: Sequence[Mapping[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalize_output_records(records))
    return buffer.getvalue()


def render_json(records: Sequence[Mapping[str, object]]) -> str:
    return json.dumps(normalize_output_records(records), ensure_ascii=False, indent=2)
