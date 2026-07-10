from aegis.investigation.uncertainty import ConfidenceBand, UncertaintyAssessment
from aegis.orchestration.decision_support import AnalystDecisionSupportEngine
from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskType


def assessment(confidence: float, missing: tuple[str, ...] = (),
               contradictions: tuple[str, ...] = ()) -> UncertaintyAssessment:
    return UncertaintyAssessment(
        "hyp-1", confidence, ConfidenceBand.LOW, 0.2, 1.0, 0.0,
        missing, contradictions,
    )


def plan() -> InvestigationPlan:
    return InvestigationPlan(
        "plan-1", "inc-1", "Reduce uncertainty",
        (
            InvestigationTask(
                "query", TaskType.QUERY_EVIDENCE, "Query historian", priority=90,
            ),
            InvestigationTask(
                "contradiction", TaskType.CHECK_CONTRADICTION,
                "Resolve conflicting PLC state", priority=100,
            ),
            InvestigationTask(
                "risk", TaskType.REEVALUATE_RISK, "Recalculate risk",
                dependencies=("query", "contradiction"), priority=70,
            ),
        ),
    )


def test_ranks_only_dependency_ready_actions() -> None:
    recommendations = AnalystDecisionSupportEngine().recommend(
        plan(), (assessment(0.35, ("historian",), ("PLC conflict",)),),
    )

    assert {item.task_id for item in recommendations} == {"query", "contradiction"}
    assert recommendations[0].task_id == "contradiction"
    assert recommendations[0].rank == 1
    assert recommendations[0].score >= recommendations[1].score


def test_completed_dependencies_unlock_terminal_action() -> None:
    recommendations = AnalystDecisionSupportEngine().recommend(
        plan(), (assessment(0.8),), completed={"query", "contradiction"},
    )

    assert len(recommendations) == 1
    assert recommendations[0].task_id == "risk"


def test_recommendations_are_explainable_and_bounded() -> None:
    recommendation = AnalystDecisionSupportEngine().recommend(
        plan(), (assessment(0.4, ("asset context",)),),
    )[0]

    assert 0.0 <= recommendation.score <= 1.0
    assert 0.0 <= recommendation.expected_information_gain <= 1.0
    assert 0.0 <= recommendation.uncertainty_reduction <= 1.0
    assert 0.0 <= recommendation.estimated_cost <= 1.0
    assert len(recommendation.rationale) == 4


def test_ranking_is_deterministic() -> None:
    engine = AnalystDecisionSupportEngine()
    state = (assessment(0.42, ("historian",), ("conflict",)),)

    first = engine.recommend(plan(), state)
    second = engine.recommend(plan(), state)

    assert first == second
