"""
Migration plan: polymath-os-android (MongoDB) -> this system's data layer (Kùzu + LanceDB).

Per plan doc Section 7 conclusion: this repo is Phase 1 of this project, not a reference
to rebuild from scratch. This script is a documented STUB — it lays out exactly what
each collection maps to and in what order, so the migration is a checklist, not a
from-memory guess, when it's actually run against the real Mongo instance.

Usage (once implemented): python scripts/migrate_polymath_os.py --mongo-uri <uri>
"""

from __future__ import annotations

import argparse

# Collection -> target node type mapping, per plan doc Section 7.
COLLECTION_MAPPING = {
    "activities": "Document",       # already has SHA-256 hash dedup — reuse the hash directly
    "journals": "journal_node",     # already tagged; carries straight into user_attested provenance
    "connections": "graph_edges",   # the "Dots to Connect" graph IS the knowledge graph — don't rebuild
    "ai_config": "n/a",             # provider config, not data — reconfigure fresh, don't migrate
}

MIGRATION_ORDER = [
    "activities",  # dedup hashes must exist before journals/connections reference them
    "journals",
    "connections",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()

    print(f"Migration plan (dry_run={args.dry_run}):")
    for collection in MIGRATION_ORDER:
        target = COLLECTION_MAPPING[collection]
        print(f"  {collection} -> {target}")
        # TODO: actual Motor/pymongo read + Kùzu/LanceDB write, once graph_store.py
        # and vector_store.py are wired to a live connection (see specs/data-layer.spec.md).
        # Every migrated node gets provenance=USER_ATTESTED (it was your own real data)
        # and schema_version=v1, per provenance.spec.md and data-layer.spec.md.

    print("\nNot yet executed — this is the documented plan, not a live migration.")


if __name__ == "__main__":
    main()
