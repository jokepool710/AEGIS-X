from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.faithfulness import FaithfulnessEvaluator, NarrativeClaim
from aegis.investigation.narrative import GroundedNarrative
from aegis.investigation.uncertainty import ConfidenceBand, UncertaintyAssessment


def bundle() -> EvidenceBundle:
    return EvidenceBundle("inc-1", "1.0", (
        EvidenceItem("alert:a1", EvidenceKind.ALERT, "detector", None, {}),
        EvidenceItem("asset:plc", EvidenceKind.ASSET, "topology", None, {}),
        EvidenceItem("risk:inc-1", EvidenceKind.RISK, "risk", None, {}),
    ))


def narrative(citations: tuple[str, ...]) -> GroundedNarrative:
    return GroundedNarrative(
        "inc-1", "Grounded summary", ("Finding",), ("Question",), citations, "stub",
    )


def test_scores_fully_grounded_narrative() -> None:
    claims = (
        NarrativeClaim("c1", "Alert observed", ("alert:a1",), True),
        NarrativeClaim("c2", "PLC affected", ("asset:plc",), True),
        NarrativeClaim("c3", "Risk assessed", ("risk:inc-1",), True),
    )

    report = FaithfulnessEvaluator().evaluate(
        narrative(("alert:a1", "asset:plc", "risk:inc-1")), bundle(), claims,
    )

    assert report.unsupported_claim_rate == 0.0
    assert report.citation_validity == 1.0
    assert report.evidence_coverage == 1.0
    assert report.contradiction_handling == 1.0
    assert report.faithfulness_score == 1.0


def test_penalizes_unsupported_claims_and_invalid_citations() -> None:
    claims = (
        NarrativeClaim("c1", "Alert observed", ("alert:a1",), True),
        NarrativeClaim("c2", "Attacker identity known", ("actor:unknown",), False),
    )

    report = FaithfulnessEvaluator().evaluate(
        narrative(("alert:a1",)), bundle(), claims,
    )

    assert report.unsupported_claim_rate == 0.5
    assert report.citation_validity == 0.5
    assert report.invalid_citation_ids == ("actor:unknown",)
    assert report.faithfulness_score < 1.0


def test_measures_contradiction_handling() -> None:
    contradiction = "incident severity low conflicts with risk level critical"
    assessment = UncertaintyAssessment(
        "hyp-1", 0.4, ConfidenceBand.LOW, 0.5, 1.0, 0.25, (), (contradiction,),
    )
    claims = (NarrativeClaim("c1", "Alert observed", ("alert:a1",), True),)

    ignored = FaithfulnessEvaluator().evaluate(
        narrative(("alert:a1",)), bundle(), claims, (assessment,),
    )
    addressed = FaithfulnessEvaluator().evaluate(
        narrative(("alert:a1",)), bundle(), claims, (assessment,), (contradiction,),
    )

    assert ignored.contradiction_handling == 0.0
    assert ignored.unaddressed_contradictions == (contradiction,)
    assert addressed.contradiction_handling == 1.0
    assert addressed.faithfulness_score > ignored.faithfulness_score


def test_duplicate_claims_reduce_consistency() -> None:
    claims = (
        NarrativeClaim("c1", "Same statement", ("alert:a1",), True),
        NarrativeClaim("c2", "Same statement", ("alert:a1",), True),
    )

    report = FaithfulnessEvaluator().evaluate(narrative(("alert:a1",)), bundle(), claims)

    assert report.narrative_consistency < 1.0
