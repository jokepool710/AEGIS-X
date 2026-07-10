from __future__ import annotations

from dataclasses import dataclass

from aegis.investigation.investigator import InvestigationResult
from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskType


@dataclass(frozen=True)
class PolicyThresholds:
    low_confidence: float = 0.65
    high_risk: float = 0.75
    weak_evidence_coverage: float = 0.60


class InvestigationPolicyEngine:
    """Convert Phase 4 investigation gaps into a deterministic, validated task plan."""

    def __init__(self, thresholds: PolicyThresholds | None = None) -> None:
        self.thresholds = thresholds or PolicyThresholds()

    def plan(self, result: InvestigationResult) -> InvestigationPlan:
        tasks: list[InvestigationTask] = []
        hypotheses = result.hypotheses
        uncertainty = result.uncertainty
        faithfulness = result.faithfulness

        collect_ids: list[str] = []
        for index, assessment in enumerate(uncertainty, start=1):
            confidence = float(assessment.get("calibrated_confidence", 1.0))
            missing = tuple(str(item) for item in assessment.get("missing_evidence", ()))
            contradictions = tuple(str(item) for item in assessment.get("contradictions", ()))

            if confidence < self.thresholds.low_confidence or missing:
                task_id = f"collect-evidence-{index}"
                collect_ids.append(task_id)
                tasks.append(InvestigationTask(
                    task_id=task_id,
                    task_type=TaskType.QUERY_EVIDENCE,
                    objective=f"Acquire discriminating evidence for hypothesis {index}",
                    required_evidence=missing,
                    parameters={"hypothesis_index": index, "confidence": confidence},
                    priority=90,
                ))

            if contradictions:
                tasks.append(InvestigationTask(
                    task_id=f"check-contradictions-{index}",
                    task_type=TaskType.CHECK_CONTRADICTION,
                    objective=f"Resolve contradictory evidence for hypothesis {index}",
                    required_evidence=contradictions,
                    parameters={"hypothesis_index": index},
                    priority=100,
                ))

        coverage = float(faithfulness.get("evidence_coverage", 1.0))
        if coverage < self.thresholds.weak_evidence_coverage:
            tasks.append(InvestigationTask(
                task_id="expand-timeline",
                task_type=TaskType.EXPAND_TIMELINE,
                objective="Expand temporal evidence coverage around the incident window",
                parameters={"current_evidence_coverage": coverage},
                priority=85,
            ))

        validation_dependencies = tuple(task.task_id for task in tasks)
        if hypotheses:
            tasks.append(InvestigationTask(
                task_id="validate-leading-hypothesis",
                task_type=TaskType.VALIDATE_HYPOTHESIS,
                objective="Re-evaluate the leading hypothesis after evidence acquisition",
                dependencies=validation_dependencies,
                parameters={"hypothesis_id": hypotheses[0].get("hypothesis_id")},
                priority=80,
            ))

        tasks.append(InvestigationTask(
            task_id="reevaluate-risk",
            task_type=TaskType.REEVALUATE_RISK,
            objective="Recalculate incident risk after investigation tasks complete",
            dependencies=("validate-leading-hypothesis",) if hypotheses else validation_dependencies,
            priority=70,
        ))

        return InvestigationPlan(
            plan_id=f"plan-{result.incident_id}",
            incident_id=result.incident_id,
            objective="Reduce investigation uncertainty and support an evidence-backed analyst decision",
            tasks=tuple(tasks),
        )
