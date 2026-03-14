from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

try:
    from src.diary_processor import parse_text_block, process_entries, render_csv, render_json
    from src.exporters.calendar_exporter import CalendarExporterError, publish_daily_message
    from src.exporters.drive_exporter import DriveExporterError, upload_daily_file
    from src.cli_messages import (
        INVALID_DATE_ERROR,
        format_input_file_not_found,
        format_missing_calendar_id,
    )
except ModuleNotFoundError:  # script execution via `python src/diary_cli.py`
    from diary_processor import parse_text_block, process_entries, render_csv, render_json
    from exporters.calendar_exporter import CalendarExporterError, publish_daily_message
    from exporters.drive_exporter import DriveExporterError, upload_daily_file
    from cli_messages import INVALID_DATE_ERROR, format_input_file_not_found, format_missing_calendar_id


CALENDAR_ID_ENV = "GOOGLE_CALENDAR_ID"


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(INVALID_DATE_ERROR) from exc


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
        help="出力ファイル名（未指定時は output/diary_YYYY-MM-DD.<format>）",
    )
    parser.add_argument(
        "--date",
        type=parse_iso_date,
        default=date.today(),
        help="出力ファイル名に使用する日付（YYYY-MM-DD、デフォルト: 今日）",
    )
    parser.add_argument(
        "--export-drive",
        action="store_true",
        help="ローカル出力後に Google Drive へアップロードする",
    )
    parser.add_argument(
        "--export-calendar",
        action="store_true",
        help="ローカル出力後に Google Calendar へ当日メッセージを配信する",
    )
    parser.add_argument(
        "--calendar-id",
        default=None,
        help=f"配信先Google Calendar ID（未指定時は環境変数 {CALENDAR_ID_ENV} を参照）",
    )
    return parser.parse_args()


def resolve_calendar_id(cli_calendar_id: str | None) -> str | None:
    return cli_calendar_id or os.getenv(CALENDAR_ID_ENV)


def build_daily_message(records: list[dict[str, str]]) -> str:
    summaries = [record.get("summary", "").strip() for record in records]
    valid_summaries = [summary for summary in summaries if summary]
    if not valid_summaries:
        return "本日の日記サマリーはありません。"

    return "\n".join(valid_summaries)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(format_input_file_not_found(input_path))
        return 1

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        requested_output = Path(args.output)
        output_path = (
            requested_output
            if requested_output.is_absolute() or requested_output.parent != Path(".")
            else output_dir / requested_output
        )
    else:
        output_path = output_dir / f"diary_{args.date.isoformat()}.{args.format}"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    parsed = parse_text_block(text)
    records = process_entries(parsed.entries)

    if args.format == "csv":
        output_path.write_text(render_csv(records), encoding="utf-8")
    else:
        output_path.write_text(render_json(records), encoding="utf-8")

    export_errors: list[str] = []

    if args.export_drive:
        try:
            upload_result = upload_daily_file(
                local_path=output_path,
                target_date=args.date,
                extension=args.format,
            )
            policy_message = "既存ファイルを上書き" if upload_result.replaced_existing else "新規作成"
            print(
                "Drive出力完了: "
                f"{upload_result.file_name} (file_id={upload_result.file_id}, policy={policy_message})"
            )
        except DriveExporterError as exc:
            export_errors.append(f"Drive出力エラー: {exc}")

    if args.export_calendar:
        calendar_id = resolve_calendar_id(args.calendar_id)
        if not calendar_id:
            export_errors.append(f"Calendar出力エラー: {format_missing_calendar_id(CALENDAR_ID_ENV)}")
        else:
            try:
                message = build_daily_message(records)
                publish_daily_message(
                    calendar_id=calendar_id,
                    target_date=args.date,
                    message=message,
                )
                print(f"Calendar出力完了: calendar_id={calendar_id}")
            except CalendarExporterError as exc:
                export_errors.append(f"Calendar出力エラー: {exc}")

    print(f"出力完了: {output_path}")
    print(f"有効件数: {len(parsed.entries)}")
    print(f"無効件数: {len(parsed.errors)}")
    for error in parsed.errors:
        print(f"- {error}")

    for error in export_errors:
        print(error)

    # Export failures are reported after local output summary.
    # Policy: if any selected exporter fails, return non-zero.
    return 1 if export_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
