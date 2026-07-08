import pytest

from aegis.investigation.citations import (
    CitationValidation, ClaimType, GroundedClaim, InvestigativeClaim,
)
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.hypotheses import InvestigationHypothesis
from aegis.investigation.uncertainty import ConfidenceBand, ConfidenceUncertaintyModel


def item(evidence_id: str, kind: EvidenceKind, source: str, payload: dict[str, object]) -> EvidenceItem:
    return EvidenceItem(evidence_id, kind, source, "2026-07-08T10:00:00+00:00", payload)


def hypothesis(evidence_ids: tuple[str, ...], confidence: float = 0.9) -> InvestigationHypothesis:
    claim = InvestigativeClaim("c1", "Grounded hypothesis", ClaimType.HYPOTHESIS, evidence_ids)
    grounded = GroundedClaim(claim, CitationValidation("c1", True, evidence_ids, ()))
    return InvestigationHypothesis("hyp-1", "Technique hypothesis", confidence, "rationale", (grounded,), evidence_ids)


def test_calibrates_with_diverse_complete_evidence() -> None:
    bundle = EvidenceBundle("inc-1", "1.0", (
        item("incident:inc-1", EvidenceKind.INCIDENT, "store", {"severity": "critical"}),
        item("alert:a1", EvidenceKind.ALERT, "detector", {}),
        item("asset:plc", EvidenceKind.ASSET, "topology", {}),
        item("edge:1", EvidenceKind.GRAPH_EDGE, "graph", {}),
        item("attack:T1", EvidenceKind.ATTACK_MAPPING, "mapper", {}),
        item("risk:inc-1", EvidenceKind.RISK, "risk", {"risk_level": "critical"}),
    ))
    evidence_ids = ("alert:a1", "asset:plc", "edge:1", "attack:T1", "risk:inc-1")

    result = ConfidenceUncertaintyModel().assess(hypothesis(evidence_ids), bundle)

    assert result.calibrated_confidence >= 0.75
    assert result.confidence_band == ConfidenceBand.HIGH
    assert result.evidence_diversity == 1.0
    assert result.citation_coverage == 1.0
    assert result.missing_evidence == ()
    assert result.contradictions == ()


def test_surfaces_missing_evidence_and_severity_contradiction() -> None:
    bundle = EvidenceBundle("inc-1", "1.0", (
        item("incident:inc-1", EvidenceKind.INCIDENT, "store", {"severity": "low"}),
        item("alert:a1", EvidenceKind.ALERT, "detector", {}),
        item("risk:inc-1", EvidenceKind.RISK, "risk", {"risk_level": "critical"}),
    ))
    result = ConfidenceUncertaintyModel().assess(
        hypothesis(("alert:a1", "risk:inc-1")), bundle,
    )

    assert "asset context" in result.missing_evidence
    assert "graph relationship evidence" in result.missing_evidence
    assert result.contradiction_penalty > 0
    assert result.contradictions
    assert result.calibrated_confidence < 0.75


def test_rejects_foreign_evidence_reference() -> None:
    bundle = EvidenceBundle("inc-1", "1.0", ())

    with pytest.raises(ValueError, match="outside the active incident bundle"):
        ConfidenceUncertaintyModel().assess(hypothesis(("alert:foreign",)), bundle)


def test_assess_many_returns_calibrated_ranking() -> None:
    bundle = EvidenceBundle("inc-1", "1.0", (
        item("alert:a1", EvidenceKind.ALERT, "detector", {}),
    ))
    high = hypothesis(("alert:a1",), 0.9)
    low_claim = InvestigativeClaim("c2", "lower", ClaimType.HYPOTHESIS, ("alert:a1",))
    low = InvestigationHypothesis(
        "hyp-2", "Lower", 0.3, "rationale",
        (GroundedClaim(low_claim, CitationValidation("c2", True, ("alert:a1",), ())),),
        ("alert:a1",),
    )

    results = ConfidenceUncertaintyModel().assess_many((low, high), bundle)

    assert results[0].hypothesis_id == "hyp-1"
    assert results[0].to_dict()["confidence_band"] in {"low", "moderate", "high"}
