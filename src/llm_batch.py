from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
from urllib import error, request
from datetime import date
import re

try:
    from src.diary_processor import OUTPUT_COLUMNS, parse_text_block
    from src.cli_messages import format_input_file_not_found
except ModuleNotFoundError:  # script execution via `python src/llm_batch.py`
    from diary_processor import OUTPUT_COLUMNS, parse_text_block
    from cli_messages import format_input_file_not_found


def prompt_template() -> str:
    from importlib.resources import files

    try:
        package = files("src.resources")
    except ModuleNotFoundError:
        package = files("resources")
    return package.joinpath("diary_tagging_v1.txt").read_text(encoding="utf-8")


@dataclass(frozen=True)
class AnalysisResult:
    mood_tag: str
    topic_tag: str
    summary: str


@dataclass(frozen=True)
class QuarantinedEntry:
    index: int
    entry: str
    reason: str


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
            exc.read()
            raise RuntimeError(f"OpenAI API error: status={exc.code}") from exc
        except error.URLError as exc:  # pragma: no cover - network integration path
            raise RuntimeError(f"OpenAI API request failed: {type(exc).__name__}") from exc

        if payload.get("status") not in {None, "completed"}:
            raise ValueError("OpenAI response is not completed")
        output_text = "".join(
            part.get("text", "")
            for item in payload.get("output", [])
            if item.get("type") == "message"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        )
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
                f"models/{self.model}:generateContent"
            ),
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )

        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network integration path
            exc.read()
            raise RuntimeError(f"Gemini API error: status={exc.code}") from exc
        except error.URLError as exc:  # pragma: no cover - network integration path
            raise RuntimeError(f"Gemini API request failed: {type(exc).__name__}") from exc

        try:
            candidate = payload["candidates"][0]
            if candidate.get("finishReason") not in {None, "STOP"}:
                raise ValueError("Gemini response is not completed")
            output_text = "".join(
                part.get("text", "")
                for part in candidate["content"]["parts"]
                if not part.get("thought")
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Gemini response did not contain text payload: {payload}") from exc

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini response was not valid JSON: {output_text}") from exc


def create_client(provider: str, model: str) -> LLMClient:
    if not model or not re.fullmatch(r"[A-Za-z0-9._:-]+", model):
        raise ValueError("Specify a valid --model or provider model environment variable")
    if provider == "gemini" and not model.startswith("gemini-"):
        raise ValueError("Gemini provider requires a gemini- model")
    if provider == "openai" and model.startswith("gemini-"):
        raise ValueError("OpenAI provider cannot use a Gemini model")
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
    prompt = prompt_template().replace("{{entry}}", entry)
    response = client.complete_json(prompt)
    if not isinstance(response, dict):
        raise ValueError("LLM response must be a JSON object")
    provider_name = getattr(client, "provider_name", "llm")
    for key in ("mood_tag", "topic_tag", "summary"):
        if key in response and not isinstance(response[key], str):
            raise ValueError(f"Invalid field type in {provider_name} response: {key}")

    mood_tag = str(response.get("mood_tag", "")).strip()
    topic_tag = str(response.get("topic_tag", "")).strip()
    summary = str(response.get("summary", "")).strip()
    allowed_moods = {"positive", "negative", "neutral", "motivated"}
    if mood_tag not in allowed_moods:
        raise ValueError(f"Invalid mood_tag in {provider_name} response: {mood_tag}")
    if not topic_tag or not summary:
        raise ValueError(f"Missing expected keys in {provider_name} response: {response}")
    if len(summary) > 30:
        raise ValueError(f"Summary exceeds 30 characters in {provider_name} response: {summary}")

    return AnalysisResult(mood_tag=mood_tag, topic_tag=topic_tag, summary=summary)


def build_rows(
    entries: Sequence[str], client: LLMClient, date_str: str
) -> tuple[list[dict[str, str]], list[QuarantinedEntry]]:
    rows: list[dict[str, str]] = []
    quarantined: list[QuarantinedEntry] = []
    for index, entry in enumerate(entries, start=1):
        try:
            result = analyze_entry(entry, client)
        except ValueError as exc:
            quarantined.append(QuarantinedEntry(index=index, entry=entry, reason=str(exc)))
            continue
        rows.append(
            {
                "date": date_str,
                "entry": entry,
                "mood_tag": result.mood_tag,
                "topic_tag": result.topic_tag,
                "summary": result.summary,
            }
        )
    return rows, quarantined


def write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_quarantine(path: Path, entries: Sequence[QuarantinedEntry]) -> None:
    if not entries:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in entries:
            f.write(
                json.dumps(
                    {
                        "index": item.index,
                        "entry": item.entry,
                        "reason": item.reason,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def parse_args(
    argv=None, *, default_provider="openai", default_output="output/diary_llm_output.csv"
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="複数日記をLLM APIで解析しCSVを出力します。")
    parser.add_argument("--input", default="input.txt", help="1行1日記の入力ファイル")
    parser.add_argument("--output", default=default_output, help="出力CSVパス")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default=default_provider,
        help="利用するLLMプロバイダ",
    )
    parser.add_argument(
        "--model", default=None, help="利用するモデル（未指定時はOPENAI_MODEL / GEMINI_MODEL）"
    )
    parser.add_argument("--date", default=None, help="出力date列の固定値（未指定時は本日）")
    parser.add_argument(
        "--quarantine-output",
        default=None,
        help="スキーマ不整合データの隔離先(JSONL)。未指定時は出力CSVと同じ場所に自動生成",
    )
    return parser.parse_args(argv)


def main(
    argv=None, *, default_provider="openai", default_output="output/diary_llm_output.csv"
) -> int:
    args = parse_args(argv, default_provider=default_provider, default_output=default_output)
    args.model = args.model or os.getenv(f"{args.provider.upper()}_MODEL", "")
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

    date_str = args.date or date.today().isoformat()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            raise ValueError
        date.fromisoformat(date_str)
    except ValueError:
        print("--date must be YYYY-MM-DD")
        return 1
    rows, quarantined = build_rows(parsed.entries, client=client, date_str=date_str)
    output_path = Path(args.output)
    write_csv(output_path, rows)
    quarantine_path = (
        Path(args.quarantine_output)
        if args.quarantine_output
        else output_path.with_suffix(".quarantine.jsonl")
    )
    write_quarantine(quarantine_path, quarantined)

    print(f"出力完了: {output_path}")
    print(f"provider: {args.provider}, model: {args.model}")
    print(f"有効件数: {len(rows)}")
    print(f"隔離件数: {len(quarantined)}")
    if quarantined:
        print(f"隔離ファイル: {quarantine_path}")
    print(f"無効件数: {len(parsed.errors)}")
    for item in parsed.errors:
        print(f"- {item}")
    return 1 if quarantined else 0


if __name__ == "__main__":
    raise SystemExit(main())
