from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.uncertainty import ConfidenceBand, UncertaintyAssessment
from aegis.orchestration.reevaluation import HypothesisReevaluationLoop


def item(evidence_id: str, kind: EvidenceKind, payload: dict[str, object],
         observed_at: str | None = None) -> EvidenceItem:
    return EvidenceItem(evidence_id, kind, "test", observed_at, payload)


def complete_bundle() -> EvidenceBundle:
    evidence = (
        item("incident:inc-1", EvidenceKind.INCIDENT, {"severity": "high"}, "2026-07-10T10:00:00+00:00"),
        item("alert:a1", EvidenceKind.ALERT, {}, "2026-07-10T10:00:01+00:00"),
        item("asset:plc", EvidenceKind.ASSET, {}),
        item("edge:1", EvidenceKind.GRAPH_EDGE, {}),
        item("attack:T1", EvidenceKind.ATTACK_MAPPING, {
            "technique_id": "T1", "technique_name": "Test technique", "confidence": 0.9,
        }),
        item("risk:inc-1", EvidenceKind.RISK, {"risk_score": 0.8, "risk_level": "high"}),
    )
    return EvidenceBundle("inc-1", "1.0", evidence)


def previous(confidence: float = 0.4, contradictions: tuple[str, ...] = ()) -> UncertaintyAssessment:
    return UncertaintyAssessment(
        "hyp-1", confidence, ConfidenceBand.LOW, 0.2, 1.0, 0.0, (), contradictions,
    )


def test_reevaluation_rebuilds_hypotheses_and_measures_confidence_delta() -> None:
    outcome = HypothesisReevaluationLoop().reevaluate(complete_bundle(), (previous(),))
    delta = next(item for item in outcome.deltas if item.hypothesis_id == "hyp-1")

    assert outcome.hypotheses
    assert outcome.uncertainty
    assert delta.previous_confidence == 0.4
    assert delta.confidence_delta is not None
    assert delta.current_confidence > delta.previous_confidence


def test_resolved_contradictions_are_reported() -> None:
    conflict = "incident severity critical conflicts with risk level low"
    outcome = HypothesisReevaluationLoop().reevaluate(
        complete_bundle(), (previous(0.4, (conflict,)),),
    )
    delta = next(item for item in outcome.deltas if item.hypothesis_id == "hyp-1")

    assert delta.resolved_contradictions == (conflict,)
    assert delta.new_contradictions == ()


def test_low_confidence_or_missing_evidence_requests_another_wave() -> None:
    sparse = EvidenceBundle("inc-1", "1.0", (
        item("incident:inc-1", EvidenceKind.INCIDENT, {"severity": "high"}, "2026-07-10T10:00:00+00:00"),
        item("alert:a1", EvidenceKind.ALERT, {}, "2026-07-10T10:00:01+00:00"),
        item("attack:T1", EvidenceKind.ATTACK_MAPPING, {
            "technique_id": "T1", "technique_name": "Test technique", "confidence": 0.4,
        }),
    ))
    outcome = HypothesisReevaluationLoop().reevaluate(sparse, ())

    assert outcome.another_acquisition_wave is True
    assert outcome.reasons


def test_empty_hypothesis_set_stops_loop() -> None:
    empty = EvidenceBundle("inc-1", "1.0", ())
    outcome = HypothesisReevaluationLoop().reevaluate(empty, ())

    assert outcome.another_acquisition_wave is False
    assert outcome.reasons == ("no hypotheses available for further acquisition",)
