from aegis.investigation.investigator import InvestigationResult
from aegis.orchestration.planning import TaskDAG
from aegis.orchestration.policy import InvestigationPolicyEngine


def result() -> InvestigationResult:
    return InvestigationResult(
        incident_id="inc-1",
        evidence={"evidence": []},
        timeline={"events": []},
        hypotheses=({"hypothesis_id": "hyp-1"},),
        uncertainty=({
            "hypothesis_id": "hyp-1",
            "calibrated_confidence": 0.42,
            "missing_evidence": ["historian telemetry"],
            "contradictions": ["conflicting PLC state"],
        },),
        narrative={},
        faithfulness={"evidence_coverage": 0.40},
    )


def test_policy_generates_gap_driven_valid_dag() -> None:
    plan = InvestigationPolicyEngine().plan(result())
    ids = {task.task_id for task in plan.tasks}

    assert "collect-evidence-1" in ids
    assert "check-contradictions-1" in ids
    assert "expand-timeline" in ids
    assert "validate-leading-hypothesis" in ids
    assert "reevaluate-risk" in ids
    assert TaskDAG(plan.tasks).execution_order()


def test_validation_waits_for_all_evidence_tasks() -> None:
    plan = InvestigationPolicyEngine().plan(result())
    validation = next(task for task in plan.tasks if task.task_id == "validate-leading-hypothesis")
    assert set(validation.dependencies) == {
        "collect-evidence-1", "check-contradictions-1", "expand-timeline",
    }


def test_risk_reevaluation_is_terminal_after_hypothesis_validation() -> None:
    plan = InvestigationPolicyEngine().plan(result())
    risk = next(task for task in plan.tasks if task.task_id == "reevaluate-risk")
    assert risk.dependencies == ("validate-leading-hypothesis",)
