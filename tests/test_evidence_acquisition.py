from aegis.investigation.evidence import EvidenceBundle
from aegis.orchestration.acquisition import EvidenceAcquisitionLoop
from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskType
from aegis.orchestration.tools import ToolRegistry, ToolSpec


def plan() -> InvestigationPlan:
    return InvestigationPlan(
        "plan-inc-1",
        "inc-1",
        "Acquire missing evidence",
        (
            InvestigationTask("collect", TaskType.QUERY_EVIDENCE, "Query historian"),
            InvestigationTask(
                "validate", TaskType.VALIDATE_HYPOTHESIS,
                "Validate hypothesis", dependencies=("collect",),
            ),
        ),
    )


def bundle() -> EvidenceBundle:
    return EvidenceBundle("inc-1", "1.0", ())


def test_executes_only_ready_tasks_and_preserves_provenance() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "historian-query",
        frozenset({TaskType.QUERY_EVIDENCE}),
        lambda _: {"records": 8, "observed_at": "2026-07-10T10:00:00+00:00"},
    ))

    outcome = EvidenceAcquisitionLoop(registry).run_ready(plan(), bundle())

    assert outcome.completed_task_ids == frozenset({"collect"})
    assert len(outcome.records) == 1
    assert outcome.records[0].succeeded is True
    item = outcome.bundle.evidence[0]
    assert item.source == "orchestration.tool:historian-query"
    assert item.payload["plan_id"] == "plan-inc-1"
    assert item.payload["task_id"] == "collect"
    assert item.payload["result"]["records"] == 8


def test_next_wave_runs_after_dependency_completion() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "hypothesis-validator",
        frozenset({TaskType.VALIDATE_HYPOTHESIS}),
        lambda _: {"validated": True},
    ))

    outcome = EvidenceAcquisitionLoop(registry).run_ready(
        plan(), bundle(), completed={"collect"},
    )

    assert outcome.completed_task_ids == frozenset({"collect", "validate"})
    assert outcome.records[0].task_id == "validate"


def test_missing_tool_does_not_complete_task() -> None:
    outcome = EvidenceAcquisitionLoop(ToolRegistry()).run_ready(plan(), bundle())

    assert outcome.completed_task_ids == frozenset()
    assert outcome.records[0].succeeded is False
    assert "no allowlisted tool" in str(outcome.records[0].error)


def test_failed_tool_result_is_not_added_as_evidence() -> None:
    def fail(_: InvestigationTask) -> dict[str, object]:
        raise RuntimeError("historian offline")

    registry = ToolRegistry()
    registry.register(ToolSpec(
        "historian-query", frozenset({TaskType.QUERY_EVIDENCE}), fail,
    ))

    outcome = EvidenceAcquisitionLoop(registry).run_ready(plan(), bundle())

    assert outcome.bundle.evidence == ()
    assert outcome.completed_task_ids == frozenset()
    assert outcome.records[0].error == "historian offline"
