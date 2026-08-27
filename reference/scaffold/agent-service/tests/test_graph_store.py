"""TDD coverage for the local graph-compatible store."""

import sqlite3

import pytest

from app.data_layer.graph_store import DuplicateNodeError, GraphStore
from app.data_layer.provenance import Provenance, ProvenanceError


def test_write_without_provenance_fails_before_storage():
    store = GraphStore()
    with pytest.raises(ProvenanceError):
        store.write_node("Habit", {"name": "smoking"}, provenance=None, schema_version="v1")
    assert store.list_nodes() == []


def test_write_without_schema_version_fails_before_storage():
    store = GraphStore()
    with pytest.raises(ValueError, match="schema_version"):
        store.write_node(
            "Habit", {"name": "smoking"}, provenance=Provenance.USER_ATTESTED, schema_version=""
        )
    assert store.list_nodes() == []


def test_write_is_staged_and_persists_required_metadata():
    store = GraphStore()
    node_id = store.write_node(
        "Habit",
        {"name": "smoking"},
        provenance=Provenance.USER_ATTESTED,
        schema_version="v1",
    )
    node = store.get_node(node_id)
    assert node["node_type"] == "Habit"
    assert node["properties"] == {"name": "smoking"}
    assert node["provenance"] == Provenance.USER_ATTESTED.value
    assert node["schema_version"] == "v1"
    assert node["staged"] is True


def test_only_owner_can_promote_staged_node_to_committed():
    store = GraphStore()
    node_id = store.write_node(
        "Habit", {"name": "walk"}, provenance=Provenance.USER_ATTESTED, schema_version="v1"
    )
    with pytest.raises(PermissionError):
        store.commit_staged(node_id, actor_role="agent:staged_write")
    store.commit_staged(node_id, actor_role="owner")
    assert store.get_node(node_id)["staged"] is False


def test_non_owner_cannot_bypass_staging():
    store = GraphStore()
    with pytest.raises(PermissionError):
        store.write_node(
            "Habit",
            {"name": "walk"},
            provenance=Provenance.USER_ATTESTED,
            schema_version="v1",
            actor_role="agent:staged_write",
            staged=False,
        )


def test_inference_requires_derived_from_pointer():
    store = GraphStore()
    with pytest.raises(ProvenanceError, match="derived_from"):
        store.write_node(
            "inference",
            {"pattern": "consistent"},
            provenance=Provenance.INFERENCE,
            schema_version="v1",
        )
    node_id = store.write_node(
        "inference",
        {"pattern": "consistent"},
        provenance=Provenance.INFERENCE,
        schema_version="v1",
        derived_from=["node_a"],
    )
    assert store.get_node(node_id)["derived_from"] == ["node_a"]


def test_exact_duplicate_is_rejected_before_promotion():
    store = GraphStore()
    store.write_node(
        "journal_node", {"content": "Same thought"}, provenance=Provenance.USER_ATTESTED, schema_version="v1", actor_role="owner", staged=False, node_id="committed",
    )
    staged_id = store.write_node(
        "journal_node", {"content": "  same   thought "}, provenance=Provenance.USER_ATTESTED, schema_version="v1", node_id="staged",
    )
    with pytest.raises(DuplicateNodeError, match="committed"):
        store.commit_staged(staged_id)
    assert store.get_node(staged_id)["staged"] is True


def test_read_only_agent_cannot_read_staging():
    store = GraphStore()
    node_id = store.write_node(
        "Habit", {"name": "read"}, provenance=Provenance.USER_ATTESTED, schema_version="v1"
    )
    assert store.list_nodes(actor_role="agent:read_only") == []
    with pytest.raises(PermissionError):
        store.get_node(node_id, actor_role="agent:read_only")


def test_store_can_use_a_supplied_sqlite_connection():
    connection = sqlite3.connect(":memory:")
    store = GraphStore(connection=connection)
    node_id = store.write_node(
        "Habit", {"name": "read"}, provenance=Provenance.USER_ATTESTED, schema_version="v1"
    )
    assert store.get_node(node_id)["id"] == node_id
