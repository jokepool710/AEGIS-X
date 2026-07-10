from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from aegis.orchestration.planning import InvestigationTask


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    incident_id: str
    plan_id: str
    task_id: str
    tool_name: str
    action_digest: str
    requested_at: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    analyst_id: str | None = None
    decided_at: str | None = None
    reason: str | None = None


class ApprovalNotFoundError(KeyError):
    pass


class ApprovalStateError(RuntimeError):
    pass


class HumanApprovalGate:
    """Bind analyst decisions to exact task/tool/parameter tuples and prevent replay."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    @staticmethod
    def action_digest(task: InvestigationTask, tool_name: str) -> str:
        payload = {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "objective": task.objective,
            "parameters": task.parameters,
            "tool_name": tool_name,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def request(self, incident_id: str, plan_id: str,
                task: InvestigationTask, tool_name: str) -> ApprovalRequest:
        digest = self.action_digest(task, tool_name)
        approval_id = f"approval:{plan_id}:{task.task_id}:{digest[:12]}"
        existing = self._requests.get(approval_id)
        if existing is not None:
            return existing
        request = ApprovalRequest(
            approval_id, incident_id, plan_id, task.task_id, tool_name, digest,
            datetime.now(timezone.utc).isoformat(),
        )
        self._requests[approval_id] = request
        return request

    def decide(self, approval_id: str, analyst_id: str, approved: bool,
               reason: str | None = None) -> ApprovalRequest:
        current = self.get(approval_id)
        if current.status is not ApprovalStatus.PENDING:
            raise ApprovalStateError("approval request has already been decided")
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        updated = ApprovalRequest(
            current.approval_id, current.incident_id, current.plan_id,
            current.task_id, current.tool_name, current.action_digest,
            current.requested_at, status, analyst_id,
            datetime.now(timezone.utc).isoformat(), reason,
        )
        self._requests[approval_id] = updated
        return updated

    def authorize(self, approval_id: str, task: InvestigationTask,
                  tool_name: str) -> ApprovalRequest:
        current = self.get(approval_id)
        if current.status is not ApprovalStatus.APPROVED:
            raise ApprovalStateError("action does not have an active approval")
        if current.action_digest != self.action_digest(task, tool_name):
            raise ApprovalStateError("approval does not match exact action parameters")
        consumed = ApprovalRequest(
            current.approval_id, current.incident_id, current.plan_id,
            current.task_id, current.tool_name, current.action_digest,
            current.requested_at, ApprovalStatus.CONSUMED, current.analyst_id,
            current.decided_at, current.reason,
        )
        self._requests[approval_id] = consumed
        return consumed

    def get(self, approval_id: str) -> ApprovalRequest:
        try:
            return self._requests[approval_id]
        except KeyError as exc:
            raise ApprovalNotFoundError(approval_id) from exc
