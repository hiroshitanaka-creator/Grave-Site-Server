from __future__ import annotations

import argparse
from pathlib import Path

from diary_processor import parse_text_block, process_entries, render_csv, render_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process Japanese diary entries into CSV/JSON")
    parser.add_argument("input", type=Path, help="Input text file path (1 line = 1 entry)")
    parser.add_argument("--csv-out", type=Path, help="Output CSV path")
    parser.add_argument("--json-out", type=Path, help="Output JSON path")
    parser.add_argument("--date", type=str, help="Override date (YYYY-MM-DD)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_text = args.input.read_text(encoding="utf-8")
    parsed = parse_text_block(raw_text)
    records = process_entries(parsed.entries, today=args.date)

    if args.csv_out:
        args.csv_out.write_text(render_csv(records), encoding="utf-8")
    if args.json_out:
        args.json_out.write_text(render_json(records), encoding="utf-8")

    for error in parsed.errors:
        print(f"[WARN] {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
