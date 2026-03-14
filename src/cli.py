from __future__ import annotations

import sys
from datetime import date

try:
    from src.diary_processor import analyze_entry
except ModuleNotFoundError:  # script execution via `python src/cli.py`
    from diary_processor import analyze_entry

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
        ValueError: If the input entry is empty/whitespace-only.
    """
    normalized = entry.strip()
    if not normalized:
        raise ValueError("空行は処理できません")

    resolved_date = today or date.today().isoformat()
    return analyze_entry(normalized, resolved_date)


if __name__ == "__main__":
    raise SystemExit(main())
