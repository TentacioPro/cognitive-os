# Spec: Agent Layer

## Orchestration
Root orchestrator built on `deepagents` (LangGraph), per the plan doc's stack decision. Each
domain agent (journal-capture, notebook-ingest, metacognitive-review, ikigai, dormant-skill,
narrative-fidelity, career-ops, curriculum, CUA-importer, resume/cover-letter) is a named
sub-agent with its own system prompt, tools, and — where cost matters — its own (possibly local,
Ollama-hosted) model, exactly as described in the plan doc's `deepagents` section.

## Every agent call, no exceptions, passes through:
1. RBAC check (does this agent's role permit this action) — enforced at the gateway, re-checked here
2. Guardrail check (`validation-guardrails.spec.md`) on the output before staging
3. Provenance tagging (`provenance.spec.md`) on anything written
4. Telemetry trace (Opik) — prompt version, tokens, latency, and which guardrail checks ran

## Sub-agent registry (spec only — each gets its own future spec file as it's built)
| Agent | Reads | Writes (to staging) |
|---|---|---|
| journal-capture | recent context | `Habit`, mood-tagged journal nodes |
| notebook-ingest | uploaded documents | `Document`, linked `Concept` nodes |
| metacognitive-review | `Decision`, journal history | `inference`-provenance analysis nodes |
| ikigai | `ValueOrPrinciple`, `CareerSkill`, `FinancialGoal` | `inference` overlap nodes |
| narrative-fidelity | journal/notebook history for a given period | nothing — read/reflect only |
| resume/cover-letter | `CareerSkill` (verified/attested only, per guardrail rule 4) | generated documents (not graph nodes) |

## Implementation
`agent-service/app/agent_layer/orchestrator.py` — root agent entry point, stubbed with the
sub-agent registry above and the mandatory pre/post hooks (RBAC re-check, guardrail, provenance,
telemetry) wired as middleware around every sub-agent call, so no individual agent can be added
later without automatically going through all four.
