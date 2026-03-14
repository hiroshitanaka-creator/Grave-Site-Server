from __future__ import annotations

import sys

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


if __name__ == "__main__":
    raise SystemExit(main())
