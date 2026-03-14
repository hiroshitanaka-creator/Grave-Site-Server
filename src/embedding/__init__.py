"""Local embedding utilities for diary summaries."""

from .models import DiaryEmbeddingRecord
from .pipeline import build_embedding_records

__all__ = ["DiaryEmbeddingRecord", "build_embedding_records"]
