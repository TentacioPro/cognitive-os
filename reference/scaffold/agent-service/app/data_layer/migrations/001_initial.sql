-- Cognitive OS data layer migration 001: create separate staging and committed namespaces.
-- Apply in lexical order with a migration runner.

CREATE TABLE IF NOT EXISTS staged_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    derived_from_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS committed_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    properties_json TEXT NOT NULL,
    provenance TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    derived_from_json TEXT,
    created_at TEXT NOT NULL
);
