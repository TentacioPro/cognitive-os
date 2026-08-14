"""
Kùzu graph store wiring — see /specs/data-layer.spec.md.

STATUS: not yet implemented. This is the intended interface; wiring in an actual
Kùzu connection is the next concrete build step after this pass. The failing
test in tests/test_graph_store.py is the correct TDD state, not an oversight —
see README.md's "what this scaffold actually is" section.
"""

from __future__ import annotations

from app.data_layer.provenance import Provenance, validate_write


class GraphStore:
    def __init__(self, connection=None):
        self.connection = connection

    def write_node(self, node_type: str, properties: dict, provenance: Provenance, schema_version: str):
        # Provenance + schema_version are required at the storage layer, not just
        # convention (data-layer.spec.md hard rule 1) — enforced even before the
        # real Kùzu call exists.
        validate_write(provenance)
        if not schema_version:
            raise ValueError("write is missing schema_version — no default exists")

        if self.connection is None:
            raise NotImplementedError(
                "GraphStore has no live Kùzu connection yet. "
                "Wiring this in is the next build step (see docs/ARCHITECTURE.md)."
            )
        # TODO: actual Kùzu write once the connection is wired in.
        raise NotImplementedError
