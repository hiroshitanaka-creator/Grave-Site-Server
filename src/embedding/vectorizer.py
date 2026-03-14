from __future__ import annotations

import hashlib
import math
from typing import Iterable


def _char_trigrams(text: str) -> Iterable[str]:
    normalized = "".join(text.lower().split())
    if len(normalized) < 3:
        if normalized:
            yield normalized
        return

    for i in range(len(normalized) - 2):
        yield normalized[i : i + 3]


def _stable_bucket(token: str, dimensions: int) -> int:
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dimensions


def embed_summary(summary: str, dimensions: int = 256) -> list[float]:
    """Create a local deterministic embedding via hashed trigram features."""

    vector = [0.0] * dimensions
    for token in _char_trigrams(summary):
        bucket = _stable_bucket(token, dimensions)
        vector[bucket] += 1.0

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vector dimensions must match")
    return sum(l * r for l, r in zip(left, right))
