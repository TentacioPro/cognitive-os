"""Local graph-compatible store with distinct staging and committed namespaces.

SQLite is the local reference adapter. A Kùzu adapter can replace the table
backend later, but agents still write only to ``staged_nodes`` and can never
bypass the owner promotion boundary.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.data_layer.provenance import Provenance, ProvenanceError, validate_write


class DuplicateNodeError(ValueError):
    def __init__(self, duplicate_id: str):
        super().__init__(f"exact duplicate detected before commit: {duplicate_id}")
        self.duplicate_id = duplicate_id


class GraphStore:
    def __init__(self, connection: sqlite3.Connection | None = None):
        self.connection = connection or sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        for table in ("staged_nodes", "committed_nodes"):
            self.connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    derived_from_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        self.connection.commit()

    def write_node(
        self,
        node_type: str,
        properties: dict[str, Any],
        provenance: Provenance,
        schema_version: str,
        *,
        actor_role: str = "agent:staged_write",
        staged: bool = True,
        derived_from: list[str] | None = None,
        node_id: str | None = None,
    ) -> str:
        validate_write(provenance)
        if not schema_version:
            raise ValueError("write is missing schema_version — no default exists")
        if not node_type:
            raise ValueError("write is missing node_type")
        if not isinstance(properties, dict):
            raise TypeError("properties must be a dictionary")
        if actor_role != "owner" and not staged:
            raise PermissionError("non-owner agents may only write to staging")
        if provenance == Provenance.INFERENCE and not derived_from:
            raise ProvenanceError("INFERENCE nodes must carry a derived_from pointer")

        identifier = node_id or str(uuid.uuid4())
        table = "staged_nodes" if staged else "committed_nodes"
        self.connection.execute(
            f"""
            INSERT INTO {table} (
                id, node_type, properties_json, provenance, schema_version,
                derived_from_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                identifier,
                node_type,
                json.dumps(properties, ensure_ascii=False, sort_keys=True),
                provenance.value,
                schema_version,
                json.dumps(derived_from, ensure_ascii=False) if derived_from else None,
                datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            ),
        )
        self.connection.commit()
        return identifier

    def get_node(self, node_id: str, *, actor_role: str = "owner") -> dict[str, Any]:
        for table, staged in (("staged_nodes", True), ("committed_nodes", False)):
            row = self.connection.execute(f"SELECT * FROM {table} WHERE id = ?", (node_id,)).fetchone()
            if row is not None:
                if staged and actor_role == "agent:read_only":
                    raise PermissionError("read-only agents cannot read staging")
                return self._row_to_node(row, staged=staged)
        raise KeyError(f"node not found: {node_id}")

    def list_nodes(self, *, staged: bool | None = None, actor_role: str = "owner") -> list[dict[str, Any]]:
        if actor_role == "agent:read_only" and staged is True:
            raise PermissionError("read-only agents cannot read staging")
        tables = [("staged_nodes", True), ("committed_nodes", False)] if staged is None else [("staged_nodes" if staged else "committed_nodes", staged)]
        nodes = []
        for table, is_staged in tables:
            rows = self.connection.execute(f"SELECT * FROM {table} ORDER BY created_at, id").fetchall()
            if actor_role == "agent:read_only" and is_staged:
                continue
            nodes.extend(self._row_to_node(row, staged=is_staged) for row in rows)
        return sorted(nodes, key=lambda node: (node["created_at"], node["id"]))

    def commit_staged(self, node_id: str, *, actor_role: str = "owner") -> None:
        if actor_role != "owner":
            raise PermissionError("only owner may promote staged nodes")
        row = self.connection.execute("SELECT * FROM staged_nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise ValueError(f"staged node not found: {node_id}")
        duplicate = self._find_exact_duplicate(row)
        if duplicate is not None:
            raise DuplicateNodeError(duplicate)
        self.connection.execute(
            "INSERT INTO committed_nodes SELECT * FROM staged_nodes WHERE id = ?", (node_id,)
        )
        self.connection.execute("DELETE FROM staged_nodes WHERE id = ?", (node_id,))
        self.connection.commit()

    def rollback_staged(self, node_id: str, *, actor_role: str = "owner") -> None:
        if actor_role != "owner":
            raise PermissionError("only owner may rollback staged nodes")
        cursor = self.connection.execute("DELETE FROM staged_nodes WHERE id = ?", (node_id,))
        self.connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"staged node not found: {node_id}")

    def _find_exact_duplicate(self, row: sqlite3.Row) -> str | None:
        normalized = self._normalized_content(json.loads(row["properties_json"]))
        if not normalized:
            return None
        for table in ("committed_nodes", "staged_nodes"):
            candidates = self.connection.execute(
                f"SELECT id, properties_json FROM {table} WHERE node_type = ? AND id <> ?",
                (row["node_type"], row["id"]),
            ).fetchall()
            for candidate in candidates:
                if self._normalized_content(json.loads(candidate["properties_json"])) == normalized:
                    return candidate["id"]
        return None

    @staticmethod
    def _normalized_content(properties: dict[str, Any]) -> str:
        content = properties.get("content") or properties.get("notes") or properties.get("text") or ""
        return re.sub(r"\s+", " ", str(content).strip().casefold())

    @staticmethod
    def _row_to_node(row: sqlite3.Row, *, staged: bool) -> dict[str, Any]:
        return {
            "id": row["id"],
            "node_type": row["node_type"],
            "properties": json.loads(row["properties_json"]),
            "provenance": row["provenance"],
            "schema_version": row["schema_version"],
            "derived_from": json.loads(row["derived_from_json"]) if row["derived_from_json"] else None,
            "staged": staged,
            "created_at": row["created_at"],
        }
