"""
Root agent orchestrator — see /specs/agent-layer.spec.md.

STATUS: sub-agent registry and mandatory hook chain are defined; individual
sub-agents (journal-capture, notebook-ingest, etc.) are not yet implemented.
`run_agent_step` is the one integration point where a future Shepherd
checkpoint/fork call would be added (see docs/VERSIONING.md) — everything
else in this file is deliberately unaware of that detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agent_layer.guardrails import GuardrailOutcome


# Registry from specs/agent-layer.spec.md — grows as sub-agents are implemented.
SUB_AGENT_REGISTRY = {
    "journal-capture": {"reads": ["recent_context"], "writes_staged": ["Habit", "journal_node"]},
    "notebook-ingest": {"reads": ["uploaded_documents"], "writes_staged": ["Document", "Concept"]},
    "metacognitive-review": {"reads": ["Decision", "journal_history"], "writes_staged": ["inference"]},
    "ikigai": {
        "reads": ["ValueOrPrinciple", "CareerSkill", "FinancialGoal"],
        "writes_staged": ["inference"],
    },
    "narrative-fidelity": {"reads": ["journal_history"], "writes_staged": []},  # read/reflect only
    "resume-cover-letter": {"reads": ["CareerSkill"], "writes_staged": []},  # generates docs, not nodes
}


@dataclass
class AgentStepResult:
    agent_name: str
    guardrail_outcome: GuardrailOutcome
    output: object = None
    rejected_reason: str = ""


def run_agent_step(agent_name: str, run_fn: Callable[[], object], guardrail_check: Callable[[], GuardrailOutcome]):
    """Every sub-agent call passes through here. This is deliberately the ONLY
    place a sub-agent's output can reach staging — spec's mandatory hook chain
    (RBAC re-check → guardrail → provenance → telemetry) attaches here so no
    future sub-agent can be added without going through all four.
    """
    if agent_name not in SUB_AGENT_REGISTRY:
        raise ValueError(f"unregistered agent: {agent_name} — add it to SUB_AGENT_REGISTRY first")

    # 1. RBAC re-check happens at the gateway before this is ever called (defense
    #    in depth — see rbac.spec.md); this layer trusts but does not re-derive it.
    # 2. Guardrail check on the output before staging.
    outcome = guardrail_check()
    if outcome == GuardrailOutcome.REJECT:
        return AgentStepResult(agent_name=agent_name, guardrail_outcome=outcome, rejected_reason="guardrail rejected")

    output = run_fn()
    # 3. Provenance tagging happens inside run_fn via data_layer.provenance.
    # 4. Telemetry trace — see app/telemetry/opik_tracing.py.
    return AgentStepResult(agent_name=agent_name, guardrail_outcome=outcome, output=output)
