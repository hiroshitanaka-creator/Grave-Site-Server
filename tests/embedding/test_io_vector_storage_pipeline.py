from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.embedding.io_utils import load_records
from src.embedding.models import DiaryEmbeddingRecord
from src.embedding.pipeline import search_similar
from src.embedding.storage import JsonEmbeddingStore, SQLiteEmbeddingStore
from src.embedding.vectorizer import embed_summary


def test_load_records_csv_json_and_invalid_json(tmp_path: Path):
    csv_path = tmp_path / "records.csv"
    csv_path.write_text("summary,id\n晴れて嬉しい,a1\n", encoding="utf-8")

    json_path = tmp_path / "records.json"
    json_path.write_text(
        json.dumps([{"summary": "散歩した", "id": "b2"}], ensure_ascii=False),
        encoding="utf-8",
    )

    invalid_json_path = tmp_path / "invalid.json"
    invalid_json_path.write_text(json.dumps({"summary": "not-list"}, ensure_ascii=False), encoding="utf-8")

    csv_rows = load_records(csv_path)
    json_rows = load_records(json_path)

    assert csv_rows == [{"summary": "晴れて嬉しい", "id": "a1"}]
    assert json_rows == [{"summary": "散歩した", "id": "b2"}]

    with pytest.raises(ValueError, match="JSON input must be an array of objects"):
        load_records(invalid_json_path)


def test_embed_summary_dimensions_and_zero_vector():
    vec = embed_summary("今日は読書した", dimensions=8)
    assert len(vec) == 8
    assert any(v != 0.0 for v in vec)

    zero_vec = embed_summary("   ", dimensions=8)
    assert len(zero_vec) == 8
    assert all(v == 0.0 for v in zero_vec)


def test_storage_json_and_sqlite_round_trip(tmp_path: Path):
    records = [
        DiaryEmbeddingRecord(
            id="r1",
            summary="運動して気分が良い",
            source="input.json",
            vector=[0.1, 0.2, 0.3],
        )
    ]

    json_store = JsonEmbeddingStore(tmp_path / "embeddings.json")
    json_store.save(records)
    assert json_store.load() == records

    sqlite_store = SQLiteEmbeddingStore(tmp_path / "embeddings.db")
    sqlite_store.save(records)
    assert sqlite_store.load() == records


def test_search_similar_top_k_boundaries_and_dimension_mismatch():
    records = [
        DiaryEmbeddingRecord(id="a", summary="aaa", source="x", vector=embed_summary("aaa", dimensions=8)),
        DiaryEmbeddingRecord(id="b", summary="bbb", source="x", vector=embed_summary("bbb", dimensions=8)),
    ]

    assert search_similar("aaa", records, dimensions=8, top_k=0) == []

    results = search_similar("aaa", records, dimensions=8, top_k=10)
    assert len(results) == 2

    mismatched = [
        DiaryEmbeddingRecord(id="bad", summary="zzz", source="x", vector=embed_summary("zzz", dimensions=4))
    ]
    with pytest.raises(ValueError, match="Vector dimensions must match"):
        search_similar("aaa", mismatched, dimensions=8, top_k=1)


def test_embedding_golden_vector_rounding():
    fixture_dir = Path(__file__).parent / "golden"
    summary = (fixture_dir / "known_summary.txt").read_text(encoding="utf-8").strip()
    expected = json.loads((fixture_dir / "expected_vector_dim8.json").read_text(encoding="utf-8"))

    actual = embed_summary(summary, dimensions=8)
    rounded = [round(value, 6) for value in actual]

    assert rounded == expected
