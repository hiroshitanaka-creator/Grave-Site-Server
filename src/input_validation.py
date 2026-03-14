from __future__ import annotations

from dataclasses import dataclass

ERR_EMPTY_LINE = "empty line"
ERR_INVALID_CHARACTERS = "invalid characters"
ERR_INVALID_TYPE = "invalid type"


@dataclass(frozen=True)
class EntryValidationResult:
    normalized: str | None
    error_code: str | None
    invalid_type_name: str | None = None


def validate_entry_item(item: object) -> EntryValidationResult:
    if not isinstance(item, str):
        return EntryValidationResult(
            normalized=None,
            error_code=ERR_INVALID_TYPE,
            invalid_type_name=type(item).__name__,
        )

    normalized = item.strip()
    if not normalized:
        return EntryValidationResult(normalized=None, error_code=ERR_EMPTY_LINE)

    if any(ord(char) < 32 and char != "\t" for char in normalized):
        return EntryValidationResult(normalized=None, error_code=ERR_INVALID_CHARACTERS)

    return EntryValidationResult(normalized=normalized, error_code=None)


def format_entry_error(*, line_number: int, validation: EntryValidationResult) -> str:
    if validation.error_code == ERR_INVALID_TYPE:
        type_name = validation.invalid_type_name or "unknown"
        return f"line {line_number}: invalid type={type_name}"

    if validation.error_code:
        return f"line {line_number}: {validation.error_code}"

    raise ValueError("validation error formatter called without error_code")
