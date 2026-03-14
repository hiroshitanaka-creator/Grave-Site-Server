from __future__ import annotations

from pathlib import Path

from .io_utils import load_records
from .models import DiaryEmbeddingRecord, resolve_record_id
from .vectorizer import cosine_similarity, embed_summary


def build_embedding_records(input_path: Path, dimensions: int = 256) -> list[DiaryEmbeddingRecord]:
    rows = load_records(input_path)
    records: list[DiaryEmbeddingRecord] = []

    for idx, row in enumerate(rows):
        summary = str(row.get("summary") or "").strip()
        if not summary:
            continue
        record_id = resolve_record_id(row, idx)
        vector = embed_summary(summary, dimensions=dimensions)
        records.append(
            DiaryEmbeddingRecord(
                id=record_id,
                summary=summary,
                source=input_path.name,
                vector=vector,
            )
        )

    return records


def search_similar(
    query: str,
    records: list[DiaryEmbeddingRecord],
    dimensions: int = 256,
    top_k: int = 5,
) -> list[tuple[DiaryEmbeddingRecord, float]]:
    query_vector = embed_summary(query, dimensions=dimensions)
    scored = [(record, cosine_similarity(query_vector, record.vector)) for record in records]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
