"""Dedup — see /specs/data-layer.spec.md hard rule 3. Exact hash first (cheap),
semantic similarity second. Runs BEFORE commit, surfaced at confirmation time —
never silently merged or silently duplicated."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


SEMANTIC_SIMILARITY_THRESHOLD = 0.90  # per spec: ~0.90-0.95 cosine threshold


@dataclass
class DedupMatch:
    matched_id: str
    match_type: str  # "exact" | "semantic"
    similarity: float


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def find_exact_match(text: str, existing_hashes: dict[str, str]) -> DedupMatch | None:
    """existing_hashes: {node_id: hash}"""
    h = content_hash(text)
    for node_id, existing_hash in existing_hashes.items():
        if existing_hash == h:
            return DedupMatch(matched_id=node_id, match_type="exact", similarity=1.0)
    return None


def find_semantic_match(
    embedding: list[float], existing_embeddings: dict[str, list[float]]
) -> DedupMatch | None:
    """Cosine similarity against nearby vectors. Real implementation will call
    LanceDB's similarity search; this is the pure-function contract it must satisfy,
    testable without a live vector store."""
    best_id, best_sim = None, 0.0
    for node_id, existing in existing_embeddings.items():
        sim = _cosine_similarity(embedding, existing)
        if sim > best_sim:
            best_id, best_sim = node_id, sim
    if best_id and best_sim >= SEMANTIC_SIMILARITY_THRESHOLD:
        return DedupMatch(matched_id=best_id, match_type="semantic", similarity=best_sim)
    return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
