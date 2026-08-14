"""Tests for /specs/data-layer.spec.md hard rule 3 (dedup)."""

from app.data_layer.dedup import find_exact_match, find_semantic_match, content_hash


def test_exact_duplicate_is_found_regardless_of_case_or_whitespace():
    existing = {"node_1": content_hash("Reduced my smoking to 30 a week")}
    match = find_exact_match("  reduced my smoking to 30 a week  ", existing)
    assert match is not None
    assert match.matched_id == "node_1"
    assert match.match_type == "exact"


def test_no_exact_match_returns_none():
    existing = {"node_1": content_hash("some other content")}
    match = find_exact_match("completely different text", existing)
    assert match is None


def test_semantic_match_above_threshold_is_found():
    existing = {"node_1": [1.0, 0.0, 0.0]}
    # near-identical vector, cosine similarity ~1.0
    match = find_semantic_match([0.99, 0.01, 0.0], existing)
    assert match is not None
    assert match.matched_id == "node_1"
    assert match.similarity >= 0.90


def test_semantic_match_below_threshold_is_not_returned():
    existing = {"node_1": [1.0, 0.0, 0.0]}
    match = find_semantic_match([0.0, 1.0, 0.0], existing)  # orthogonal, sim = 0
    assert match is None
