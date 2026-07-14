from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from aegis.orchestration.planning import InvestigationTask, TaskType


class ToolRisk(str, Enum):
    READ_ONLY = "read_only"
    CONTROLLED_WRITE = "controlled_write"


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    task_id: str
    succeeded: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ToolSpec:
    name: str
    task_types: frozenset[TaskType]
    handler: Callable[[InvestigationTask], dict[str, Any]]
    risk: ToolRisk = ToolRisk.READ_ONLY
    requires_approval: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name must not be empty")
        if not self.task_types:
            raise ValueError("tool must support at least one task type")
        if self.risk is ToolRisk.CONTROLLED_WRITE and not self.requires_approval:
            raise ValueError("controlled-write tools must require approval")


class ToolNotAllowedError(PermissionError):
    pass


class ToolApprovalRequiredError(PermissionError):
    pass


class ToolRegistry:
    """Explicit allowlist of typed investigation tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotAllowedError(f"tool is not allowlisted: {name}") from exc

    def compatible(self, task_type: TaskType) -> tuple[ToolSpec, ...]:
        return tuple(
            sorted(
                (spec for spec in self._tools.values() if task_type in spec.task_types),
                key=lambda spec: spec.name,
            )
        )


class SafeToolExecutor:
    """Enforce allowlisting, task compatibility, and approval gates before execution."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, tool_name: str, task: InvestigationTask,
                approved: bool = False) -> ToolResult:
        spec = self.registry.get(tool_name)
        if task.task_type not in spec.task_types:
            raise ToolNotAllowedError(
                f"tool {tool_name} cannot execute task type {task.task_type.value}"
            )
        if spec.requires_approval and not approved:
            raise ToolApprovalRequiredError(
                f"tool {tool_name} requires explicit analyst approval"
            )
        try:
            payload = spec.handler(task)
        except Exception as exc:
            return ToolResult(tool_name, task.task_id, False, error=str(exc))
        if not isinstance(payload, dict):
            return ToolResult(
                tool_name, task.task_id, False,
                error="tool handler must return a dictionary payload",
            )
        return ToolResult(tool_name, task.task_id, True, payload=payload)
