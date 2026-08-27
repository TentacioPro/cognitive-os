# Cognitive OS

> **Cognitive OS is an operating system for personal knowledge management: a data schema + pipeline spec + backup contract, now paired with a local reference application.**

Cognitive OS connects low-friction capture to trustworthy review. The foundational contract remains portable: entries are timestamped, provenance-aware records; extraction is conservative; storage is redundant; review never mutates history silently. This repository now also ships the tested local web, mobile, backend, and agent-service reference surfaces that consume that contract.

## Architecture

```text
Capture → Extract → Store → Review
   ↑                              │
   └──────────── feedback ────────┘
```

| Stage | Canonical tools | Reference implementation |
| --- | --- | --- |
| **Capture** | VoxLog voice, Telegram text, Logseq manual entry | `pipelines/voice-to-sqlite.py`, web Capture screen, mobile Capture screen |
| **Extract** | Gemini Flash categorization | Conservative JSON extraction adapter with deterministic local fallback |
| **Store** | SQLite local, JSONL backup, GitHub archive | Backend `JournalStore`, graph-compatible staged/committed store, JSONL integrity checker |
| **Review** | Streamlit dashboard and weekly markdown export | Responsive web Review/System screens and `pipelines/weekly-review.py` |

The web and mobile clients use the same backend API contract. Clients never call the agent service directly. The backend owns authentication, RBAC, validation, audit logging, journal persistence, and optional proxying to the agent service.

## Repository map

| Path | Responsibility |
| --- | --- |
| `schemas/` | Canonical life-entry, domain, and backup contracts. |
| `pipelines/` | Dependency-free capture, review, and JSONL integrity scripts. |
| `reference/scaffold/backend/` | Express API, RBAC, request validation, timestamped audit persistence, and SQLite journal store. |
| `reference/scaffold/agent-service/` | FastAPI agent boundary, provenance/guardrail enforcement, graph/vector adapters, orchestrator, and local telemetry. |
| `reference/scaffold/web/` | Vite React dashboard with Capture, Review, System, navigation, responsive styling, and Playwright coverage. |
| `reference/scaffold/mobile/` | Expo React Native client with shared API flows and an Expo web-export path. |
| `tests/` | Runtime pipeline tests and the timestamped clean-room test runner. |
| `docs/tdd-matrix.md` | Requirement-to-test-to-implementation matrix for every gathered specification. |
| `docs/testing.md` | Latest test evidence, budgets, environment limitations, and reproduction commands. |
| `integrations/voxlog-bridge.md` | VoxLog normalization and provenance handoff contract. |

## Data contract

A life entry is the atomic record. The required fields are `domain`, `value`, `unit`, `notes`, `sentiment`, `energy`, and `timestamp`; the reference implementations additionally preserve raw capture text, source, provenance, and extraction metadata. See [`schemas/entry.schema.json`](schemas/entry.schema.json) and the valid [`schemas/sample-entry.json`](schemas/sample-entry.json).

The store has separate staging and committed namespaces. Agent or non-owner writes enter `staged_nodes`; only the owner can promote them into `committed_nodes`. Every write carries a schema version and provenance. Exact duplicates are surfaced before promotion. The vector adapter exposes thresholded cosine search and can be replaced by LanceDB without changing the contract.

Audit events are timestamped, append-only JSONL records in the backend’s local data directory. Every request receives a `request_id`; denied requests are recorded with a reason. The JSONL backup contract remains non-negotiable: every committed entry must exist in SQLite, JSONL, and Git.

## Running locally

The commands below intentionally use the repository’s existing scaffold rather than introducing a new framework project.

```bash
# Agent service
cd reference/scaffold/agent-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/uvicorn app.main:app --port 8001

# Backend, in another shell
cd reference/scaffold/backend
npm ci
AGENT_SERVICE_URL=http://127.0.0.1:8001 npm start

# Web, in another shell
cd reference/scaffold/web
npm ci
npm run dev -- --port 4173

# Mobile web export, in another shell
cd reference/scaffold/mobile
npm ci
npm run export:web
```

Open `http://127.0.0.1:4173`. The backend defaults to an on-disk SQLite database at `reference/scaffold/backend/data/cognitive-os.db`; set `COGNITIVE_OS_DB=:memory:` for ephemeral runs. Set `COGNITIVE_OS_AUDIT_LOG=off` to disable local audit persistence during a disposable test.

## Verification

The clean-room runner records UTC timestamps for every command and writes its log to `test-results/test-run-<timestamp>.log`:

```bash
python3 tests/run-all.py
```

The individual gates are also available:

```bash
# Runtime Python tests
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Agent-service tests
cd reference/scaffold/agent-service
PYTHONPATH=. .venv/bin/pytest -q

# Backend tests
cd ../backend
npm test -- --runInBand

# Web build and Chromium UI/responsive/performance tests
cd ../web
npm run build
npx playwright test --config=playwright.config.js

# Expo web export and mobile-export browser tests
cd ../mobile
npm run export:web
cd ../web
npx playwright test tests/mobile-web.spec.js --config=playwright.mobile.config.js
```

The native-device flow is committed at `reference/scaffold/mobile/tests/maestro/cognitive-os-flow.yaml`. Maestro and Android Debug Bridge are not installed in the current sandbox, so native Android/iOS execution must run in a device or emulator CI job. Playwright covers the exported mobile web bundle at phone and tablet sizes.

## Scope and provider boundaries

The reference application is local-first, not a hosted multi-user product. Authentication is represented by a local role header in the scaffold and must be replaced by real identity verification before exposure outside localhost. Agent invocation uses a deterministic local fallback when `AGENT_SERVICE_URL` is absent; when configured, the backend proxies to the FastAPI agent service. A hosted Gemini Flash or deepagents implementation can replace the deterministic provider without changing the schema or hook boundaries.

The Streamlit dashboard remains a compatible review consumer rather than a required runtime dependency; the shipped web dashboard provides the tested interactive review surface. VoxLog, Telegram, and Logseq remain external capture adapters, documented by their normalized handoff contracts rather than reimplemented here.

## AgenticLoop development method

Cognitive OS changes follow [AgenticLoop](https://github.com/TentacioPro/AgenticLoop): **read → red → green → gate → record → update**. Read the current schemas, specs, tests, and decision history. Red means add a failing test or reproducible check. Green means implement the smallest behavior that satisfies it. Gate means run all applicable suites, including browser and performance checks. Record means preserve decisions and timestamped evidence. Update means leave the next state discoverable from committed files rather than chat memory.

See [`AGENTS.md`](AGENTS.md), [`docs/tdd-matrix.md`](docs/tdd-matrix.md), and [`docs/testing.md`](docs/testing.md) for the repository-specific workflow.

## References

- [AgenticLoop](https://github.com/TentacioPro/AgenticLoop)
- [Entry schema](schemas/entry.schema.json)
- [Backup contract](schemas/backup.contract.md)
- [VoxLog bridge](integrations/voxlog-bridge.md)
