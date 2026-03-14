from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.gemini_diary_batch import analyze_entry, build_rows, write_csv


class StubClient:
    def __init__(self, responses: list[dict[str, str]]):
        self._responses = responses
        self._idx = 0

    def complete_json(self, prompt: str) -> dict[str, str]:
        response = self._responses[self._idx]
        self._idx += 1
        return response


def test_analyze_entry_extracts_required_fields():
    client = StubClient(
        [{"mood_tag": "positive", "topic_tag": "health", "summary": "散歩で気分転換した"}]
    )

    result = analyze_entry("散歩して落ち着いた", client=client)

    assert result.mood_tag == "positive"
    assert result.topic_tag == "health"
    assert result.summary == "散歩で気分転換した"


def test_analyze_entry_raises_on_missing_fields():
    client = StubClient([{"mood_tag": "neutral"}])

    with pytest.raises(ValueError, match="Missing expected keys"):
        analyze_entry("普通の一日", client=client)


def test_build_rows_and_write_csv(tmp_path: Path):
    entries = ["仕事で達成感があった", "夜は読書して落ち着いた"]
    client = StubClient(
        [
            {"mood_tag": "positive", "topic_tag": "work", "summary": "仕事で成果が出た"},
            {"mood_tag": "neutral", "topic_tag": "learning", "summary": "読書で一日を締めた"},
        ]
    )

    rows = build_rows(entries, client=client, date_str="2026-02-08")

    assert len(rows) == 2
    assert rows[0]["date"] == "2026-02-08"
    assert rows[1]["entry"] == entries[1]

    output_path = tmp_path / "output.csv"
    write_csv(output_path, rows)

    with output_path.open("r", encoding="utf-8", newline="") as f:
        result_rows = list(csv.DictReader(f))

    assert len(result_rows) == 2
    assert result_rows[0]["mood_tag"] == "positive"
    assert result_rows[1]["topic_tag"] == "learning"
