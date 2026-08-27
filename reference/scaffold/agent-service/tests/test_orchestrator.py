"""TDD coverage for the agent-layer registry and mandatory hook boundary."""

from app.agent_layer.guardrails import GuardrailOutcome
from app.agent_layer.orchestrator import SUB_AGENT_REGISTRY, run_agent_step


def test_registered_agent_runs_when_guardrail_passes():
    calls = []
    result = run_agent_step(
        "journal-capture",
        lambda: calls.append("run") or {"content": "captured"},
        lambda: GuardrailOutcome.PASS,
    )
    assert result.guardrail_outcome == GuardrailOutcome.PASS
    assert result.output == {"content": "captured"}
    assert calls == ["run"]


def test_rejected_agent_output_never_reaches_staging_callable():
    calls = []
    result = run_agent_step(
        "journal-capture",
        lambda: calls.append("run"),
        lambda: GuardrailOutcome.REJECT,
    )
    assert result.guardrail_outcome == GuardrailOutcome.REJECT
    assert result.output is None
    assert calls == []
    assert "rejected" in result.rejected_reason


def test_flagged_agent_output_is_returned_for_owner_review():
    result = run_agent_step(
        "metacognitive-review",
        lambda: {"needs_review": True},
        lambda: GuardrailOutcome.FLAG,
    )
    assert result.guardrail_outcome == GuardrailOutcome.FLAG
    assert result.output == {"needs_review": True}


def test_unregistered_agent_is_rejected_before_execution():
    try:
        run_agent_step("not-registered", lambda: None, lambda: GuardrailOutcome.PASS)
    except ValueError as exc:
        assert "unregistered agent" in str(exc)
    else:
        raise AssertionError("unregistered agent unexpectedly ran")


def test_registry_contains_every_specified_agent():
    assert {
        "journal-capture",
        "notebook-ingest",
        "metacognitive-review",
        "ikigai",
        "narrative-fidelity",
        "resume-cover-letter",
    }.issubset(SUB_AGENT_REGISTRY)
