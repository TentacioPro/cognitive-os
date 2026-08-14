"""
Provenance enforcement — see /specs/provenance.spec.md.

This is the direct fix for the failure mode that motivated this project: content
drifting from "notes about real work" into "confident prose" with no marker of
where the line was crossed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Provenance(str, Enum):
    USER_ATTESTED = "user_attested"
    VERIFIED_ARTIFACT = "verified_artifact"
    STRUCTURALLY_EVIDENCED = "structurally_evidenced"
    AI_GENERATED_UNVERIFIED = "ai_generated_unverified"
    INFERENCE = "inference"


# Rank used to enforce "provenance only moves toward more trusted" (spec hard rule 2).
# Lower index = less trusted. INFERENCE is ranked separately since it's not a point on
# the same trust ladder (it's not a source-verification level; it's a derived claim).
_TRUST_ORDER = [
    Provenance.AI_GENERATED_UNVERIFIED,
    Provenance.STRUCTURALLY_EVIDENCED,
    Provenance.VERIFIED_ARTIFACT,
]

# Only these two are eligible for anything that leaves the system and reaches a third
# party (resume/cover-letter agent) — spec hard rule 3.
EXTERNAL_OUTPUT_ELIGIBLE = {Provenance.USER_ATTESTED, Provenance.VERIFIED_ARTIFACT}


class ProvenanceError(ValueError):
    """Raised whenever a write would violate a provenance hard rule."""


@dataclass(frozen=True)
class ProvenanceRecord:
    level: Provenance
    verified_by: Optional[str] = None  # e.g. "checked against commit abc123"
    derived_from: Optional[list[str]] = None  # required for INFERENCE (hard rule 4)
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.level == Provenance.INFERENCE and not self.derived_from:
            raise ProvenanceError(
                "INFERENCE nodes must carry a derived_from pointer (spec hard rule 4)"
            )


def validate_write(provenance: Optional[Provenance]) -> None:
    """Hard rule 1: no node ships without a provenance level."""
    if provenance is None:
        raise ProvenanceError("node write is missing a provenance level — no default exists")


def validate_transition(current: Provenance, proposed: Provenance, verified_by: Optional[str]) -> None:
    """Hard rule 2: provenance only moves toward more trusted, and only with a logged
    verification action — not automatically, not just because time passed."""
    if current == Provenance.INFERENCE or proposed == Provenance.INFERENCE:
        raise ProvenanceError("INFERENCE is not part of the verification trust ladder")

    if current not in _TRUST_ORDER or proposed not in _TRUST_ORDER:
        raise ProvenanceError(f"unrecognized provenance level in transition: {current} -> {proposed}")

    if _TRUST_ORDER.index(proposed) <= _TRUST_ORDER.index(current):
        raise ProvenanceError(
            f"cannot transition provenance backward or sideways: {current.value} -> {proposed.value}"
        )

    if not verified_by:
        raise ProvenanceError(
            "provenance upgrade requires a logged verification action (verified_by), "
            "not an unexplained transition"
        )


def validate_external_output(records: list[ProvenanceRecord]) -> list[ProvenanceRecord]:
    """Hard rule 3: resume/cover-letter (and anything reaching a third party) may only
    use user_attested or verified_artifact records. Returns the ineligible ones so the
    caller can report exactly what was excluded, rather than silently dropping content."""
    ineligible = [r for r in records if r.level not in EXTERNAL_OUTPUT_ELIGIBLE]
    return ineligible
