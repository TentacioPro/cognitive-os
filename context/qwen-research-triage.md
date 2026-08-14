# Triage — Qwen Research Docs (July 2025 era) vs. the Current Plan

*Both source docs are provenance `ai_generated_unverified`: deep-research outputs, one of which
explicitly states it could not inspect the actual repositories and inferred patterns from best
practices. Ideas below were judged on merit against the plan doc's already-made stack decisions —
never on the docs' authority. Per guardrail check 3: these docs repeating each other is one
origin, not corroboration.*

Sources:
- `From_Forked_Repositories_to_a_Unified_Cognitive_Engine...` ("exocortex doc")
- `From_Disparate_Repositories_to_a_Unified_Interface...` ("error-handling doc")

---

## ADOPTED — fills a real gap in current specs

| Idea | Source | Gap it fills | Lands in |
|---|---|---|---|
| Structured error payload contract (`{code, details:[{path, message}]}`), backend → client, mapped to form fields or toasts | error-handling doc | `api.spec.md` has `request_id` but no error-shape contract; clients currently have no defined way to render a denial | Task 05; new `specs/modules/error-contract.spec.md` |
| Dual-layer validation: client-side schema validation for UX + backend re-validation as the only trusted layer | error-handling doc | Backend validation exists (`validateRequest.js`, FastAPI); client-side layer unspecced | Task 05 / Task 09 |
| Failure-scenario Playwright matrix: malformed input, network timeout, expired auth, backend validation error, success path — incl. transient-element (toast) assertions via stable `data-test-id` selectors | error-handling doc | polymath-os-android has 21 Playwright tests; failure scenarios not systematically covered | Task 09's TDD contract |
| Notification standards: severity levels, consistent visual language, ARIA live regions, persistent-until-dismissed for critical errors | error-handling doc | No notification spec exists; needed when extending the M3 UI | `specs/modules/notifications.spec.md`, Task 09 |
| "The Vault": automated, versioned, immutable backups + documented restore procedure ("fresh machine → restore → up") | exocortex doc | **Nothing in current specs covers backup/restore.** Biggest genuine find in either doc | Task 10; new `specs/modules/backup-restore.spec.md` |
| Offline-first client posture (local cache, sync on reconnect) | exocortex doc | Matters for the 100km-commute reality; unspecced | Design constraint noted in Task 09 |
| Mock-based testing of tool connectors (simulate tool failure → assert orchestrator error path → assert user-facing surface) | error-handling doc | agent-service orchestrator error paths untested | Task 08's TDD contract |

## ALREADY COVERED — no action, noted for the record

| Idea | Where it already lives |
|---|---|
| Observability on every agent call (doc suggests OpenTelemetry/Langfuse) | Opik tracing, `telemetry/opik_tracing.py`, agent-layer spec check 4 |
| Schema constraints at write time (doc suggests SHACL) | `validate_write` + required `schema_version`/`provenance` — lighter, same intent |
| At-rest encryption (doc suggests MongoDB CSFLE + Vault KMS) | `crypto.py` AES-256-GCM in polymath-os-android, tested |
| Auth (doc suggests Keycloak/OAuth) | `auth.py` JWT + Argon2id, tested |
| Firecrawl/Crawl4AI for scraping | Plan doc stack decision (self-log §4) |
| Ingestion pipeline: scrape → clean markdown → embed → graph | Plan's multi-modal import + staging-confirmation flow, with the added provenance layer the doc lacks |

## REJECTED — with reasons (recorded so no future session re-litigates them)

| Idea | Why rejected |
|---|---|
| Apache Kafka as the "central nervous system" | Single-user local system on i5/16GB/RTX-3050-4GB. Kafka's own doc admits RAM tuning pain. Append-only writes + audit log + Opik traces already provide the event-history properties. If async decoupling is ever needed: a job queue (e.g. Redis + worker), not a broker cluster |
| Neo4j + RDF/OWL/SHACL semantic-web stack | Contradicts the made decision: Kùzu + LanceDB. Full W3C tooling is enterprise-interop machinery; a personal graph needs schema discipline, which exists |
| MongoDB Enterprise CSFLE + HashiCorp Vault | Requires a paid Enterprise license; the plan is migrating OFF Mongo (Task 06). Existing AES-256-GCM covers at-rest encryption |
| "Full integration of all ten forked repos from day one" (Plane, AFFiNE, Inbox-Zero, Zed, Linkwarden, Qubic...) | The exact opposite of the corrected plan's "one source of truth per concern." Individual tools may be adopted later as MCP integrations, one at a time, behind a task spec |
| Qubic edge-node compute offload | Speculative; no current workload justifies it |
| Always-on voice engine (WebRTC + Whisper), voice cloning | Deferred, not rejected in principle — the plan already documents voice as a future integration point (self-log §2). Not before core loop works |
| Keycloak IAM | A second auth system next to a tested one = the parallel-implementation failure mode by definition |
