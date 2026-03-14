from src.input_validation import (
    ERR_EMPTY_LINE,
    ERR_INVALID_CHARACTERS,
    ERR_INVALID_TYPE,
    format_entry_error,
    validate_entry_item,
)


def test_validate_entry_item_returns_error_for_non_string() -> None:
    validation = validate_entry_item(123)

    assert validation.error_code == ERR_INVALID_TYPE
    assert validation.invalid_type_name == "int"
    assert validation.normalized is None


def test_validate_entry_item_returns_error_for_empty_line() -> None:
    validation = validate_entry_item("   ")

    assert validation.error_code == ERR_EMPTY_LINE


def test_validate_entry_item_returns_error_for_control_characters() -> None:
    validation = validate_entry_item("invalid\x00line")

    assert validation.error_code == ERR_INVALID_CHARACTERS


def test_validate_entry_item_returns_normalized_value() -> None:
    validation = validate_entry_item("  今日も勉強した  ")

    assert validation.error_code is None
    assert validation.normalized == "今日も勉強した"


def test_format_entry_error_formats_invalid_type() -> None:
    validation = validate_entry_item(123)

    assert format_entry_error(line_number=2, validation=validation) == "line 2: invalid type=int"
