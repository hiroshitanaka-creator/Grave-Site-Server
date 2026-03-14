#!/usr/bin/env python3
"""Backward-compatible prompt builder CLI wrapper."""

from __future__ import annotations

import sys

from src import prompt_cli


def main() -> None:
    print(
        "[Deprecated] `python cli.py` は後方互換のために残されています。"
        "今後は `python src/prompt_cli.py` を利用してください。",
        file=sys.stderr,
    )
    prompt_cli.main()


if __name__ == "__main__":
    main()
