"""
Opik tracing hook — every agent call gets traced, per the plan doc's telemetry
requirement (and swappable for Arize Phoenix per the same doc).

STATUS: interface defined, not yet wired to a live Opik instance. Swap the body
of `trace_agent_call` for the real Opik/Arize SDK call when standing up
telemetry — nothing else in the codebase needs to change, since every caller
goes through this one function.
"""

from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def trace_agent_call(agent_name: str, prompt_version: str):
    """Wrap an agent call: records prompt version, latency, and (once wired to
    guardrails.py's return value) which guardrail checks ran and their outcomes.
    """
    # TODO: replace with `opik.track` or equivalent once self-hosted Opik is running.
    trace_record = {"agent_name": agent_name, "prompt_version": prompt_version}
    try:
        yield trace_record
    finally:
        # TODO: flush trace_record to Opik here.
        pass
