"""Compatibility API; CLI delegates to the shared validation/quarantine pipeline."""

from __future__ import annotations

try:
    from src.llm_batch import (
        GeminiClient,
        analyze_entry,
        build_rows as _build_rows,
        write_csv,
        main as _main,
    )
except ModuleNotFoundError:
    from llm_batch import (
        GeminiClient,
        analyze_entry,
        build_rows as _build_rows,
        write_csv,
        main as _main,
    )

__all__ = ["GeminiGenerateContentClient", "analyze_entry", "build_rows", "write_csv", "main"]
GeminiGenerateContentClient = GeminiClient


def build_rows(entries, client, date_str):
    rows, quarantined = _build_rows(entries, client, date_str)
    if quarantined:
        raise ValueError(quarantined[0].reason)
    return rows


def main():
    return _main(default_provider="gemini", default_output="output/diary_gemini_output.csv")


if __name__ == "__main__":
    raise SystemExit(main())
