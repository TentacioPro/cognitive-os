"""Deterministic agent orchestration boundary.

The registry and hook chain are intentionally provider-neutral. Each registered
agent enters through ``run_agent_step``; guardrail rejection prevents execution,
while timestamped local tracing records success and failure for later Opik/Arize
export.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agent_layer.guardrails import GuardrailOutcome
from app.telemetry.opik_tracing import trace_agent_call


SUB_AGENT_REGISTRY = {
    "journal-capture": {"reads": ["recent_context"], "writes_staged": ["Habit", "journal_node"]},
    "notebook-ingest": {"reads": ["uploaded_documents"], "writes_staged": ["Document", "Concept"]},
    "metacognitive-review": {"reads": ["Decision", "journal_history"], "writes_staged": ["inference"]},
    "ikigai": {
        "reads": ["ValueOrPrinciple", "CareerSkill", "FinancialGoal"],
        "writes_staged": ["inference"],
    },
    "narrative-fidelity": {"reads": ["journal_history"], "writes_staged": []},
    "resume-cover-letter": {"reads": ["CareerSkill"], "writes_staged": []},
}


@dataclass
class AgentStepResult:
    agent_name: str
    guardrail_outcome: GuardrailOutcome
    output: object = None
    rejected_reason: str = ""


def run_agent_step(
    agent_name: str,
    run_fn: Callable[[], object],
    guardrail_check: Callable[[], GuardrailOutcome],
    *,
    prompt_version: str = "v1",
) -> AgentStepResult:
    """Run a registered agent through guardrails and timestamped telemetry.

    Gateway RBAC remains the first external boundary. This function provides the
    agent-service defense-in-depth boundary and is the only route to staging.
    """

    if agent_name not in SUB_AGENT_REGISTRY:
        raise ValueError(f"unregistered agent: {agent_name} — add it to SUB_AGENT_REGISTRY first")

    with trace_agent_call(agent_name, prompt_version) as trace:
        outcome = guardrail_check()
        trace["guardrail_outcome"] = outcome.value
        if outcome == GuardrailOutcome.REJECT:
            trace["staged"] = False
            return AgentStepResult(
                agent_name=agent_name,
                guardrail_outcome=outcome,
                rejected_reason="guardrail rejected",
            )

        output = run_fn()
        trace["staged"] = True
        return AgentStepResult(agent_name=agent_name, guardrail_outcome=outcome, output=output)
