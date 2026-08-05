from __future__ import annotations

import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum

from aegis.common.storage import TelemetryStore
from aegis.response.actions import ActionSeverity, ResponseAction


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ResponseApprovalRequest:
    request_id: str
    plan_id: str
    action_id: str
    action_type: str
    severity: ActionSeverity
    approver: str | None
    state: ApprovalState
    reason: str | None
    created_at: str
    decided_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "severity": self.severity.value,
            "state": self.state.value,
        }


class ResponseApprovalEngine:
    """Enforce mandatory human-in-the-loop authorization gates for response actions."""

    def __init__(self, storage: TelemetryStore) -> None:
        self.db_path = storage.db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS response_approvals (
                    request_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    approver TEXT,
                    state TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_approval_plan ON response_approvals(plan_id)"
            )

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> ResponseApprovalRequest:
        item = dict(row)
        return ResponseApprovalRequest(
            request_id=str(item["request_id"]),
            plan_id=str(item["plan_id"]),
            action_id=str(item["action_id"]),
            action_type=str(item["action_type"]),
            severity=ActionSeverity(str(item["severity"])),
            approver=str(item["approver"]) if item["approver"] else None,
            state=ApprovalState(str(item["state"])),
            reason=str(item["reason"]) if item["reason"] else None,
            created_at=str(item["created_at"]),
            decided_at=str(item["decided_at"]) if item["decided_at"] else None,
        )

    def request_approval(self, plan_id: str, action: ResponseAction) -> ResponseApprovalRequest:
        request_id = f"req-{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC).isoformat()
        initial_state = ApprovalState.APPROVED if not action.requires_approval else ApprovalState.PENDING

        request = ResponseApprovalRequest(
            request_id=request_id,
            plan_id=plan_id,
            action_id=action.action_id,
            action_type=action.action_type.value,
            severity=action.severity,
            approver="system.auto" if not action.requires_approval else None,
            state=initial_state,
            reason=None,
            created_at=now,
            decided_at=now if not action.requires_approval else None,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO response_approvals (
                    request_id, plan_id, action_id, action_type, severity,
                    approver, state, reason, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id, request.plan_id, request.action_id,
                    request.action_type, request.severity.value, request.approver,
                    request.state.value, request.reason, request.created_at, request.decided_at,
                ),
            )
        return request

    def get(self, request_id: str) -> ResponseApprovalRequest:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM response_approvals WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"approval request not found: {request_id}")
        return self._deserialize(row)

    def grant(self, request_id: str, approver: str, reason: str | None = None) -> ResponseApprovalRequest:
        request = self.get(request_id)
        if request.state != ApprovalState.PENDING:
            raise ValueError(f"cannot approve request in state {request.state.value}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE response_approvals
                SET state = ?, approver = ?, reason = ?, decided_at = ?
                WHERE request_id = ?
                """,
                (ApprovalState.APPROVED.value, approver, reason, now, request_id),
            )
        return self.get(request_id)

    def reject(self, request_id: str, approver: str, reason: str) -> ResponseApprovalRequest:
        request = self.get(request_id)
        if request.state != ApprovalState.PENDING:
            raise ValueError(f"cannot reject request in state {request.state.value}")

        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE response_approvals
                SET state = ?, approver = ?, reason = ?, decided_at = ?
                WHERE request_id = ?
                """,
                (ApprovalState.REJECTED.value, approver, reason, now, request_id),
            )
        return self.get(request_id)
