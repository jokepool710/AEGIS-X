from pathlib import Path

import pytest

from aegis.common.storage import TelemetryStore
from aegis.response.actions import ActionSeverity, ActionType, ResponseAction
from aegis.response.approvals import ApprovalState, ResponseApprovalEngine


@pytest.fixture
def store(tmp_path: Path) -> TelemetryStore:
    return TelemetryStore(str(tmp_path / "test_approvals.db"))


def test_approval_lifecycle(store: TelemetryStore) -> None:
    engine = ResponseApprovalEngine(store)
    action = ResponseAction(
        action_id="act-test",
        target_id="plc-01",
        action_type=ActionType.SET_SAFE_STATE,
        severity=ActionSeverity.HIGH,
        description="Set safe state",
        parameters={},
        reversible=True,
        requires_approval=True,
    )
    req = engine.request_approval(plan_id="plan-1", action=action)
    assert req.state == ApprovalState.PENDING

    # Grant approval
    granted = engine.grant(req.request_id, approver="analyst-1", reason="Authorized for containment")
    assert granted.state == ApprovalState.APPROVED
    assert granted.approver == "analyst-1"
