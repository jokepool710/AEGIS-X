from __future__ import annotations

from dataclasses import asdict, dataclass

from aegis.common.storage import TelemetryStore
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.investigator import InvestigationResult
from aegis.investigation.uncertainty import ConfidenceBand, UncertaintyAssessment
from aegis.orchestration.acquisition import AcquisitionOutcome, EvidenceAcquisitionLoop
from aegis.orchestration.decision_support import AnalystDecisionSupportEngine, DecisionRecommendation
from aegis.orchestration.ledger import DecisionEventType, DecisionLedger
from aegis.orchestration.policy import InvestigationPolicyEngine
from aegis.orchestration.reevaluation import HypothesisReevaluationLoop, ReevaluationOutcome
from aegis.orchestration.tools import ToolRegistry


@dataclass(frozen=True)
class OrchestrationOutcome:
    incident_id: str
    plan_id: str
    acquisition: AcquisitionOutcome
    reevaluation: ReevaluationOutcome
    recommendations: tuple[DecisionRecommendation, ...]
    ledger_integrity: bool


class Phase5Orchestrator:
    """Run one controlled investigation cycle from Phase 4 state to analyst recommendations."""

    def __init__(self, registry: ToolRegistry, storage: TelemetryStore) -> None:
        self.registry = registry
        self.ledger = DecisionLedger(storage)

    def run_cycle(self, result: InvestigationResult) -> OrchestrationOutcome:
        plan = InvestigationPolicyEngine().plan(result)
        self.ledger.append(
            result.incident_id, plan.plan_id, DecisionEventType.PLAN_CREATED,
            "phase5-policy-engine", {"task_count": len(plan.tasks), "objective": plan.objective},
        )
        bundle = self._bundle(result.evidence)
        previous = self._uncertainty(result.uncertainty)
        acquisition = EvidenceAcquisitionLoop(self.registry).run_ready(plan, bundle)
        for record in acquisition.records:
            if record.succeeded:
                self.ledger.append(
                    result.incident_id, plan.plan_id, DecisionEventType.EVIDENCE_ACQUIRED,
                    "phase5-acquisition-loop", asdict(record),
                )
        reevaluation = HypothesisReevaluationLoop().reevaluate(acquisition.bundle, previous)
        for delta in reevaluation.deltas:
            self.ledger.append(
                result.incident_id, plan.plan_id, DecisionEventType.CONFIDENCE_CHANGED,
                "phase5-reevaluation-loop", asdict(delta),
            )
        recommendations = AnalystDecisionSupportEngine().recommend(
            plan, reevaluation.uncertainty, set(acquisition.completed_task_ids),
        )
        for recommendation in recommendations:
            self.ledger.append(
                result.incident_id, plan.plan_id, DecisionEventType.RECOMMENDATION_CREATED,
                "phase5-decision-support", recommendation.to_dict(),
            )
        return OrchestrationOutcome(
            result.incident_id, plan.plan_id, acquisition, reevaluation,
            recommendations, self.ledger.verify_integrity(),
        )

    @staticmethod
    def _bundle(payload: dict[str, object]) -> EvidenceBundle:
        items = tuple(
            EvidenceItem(
                str(item["evidence_id"]), EvidenceKind(str(item["kind"])),
                str(item["source"]), item.get("observed_at"), dict(item["payload"]),
            )
            for item in payload["evidence"]  # type: ignore[union-attr]
        )
        return EvidenceBundle(str(payload["incident_id"]), str(payload["schema_version"]), items)

    @staticmethod
    def _uncertainty(payloads: tuple[dict[str, object], ...]) -> tuple[UncertaintyAssessment, ...]:
        return tuple(
            UncertaintyAssessment(
                str(item["hypothesis_id"]), float(item["calibrated_confidence"]),
                ConfidenceBand(str(item["confidence_band"])), float(item["evidence_diversity"]),
                float(item["citation_coverage"]), float(item["inference_penalty"]),
                tuple(item["missing_evidence"]), tuple(item["contradictions"]),
            )
            for item in payloads
        )
