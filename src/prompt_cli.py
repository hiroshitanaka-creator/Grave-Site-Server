#!/usr/bin/env python3
"""Diary tagging prompt builder CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a tagging prompt from a diary entry and a prompt template file."
    )
    parser.add_argument(
        "entry",
        nargs="?",
        help="Diary entry text. If omitted, stdin is used.",
    )
    parser.add_argument(
        "--prompt-file",
        default="prompts/diary_tagging_v1.txt",
        help="Path to prompt template file.",
    )
    return parser.parse_args()


def load_entry(arg_entry: str | None) -> str:
    if arg_entry is not None:
        return arg_entry.strip()

    import sys

    stdin_text = sys.stdin.read().strip()
    if stdin_text:
        return stdin_text
    raise SystemExit("Diary entry is required. Pass it as an argument or via stdin.")


def load_template(path: str) -> str:
    template_path = Path(path)
    if not template_path.exists():
        raise SystemExit(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def build_prompt(template: str, entry: str) -> str:
    if "{{entry}}" not in template:
        raise SystemExit("Prompt template must include '{{entry}}' placeholder.")
    return template.replace("{{entry}}", entry)


def main() -> None:
    args = parse_args()
    entry = load_entry(args.entry)
    template = load_template(args.prompt_file)
    print(build_prompt(template, entry))


if __name__ == "__main__":
    main()
