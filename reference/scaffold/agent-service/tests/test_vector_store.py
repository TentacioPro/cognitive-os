"""TDD coverage for the LanceDB-compatible vector-store contract."""

import pytest

from app.data_layer.vector_store import VectorStore


def test_upsert_and_similarity_search_returns_metadata():
    store = VectorStore(threshold=0.90)
    store.upsert("node_1", [1.0, 0.0, 0.0], {"domain": "health"})
    matches = store.search([0.99, 0.01, 0.0])
    assert len(matches) == 1
    assert matches[0].matched_id == "node_1"
    assert matches[0].similarity >= 0.90
    assert matches[0].metadata == {"domain": "health"}


def test_search_does_not_return_below_threshold_vectors():
    store = VectorStore(threshold=0.90)
    store.upsert("node_1", [1.0, 0.0, 0.0])
    assert store.search([0.0, 1.0, 0.0]) == []


def test_search_orders_by_similarity_and_applies_limit():
    store = VectorStore(threshold=0.0)
    store.upsert("far", [0.0, 1.0])
    store.upsert("near", [1.0, 0.1])
    matches = store.search([1.0, 0.0], limit=1)
    assert [match.matched_id for match in matches] == ["near"]


def test_invalid_vector_inputs_are_rejected():
    store = VectorStore()
    with pytest.raises(ValueError):
        store.upsert("", [1.0])
    with pytest.raises(ValueError):
        store.upsert("node", [])
    with pytest.raises(ValueError):
        store.search([1.0], limit=0)
