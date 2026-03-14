from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
from urllib import error, parse, request

try:
    from src.diary_processor import OUTPUT_COLUMNS, parse_text_block
    from src.cli_messages import format_input_file_not_found
except ModuleNotFoundError:  # script execution via `python src/gemini_diary_batch.py`
    from diary_processor import OUTPUT_COLUMNS, parse_text_block
    from cli_messages import format_input_file_not_found


PROMPT_TEMPLATE = """次の日記を分析して、JSONのみで返してください。

制約:
- mood_tag は `positive` / `negative` / `neutral` / `motivated` のいずれか
- topic_tag は英語タグをカンマ区切り（例: `work, health`）
- summary は日本語で30文字以内

出力JSON形式:
{{
  "mood_tag": "...",
  "topic_tag": "...",
  "summary": "..."
}}

日記:
{entry}
"""


@dataclass(frozen=True)
class AnalysisResult:
    mood_tag: str
    topic_tag: str
    summary: str


class LLMClient(Protocol):
    def complete_json(self, prompt: str) -> dict[str, str]:
        """Return JSON object containing mood_tag/topic_tag/summary."""


class GeminiGenerateContentClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete_json(self, prompt: str) -> dict[str, str]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={parse.quote(self.api_key)}"
        )
        req = request.Request(
            url=endpoint,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network integration path
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini API error: status={exc.code}, detail={detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network integration path
            raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

        candidates = payload.get("candidates") or []
        if not candidates:
            raise ValueError(f"Gemini response did not contain candidates: {payload}")

        parts = (candidates[0].get("content") or {}).get("parts") or []
        if not parts:
            raise ValueError(f"Gemini response did not contain parts: {payload}")

        text = str(parts[0].get("text", "")).strip()
        if not text:
            raise ValueError(f"Gemini response text was empty: {payload}")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini response was not valid JSON: {text}") from exc


def analyze_entry(entry: str, client: LLMClient) -> AnalysisResult:
    prompt = PROMPT_TEMPLATE.format(entry=entry)
    response = client.complete_json(prompt)

    mood_tag = str(response.get("mood_tag", "")).strip()
    topic_tag = str(response.get("topic_tag", "")).strip()
    summary = str(response.get("summary", "")).strip()
    if not mood_tag or not topic_tag or not summary:
        raise ValueError(f"Missing expected keys in Gemini response: {response}")

    return AnalysisResult(mood_tag=mood_tag, topic_tag=topic_tag, summary=summary)


def build_rows(entries: Sequence[str], client: LLMClient, date_str: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in entries:
        result = analyze_entry(entry, client)
        rows.append(
            {
                "date": date_str,
                "entry": entry,
                "mood_tag": result.mood_tag,
                "topic_tag": result.topic_tag,
                "summary": result.summary,
            }
        )
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="複数日記をGemini APIで解析しCSVを出力します。")
    parser.add_argument("--input", default="input.txt", help="1行1日記の入力ファイル")
    parser.add_argument("--output", default="output/diary_gemini_output.csv", help="出力CSVパス")
    parser.add_argument("--model", default="gemini-2.5-flash", help="利用するGeminiモデル")
    parser.add_argument("--date", default=None, help="出力date列の固定値（未指定時は本日）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(format_input_file_not_found(input_path))
        return 1

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY が未設定です。")
        return 1

    parsed = parse_text_block(input_path.read_text(encoding="utf-8"))
    if not parsed.entries:
        print("有効な日記がありません。")
        return 1

    from datetime import date

    date_str = args.date or date.today().isoformat()
    client = GeminiGenerateContentClient(api_key=api_key, model=args.model)
    rows = build_rows(parsed.entries, client=client, date_str=date_str)
    output_path = Path(args.output)
    write_csv(output_path, rows)

    print(f"出力完了: {output_path}")
    print(f"有効件数: {len(parsed.entries)}")
    print(f"無効件数: {len(parsed.errors)}")
    for item in parsed.errors:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
