from __future__ import annotations

import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum

from aegis.common.storage import TelemetryStore
from aegis.response.actions import ResponseAction
from aegis.response.approvals import ApprovalState, ResponseApprovalEngine


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class ResponseExecutionResult:
    execution_id: str
    plan_id: str
    action_id: str
    action_type: str
    status: ExecutionStatus
    output: dict[str, object]
    error: str | None
    executed_at: str
    rolled_back_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "status": self.status.value,
        }


class ResponseExecutionEngine:
    """Execute authorized response actions and handle automated rollbacks."""

    def __init__(self, storage: TelemetryStore) -> None:
        self.storage = storage
        self.db_path = storage.db_path
        self.approval_engine = ResponseApprovalEngine(storage)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS response_executions (
                    execution_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    error TEXT,
                    executed_at TEXT NOT NULL,
                    rolled_back_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_plan ON response_executions(plan_id)"
            )

    def execute(self, plan_id: str, action: ResponseAction, approval_request_id: str | None = None) -> ResponseExecutionResult:
        if action.requires_approval:
            if not approval_request_id:
                raise PermissionError("action requires explicit human approval request ID")
            approval = self.approval_engine.get(approval_request_id)
            if approval.state != ApprovalState.APPROVED:
                raise PermissionError(f"cannot execute action with approval state {approval.state.value}")

        execution_id = f"exec-{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC).isoformat()

        # Simulated safe execution handler
        output = {
            "target_id": action.target_id,
            "action_type": action.action_type.value,
            "parameters": action.parameters,
            "status_message": f"Successfully performed {action.action_type.value} on {action.target_id}",
        }

        result = ResponseExecutionResult(
            execution_id=execution_id,
            plan_id=plan_id,
            action_id=action.action_id,
            action_type=action.action_type.value,
            status=ExecutionStatus.SUCCESS,
            output=output,
            error=None,
            executed_at=now,
            rolled_back_at=None,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO response_executions (
                    execution_id, plan_id, action_id, action_type, status,
                    output_json, error, executed_at, rolled_back_at
                ) VALUES (?, ?, ?, ?, ?, json(?), ?, ?, ?)
                """,
                (
                    result.execution_id, result.plan_id, result.action_id,
                    result.action_type, result.status.value,
                    sqlite3.Binary(str(output).encode()) if False else str(output).replace("'", '"'),
                    result.error, result.executed_at, result.rolled_back_at,
                ),
            )
        return result

    def rollback(self, execution_id: str) -> ResponseExecutionResult:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM response_executions WHERE execution_id = ?", (execution_id,)
            ).fetchone()

        if row is None:
            raise KeyError(f"execution record not found: {execution_id}")

        item = dict(row)
        if item["status"] == ExecutionStatus.ROLLED_BACK.value:
            raise ValueError(f"execution {execution_id} is already rolled back")

        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE response_executions
                SET status = ?, rolled_back_at = ?
                WHERE execution_id = ?
                """,
                (ExecutionStatus.ROLLED_BACK.value, now, execution_id),
            )

        return ResponseExecutionResult(
            execution_id=str(item["execution_id"]),
            plan_id=str(item["plan_id"]),
            action_id=str(item["action_id"]),
            action_type=str(item["action_type"]),
            status=ExecutionStatus.ROLLED_BACK,
            output={"rolled_back": True, "original_execution_id": execution_id},
            error=None,
            executed_at=str(item["executed_at"]),
            rolled_back_at=now,
        )
