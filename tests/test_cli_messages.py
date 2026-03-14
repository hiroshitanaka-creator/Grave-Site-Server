from pathlib import Path

from src.cli_messages import (
    EMPTY_ENTRY_ERROR,
    INVALID_DATE_ERROR,
    INVALID_ENTRY_ERROR,
    format_input_file_not_found,
    format_missing_calendar_id,
)


def test_entry_error_messages_are_fixed_strings() -> None:
    assert EMPTY_ENTRY_ERROR == "空行は処理できません"
    assert INVALID_ENTRY_ERROR == "異常文字列は処理できません"
    assert INVALID_DATE_ERROR == "--date は YYYY-MM-DD 形式で指定してください"


def test_format_input_file_not_found_message() -> None:
    assert format_input_file_not_found(Path("input.txt")) == "入力ファイルが見つかりません: input.txt"


def test_format_missing_calendar_id_message() -> None:
    assert (
        format_missing_calendar_id("GOOGLE_CALENDAR_ID")
        == "--calendar-id または環境変数 GOOGLE_CALENDAR_ID を設定してください。"
    )
