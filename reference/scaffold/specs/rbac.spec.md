# Spec: RBAC (Role-Based Access Control)

## Purpose
You and your agents both act on the same data. RBAC exists so an agent's mistake or a runaway loop
can't silently do something you didn't authorize — every write, everywhere, is checked against a
role's permissions first.

## Roles

| Role | Who/what holds it | Default permissions |
|---|---|---|
| `owner` | You, authenticated via your own login | Full read/write on all your data; the only role that can grant/revoke other roles |
| `agent:read_only` | Agents whose job is pure retrieval/analysis (metacognitive-review, ikigai) | Read all; write only to their own agent-output nodes (labeled `inference`) |
| `agent:staged_write` | Agents that ingest new content (journal-capture, notebook-ingest, CUA-importer) | Read all; write only to the **staging area**, never directly to committed graph nodes |
| `agent:service` | Internal service-to-service calls (backend → agent-service) | Scoped per-request to whatever role the originating request actually carries — never a blanket bypass |

## Hard rules

1. **No agent role can commit directly to the graph.** Every agent write lands in staging first;
   only `owner` confirmation (or an explicit, narrowly-scoped auto-commit rule you set — see the
   plan doc's confirmation-flow section) promotes it to committed.
2. **No role can escalate itself.** Only `owner` grants roles, and that action is itself audit-logged.
3. **Permission checks happen in `backend/`, not in the agent code.** An agent that "forgets" to
   check permissions still can't act outside them, because the gateway enforces it independently.

## Permission matrix (excerpt — full matrix lives in code as the source of truth)

| Action | `owner` | `agent:read_only` | `agent:staged_write` |
|---|---|---|---|
| Read any node | ✅ | ✅ | ✅ |
| Write to staging | ✅ | ❌ | ✅ |
| Commit staged → graph | ✅ | ❌ | ❌ |
| Modify `schema_version` | ✅ | ❌ | ❌ |
| Read audit log | ✅ | ❌ | ❌ |
| Grant/revoke roles | ✅ | ❌ | ❌ |

## Implementation
`backend/src/middleware/rbac.js` — see tests in `backend/src/__tests__/rbac.test.js` for the
enforced contract. The matrix above is implemented as data (`PERMISSIONS` object), not scattered
if/else logic, so adding a role or action is a data change, not a code change.
