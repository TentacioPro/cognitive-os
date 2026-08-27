# Cognitive OS Backup Contract

> **Every entry must exist in 3 places: SQLite, JSONL, Git.**

This contract is the durability boundary for a Cognitive OS implementation. An entry is not considered backed up because it exists in one local database, in an uncommitted text file, or in a chat transcript. The same canonical JSON object must be represented in all three stores.

| Copy | Role | Required condition |
| --- | --- | --- |
| **SQLite** | Local operational store used for queries and weekly review generation. | The entry is inserted into the local `entries` table with its stable ID and timestamp. |
| **JSONL** | Portable, line-oriented recovery source. | The exact canonical entry is serialized as one complete JSON object on one line, with no duplicate IDs. |
| **Git** | Versioned archive and off-device history. | The JSONL file and any associated schema changes are committed to a Git repository with an identifiable commit. |

## Write protocol

A pipeline must validate an entry before writing it. It should then write the entry to SQLite, append the same object to JSONL, and commit the JSONL change to Git as part of the caller’s archival workflow. The reference voice pipeline performs the first two actions when `--jsonl` is supplied; it intentionally does not run `git commit` implicitly because commit boundaries are human-visible archival decisions.

The JSONL line is the portable source of truth for restoring SQLite. Do not hand-edit a single copy to “fix” drift. If a correction is needed, create a new entry or perform an explicit migration that updates all copies and records the decision.

## Integrity rules

Every JSONL line must be valid JSON and must validate against `schemas/entry.schema.json`. Each entry must have a unique `id` when IDs are present. Lines must not be silently skipped, truncated, or replaced with error messages. A validator must report the line number for malformed or invalid records and exit non-zero if any record fails.

The JSONL file may be split by date or domain, but a recovery procedure must be able to enumerate every file and reconstruct the same logical entry set. A Git archive should keep the schema version and the data changes together so that an older commit remains interpretable.

## Recovery test

A system satisfies this contract only if it can pass a restore drill:

1. Clone the Git archive into a clean directory.
2. Validate every JSONL line against the committed schema.
3. Create a new SQLite database using the pipeline’s table definition.
4. Insert each validated JSONL object into the new database.
5. Compare the restored IDs and canonical fields with the archived JSONL objects.
6. Record the drill date and result in the project’s decision or operations log.

This contract protects against a corrupted SQLite file, an accidental local deletion, and an unreviewed data mutation. It does not replace encrypted off-site storage or a separate secrets-management policy for any capture-tool credentials.
