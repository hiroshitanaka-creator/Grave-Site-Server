from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli import build_record


ROOT = Path(__file__).resolve().parents[1]


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src.cli", *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_cli_json_output_success(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("今日は仕事が順調だった。\n", encoding="utf-8")

    result = _run_cli(tmp_path, "--input", str(input_file), "--format", "json")

    assert result.returncode == 0
    output_file = tmp_path / "output" / "diary_output.json"
    assert output_file.exists()

    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["entry"] == "今日は仕事が順調だった。"


def test_cli_csv_output_success(tmp_path: Path):
    input_file = tmp_path / "input.txt"
    input_file.write_text("運動して気分転換した。\n", encoding="utf-8")

    result = _run_cli(tmp_path, "--input", str(input_file), "--format", "csv")

    assert result.returncode == 0
    output_file = tmp_path / "output" / "diary_output.csv"
    assert output_file.exists()

    with output_file.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["entry"] == "運動して気分転換した。"


def test_cli_no_input_raises_value_error():
    with pytest.raises(ValueError, match="空行は処理できません"):
        build_record("   ")


def test_cli_missing_input_file_returns_error(tmp_path: Path):
    missing_file = tmp_path / "missing.txt"

    result = _run_cli(tmp_path, "--input", str(missing_file), "--format", "json")

    assert result.returncode == 1
    assert "入力ファイルが見つかりません" in result.stdout
