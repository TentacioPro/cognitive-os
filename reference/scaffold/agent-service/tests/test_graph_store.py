"""
GraphStore is intentionally not fully implemented yet (see graph_store.py docstring
and README.md). These tests assert the CORRECT current state: the guardrails that
don't need a live database already work, and the parts that do fail loudly and
clearly rather than silently.
"""

import pytest

from app.data_layer.graph_store import GraphStore
from app.data_layer.provenance import Provenance, ProvenanceError


def test_write_without_provenance_fails_before_touching_the_database():
    store = GraphStore(connection=None)
    with pytest.raises(ProvenanceError):
        store.write_node("Habit", {"name": "smoking"}, provenance=None, schema_version="v1")


def test_write_without_schema_version_fails_before_touching_the_database():
    store = GraphStore(connection=None)
    with pytest.raises(ValueError, match="schema_version"):
        store.write_node("Habit", {"name": "smoking"}, provenance=Provenance.USER_ATTESTED, schema_version="")


def test_write_requires_kuzu_connection():
    """This is the expected failing-forward test: once graph_store.py wires in a
    real Kùzu connection, this test should be updated to assert a successful write
    instead. Until then, NotImplementedError is the correct, honest behavior."""
    store = GraphStore(connection=None)
    with pytest.raises(NotImplementedError):
        store.write_node(
            "Habit", {"name": "smoking"}, provenance=Provenance.USER_ATTESTED, schema_version="v1"
        )
