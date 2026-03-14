from __future__ import annotations

import sys
from datetime import date

try:
    from src.diary_processor import analyze_entry
except ModuleNotFoundError:  # script execution via `python src/cli.py`
    from diary_processor import analyze_entry

try:
    from src.input_validation import ERR_EMPTY_LINE, validate_entry_item
except ModuleNotFoundError:  # script execution via `python src/cli.py`
    from input_validation import ERR_EMPTY_LINE, validate_entry_item

try:
    from src import diary_cli
except ModuleNotFoundError:  # script execution via `python src/cli.py`
    import diary_cli


def main() -> int:
    print(
        "[Deprecated] `python src/cli.py` は後方互換のために残されています。"
        "今後は `python src/diary_cli.py` を利用してください。",
        file=sys.stderr,
    )
    return diary_cli.main()


def build_record(entry: str, today: str | None = None) -> dict[str, str]:
    """Backward-compatible helper for older tests and callers.

    Raises:
        ValueError: If the input entry cannot be normalized as a valid diary line.
    """
    validation = validate_entry_item(entry)
    if validation.error_code:
        if validation.error_code == ERR_EMPTY_LINE:
            raise ValueError("空行は処理できません")
        raise ValueError("異常文字列は処理できません")

    resolved_date = today or date.today().isoformat()
    return analyze_entry(validation.normalized or "", resolved_date)


if __name__ == "__main__":
    raise SystemExit(main())
