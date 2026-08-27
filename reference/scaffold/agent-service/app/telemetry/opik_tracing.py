"""Structured local tracing with an optional export seam for Opik/Arize.

Every agent call receives a timestamped trace record. The in-memory buffer is
intentionally small and deterministic for local tests; production can replace
``flush_trace`` with an Opik exporter without changing call sites.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator


_TRACE_BUFFER: list[dict] = []


def trace_buffer() -> list[dict]:
    """Return a defensive copy of completed traces."""

    return [dict(record) for record in _TRACE_BUFFER]


def clear_trace_buffer() -> None:
    _TRACE_BUFFER.clear()


def flush_trace(record: dict) -> None:
    """Store a completed trace locally; replace with an Opik exporter in production."""

    _TRACE_BUFFER.append(dict(record))


@contextmanager
def trace_agent_call(agent_name: str, prompt_version: str) -> Iterator[dict]:
    """Capture timestamp, prompt version, duration, result, and guardrail metadata."""

    started_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    started = time.perf_counter()
    trace_record = {
        "agent_name": agent_name,
        "prompt_version": prompt_version,
        "started_at": started_at,
        "status": "running",
    }
    try:
        yield trace_record
    except Exception as exc:
        trace_record.update(
            status="error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise
    else:
        trace_record["status"] = "success"
    finally:
        trace_record["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        trace_record["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        flush_trace(trace_record)
