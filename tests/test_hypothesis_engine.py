import pytest

from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.hypotheses import HypothesisEngine
from aegis.investigation.timeline import InvestigationTimeline, TimelineEvent


def evidence(evidence_id: str, kind: EvidenceKind, payload: dict[str, object]) -> EvidenceItem:
    return EvidenceItem(evidence_id, kind, "test", "2026-07-08T10:00:00+00:00", payload)


def test_generates_ranked_competing_grounded_hypotheses() -> None:
    bundle = EvidenceBundle(
        "inc-1", "1.0",
        (
            evidence("alert:a1", EvidenceKind.ALERT, {"metric": "pressure"}),
            evidence("alert:a2", EvidenceKind.ALERT, {"metric": "flow"}),
            evidence("edge:0001", EvidenceKind.GRAPH_EDGE, {"edge_type": "temporal"}),
            evidence("attack:T0855", EvidenceKind.ATTACK_MAPPING, {
                "technique_id": "T0855", "technique_name": "Unauthorized Command Message",
                "confidence": 0.9,
            }),
            evidence("risk:inc-1", EvidenceKind.RISK, {"risk_score": 0.88, "risk_level": "critical"}),
        ),
    )
    timeline = InvestigationTimeline(
        "inc-1", (TimelineEvent(1, "2026-07-08T10:00:00+00:00", "alert", "observed", ("alert:a1",)),),
    )

    hypotheses = HypothesisEngine().generate(bundle, timeline)

    assert len(hypotheses) == 3
    assert hypotheses[0].confidence >= hypotheses[1].confidence >= hypotheses[2].confidence
    assert {item.hypothesis_id for item in hypotheses} == {"hyp-1", "hyp-topology", "hyp-impact"}
    for hypothesis in hypotheses:
        assert hypothesis.evidence_ids
        assert set(hypothesis.evidence_ids) <= bundle.evidence_ids
        assert all(claim.citations.valid for claim in hypothesis.claims)
    assert hypotheses[0].to_dict()["claims"]


def test_is_deterministic_for_same_inputs() -> None:
    bundle = EvidenceBundle(
        "inc-1", "1.0",
        (evidence("attack:T0001", EvidenceKind.ATTACK_MAPPING, {
            "technique_id": "T0001", "technique_name": "Technique", "confidence": 0.7,
        }),),
    )
    timeline = InvestigationTimeline("inc-1", ())
    engine = HypothesisEngine()

    first = engine.generate(bundle, timeline)
    second = engine.generate(bundle, timeline)

    assert first == second


def test_rejects_cross_incident_timeline() -> None:
    bundle = EvidenceBundle("inc-1", "1.0", ())
    timeline = InvestigationTimeline("inc-other", ())

    with pytest.raises(ValueError, match="same incident"):
        HypothesisEngine().generate(bundle, timeline)
