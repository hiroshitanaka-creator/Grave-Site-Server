from pathlib import Path

from src.cli_messages import EMPTY_ENTRY_ERROR, INVALID_ENTRY_ERROR, format_input_file_not_found


def test_entry_error_messages_are_fixed_strings() -> None:
    assert EMPTY_ENTRY_ERROR == "空行は処理できません"
    assert INVALID_ENTRY_ERROR == "異常文字列は処理できません"


def test_format_input_file_not_found_message() -> None:
    assert format_input_file_not_found(Path("input.txt")) == "入力ファイルが見つかりません: input.txt"
