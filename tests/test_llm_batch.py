from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.llm_batch import (
    GeminiClient,
    OpenAIResponsesClient,
    analyze_entry,
    build_rows,
    create_client,
    write_csv,
)


class StubClient:
    provider_name = "stub"

    def __init__(self, responses: list[dict[str, str]]):
        self._responses = responses
        self._idx = 0

    def complete_json(self, prompt: str) -> dict[str, str]:
        response = self._responses[self._idx]
        self._idx += 1
        return response


@pytest.fixture(autouse=True)
def clear_api_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_analyze_entry_extracts_required_fields():
    client = StubClient(
        [{"mood_tag": "positive", "topic_tag": "health", "summary": "散歩で気分転換した"}]
    )

    result = analyze_entry("散歩して落ち着いた", client=client)

    assert result.mood_tag == "positive"
    assert result.topic_tag == "health"
    assert result.summary == "散歩で気分転換した"


def test_analyze_entry_raises_on_missing_fields_with_provider_name():
    client = StubClient([{"mood_tag": "neutral"}])

    with pytest.raises(ValueError, match="Missing expected keys in stub response"):
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


def test_create_client_switches_openai_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")

    client = create_client(provider="openai", model="gpt-4o-mini")

    assert isinstance(client, OpenAIResponsesClient)
    assert client.model == "gpt-4o-mini"


def test_create_client_switches_gemini_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

    client = create_client(provider="gemini", model="gemini-1.5-flash")

    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-1.5-flash"


def test_create_client_requires_provider_specific_env_var():
    with pytest.raises(ValueError, match="OPENAI_API_KEY が未設定です"):
        create_client(provider="openai", model="gpt-4o-mini")

    with pytest.raises(ValueError, match="GEMINI_API_KEY が未設定です"):
        create_client(provider="gemini", model="gemini-1.5-flash")
