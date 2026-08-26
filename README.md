# Cognitive OS

> **Cognitive OS is not an app. It is a data schema + pipeline spec + backup contract for personal knowledge management.**

This repository defines a small, portable operating system for tracking a life. It does not provide a frontend, backend server, or hosted product. It defines the records that a personal system must produce, the transformations that make those records useful, the stores that keep them durable, and the review artifact that turns them back into decisions.

A stranger should be able to read this file, connect the capture tools they already use, and build a compatible Cognitive OS without adopting a particular application framework.

## Architecture

The runtime is organized as **three implementation layers plus a review loop**:

```text
Capture  →  Extract  →  Store  →  Review
   ↑                              │
   └──────────── feedback ────────┘
```

Capture, Extract, and Store are the data path. Review is the human feedback loop: it reads the durable record, produces a weekly markdown report, and informs what should be captured next. Every stage must preserve the entry’s timestamp and provenance so that an interpretation can be checked against the original observation.

| Stage | Responsibility | Canonical tool | Repository contract |
| --- | --- | --- | --- |
| **Capture** | Accept observations with as little friction as possible. | **VoxLog** for voice, **Telegram** for text, **Logseq** for manual entry. | Capture may be messy, but it must retain the original text or transcript and an event timestamp. |
| **Extract** | Turn an observation into structured fields. | **Gemini Flash** for categorization and lightweight field extraction. | Extraction is an interpretation, not a replacement for the raw capture. Record the method and preserve the source. |
| **Store** | Make the structured entry queryable and recoverable. | **SQLite** locally, **JSONL** as the portable backup, **GitHub** as the archive. | A committed entry must exist in all three stores described by [`schemas/backup.contract.md`](schemas/backup.contract.md). |
| **Review** | Aggregate recent entries into a human-readable decision surface. | **Streamlit dashboard** for local exploration and a **weekly markdown export** for durable review. | Review is read-only with respect to source entries; its markdown output is a derived artifact. |

### Capture

Capture tools are adapters, not the system of record. VoxLog supplies a voice recording and/or transcript. Telegram supplies a text message. Logseq supplies a manually authored entry. An adapter should normalize all three into an input that contains at least `raw_text`, `timestamp`, and `source`.

The repository does not build those tools or their UIs. A personal implementation may use an export, webhook, folder watcher, or a one-off command, provided that the normalized input can be replayed without losing the original observation.

### Extract

The extraction step categorizes the capture into one or more life domains and fills the fields in [`schemas/entry.schema.json`](schemas/entry.schema.json). Gemini Flash is the reference categorizer because the task is lightweight classification and normalization rather than autonomous decision-making. The pipeline must keep the raw capture, the extracted entry, and the extraction method together. If Gemini is unavailable, a deterministic local fallback may create a reviewable entry rather than silently dropping data.

A useful extraction prompt asks for JSON only and supplies the active domain definitions from [`schemas/domain.schema.json`](schemas/domain.schema.json). It should request a conservative result: do not invent a value, unit, sentiment, or energy score that is not supported by the capture. Uncertain values should be `null` and reviewed by a person.

### Store

SQLite is the operational local store. It provides a simple query surface for the weekly review and can be copied as a local working database. JSONL is the portable, append-oriented backup: one complete entry per line, with no dependence on SQLite internals. GitHub is the archive and change history for the JSONL backup and schema changes.

The three stores have different jobs. SQLite optimizes for local queries, JSONL optimizes for inspection and recovery, and GitHub optimizes for versioned history. They are intentionally redundant. See the non-negotiable [backup contract](schemas/backup.contract.md).

### Review

The review loop has two outputs. A future Streamlit dashboard can query SQLite for trends and filtering, while [`pipelines/weekly-review.py`](pipelines/weekly-review.py) produces a plain markdown report that is readable without a running service. The weekly report should be committed or otherwise archived alongside the data when it is part of the personal record.

Review does not rewrite historical facts. It may contain observations, questions, and decisions, but those belong in a separate derived document or a new life entry.

## Canonical data model

A life entry is the atomic record. It describes one observation, measurement, or manually recorded event. The required fields are `domain`, `value`, `unit`, `notes`, `sentiment`, `energy`, and `timestamp`; optional provenance fields may be carried by implementations and are used by the reference pipeline.

A domain definition describes a category such as health, work, relationships, or learning. It includes a display `name`, an `icon`, a `color`, a JSON-encoded domain-specific schema in `schema_json`, and an `active` flag. The domain schema is deliberately data-driven: a personal Cognitive OS can add or retire domains without changing the pipeline’s core code.

The schemas are standard JSON Schema documents:

* [`schemas/entry.schema.json`](schemas/entry.schema.json) defines the life-entry envelope.
* [`schemas/domain.schema.json`](schemas/domain.schema.json) defines configurable domains.
* [`schemas/sample-entry.json`](schemas/sample-entry.json) is a valid example used by the local verification command.
* [`schemas/backup.contract.md`](schemas/backup.contract.md) defines the three-copy durability rule.

## Reference pipeline

The scripts in `pipelines/` are intentionally small, dependency-free Python programs. They are reference implementations, not a server or a product.

| Script | Purpose | Example |
| --- | --- | --- |
| [`voice-to-sqlite.py`](pipelines/voice-to-sqlite.py) | Normalize a VoxLog-style transcript, optionally call a categorizer, validate the entry, and write it to SQLite. | `python3 pipelines/voice-to-sqlite.py --db data/cognitive.db --text "Walked 30 minutes" --domain health --value 30 --unit minutes` |
| [`weekly-review.py`](pipelines/weekly-review.py) | Read SQLite and generate a markdown report for a chosen ISO week. | `python3 pipelines/weekly-review.py --db data/cognitive.db --output reviews/2026-W34.md --week 2026-W34` |
| [`jsonl-backup.py`](pipelines/jsonl-backup.py) | Validate that each JSONL line is parseable, schema-valid, and free of duplicate entry IDs. | `python3 pipelines/jsonl-backup.py --jsonl data/entries.jsonl --schema schemas/entry.schema.json` |

The reference pipeline uses only the Python standard library. If you want full JSON Schema validation in another implementation, use a standards-compliant validator and keep the same schema documents. The included scripts provide a strict enough local gate for this repository without requiring a package installation.

### Minimal local build

To create a compatible system from scratch:

1. Copy the `schemas/` and `pipelines/` directories into a new repository.
2. Define the domains that matter to you and store them as records conforming to `domain.schema.json`.
3. Export VoxLog, Telegram, and Logseq into a normalized capture format. Preserve the original text, source, and timestamp.
4. Run the extraction adapter. Gemini Flash may categorize the capture, but the adapter must emit valid JSON and retain the raw input.
5. Run `voice-to-sqlite.py` or an equivalent importer to write the validated entry to SQLite.
6. Append the exact same JSON object to JSONL and commit the JSONL file to GitHub. Do not create a second, slightly different representation.
7. Generate the weekly markdown report and inspect it as a human. Add corrections as new entries or derived review notes rather than mutating history silently.
8. Test recovery by rebuilding SQLite from JSONL. A backup is only real if it can be restored.

### Input and output conventions

The reference voice pipeline accepts either direct command-line fields or a JSON object/file containing `raw_text`, `timestamp`, `source`, and optional extracted fields. Its output is a canonical entry written to SQLite and, when `--jsonl` is supplied, appended as the same serialized object to JSONL. The script’s module docstring includes pseudocode before the executable implementation.

Timestamps must be ISO 8601 strings with a timezone offset or `Z`. Numeric fields use the units declared by the entry. The system does not assume that every domain is numeric: `value` may be a number, string, boolean, or structured JSON value, while `unit` may be `null` when no unit applies.

## Scope boundaries

This repository deliberately has **no new app, no UI, and no backend server**. The words “Streamlit dashboard” describe the intended review consumer, not an implementation shipped here. The existing `reference/scaffold/` tree is historical context from the initial repository commit; it is not part of this runtime-definition build and is not expanded by this work.

The system also does not prescribe a single AI provider API, Telegram bot deployment, VoxLog export format, or Logseq plugin. Those are adapters at the edges. Compatibility is defined by the schemas, provenance requirements, backup contract, and reproducible scripts.

## AgenticLoop operating method

Cognitive OS changes follow the six-step loop from [AgenticLoop](https://github.com/TentacioPro/AgenticLoop): **read → red → green → gate → record → update**.[1] Read the current schema, pipeline, and decision history before changing them. Red means define a failing validation or reproducible check. Green means make the smallest sufficient change. Gate means run the full local verification, not only the new check. Record means write the decision and rejected alternatives into repository history. Update means leave the next state discoverable from committed files rather than chat memory.

This repository applies that method proportionally. A schema change must include a sample or validator check. A pipeline change must include a runnable test entry and a backup-integrity check. A design change must be recorded in `DECISIONS.md`. The owner decides semantics, the agent implements the smallest diff, and the gate is the local verification output plus a clean Git status.

## References

[1]: https://github.com/TentacioPro/AgenticLoop "TentacioPro/AgenticLoop README and methodology reference"
