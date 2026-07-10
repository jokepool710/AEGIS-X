from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.orchestration.planning import InvestigationPlan, InvestigationTask, TaskDAG
from aegis.orchestration.tools import SafeToolExecutor, ToolRegistry, ToolResult


@dataclass(frozen=True)
class AcquisitionRecord:
    task_id: str
    tool_name: str
    evidence_id: str | None
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True)
class AcquisitionOutcome:
    bundle: EvidenceBundle
    completed_task_ids: frozenset[str]
    records: tuple[AcquisitionRecord, ...]


class EvidenceAcquisitionLoop:
    """Execute ready investigation tasks and append tool outputs as provenance-bound evidence."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.executor = SafeToolExecutor(registry)

    def run_ready(self, plan: InvestigationPlan, bundle: EvidenceBundle,
                  completed: set[str] | None = None) -> AcquisitionOutcome:
        completed_ids = set(completed or set())
        dag = TaskDAG(plan.tasks)
        records: list[AcquisitionRecord] = []
        new_items: list[EvidenceItem] = []

        for task in dag.ready_tasks(completed_ids):
            compatible = self.registry.compatible(task.task_type)
            if not compatible:
                records.append(AcquisitionRecord(
                    task.task_id, "", None, False,
                    f"no allowlisted tool for task type {task.task_type.value}",
                ))
                continue

            tool = compatible[0]
            result = self.executor.execute(tool.name, task)
            record, item = self._convert_result(plan, task, result)
            records.append(record)
            if item is not None:
                new_items.append(item)
                completed_ids.add(task.task_id)

        merged = self._merge(bundle, new_items)
        return AcquisitionOutcome(merged, frozenset(completed_ids), tuple(records))

    @staticmethod
    def _convert_result(plan: InvestigationPlan, task: InvestigationTask,
                        result: ToolResult) -> tuple[AcquisitionRecord, EvidenceItem | None]:
        if not result.succeeded:
            return AcquisitionRecord(
                task.task_id, result.tool_name, None, False, result.error,
            ), None

        evidence_id = f"acquired:{plan.plan_id}:{task.task_id}:{result.tool_name}"
        observed_at = result.payload.get("observed_at")
        item = EvidenceItem(
            evidence_id=evidence_id,
            kind=EvidenceKind.LIFECYCLE,
            source=f"orchestration.tool:{result.tool_name}",
            observed_at=str(observed_at) if observed_at is not None else datetime.now(timezone.utc).isoformat(),
            payload={
                "plan_id": plan.plan_id,
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "objective": task.objective,
                "tool_name": result.tool_name,
                "result": dict(result.payload),
            },
        )
        return AcquisitionRecord(task.task_id, result.tool_name, evidence_id, True), item

    @staticmethod
    def _merge(bundle: EvidenceBundle, additions: list[EvidenceItem]) -> EvidenceBundle:
        existing = set(bundle.evidence_ids)
        for item in additions:
            if item.evidence_id in existing:
                raise ValueError(f"duplicate acquired evidence ID: {item.evidence_id}")
            existing.add(item.evidence_id)
        evidence = tuple(sorted(bundle.evidence + tuple(additions), key=lambda item: item.evidence_id))
        return EvidenceBundle(bundle.incident_id, bundle.schema_version, evidence)
