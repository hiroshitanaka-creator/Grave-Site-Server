from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src import diary_cli

ROOT = Path(__file__).resolve().parents[1]


def _run_diary_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src.diary_cli", *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_diary_cli_default_output_name_uses_date(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("朝に散歩した。\n", encoding="utf-8")

    result = _run_diary_cli(tmp_path, "--input", str(input_file), "--format", "json", "--date", "2026-02-06")

    assert result.returncode == 0
    assert (tmp_path / "output" / "diary_2026-02-06.json").exists()


def test_diary_cli_export_drive_requires_env_vars(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("夜に読書した。\n", encoding="utf-8")

    result = _run_diary_cli(
        tmp_path,
        "--input",
        str(input_file),
        "--format",
        "csv",
        "--date",
        "2026-02-06",
        "--export-drive",
    )

    assert result.returncode == 1
    assert "Drive出力エラー" in result.stdout
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in result.stdout
    assert (tmp_path / "output" / "diary_2026-02-06.csv").exists()


def test_diary_cli_export_calendar_requires_calendar_id(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("夜に読書した。\n", encoding="utf-8")

    result = _run_diary_cli(
        tmp_path,
        "--input",
        str(input_file),
        "--format",
        "json",
        "--date",
        "2026-02-06",
        "--export-calendar",
    )

    assert result.returncode == 1
    assert "Calendar出力エラー" in result.stdout
    assert "GOOGLE_CALENDAR_ID" in result.stdout
    assert (tmp_path / "output" / "diary_2026-02-06.json").exists()


def test_diary_cli_export_calendar_calls_publisher(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("朝に散歩した。\n", encoding="utf-8")

    called: dict[str, str] = {}

    def fake_publish_daily_message(*, calendar_id: str, target_date, message: str):
        called["calendar_id"] = calendar_id
        called["target_date"] = target_date.isoformat()
        called["message"] = message

    monkeypatch.setattr(diary_cli, "publish_daily_message", fake_publish_daily_message)
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "calendar-123")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "diary_cli.py",
            "--input",
            str(input_file),
            "--format",
            "json",
            "--date",
            "2026-02-06",
            "--export-calendar",
        ],
    )

    result = diary_cli.main()

    assert result == 0
    assert called == {
        "calendar_id": "calendar-123",
        "target_date": "2026-02-06",
        "message": "朝に散歩した。",
    }


def test_diary_cli_output_path_with_directory_is_respected(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("朝に散歩した。\n", encoding="utf-8")
    custom_output = tmp_path / "artifacts" / "custom.json"

    result = _run_diary_cli(
        tmp_path,
        "--input",
        str(input_file),
        "--format",
        "json",
        "--output",
        str(custom_output),
    )

    assert result.returncode == 0
    assert custom_output.exists()
    assert not (tmp_path / "output" / "custom.json").exists()


def test_diary_cli_output_filename_without_directory_is_written_under_output(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("朝に散歩した。\n", encoding="utf-8")

    result = _run_diary_cli(
        tmp_path,
        "--input",
        str(input_file),
        "--format",
        "json",
        "--output",
        "custom.json",
    )

    assert result.returncode == 0
    assert (tmp_path / "output" / "custom.json").exists()
    assert not (tmp_path / "custom.json").exists()
