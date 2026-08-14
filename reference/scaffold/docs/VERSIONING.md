# Versioning — "git-like" for both what the system makes and how it's built

Two separate things were asked for here; they need different tools.

## 1. Versioning what the system produces (graph state, agent runs)

This is Shepherd's actual use case (Stanford — reversible, fork/replay/revert execution traces,
covered in an earlier turn). **Honest status**: Shepherd is early/alpha research software with no
stable public package to `pip install` as of this writing. Don't build a hard dependency on it yet.

**What to do instead, now**: `data_layer` writes are already append-only with `schema_version`
(see `data-layer.spec.md`), which gives you the core property Shepherd would add — the ability to
see exactly what the graph looked like at any point in time — via ordinary versioned writes rather
than a specialized runtime. `agent-service/app/telemetry/` traces every agent run to Opik, which
covers "what did this run do" even without fork/replay.

**Integration point for later**: `agent_layer/orchestrator.py` wraps every sub-agent call in a
single function (`run_agent_step`). When Shepherd (or an equivalent) is ready to adopt, that's the
one place a checkpoint/fork call gets added — the rest of the codebase doesn't need to change.

## 2. Versioning the system's own build process (this codebase)

This is ordinary git, used deliberately:
- Every spec file in `/specs` is written *before* the code that implements it (TDD, see below),
  and both are committed together — a spec without a matching test is treated as incomplete.
- Migrations (`data_layer/migrations/`) are the same discipline applied to schema — each one is a
  committed, reversible script, never a manual edit to a running database.
- This is genuinely simpler than it needs a special tool for. The "AI-native git" tools discussed
  earlier solve problems at a different layer (agent execution state, harness self-improvement) —
  they're not a replacement for committing your own code carefully.

## TDD discipline enforced across this repo
Every module in `/specs` has a matching test file that exists *before* full implementation:
- Passing tests = the cross-cutting concerns (RBAC, audit, provenance, guardrails, dedup) — done
  this pass, and required to keep passing before anything else is added.
- Failing/`NotImplementedError` tests = the intentional TDD starting point for modules not yet
  built (graph_store, vector_store, individual sub-agents). A red test here is correct state, not
  a bug — it's the spec enforcing itself.
