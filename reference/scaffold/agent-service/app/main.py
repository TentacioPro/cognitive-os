"""Agent-service HTTP boundary.

Only the backend calls this service. The implementation is deterministic locally
so the trust boundary can be tested without a hosted model; a future deepagents
provider can replace the runner while preserving the registry and hooks.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agent_layer.guardrails import GuardrailOutcome
from app.agent_layer.orchestrator import SUB_AGENT_REGISTRY, run_agent_step
from app.telemetry.opik_tracing import trace_buffer

app = FastAPI(title="personal-cognitive-os agent-service")


@app.get("/health")
def health():
    return {"status": "ok"}


def _deterministic_agent_output(agent_name: str, payload: dict) -> dict:
    input_value = payload.get("input")
    if agent_name == "narrative-fidelity":
        return {"reflection": f"Review requested for: {input_value}", "writes_staged": []}
    if agent_name == "resume-cover-letter":
        return {"document": "Draft requires verified or user-attested source records.", "writes_staged": []}
    return {
        "agent": agent_name,
        "input": input_value,
        "provenance": "ai_generated_unverified",
        "writes_staged": SUB_AGENT_REGISTRY[agent_name]["writes_staged"],
    }


@app.post("/invoke")
def invoke(payload: dict):
    agent_name = payload.get("agent") or payload.get("agent_name")
    actor_role = payload.get("actor_role", "owner")
    if actor_role not in {"owner", "agent:service"}:
        raise HTTPException(status_code=403, detail="agent invocation requires owner or agent:service")
    if agent_name not in SUB_AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail="agent not registered")

    result = run_agent_step(
        agent_name,
        lambda: _deterministic_agent_output(agent_name, payload),
        lambda: GuardrailOutcome.PASS,
        prompt_version=payload.get("prompt_version", "v1"),
    )
    return {
        "agent": result.agent_name,
        "status": "accepted",
        "guardrail_outcome": result.guardrail_outcome.value,
        "output": result.output,
        "traces_available": len(trace_buffer()),
    }
