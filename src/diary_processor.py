from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io
import json
from typing import Iterable, Sequence


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

        entries.append(normalized)

    return ParseResult(entries=entries, errors=errors)


def parse_text_block(text: str) -> ParseResult:
    return parse_entries(text.splitlines())


def analyze_entry(entry: str, today: str) -> dict[str, str]:
    mood_tag = _infer_mood(entry)
    topic_tag = _infer_topic(entry)
    summary = _summarize(entry)

    return {
        "date": today,
        "entry": entry,
        "mood_tag": mood_tag,
        "topic_tag": topic_tag,
        "summary": summary,
    }


def process_entries(entries: Iterable[str], today: str | None = None) -> list[dict[str, str]]:
    resolved_date = today or date.today().isoformat()
    return [analyze_entry(entry, resolved_date) for entry in entries]


def render_csv(records: Sequence[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_json(records: Sequence[dict[str, str]]) -> str:
    return json.dumps(records, ensure_ascii=False, indent=2)


def _infer_mood(entry: str) -> str:
    if any(word in entry for word in ["嬉しい", "楽しい", "最高", "よかった"]):
        return "positive"
    if any(word in entry for word in ["怒", "悲しい", "不安", "つらい"]):
        return "negative"
    if "成長" in entry or "頑張" in entry:
        return "motivated"
    return "neutral"


def _infer_topic(entry: str) -> str:
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


def _summarize(entry: str) -> str:
    text = entry.replace("\n", " ").strip()
    return text[:30]
