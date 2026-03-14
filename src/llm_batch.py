from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
from urllib import error, request

try:
    from src.diary_processor import OUTPUT_COLUMNS, parse_text_block
    from src.cli_messages import format_input_file_not_found
except ModuleNotFoundError:  # script execution via `python src/llm_batch.py`
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
    provider_name: str

    def complete_json(self, prompt: str) -> dict[str, str]:
        """Return JSON object containing mood_tag/topic_tag/summary."""


class OpenAIResponsesClient:
    provider_name = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete_json(self, prompt: str) -> dict[str, str]:
        body = {
            "model": self.model,
            "input": prompt,
            "text": {"format": {"type": "json_object"}},
        }
        req = request.Request(
            url="https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network integration path
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI API error: status={exc.code}, detail={detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network integration path
            raise RuntimeError(f"OpenAI API request failed: {exc.reason}") from exc

        output_text = payload.get("output_text")
        if not output_text:
            raise ValueError("OpenAI response did not contain output_text")

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI response was not valid JSON: {output_text}") from exc


class GeminiClient:
    provider_name = "gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete_json(self, prompt: str) -> dict[str, str]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        req = request.Request(
            url=(
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{self.model}:generateContent?key={self.api_key}"
            ),
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

        try:
            output_text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Gemini response did not contain text payload: {payload}") from exc

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini response was not valid JSON: {output_text}") from exc


def create_client(provider: str, model: str) -> LLMClient:
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY が未設定です。")
        return OpenAIResponsesClient(api_key=api_key, model=model)

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY が未設定です。")
        return GeminiClient(api_key=api_key, model=model)

    raise ValueError(f"Unsupported provider: {provider}")


def analyze_entry(entry: str, client: LLMClient) -> AnalysisResult:
    prompt = PROMPT_TEMPLATE.format(entry=entry)
    response = client.complete_json(prompt)

    mood_tag = str(response.get("mood_tag", "")).strip()
    topic_tag = str(response.get("topic_tag", "")).strip()
    summary = str(response.get("summary", "")).strip()
    if not mood_tag or not topic_tag or not summary:
        raise ValueError(f"Missing expected keys in {client.provider_name} response: {response}")

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
    parser = argparse.ArgumentParser(
        description="複数日記をLLM APIで解析しCSVを出力します。"
    )
    parser.add_argument("--input", default="input.txt", help="1行1日記の入力ファイル")
    parser.add_argument("--output", default="output/diary_llm_output.csv", help="出力CSVパス")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default="openai",
        help="利用するLLMプロバイダ",
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="利用するモデル")
    parser.add_argument("--date", default=None, help="出力date列の固定値（未指定時は本日）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(format_input_file_not_found(input_path))
        return 1

    parsed = parse_text_block(input_path.read_text(encoding="utf-8"))
    if not parsed.entries:
        print("有効な日記がありません。")
        return 1

    try:
        client = create_client(provider=args.provider, model=args.model)
    except ValueError as exc:
        print(str(exc))
        return 1

    from datetime import date

    date_str = args.date or date.today().isoformat()
    rows = build_rows(parsed.entries, client=client, date_str=date_str)
    output_path = Path(args.output)
    write_csv(output_path, rows)

    print(f"出力完了: {output_path}")
    print(f"provider: {args.provider}, model: {args.model}")
    print(f"有効件数: {len(parsed.entries)}")
    print(f"無効件数: {len(parsed.errors)}")
    for item in parsed.errors:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
