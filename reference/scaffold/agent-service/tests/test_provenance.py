"""Tests for /specs/provenance.spec.md — every hard rule gets a direct test."""

import pytest

from app.data_layer.provenance import (
    Provenance,
    ProvenanceError,
    ProvenanceRecord,
    validate_write,
    validate_transition,
    validate_external_output,
)


def test_write_missing_provenance_is_rejected():
    """Hard rule 1: no node ships without a provenance level."""
    with pytest.raises(ProvenanceError):
        validate_write(None)


def test_write_with_provenance_is_accepted():
    validate_write(Provenance.USER_ATTESTED)  # should not raise


def test_backward_transition_is_rejected():
    """Hard rule 2: provenance only moves toward more trusted."""
    with pytest.raises(ProvenanceError):
        validate_transition(
            current=Provenance.VERIFIED_ARTIFACT,
            proposed=Provenance.AI_GENERATED_UNVERIFIED,
            verified_by="someone said so",
        )


def test_transition_without_verification_is_rejected():
    """Hard rule 2: upgrades require a logged verification action, not just time passing."""
    with pytest.raises(ProvenanceError):
        validate_transition(
            current=Provenance.AI_GENERATED_UNVERIFIED,
            proposed=Provenance.VERIFIED_ARTIFACT,
            verified_by=None,
        )


def test_valid_upgrade_with_verification_succeeds():
    validate_transition(
        current=Provenance.AI_GENERATED_UNVERIFIED,
        proposed=Provenance.STRUCTURALLY_EVIDENCED,
        verified_by="found matching file tree in Master_Projects_Compiled.html",
    )  # should not raise


def test_inference_node_without_derived_from_is_rejected():
    """Hard rule 4: INFERENCE nodes always carry a derived_from pointer."""
    with pytest.raises(ProvenanceError):
        ProvenanceRecord(level=Provenance.INFERENCE, derived_from=None)


def test_inference_node_with_derived_from_is_accepted():
    record = ProvenanceRecord(level=Provenance.INFERENCE, derived_from=["node_123", "node_456"])
    assert record.derived_from == ["node_123", "node_456"]


def test_external_output_excludes_unverified_content():
    """Hard rule 3: resume/cover-letter agent only uses user_attested / verified_artifact.

    This is a direct regression test for the real Maaxly bio-doc percentage claims —
    those are ai_generated_unverified and must never reach a resume output.
    """
    records = [
        ProvenanceRecord(level=Provenance.VERIFIED_ARTIFACT),   # e.g. AWS cert
        ProvenanceRecord(level=Provenance.USER_ATTESTED),       # e.g. journal-confirmed fact
        ProvenanceRecord(level=Provenance.AI_GENERATED_UNVERIFIED),  # e.g. "70% reduction" claim
        ProvenanceRecord(level=Provenance.STRUCTURALLY_EVIDENCED),   # e.g. project w/ file tree
    ]
    ineligible = validate_external_output(records)
    assert len(ineligible) == 2
    assert all(
        r.level in (Provenance.AI_GENERATED_UNVERIFIED, Provenance.STRUCTURALLY_EVIDENCED)
        for r in ineligible
    )
