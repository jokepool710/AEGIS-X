from aegis.common.storage import TelemetryStore
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.investigator import InvestigationResult
from aegis.orchestration.ledger import DecisionEventType, DecisionLedger
from aegis.orchestration.orchestrator import Phase5Orchestrator
from aegis.orchestration.planning import TaskType
from aegis.orchestration.tools import ToolRegistry, ToolSpec


def baseline() -> InvestigationResult:
    evidence = EvidenceBundle(
        "inc-e2e", "1.0",
        (
            EvidenceItem("incident:inc-e2e", EvidenceKind.INCIDENT, "test", "2026-07-10T10:00:00+00:00", {"severity": "high"}),
            EvidenceItem("alert:a1", EvidenceKind.ALERT, "test", "2026-07-10T10:00:01+00:00", {}),
            EvidenceItem("attack:T1", EvidenceKind.ATTACK_MAPPING, "test", None, {
                "technique_id": "T1", "technique_name": "Unauthorized command", "confidence": 0.45,
            }),
        ),
    )
    return InvestigationResult(
        "inc-e2e", evidence.to_dict(), {"events": []},
        ({"hypothesis_id": "hyp-1"},),
        ({
            "hypothesis_id": "hyp-1", "calibrated_confidence": 0.35,
            "confidence_band": "low", "evidence_diversity": 0.2,
            "citation_coverage": 1.0, "inference_penalty": 0.0,
            "missing_evidence": ["historian telemetry"], "contradictions": [],
        },),
        {}, {"evidence_coverage": 0.4},
    )


def registry() -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(ToolSpec(
        "historian-query", frozenset({TaskType.QUERY_EVIDENCE}),
        lambda _: {
            "observed_at": "2026-07-10T10:00:02+00:00",
            "records": 12, "finding": "command sequence confirmed",
        },
    ))
    tools.register(ToolSpec(
        "timeline-query", frozenset({TaskType.EXPAND_TIMELINE}),
        lambda _: {
            "observed_at": "2026-07-10T09:59:50+00:00",
            "events": 6,
        },
    ))
    return tools


def test_phase5_orchestration_improves_static_baseline_and_is_auditable(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "phase5-e2e.db"))
    initial = baseline()
    outcome = Phase5Orchestrator(registry(), storage).run_cycle(initial)

    assert outcome.acquisition.completed_task_ids
    assert len(outcome.acquisition.bundle.evidence) > len(initial.evidence["evidence"])
    assert outcome.reevaluation.hypotheses
    assert outcome.reevaluation.uncertainty
    assert outcome.recommendations
    assert outcome.ledger_integrity is True

    ledger = DecisionLedger(storage)
    event_types = {event.event_type for event in ledger.list("inc-e2e")}
    assert DecisionEventType.PLAN_CREATED in event_types
    assert DecisionEventType.EVIDENCE_ACQUIRED in event_types
    assert DecisionEventType.CONFIDENCE_CHANGED in event_types
    assert DecisionEventType.RECOMMENDATION_CREATED in event_types
    assert ledger.verify_integrity() is True

    baseline_evidence_count = len(initial.evidence["evidence"])
    orchestrated_evidence_count = len(outcome.acquisition.bundle.evidence)
    assert orchestrated_evidence_count > baseline_evidence_count

    baseline_confidence = float(initial.uncertainty[0]["calibrated_confidence"])
    leader = max(item.calibrated_confidence for item in outcome.reevaluation.uncertainty)
    assert leader >= baseline_confidence
