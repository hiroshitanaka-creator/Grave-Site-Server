from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_embedding_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src.embedding.cli", *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_embedding_cli_index_and_search_sqlite(tmp_path: Path):
    input_path = tmp_path / "records.json"
    input_path.write_text(
        json.dumps(
            [
                {"id": "a1", "summary": "今日は散歩して落ち着いた"},
                {"id": "b2", "summary": "仕事が進んで達成感があった"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store_path = tmp_path / "embeddings.db"

    index_result = _run_embedding_cli(
        tmp_path,
        "index",
        "--input",
        str(input_path),
        "--output",
        str(store_path),
        "--backend",
        "sqlite",
        "--dimensions",
        "8",
    )

    assert index_result.returncode == 0
    assert store_path.exists()
    assert "Indexed 2 summary embeddings" in index_result.stdout

    search_result = _run_embedding_cli(
        tmp_path,
        "search",
        "--query",
        "散歩",
        "--store",
        str(store_path),
        "--backend",
        "sqlite",
        "--dimensions",
        "8",
        "--top-k",
        "1",
    )

    assert search_result.returncode == 0
    assert "Query: 散歩" in search_result.stdout
    assert "1. id=" in search_result.stdout


def test_embedding_cli_search_fails_when_store_is_empty(tmp_path: Path):
    store_path = tmp_path / "empty.json"
    store_path.write_text("[]", encoding="utf-8")

    result = _run_embedding_cli(
        tmp_path,
        "search",
        "--query",
        "散歩",
        "--store",
        str(store_path),
        "--backend",
        "json",
    )

    assert result.returncode == 1
    assert "No embeddings found. Run `index` first." in result.stderr


def test_embedding_cli_rejects_non_positive_dimensions(tmp_path: Path):
    input_path = tmp_path / "records.json"
    input_path.write_text(
        json.dumps([{"id": "a1", "summary": "今日は散歩して落ち着いた"}], ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run_embedding_cli(
        tmp_path,
        "index",
        "--input",
        str(input_path),
        "--output",
        str(tmp_path / "embeddings.json"),
        "--backend",
        "json",
        "--dimensions",
        "0",
    )

    assert result.returncode != 0
    assert "must be a positive integer" in result.stderr


def test_embedding_cli_rejects_non_positive_top_k(tmp_path: Path):
    store_path = tmp_path / "store.json"
    store_path.write_text(
        json.dumps([{"id": "a1", "summary": "今日は散歩して落ち着いた", "embedding": [0.1] * 8}], ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run_embedding_cli(
        tmp_path,
        "search",
        "--query",
        "散歩",
        "--store",
        str(store_path),
        "--backend",
        "json",
        "--dimensions",
        "8",
        "--top-k",
        "0",
    )

    assert result.returncode != 0
    assert "must be a positive integer" in result.stderr
