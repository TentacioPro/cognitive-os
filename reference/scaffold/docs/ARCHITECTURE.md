# Architecture — End to End

## Layers, and what crosses between them

```
┌─────────────┐     ┌─────────────┐
│  web/ (JSX) │     │ mobile/(RN) │
└──────┬──────┘     └──────┬──────┘
       │      HTTPS + JWT         │
       └───────────┬──────────────┘
                    ▼
        ┌───────────────────────┐
        │   backend/ (Express)  │   ← the ONLY thing web/mobile talk to
        │  - auth                │
        │  - RBAC middleware     │
        │  - audit log middleware│
        │  - request validation  │
        └───────────┬────────────┘
                     │  internal HTTP, service-to-service auth
                     ▼
        ┌───────────────────────┐
        │ agent-service/ (FastAPI)│
        │  - agent_layer/         │  ← LangGraph deepagents orchestrator + guardrails
        │  - data_layer/          │  ← Kùzu (graph) + LanceDB (vectors) + provenance
        │  - telemetry/           │  ← Opik/Arize tracing on every call
        └───────────┬────────────┘
                     ▼
        Kùzu graph · LanceDB · local filesystem (versioned)
```

## Why the split

- **`backend/` (Node/Express) is the trust boundary.** Every request from web or mobile passes
  through auth → RBAC → audit-log → validation, in that order, before anything else happens. This
  is deliberately in Node/Express, not Python, because it's the layer product-facing clients talk
  to directly, and keeping it separate from the agent/data layer means a bug in an experimental
  agent can never accidentally bypass RBAC or skip an audit entry — the backend enforces those
  regardless of what the agent service does internally.
- **`agent-service/` (Python/FastAPI) is where DSPy, LangGraph/deepagents, Kùzu, and LanceDB
  actually live**, per the stack decision in the plan doc. It never talks to web/mobile directly —
  only to `backend/`, over an internal service call that still carries the authenticated
  identity (user vs. agent — see `specs/rbac.spec.md`) so the data layer can enforce row-level
  provenance and access rules independently of the gateway.

## Request flow example: journal entry via mobile

1. Mobile app sends `POST /api/journal` with JWT.
2. `backend/` — `authenticate` → `rbac` (does this identity have `journal:write`?) → `validate`
   (schema-check the body) → `auditLog` (record the attempt) → proxy to `agent-service`.
3. `agent-service/agent_layer` runs the journal-capture agent, which stages the entry
   (per the confirmation-before-write flow in the plan doc) rather than committing immediately.
4. `data_layer` writes the staged entry with `provenance: user_attested` once confirmed, versioned
   with `schema_version`.
5. `telemetry` logs the full agent trace (prompt version, tokens, latency) to Opik.
6. `backend/` writes a second audit entry: what was actually committed, by which identity.

Every step above has a corresponding spec in `/specs` and, where implemented, a test in
`__tests__/` or `tests/`.
