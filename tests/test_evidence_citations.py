import pytest

from aegis.investigation.citations import (
    CitationValidationError,
    ClaimType,
    EvidenceCitationValidator,
    InvestigativeClaim,
)
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind


def bundle() -> EvidenceBundle:
    return EvidenceBundle(
        "inc-1", "1.0",
        (
            EvidenceItem("alert:a1", EvidenceKind.ALERT, "test", "2026-07-08T10:00:00+00:00", {}),
            EvidenceItem("asset:plc-1", EvidenceKind.ASSET, "test", None, {}),
        ),
    )


def test_accepts_claim_when_all_citations_resolve() -> None:
    claim = InvestigativeClaim(
        "claim-1", "The alert was observed on PLC 1.", ClaimType.OBSERVATION,
        ("alert:a1", "asset:plc-1"),
    )

    grounded = EvidenceCitationValidator().ground(claim, bundle())

    assert grounded.citations.valid is True
    assert grounded.citations.resolved_evidence_ids == ("alert:a1", "asset:plc-1")
    assert grounded.to_dict()["claim"]["claim_type"] == "observation"


def test_rejects_claim_without_citations() -> None:
    claim = InvestigativeClaim("claim-1", "Unsupported statement", ClaimType.INFERENCE, ())

    with pytest.raises(CitationValidationError, match="no evidence citations"):
        EvidenceCitationValidator().ground(claim, bundle())


def test_rejects_cross_bundle_or_unknown_evidence() -> None:
    claim = InvestigativeClaim(
        "claim-1", "Claim cites another incident.", ClaimType.HYPOTHESIS,
        ("alert:a1", "alert:other-incident"),
    )

    validation = EvidenceCitationValidator().validate(claim, bundle())

    assert validation.valid is False
    assert validation.resolved_evidence_ids == ("alert:a1",)
    assert validation.invalid_evidence_ids == ("alert:other-incident",)


def test_rejects_duplicate_claim_ids_in_batch() -> None:
    claims = (
        InvestigativeClaim("claim-1", "First", ClaimType.OBSERVATION, ("alert:a1",)),
        InvestigativeClaim("claim-1", "Second", ClaimType.INFERENCE, ("asset:plc-1",)),
    )

    with pytest.raises(CitationValidationError, match="duplicate claim_id"):
        EvidenceCitationValidator().ground_many(claims, bundle())
