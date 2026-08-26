# Cognitive OS Test and Coverage Report

## Executive result

The repository contains two different surfaces. The new runtime-definition surface is documentation, JSON schemas, and local Python pipelines. The older `reference/scaffold/` tree contains a partially implemented backend, agent-service pure functions, and minimal web/mobile JSX placeholders. They must not be reported as one complete application.

A clean-room run from fresh temporary environments produced **25 passing Python tests**, **12 passing backend Jest tests**, and **7 passing runtime pipeline tests**. The current branch has no task files or task directory. The runtime-definition work has no browser-runnable UI, so UI, responsiveness, and frontend performance cannot honestly be marked as passing; the audit records those checks as not applicable or blocked by missing build/runtime surfaces.

| Area | Result | Evidence |
| --- | --- | --- |
| Runtime pipeline | Pass: 7/7 | `python3 -m unittest discover -s tests -p 'test_*.py' -v` |
| Legacy agent-service tests | Pass: 25/25 | Isolated virtual environment with `pytest -q` |
| Legacy backend tests | Pass: 12/12 | Fresh `npm ci` followed by Jest |
| JSON Schema sample | Pass | `schemas/sample-entry.json` validated against `schemas/entry.schema.json` with JSON Schema validation |
| JSONL corruption and duplicate checks | Pass | Valid fixture accepted; malformed JSON and duplicate IDs rejected with line diagnostics |
| Backend health smoke test | Pass | Local `GET /api/health` returned `{"status":"ok", ...}` |
| UI browser tests | Not runnable | No web `index.html`, build script, bundler config, or mobile app config exists |
| Responsiveness tests | Not applicable | No built page or navigation surface is available to exercise at viewport sizes |
| Frontend performance tests | Not applicable | No built frontend artifact exists |
| Backend local latency baseline | Informational only | 50 loopback health requests: average 0.000647 s, minimum 0.000504 s, maximum 0.001372 s |

The latency number is not a production performance claim. It measures an in-memory localhost scaffold health route with no database, authentication provider, agent call, network dependency, or realistic payload.

## Repository inventory

The repository has seven legacy specifications under `reference/scaffold/specs/`: agent layer, backend API, audit logging, data layer, provenance, RBAC, and validation/anti-hallucination guardrails. There are **no files under a `tasks/` directory and no task-named files** in the repository. The existing test inventory is three backend Jest suites and four Python test modules, supplemented on this branch by `tests/test_runtime_pipeline.py`.

| Spec | Current implementation | Test coverage | Status |
| --- | --- | --- | --- |
| `rbac.spec.md` | `backend/src/middleware/rbac.js` | 5 Jest tests | Implemented middleware rules pass; API role surface remains partial. |
| `audit-log.spec.md` | `backend/src/middleware/auditLog.js` | 4 Jest tests | In-memory append-only behavior and request IDs pass. Durable separate storage is not implemented. |
| `api.spec.md` | `backend/src/index.js` | 3 validation tests plus RBAC/audit integration | `/api/health`, `/api/journal`, and `/api/audit` exist; confirm, agent-invoke, and role-management routes are not implemented. |
| `validation-guardrails.spec.md` | `backend/src/middleware/validateRequest.js` and `agent-service/app/agent_layer/guardrails.py` | 3 Jest validation tests and 8 Python guardrail tests | Implemented pure checks pass. Full agent-output integration is not present. |
| `provenance.spec.md` | `agent-service/app/data_layer/provenance.py` | 9 Python tests | Enum, write validation, transitions, inference pointers, and external-output eligibility pass. |
| `data-layer.spec.md` | `dedup.py` plus partial `graph_store.py` | 4 dedup tests and 3 graph-store tests | Exact/semantic pure-function dedup passes. Kùzu/LanceDB persistence is intentionally unimplemented. |
| `agent-layer.spec.md` | Registry and hook-shaped orchestrator stub | No dedicated orchestrator or telemetry tests | Registry exists, but sub-agents, RBAC re-check integration, provenance wiring, and live Opik tracing are not implemented. |
| Cognitive OS runtime definition | `schemas/`, `pipelines/`, `README.md` | 7 clean-room runtime tests plus independent schema check | The requested documentation/schema/script surface passes its available local tests. |

## Clean-room commands

The legacy Python suite was run in a new temporary virtual environment using the committed `reference/scaffold/agent-service/requirements.txt`. The backend suite was run after deleting and recreating its installed dependencies with `npm ci`. The runtime suite uses only the Python standard library and creates temporary SQLite and JSONL files for every test.

```bash
# Runtime-definition tests
python3 -m unittest discover -s tests -p 'test_*.py' -v

# Legacy agent-service tests from a clean environment
python3 -m venv /tmp/cognitive-os-testenv
/tmp/cognitive-os-testenv/bin/pip install -r reference/scaffold/agent-service/requirements.txt
cd reference/scaffold/agent-service
PYTHONPATH=. /tmp/cognitive-os-testenv/bin/pytest -q

# Legacy backend tests from a clean dependency install
cd ../backend
npm ci
npm test -- --runInBand
```

The schema and pipeline checks can also be run directly:

```bash
python3 -m jsonschema -i schemas/sample-entry.json schemas/entry.schema.json
python3 pipelines/voice-to-sqlite.py \
  --input schemas/sample-entry.json \
  --db /tmp/cognitive-os.db \
  --jsonl /tmp/cognitive-os.jsonl
python3 pipelines/jsonl-backup.py \
  --jsonl /tmp/cognitive-os.jsonl \
  --schema schemas/entry.schema.json
python3 pipelines/weekly-review.py \
  --db /tmp/cognitive-os.db \
  --output /tmp/cognitive-os-weekly.md \
  --week 2026-W35
```

## UI, responsiveness, and performance findings

The repository contains `reference/scaffold/web/src/App.jsx` and `reference/scaffold/mobile/src/App.jsx`, but those are source placeholders rather than runnable applications. The web and mobile package manifests contain dependencies only; they do not define `start`, `build`, or test scripts. There is no web `index.html`, bundler configuration, Expo app configuration, or test runner for either client. A build probe therefore fails with `npm error Missing script: "build"`.

For that reason, no browser UI test, responsive viewport matrix, Lighthouse run, mobile device test, or frontend performance profile was claimed. There is no artifact to load into a browser. Adding such tests would require a separate, explicitly scoped application build, which would conflict with the runtime-definition branch’s documented anti-requirements.

The backend scaffold can be launched locally, and its public health endpoint was smoke-tested. A small loopback baseline over 50 requests completed with the timings shown above. This is useful only as a regression smoke signal. It cannot establish throughput, tail latency, database performance, agent latency, mobile performance, or production capacity because those components are absent.

## Clean-test conclusion

The implemented and testable functionality is green. The legacy scaffold’s incomplete areas are not hidden: Kùzu/LanceDB storage, concrete agents, live telemetry, most API routes, durable audit storage, and both client runtimes remain unimplemented or partial as explicitly described by their specs. A future application phase should add a buildable frontend and backend contract, then introduce browser automation, viewport snapshots, accessibility checks, mobile/device coverage, load testing, and performance budgets as separate gates.
