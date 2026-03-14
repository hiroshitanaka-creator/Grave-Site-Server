from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from dataclasses import asdict

from .models import DiaryEmbeddingRecord


class JsonEmbeddingStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, records: list[DiaryEmbeddingRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in records]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> list[DiaryEmbeddingRecord]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [DiaryEmbeddingRecord(**row) for row in payload]


class SQLiteEmbeddingStore:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                source TEXT NOT NULL,
                vector TEXT NOT NULL
            )
            """
        )
        return conn

    def save(self, records: list[DiaryEmbeddingRecord]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO embeddings (id, summary, source, vector)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    summary=excluded.summary,
                    source=excluded.source,
                    vector=excluded.vector
                """,
                [
                    (
                        record.id,
                        record.summary,
                        record.source,
                        json.dumps(record.vector),
                    )
                    for record in records
                ],
            )

    def load(self) -> list[DiaryEmbeddingRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, summary, source, vector FROM embeddings ORDER BY id"
            ).fetchall()

        return [
            DiaryEmbeddingRecord(
                id=row[0],
                summary=row[1],
                source=row[2],
                vector=json.loads(row[3]),
            )
            for row in rows
        ]
