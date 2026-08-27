"""Small vector-store contract used by the local agent service.

The production adapter can replace this in-memory implementation with LanceDB.
The public methods intentionally expose the behavior the data-layer spec needs:
upsert vectors, search by cosine similarity, and avoid silently merging records.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VectorMatch:
    matched_id: str
    similarity: float
    metadata: dict


class VectorStore:
    def __init__(self, threshold: float = 0.90):
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold
        self._vectors: dict[str, tuple[list[float], dict]] = {}

    def upsert(self, vector_id: str, embedding: list[float], metadata: dict | None = None) -> None:
        if not vector_id:
            raise ValueError("vector_id is required")
        if not embedding or not all(isinstance(value, (int, float)) for value in embedding):
            raise ValueError("embedding must be a non-empty numeric list")
        self._vectors[vector_id] = (list(embedding), dict(metadata or {}))

    def search(self, embedding: list[float], *, limit: int = 10) -> list[VectorMatch]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        scored = []
        for vector_id, (existing, metadata) in self._vectors.items():
            similarity = self._cosine_similarity(embedding, existing)
            if similarity >= self.threshold:
                scored.append(VectorMatch(vector_id, similarity, dict(metadata)))
        scored.sort(key=lambda match: (-match.similarity, match.matched_id))
        return scored[:limit]

    def get(self, vector_id: str) -> VectorMatch | None:
        record = self._vectors.get(vector_id)
        if record is None:
            return None
        embedding, metadata = record
        return VectorMatch(vector_id, 1.0, dict(metadata))

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
