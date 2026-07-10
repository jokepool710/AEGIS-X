import pytest

from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskDAG, TaskType


def task(task_id: str, dependencies: tuple[str, ...] = (), priority: int = 50) -> InvestigationTask:
    return InvestigationTask(
        task_id=task_id,
        task_type=TaskType.QUERY_EVIDENCE,
        objective=f"Investigate {task_id}",
        dependencies=dependencies,
        priority=priority,
    )


def test_plan_validates_and_produces_dependency_order() -> None:
    tasks = (
        task("collect"),
        task("validate", ("collect",)),
        task("reevaluate", ("validate",)),
    )
    plan = InvestigationPlan("plan-1", "inc-1", "Resolve incident", tasks)

    assert TaskDAG(plan.tasks).execution_order() == ("collect", "validate", "reevaluate")


def test_ready_tasks_respect_dependencies_and_priority() -> None:
    dag = TaskDAG((
        task("collect-a", priority=80),
        task("collect-b", priority=90),
        task("validate", ("collect-a", "collect-b"), priority=100),
    ))

    assert tuple(item.task_id for item in dag.ready_tasks(set())) == ("collect-b", "collect-a")
    assert tuple(item.task_id for item in dag.ready_tasks({"collect-a", "collect-b"})) == ("validate",)


def test_unknown_dependency_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown dependencies"):
        InvestigationPlan("plan-1", "inc-1", "Resolve incident", (task("validate", ("missing",)),))


def test_cycle_is_rejected() -> None:
    tasks = (task("a", ("b",)), task("b", ("a",)))
    with pytest.raises(ValueError, match="cycle"):
        InvestigationPlan("plan-1", "inc-1", "Resolve incident", tasks)


def test_duplicate_task_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        InvestigationPlan("plan-1", "inc-1", "Resolve incident", (task("a"), task("a")))


def test_descendants_are_transitive_and_deterministic() -> None:
    dag = TaskDAG((task("a"), task("b", ("a",)), task("c", ("b",)), task("d", ("a",))))
    assert dag.descendants("a") == ("b", "c", "d")
