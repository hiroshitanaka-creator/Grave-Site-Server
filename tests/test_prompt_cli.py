from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.prompt_cli import build_prompt, load_entry

ROOT = Path(__file__).resolve().parents[1]


def _run_prompt_cli(tmp_path: Path, *args: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src.prompt_cli", *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        input=stdin,
        env=env,
        check=False,
    )


def test_build_prompt_requires_entry_placeholder():
    with pytest.raises(SystemExit, match="must include"):
        build_prompt("entry is missing", "今日は良い日")


def test_load_entry_from_arg():
    assert load_entry("  少し疲れた  ") == "少し疲れた"


def test_load_entry_raises_when_arg_and_stdin_are_empty(monkeypatch: pytest.MonkeyPatch):
    class DummyStdin:
        @staticmethod
        def read() -> str:
            return "   "

    monkeypatch.setattr(sys, "stdin", DummyStdin())

    with pytest.raises(SystemExit, match="Diary entry is required"):
        load_entry(None)


def test_prompt_cli_renders_template_from_stdin(tmp_path: Path):
    template_path = tmp_path / "template.txt"
    template_path.write_text("日記: {{entry}}", encoding="utf-8")

    result = _run_prompt_cli(
        tmp_path,
        "--prompt-file",
        str(template_path),
        stdin="今日は散歩して落ち着いた。",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "日記: 今日は散歩して落ち着いた。"


def test_prompt_cli_fails_with_missing_placeholder(tmp_path: Path):
    template_path = tmp_path / "template.txt"
    template_path.write_text("placeholder is absent", encoding="utf-8")

    result = _run_prompt_cli(tmp_path, "--prompt-file", str(template_path), "本文")

    assert result.returncode != 0
    assert "must include" in result.stderr
