import pytest

from aegis.orchestration.approvals import ApprovalStateError, ApprovalStatus, HumanApprovalGate
from aegis.orchestration.planning import InvestigationTask, TaskType


def task(parameters: dict[str, object] | None = None) -> InvestigationTask:
    return InvestigationTask(
        "inspect-plc", TaskType.INSPECT_ASSET, "Inspect PLC state",
        parameters=parameters or {"asset_id": "plc-01"},
    )


def test_approval_is_bound_to_exact_action_and_can_be_consumed_once() -> None:
    gate = HumanApprovalGate()
    request = gate.request("inc-1", "plan-1", task(), "controlled-inspector")
    approved = gate.decide(request.approval_id, "analyst-1", True, "validated scope")

    assert approved.status is ApprovalStatus.APPROVED
    consumed = gate.authorize(request.approval_id, task(), "controlled-inspector")
    assert consumed.status is ApprovalStatus.CONSUMED

    with pytest.raises(ApprovalStateError, match="active approval"):
        gate.authorize(request.approval_id, task(), "controlled-inspector")


def test_parameter_change_invalidates_approval() -> None:
    gate = HumanApprovalGate()
    request = gate.request("inc-1", "plan-1", task(), "controlled-inspector")
    gate.decide(request.approval_id, "analyst-1", True)

    changed = task({"asset_id": "plc-02"})
    with pytest.raises(ApprovalStateError, match="exact action parameters"):
        gate.authorize(request.approval_id, changed, "controlled-inspector")


def test_tool_change_invalidates_approval() -> None:
    gate = HumanApprovalGate()
    request = gate.request("inc-1", "plan-1", task(), "controlled-inspector")
    gate.decide(request.approval_id, "analyst-1", True)

    with pytest.raises(ApprovalStateError, match="exact action parameters"):
        gate.authorize(request.approval_id, task(), "other-tool")


def test_rejected_request_cannot_authorize_action() -> None:
    gate = HumanApprovalGate()
    request = gate.request("inc-1", "plan-1", task(), "controlled-inspector")
    rejected = gate.decide(request.approval_id, "analyst-1", False, "unsafe during production")

    assert rejected.status is ApprovalStatus.REJECTED
    with pytest.raises(ApprovalStateError, match="active approval"):
        gate.authorize(request.approval_id, task(), "controlled-inspector")


def test_decision_cannot_be_overwritten() -> None:
    gate = HumanApprovalGate()
    request = gate.request("inc-1", "plan-1", task(), "controlled-inspector")
    gate.decide(request.approval_id, "analyst-1", True)

    with pytest.raises(ApprovalStateError, match="already been decided"):
        gate.decide(request.approval_id, "analyst-2", False)
