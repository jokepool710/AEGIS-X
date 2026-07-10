from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from graphlib import CycleError, TopologicalSorter
from typing import Any


class TaskType(str, Enum):
    QUERY_EVIDENCE = "query_evidence"
    VALIDATE_HYPOTHESIS = "validate_hypothesis"
    CHECK_CONTRADICTION = "check_contradiction"
    EXPAND_TIMELINE = "expand_timeline"
    INSPECT_ASSET = "inspect_asset"
    REEVALUATE_RISK = "reevaluate_risk"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class InvestigationTask:
    task_id: str
    task_type: TaskType
    objective: str
    dependencies: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    status: TaskStatus = TaskStatus.PENDING

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.objective.strip():
            raise ValueError("task objective must not be empty")
        if not 0 <= self.priority <= 100:
            raise ValueError("task priority must be between 0 and 100")
        if self.task_id in self.dependencies:
            raise ValueError("task cannot depend on itself")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("task dependencies must be unique")


@dataclass(frozen=True)
class InvestigationPlan:
    plan_id: str
    incident_id: str
    objective: str
    tasks: tuple[InvestigationTask, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.incident_id.strip():
            raise ValueError("plan_id and incident_id must not be empty")
        if not self.objective.strip():
            raise ValueError("plan objective must not be empty")
        if not self.tasks:
            raise ValueError("investigation plan requires at least one task")
        TaskDAG(self.tasks).validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskDAG:
    """Validated deterministic dependency graph for investigation tasks."""

    def __init__(self, tasks: tuple[InvestigationTask, ...]) -> None:
        self.tasks = tasks
        self._by_id = {task.task_id: task for task in tasks}

    def validate(self) -> None:
        if len(self._by_id) != len(self.tasks):
            raise ValueError("task IDs must be unique")
        known = set(self._by_id)
        for task in self.tasks:
            missing = set(task.dependencies) - known
            if missing:
                raise ValueError(f"task {task.task_id} has unknown dependencies: {sorted(missing)}")
        try:
            tuple(TopologicalSorter(self._graph()).static_order())
        except CycleError as exc:
            raise ValueError("task dependency graph contains a cycle") from exc

    def _graph(self) -> dict[str, set[str]]:
        return {task.task_id: set(task.dependencies) for task in self.tasks}

    def execution_order(self) -> tuple[str, ...]:
        self.validate()
        return tuple(TopologicalSorter(self._graph()).static_order())

    def ready_tasks(self, completed: set[str]) -> tuple[InvestigationTask, ...]:
        unknown = completed - set(self._by_id)
        if unknown:
            raise ValueError(f"unknown completed task IDs: {sorted(unknown)}")
        ready = [
            task
            for task in self.tasks
            if task.task_id not in completed and set(task.dependencies) <= completed
        ]
        return tuple(sorted(ready, key=lambda task: (-task.priority, task.task_id)))

    def descendants(self, task_id: str) -> tuple[str, ...]:
        if task_id not in self._by_id:
            raise KeyError(task_id)
        result: set[str] = set()
        frontier = [task_id]
        while frontier:
            current = frontier.pop()
            children = [task.task_id for task in self.tasks if current in task.dependencies]
            for child in children:
                if child not in result:
                    result.add(child)
                    frontier.append(child)
        return tuple(sorted(result))
