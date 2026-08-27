# Cognitive OS Decisions

This file is append-only in spirit: add a dated decision rather than rewriting history when a contract changes.

## 2026-08-26 — Runtime definition instead of an application

**Decision:** Treat Cognitive OS as a data schema, pipeline specification, and backup contract. Add only `README.md`, `AGENTS.md`, `schemas/`, `pipelines/`, and this decision log to the runtime-definition surface.

**Rationale:** The requested system connects existing tools—VoxLog, Telegram, Logseq, Gemini Flash, SQLite, JSONL, GitHub, and review consumers—rather than replacing them. A UI, frontend, or backend would turn an interoperability contract into another app and violate the scope.

**Rejected alternatives:** Building a new capture app, adding a hosted API, or turning Streamlit into the primary product.

**Consequence:** Integrations remain adapters owned by the user. The repository’s reference scripts are local and replayable, while dashboard and bot implementations are intentionally outside this branch.

## 2026-08-26 — Three implementation layers plus review loop

**Decision:** Model the data path as Capture → Extract → Store and treat Review as the human feedback loop, while documenting all four stages together.

**Rationale:** Capture, extraction, and persistence are implementation boundaries. Review consumes durable data and feeds future capture habits but must not mutate source entries silently.

**Rejected alternatives:** Calling Review a fourth persistence layer or allowing reports to overwrite entries.

**Consequence:** Weekly markdown is a derived artifact; corrections are new entries or explicit migrations.

## 2026-08-26 — Canonical entry envelope with provenance

**Decision:** Require `domain`, `value`, `unit`, `notes`, `sentiment`, `energy`, and `timestamp`; allow stable IDs and provenance fields such as `source`, `raw_text`, and `extraction_method`.

**Rationale:** The required fields cover the requested life-tracking semantics. Provenance makes a model-derived categorization auditable and makes reprocessing possible.

**Rejected alternatives:** A domain-specific schema with no common envelope, or dropping raw transcript data after extraction.

**Consequence:** `value` remains flexible across numeric measurements and qualitative observations, while the envelope stays stable across tools.

## 2026-08-26 — SQLite + JSONL + Git durability contract

**Decision:** The same canonical JSON object must be present in SQLite, JSONL, and a Git archive. The reference importer writes SQLite and JSONL but does not invoke `git commit` automatically.

**Rationale:** SQLite is convenient for local queries, JSONL is portable for recovery, and Git supplies inspectable history. Git commits are human-visible archive decisions and should not be hidden inside an ingestion command.

**Rejected alternatives:** SQLite-only storage, a database dump as the only backup, or an importer that runs Git commands implicitly.

**Consequence:** Operators must commit the JSONL change as part of their archival workflow and periodically perform a restore drill.

## 2026-08-26 — Standard-library reference implementation with explicit Gemini opt-in

**Decision:** Keep the scripts dependency-free and provide a provider-agnostic Gemini Flash adapter that only runs when explicitly selected and configured.

**Rationale:** A stranger should be able to run the smoke test locally without API credentials, while a real VoxLog deployment can opt into model categorization without coupling the repository to a hosted backend.

**Rejected alternatives:** Making every local run require a model API, embedding credentials, or pretending that a network categorizer is available offline.

**Consequence:** The deterministic fallback creates a valid, reviewable entry and preserves uncertainty as `null`; the Gemini adapter requires `GEMINI_FLASH_ENDPOINT` and `GEMINI_FLASH_API_KEY`.

## 2026-08-26 — Branch base

**Decision:** Create `manus/runtime-def` from the repository’s current default tip and create a local `main` alias at that same commit.

**Rationale:** The remote exposes only `master` (`origin/master`) and has no `origin/main`. The requested branch therefore has an explicit local `main` base without rewriting or inventing remote history.

**Rejected alternatives:** Waiting for a nonexistent remote `main`, rebasing unrelated history, or force-pushing a new default branch.

**Consequence:** The branch is reproducibly based on commit `59631b6`; the remote default remains unchanged unless the owner later chooses to publish or rename it.

## References

* [AgenticLoop README and methodology](https://github.com/TentacioPro/AgenticLoop), consulted for the `read → red → green → gate → record → update` operating method.
