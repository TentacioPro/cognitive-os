# Personal Cognitive OS — Architecture

Companion codebase to `personal_cognitive_os_plan_v5.md`. **Read that file and
`conversation_self_log.md` first** — they're the context this code implements.

## What this scaffold actually is (read before assuming more)

This is a real, structured starting point — not a finished product. In this pass:

- **Fully implemented and tested**: the cross-cutting concerns that every other module depends on
  — RBAC, audit logging, request validation, provenance enforcement, the anti-hallucination
  guardrail, and dedup. These are the parts that are dangerous to get wrong later, so they're built
  first and built solid.
- **Specified in full, scaffolded in structure, not yet implemented**: the individual agents
  (journal-capture, notebook-ingest, metacognitive-review, etc.), the graph/vector store
  integrations, the web and mobile UIs. Each has a spec file in `/specs` and a directory with a
  clear entry point, but the business logic inside is a stub with a `TODO` and a failing test —
  which is the correct TDD starting state, not an oversight.
- **Documented as an integration point, not built**: Shepherd (Stanford's agent-native git). It's
  early/alpha software with no stable installable package as of this writing. `VERSIONING.md`
  documents exactly how it plugs in and what to swap it for in the meantime.

Claiming this pass fully built a production system would be the exact failure mode this whole
project exists to catch. It doesn't. It builds the foundation correctly and honestly.

## Layout

```
personal-cognitive-os/
├── specs/                  # One spec file per module — read these before writing code in that module
├── backend/                # Node.js/Express — API gateway, RBAC, audit, validation. Serves web + mobile.
├── agent-service/          # Python/FastAPI — data layer, agent layer, guardrails, telemetry
├── web/                    # React (JSX) web client
├── mobile/                 # Expo/React Native mobile client
├── scripts/                # One-off scripts, incl. the polymath-os-android migration
├── docs/                   # ARCHITECTURE.md, VERSIONING.md
```

## Why one backend, two clients

Both `web/` and `mobile/` talk to the same `backend/` over REST. `backend/` is the only thing that
enforces RBAC and writes audit logs — neither client is trusted to do that itself. `backend/`
proxies AI-specific work to `agent-service/`, which is where the data layer, the agent
orchestration, and the guardrails actually live. See `docs/ARCHITECTURE.md` for the full request
flow.

## Running what's here

```bash
# Backend (Node/Express)
cd backend && npm install && npm test        # runs the RBAC/audit/validation test suite
cd backend && npm start                       # starts the API gateway

# Agent service (Python/FastAPI)
cd agent-service && pip install -r requirements.txt --break-system-packages
cd agent-service && pytest                     # runs the provenance/guardrail/dedup test suite
cd agent-service && uvicorn app.main:app --reload
```
