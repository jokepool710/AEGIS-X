from pathlib import Path

import pytest

from aegis.common.storage import TelemetryStore
from aegis.response.actions import ActionSeverity, ActionType, ResponseAction
from aegis.response.approvals import ResponseApprovalEngine
from aegis.response.executor import ExecutionStatus, ResponseExecutionEngine


@pytest.fixture
def store(tmp_path: Path) -> TelemetryStore:
    return TelemetryStore(str(tmp_path / "test_executor.db"))


def test_execution_and_rollback(store: TelemetryStore) -> None:
    executor = ResponseExecutionEngine(store)
    approval_engine = ResponseApprovalEngine(store)

    action = ResponseAction(
        action_id="act-exec",
        target_id="pump-01",
        action_type=ActionType.ISOLATE_ASSET,
        severity=ActionSeverity.MEDIUM,
        description="Isolate pump",
        parameters={},
        reversible=True,
        requires_approval=True,
    )

    req = approval_engine.request_approval(plan_id="plan-exec", action=action)
    with pytest.raises(PermissionError):
        executor.execute(plan_id="plan-exec", action=action)

    approval_engine.grant(req.request_id, approver="lead-analyst")
    res = executor.execute(plan_id="plan-exec", action=action, approval_request_id=req.request_id)
    assert res.status == ExecutionStatus.SUCCESS

    # Rollback
    rb = executor.rollback(res.execution_id)
    assert rb.status == ExecutionStatus.ROLLED_BACK
