"""
Anti-hallucination guardrails — see /specs/validation-guardrails.spec.md.

Runs on every agent output before it's allowed into staging. Distinct from
backend/'s request validation: that checks "is this well-formed", this checks
"is this making a claim it can't support".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.data_layer.provenance import Provenance


class GuardrailOutcome(str, Enum):
    PASS = "pass"
    FLAG = "flag"     # surfaced to the user for review, not auto-rejected
    REJECT = "reject"  # hard stop, logged as a denial


@dataclass
class GuardrailResult:
    outcome: GuardrailOutcome
    reason: str = ""
    details: dict = field(default_factory=dict)


_NUMBER_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d+)?%|\$[\d,]+(?:\.\d+)?|\b\d{2,}\+?\s?(?:users|concurrent)")


def check_quantified_claims(output_text: str, source_text: str) -> GuardrailResult:
    """Check 1: does the output contain a specific number not present in / derivable
    from its source? Flags (doesn't reject) — surfaced as a named discrepancy."""
    output_numbers = set(_NUMBER_PATTERN.findall(output_text))
    source_numbers = set(_NUMBER_PATTERN.findall(source_text))
    unsupported = output_numbers - source_numbers
    if unsupported:
        return GuardrailResult(
            outcome=GuardrailOutcome.FLAG,
            reason="output contains quantified claims not found in source material",
            details={"unsupported_numbers": sorted(unsupported)},
        )
    return GuardrailResult(outcome=GuardrailOutcome.PASS)


def check_provenance_downgrade(claimed: Provenance, actual: Provenance) -> GuardrailResult:
    """Check 2: does the output claim a higher provenance than its source supports?
    This one is a hard stop, not a flag."""
    order = [
        Provenance.AI_GENERATED_UNVERIFIED,
        Provenance.STRUCTURALLY_EVIDENCED,
        Provenance.VERIFIED_ARTIFACT,
    ]
    if claimed in order and actual in order and order.index(claimed) > order.index(actual):
        return GuardrailResult(
            outcome=GuardrailOutcome.REJECT,
            reason=f"output claims provenance '{claimed.value}' but source only supports '{actual.value}'",
        )
    return GuardrailResult(outcome=GuardrailOutcome.PASS)


def check_cross_document_consistency(claim_sources: list[str]) -> GuardrailResult:
    """Check 3: repetition across documents from the SAME origin session is one claim,
    not independent corroboration. This is a direct implementation of the resume/bio
    duplication finding from this conversation."""
    unique_origins = set(claim_sources)
    if len(claim_sources) > 1 and len(unique_origins) == 1:
        return GuardrailResult(
            outcome=GuardrailOutcome.FLAG,
            reason="claim repeated across documents but traces to a single origin — not independently verified",
            details={"origin": next(iter(unique_origins)), "repeat_count": len(claim_sources)},
        )
    return GuardrailResult(outcome=GuardrailOutcome.PASS)


def check_external_output_eligible(provenance: Provenance) -> GuardrailResult:
    """Check 4: anything destined for the resume/cover-letter agent must be
    user_attested or verified_artifact. No exceptions."""
    from app.data_layer.provenance import EXTERNAL_OUTPUT_ELIGIBLE

    if provenance not in EXTERNAL_OUTPUT_ELIGIBLE:
        return GuardrailResult(
            outcome=GuardrailOutcome.REJECT,
            reason=f"provenance '{provenance.value}' is not eligible for external output",
        )
    return GuardrailResult(outcome=GuardrailOutcome.PASS)


def check_status_claim_against_later_evidence(
    status_claim: str, status_date: str, contradicting_doc_date: str, contradicting_doc_summary: str
) -> GuardrailResult:
    """Check for 'Current Status'-style claims contradicted by a LATER document.

    Direct implementation of the real Maaxly finding: a resume dated October 2025
    claimed 'MVP Complete, Deployment Ready' on AWS, while a November 2025 document
    re-derived the entire cloud decision from scratch on GCP. A status claim
    contradicted by later, more specific evidence should flag, not silently stand.
    """
    if contradicting_doc_date > status_date:
        return GuardrailResult(
            outcome=GuardrailOutcome.FLAG,
            reason="status claim is contradicted by a later, more specific document",
            details={
                "claim": status_claim,
                "claim_date": status_date,
                "contradicting_date": contradicting_doc_date,
                "contradicting_summary": contradicting_doc_summary,
            },
        )
    return GuardrailResult(outcome=GuardrailOutcome.PASS)
