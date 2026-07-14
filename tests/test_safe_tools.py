import pytest

from aegis.orchestration.planning import InvestigationTask, TaskType
from aegis.orchestration.tools import (
    SafeToolExecutor,
    ToolApprovalRequiredError,
    ToolNotAllowedError,
    ToolRegistry,
    ToolRisk,
    ToolSpec,
)


def task(task_type: TaskType = TaskType.QUERY_EVIDENCE) -> InvestigationTask:
    return InvestigationTask("task-1", task_type, "Collect evidence")


def test_executes_allowlisted_compatible_read_only_tool() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "historian-query",
        frozenset({TaskType.QUERY_EVIDENCE}),
        lambda item: {"task_id": item.task_id, "records": 4},
    ))

    result = SafeToolExecutor(registry).execute("historian-query", task())

    assert result.succeeded is True
    assert result.payload["records"] == 4


def test_rejects_unregistered_tool() -> None:
    with pytest.raises(ToolNotAllowedError, match="not allowlisted"):
        SafeToolExecutor(ToolRegistry()).execute("shell", task())


def test_rejects_incompatible_task_type() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "timeline-query",
        frozenset({TaskType.EXPAND_TIMELINE}),
        lambda _: {},
    ))

    with pytest.raises(ToolNotAllowedError, match="cannot execute"):
        SafeToolExecutor(registry).execute("timeline-query", task())


def test_controlled_write_requires_approval_by_contract() -> None:
    with pytest.raises(ValueError, match="must require approval"):
        ToolSpec(
            "contain-asset",
            frozenset({TaskType.INSPECT_ASSET}),
            lambda _: {},
            risk=ToolRisk.CONTROLLED_WRITE,
            requires_approval=False,
        )


def test_approval_gated_tool_cannot_execute_without_explicit_approval() -> None:
    registry = ToolRegistry()
    registry.register(ToolSpec(
        "controlled-action",
        frozenset({TaskType.INSPECT_ASSET}),
        lambda _: {"changed": True},
        risk=ToolRisk.CONTROLLED_WRITE,
        requires_approval=True,
    ))

    executor = SafeToolExecutor(registry)
    with pytest.raises(ToolApprovalRequiredError, match="explicit analyst approval"):
        executor.execute("controlled-action", task(TaskType.INSPECT_ASSET))

    result = executor.execute("controlled-action", task(TaskType.INSPECT_ASSET), approved=True)
    assert result.succeeded is True


def test_handler_failure_is_contained_as_result() -> None:
    def fail(_: InvestigationTask) -> dict[str, object]:
        raise RuntimeError("source unavailable")

    registry = ToolRegistry()
    registry.register(ToolSpec("failing-query", frozenset({TaskType.QUERY_EVIDENCE}), fail))
    result = SafeToolExecutor(registry).execute("failing-query", task())

    assert result.succeeded is False
    assert result.error == "source unavailable"
