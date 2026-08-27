# Cognitive OS Test and Coverage Report

## Executive result

The repository now contains a functional local reference application across the data layer, agent service, backend API, web client, and Expo mobile client. The implementation was developed red → green: new tests were added for the unresolved behavior before the graph store, vector store, orchestrator, durable audit log, API flows, and client surfaces were completed.

The timestamped clean-room runner completed with **zero failures** at `2026-08-27T00:36:16Z`. The versioned evidence note is [`docs/test-runs/20260827T003616Z.md`](test-runs/20260827T003616Z.md); the raw log is generated under the ignored `test-results/` directory for each run.

| Suite | Result | Scope |
| --- | --- | --- |
| Runtime Python unittest | **7 passed** | Canonical entry ingestion, SQLite/JSONL durability, weekly review, schema rejection, malformed JSON, and duplicate IDs. |
| Agent-service pytest | **40 passed** | Provenance, guardrails, dedup, distinct graph staging/commit/rollback, exact duplicate detection, read scoping, vector search, orchestrator registry, guardrail hook, and trace behavior. |
| Backend Jest | **18 passed** | Request validation, RBAC, timestamped append-only audit, journal staging/confirmation, domains, roles, API envelopes, persistent journal store, and optional agent-service proxy. |
| Web production build | **Passed** | Vite bundle generated successfully. |
| Web Playwright Chromium | **7 passed** | Dashboard, navigation, capture → review → confirmation, system/audit page, phone/tablet/desktop overflow, and local performance budgets. |
| Mobile Expo web export | **Passed** | Expo classic AppEntry bundle generated successfully. |
| Mobile-export Playwright | **2 passed** | Phone 390×844 and tablet 768×1024 load, capture navigation, editable observation field, and horizontal-overflow checks. |
| Maestro native device flow | **Not run in sandbox** | A committed flow exists, but Maestro and Android Debug Bridge are unavailable here. |

## Specification coverage

The repository contains seven legacy specifications under `reference/scaffold/specs/` and no user task directory. The following table maps each specification to its implementation and current gate.

| Spec | Implementation | Coverage | Status |
| --- | --- | --- | --- |
| `rbac.spec.md` | `backend/src/middleware/rbac.js` plus `GraphStore` actor-role checks | Backend authorization tests and data-layer read-scope tests | **Implemented locally**; identity is still a local role-header stub. |
| `audit-log.spec.md` | `backend/src/middleware/auditLog.js` | Denied requests, request IDs, immutability, append-only records, JSONL persistence path | **Implemented locally**; separate durable audit file, not graph storage. |
| `api.spec.md` | `backend/src/index.js` | Health, journal POST/GET, confirmation, agent invoke, audit, domains, roles, validation envelopes | **Implemented locally**; agent route proxies when `AGENT_SERVICE_URL` is configured. |
| `validation-guardrails.spec.md` | Backend request validator plus agent-service guardrails | Existing guardrail tests and orchestrator pass/flag/reject tests | **Implemented at the local contract boundary**. |
| `provenance.spec.md` | `agent-service/app/data_layer/provenance.py` and GraphStore | Existing provenance tests plus graph write and inference-pointer tests | **Implemented**. |
| `data-layer.spec.md` | `GraphStore`, `VectorStore`, migrations, dedup helpers | Distinct staged/committed tables, exact duplicate gate, vector threshold search, RBAC-scoped reads | **Implemented as local compatibility adapters**; not live Kùzu/LanceDB. |
| `agent-layer.spec.md` | `agent_layer/orchestrator.py`, telemetry, FastAPI `/invoke` | Registry, guardrail boundary, timestamps, local agent invocation and backend proxy smoke test | **Implemented as deterministic local agent boundary**; hosted deepagents/model provider remains an adapter seam. |

The runtime-definition contract remains covered by `schemas/`, `pipelines/`, and `tests/test_runtime_pipeline.py`. VoxLog mapping is documented in [`integrations/voxlog-bridge.md`](../integrations/voxlog-bridge.md), and the local app’s capture screens use the same normalized journal contract.

## UI, responsiveness, and navigation

The web client is a buildable Vite React application. It provides a dashboard overview, capture form, review/confirmation flow, system architecture view, audit trace, API health state, error banner, empty states, keyboard-visible focus states, and hash-based navigation with clear escape routes. The mobile client is an Expo React Native application with the same Capture, Review, Overview, and System flows, safe-area-aware layout, touch feedback, horizontal domain chips, and a tested Expo web export.

Playwright tests exercise the actual built client paths, not static snapshots of source. The web responsive suite runs at 375×812, 768×1024, and 1440×900. It checks navigation reachability, form editability, and `document.documentElement.scrollWidth <= window.innerWidth + 1`. The mobile-export suite runs at 390×844 and 768×1024 and checks the same invariants against the Expo-generated web bundle.

The native flow is defined at `reference/scaffold/mobile/tests/maestro/cognitive-os-flow.yaml`. It could not be executed in this sandbox because `maestro`, `adb`, and an Android/iOS emulator are unavailable. A device CI job must run that flow before claiming native Android/iOS coverage.

## Performance gates

`reference/scaffold/web/tests/performance.spec.js` sets local regression budgets of less than 2,000 ms from navigation start to the dashboard heading becoming visible, less than 500,000 transferred JavaScript bytes, and fewer than three long tasks in the page performance buffer. The current Chromium run passed these budgets. The Vite production bundle was approximately 156 kB JavaScript and 13 kB CSS before compression.

The backend’s local health route and the end-to-end agent proxy were also smoke-tested. These are development regression signals, not production capacity claims. There is no representative multi-user load profile, hosted database, external Gemini latency, or mobile-device performance trace in this sandbox.

## Timestamped test logging

Run the complete matrix from the repository root:

```bash
python3 tests/run-all.py
```

The runner records the UTC timestamp, runtime versions, tool availability, command, stdout/stderr, pass/fail state, and final summary to `test-results/test-run-<timestamp>.log`. It explicitly reports Maestro as not applicable when the executable is absent instead of silently skipping the native requirement.

The individual gates can be run as follows:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v

cd reference/scaffold/agent-service
PYTHONPATH=. /tmp/cognitive-os-testenv/bin/pytest -q

cd ../backend
npm ci
npm test -- --runInBand

cd ../web
npm ci
npm run build
npx playwright test --config=playwright.config.js

cd ../mobile
npm ci
npm run export:web

cd ../web
npx playwright test tests/mobile-web.spec.js --config=playwright.mobile.config.js
```

## Remaining production blockers

The application is functional locally but is not yet a production deployment. Local role headers must be replaced with real authentication and session verification. The deterministic agent implementation must be replaced or augmented with the configured Gemini/deepagents provider and external credential handling. The local graph/vector adapters need production Kùzu/LanceDB adapters if those vendors remain a hard requirement. VoxLog, Telegram, and Logseq need live connectors with real replay and retry behavior. Finally, native Maestro execution must run on Android/iOS device infrastructure.
