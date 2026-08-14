# Spec: Backend API (web + mobile shared contract)

Both `web/` and `mobile/` are thin clients against this single contract — no client-specific
endpoints, so behavior can never silently diverge between platforms.

## Middleware order (every route, no exceptions)
`authenticate` → `rbac` → `validateRequest` → `auditLog` → route handler → `auditLog` (result)

## Core routes (this pass: scaffolded + middleware chain tested; handlers are TODO stubs)

| Route | Method | RBAC action | Notes |
|---|---|---|---|
| `/api/health` | GET | none (public) | liveness check, no auth required |
| `/api/journal` | POST | `journal:write` | stages a journal entry, per confirmation flow |
| `/api/journal/:id/confirm` | POST | `journal:write`, `owner` only | promotes staged → committed |
| `/api/agents/:name/invoke` | POST | `agent:invoke` | proxies to agent-service, identity forwarded |
| `/api/audit` | GET | `owner` only | read audit log — see `audit-log.spec.md` |
| `/api/roles` | POST | `owner` only | grant/revoke — see `rbac.spec.md` hard rule 2 |

## Contract rule
Every response includes `request_id`, so a client-reported issue can be traced through the audit
log and the Opik trace without ambiguity.
