"""Tests for /specs/validation-guardrails.spec.md."""

from app.agent_layer.guardrails import (
    GuardrailOutcome,
    check_quantified_claims,
    check_provenance_downgrade,
    check_cross_document_consistency,
    check_external_output_eligible,
    check_status_claim_against_later_evidence,
)
from app.data_layer.provenance import Provenance


def test_unsupported_quantified_claim_is_flagged():
    output = "Reduced screening time by 70% through automation."
    source = "Built a resume screening module for the ATS."
    result = check_quantified_claims(output, source)
    assert result.outcome == GuardrailOutcome.FLAG
    assert "70%" in result.details["unsupported_numbers"]


def test_supported_quantified_claim_passes():
    output = "Achieved 96% accuracy on the test set."
    source = "Model evaluation results: 96% accuracy on held-out test set."
    result = check_quantified_claims(output, source)
    assert result.outcome == GuardrailOutcome.PASS


def test_provenance_downgrade_is_rejected():
    """Check 2 is a hard stop, not a flag."""
    result = check_provenance_downgrade(
        claimed=Provenance.VERIFIED_ARTIFACT,
        actual=Provenance.AI_GENERATED_UNVERIFIED,
    )
    assert result.outcome == GuardrailOutcome.REJECT


def test_matching_provenance_passes():
    result = check_provenance_downgrade(
        claimed=Provenance.STRUCTURALLY_EVIDENCED,
        actual=Provenance.STRUCTURALLY_EVIDENCED,
    )
    assert result.outcome == GuardrailOutcome.PASS


def test_same_origin_repetition_is_flagged_not_trusted():
    """Direct implementation of the resume/bio duplication finding: the same
    unverified claim appearing in two documents from one origin session is not
    independent corroboration."""
    result = check_cross_document_consistency(
        claim_sources=["ai_bio_generation_session_2025-10", "ai_bio_generation_session_2025-10"]
    )
    assert result.outcome == GuardrailOutcome.FLAG
    assert result.details["repeat_count"] == 2


def test_independently_sourced_claim_passes():
    result = check_cross_document_consistency(
        claim_sources=["maaxly_gcp_research_doc", "actual_git_commit_log"]
    )
    assert result.outcome == GuardrailOutcome.PASS


def test_ai_generated_unverified_cannot_reach_external_output():
    """Direct regression test: the bio doc's '70% reduction' style claims must
    never reach a resume, even if they're sitting right there in the graph."""
    result = check_external_output_eligible(Provenance.AI_GENERATED_UNVERIFIED)
    assert result.outcome == GuardrailOutcome.REJECT


def test_verified_artifact_can_reach_external_output():
    result = check_external_output_eligible(Provenance.VERIFIED_ARTIFACT)
    assert result.outcome == GuardrailOutcome.PASS


def test_maaxly_status_claim_regression():
    """The actual case from this conversation: resume (Oct 2025) claimed Maaxly
    was 'MVP Complete, Deployment Ready' on AWS; the real GCP research doc
    (Nov 2025) re-derived the cloud choice from scratch. This must always flag.
    """
    result = check_status_claim_against_later_evidence(
        status_claim="MVP Complete, Deployment Ready (AWS, $231/month)",
        status_date="2025-10",
        contradicting_doc_date="2025-11",
        contradicting_doc_summary="GCP $300 trial budget research re-deriving cloud choice from zero",
    )
    assert result.outcome == GuardrailOutcome.FLAG
    assert result.details["contradicting_date"] == "2025-11"


def test_status_claim_with_no_later_contradiction_passes():
    result = check_status_claim_against_later_evidence(
        status_claim="Deployed and stable",
        status_date="2025-11",
        contradicting_doc_date="2025-08",
        contradicting_doc_summary="earlier planning doc, superseded",
    )
    assert result.outcome == GuardrailOutcome.PASS
