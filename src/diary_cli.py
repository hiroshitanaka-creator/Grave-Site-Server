from __future__ import annotations

import argparse
from pathlib import Path

try:
    from src.diary_processor import parse_text_block, process_entries, render_csv, render_json
except ModuleNotFoundError:  # script execution via `python src/diary_cli.py`
    from diary_processor import parse_text_block, process_entries, render_csv, render_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="input.txt の日記を解析して output/ に CSV または JSON を保存します。"
    )
    parser.add_argument(
        "--input",
        default="input.txt",
        help="入力ファイルパス（デフォルト: input.txt）",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="json",
        help="出力フォーマット（csv または json）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="出力ファイル名（未指定時は output/diary_output.<format>）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"入力ファイルが見つかりません: {input_path}")
        return 1

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = args.output or f"diary_output.{args.format}"
    output_path = output_dir / output_name

    text = input_path.read_text(encoding="utf-8")
    parsed = parse_text_block(text)
    records = process_entries(parsed.entries)

    if args.format == "csv":
        output_path.write_text(render_csv(records), encoding="utf-8")
    else:
        output_path.write_text(render_json(records), encoding="utf-8")

    print(f"出力完了: {output_path}")
    print(f"有効件数: {len(parsed.entries)}")
    print(f"無効件数: {len(parsed.errors)}")
    for error in parsed.errors:
        print(f"- {error}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
