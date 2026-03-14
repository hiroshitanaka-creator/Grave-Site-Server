from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
