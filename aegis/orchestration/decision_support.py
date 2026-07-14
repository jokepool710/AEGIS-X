from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from aegis.investigation.uncertainty import UncertaintyAssessment
from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskDAG, TaskType


class ActionRisk(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class DecisionRecommendation:
    rank: int
    task_id: str
    action: str
    score: float
    expected_information_gain: float
    uncertainty_reduction: float
    operational_risk: ActionRisk
    estimated_cost: float
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "operational_risk": self.operational_risk.value}


class AnalystDecisionSupportEngine:
    """Rank dependency-ready investigative actions for analyst review."""

    _TYPE_INFORMATION_GAIN = {
        TaskType.CHECK_CONTRADICTION: 0.95,
        TaskType.VALIDATE_HYPOTHESIS: 0.90,
        TaskType.QUERY_EVIDENCE: 0.85,
        TaskType.EXPAND_TIMELINE: 0.75,
        TaskType.INSPECT_ASSET: 0.70,
        TaskType.REEVALUATE_RISK: 0.45,
    }
    _TYPE_COST = {
        TaskType.QUERY_EVIDENCE: 0.25,
        TaskType.CHECK_CONTRADICTION: 0.35,
        TaskType.EXPAND_TIMELINE: 0.40,
        TaskType.VALIDATE_HYPOTHESIS: 0.30,
        TaskType.INSPECT_ASSET: 0.60,
        TaskType.REEVALUATE_RISK: 0.15,
    }
    _TYPE_RISK = {
        TaskType.INSPECT_ASSET: ActionRisk.MODERATE,
    }

    def recommend(self, plan: InvestigationPlan,
                  uncertainty: tuple[UncertaintyAssessment, ...] | list[UncertaintyAssessment],
                  completed: set[str] | None = None) -> tuple[DecisionRecommendation, ...]:
        ready = TaskDAG(plan.tasks).ready_tasks(set(completed or set()))
        uncertainty_pressure = self._uncertainty_pressure(uncertainty)
        scored = [self._score(task, uncertainty_pressure) for task in ready]
        ordered = sorted(scored, key=lambda item: (-item[0], item[1].task_id))
        return tuple(
            DecisionRecommendation(
                rank=index,
                task_id=task.task_id,
                action=task.objective,
                score=score,
                expected_information_gain=info_gain,
                uncertainty_reduction=uncertainty_reduction,
                operational_risk=risk,
                estimated_cost=cost,
                rationale=rationale,
            )
            for index, (score, task, info_gain, uncertainty_reduction, risk, cost, rationale)
            in enumerate(ordered, start=1)
        )

    @staticmethod
    def _uncertainty_pressure(assessments: tuple[UncertaintyAssessment, ...] |
                              list[UncertaintyAssessment]) -> float:
        if not assessments:
            return 0.5
        leader = max(assessments, key=lambda item: item.calibrated_confidence)
        missing_pressure = min(1.0, len(leader.missing_evidence) / 3.0)
        contradiction_pressure = min(1.0, len(leader.contradictions) / 2.0)
        confidence_gap = 1.0 - leader.calibrated_confidence
        return round(
            confidence_gap * 0.55 + missing_pressure * 0.25 + contradiction_pressure * 0.20,
            4,
        )

    def _score(self, task: InvestigationTask, uncertainty_pressure: float) -> tuple[
        float, InvestigationTask, float, float, ActionRisk, float, tuple[str, ...]
    ]:
        info_gain = self._TYPE_INFORMATION_GAIN[task.task_type]
        cost = self._TYPE_COST[task.task_type]
        risk = self._TYPE_RISK.get(task.task_type, ActionRisk.LOW)
        uncertainty_reduction = round(info_gain * uncertainty_pressure, 4)
        priority_signal = task.priority / 100.0
        risk_penalty = {ActionRisk.LOW: 0.0, ActionRisk.MODERATE: 0.12, ActionRisk.HIGH: 0.30}[risk]
        score = round(
            0.40 * info_gain
            + 0.30 * uncertainty_reduction
            + 0.20 * priority_signal
            - 0.07 * cost
            - 0.03 * risk_penalty,
            4,
        )
        rationale = (
            f"expected information gain={info_gain:.2f}",
            f"uncertainty reduction potential={uncertainty_reduction:.2f}",
            f"estimated investigation cost={cost:.2f}",
            f"operational risk={risk.value}",
        )
        return score, task, info_gain, uncertainty_reduction, risk, cost, rationale
