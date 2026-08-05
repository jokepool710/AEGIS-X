from pathlib import Path

from aegis.common.storage import TelemetryStore
from aegis.response.approvals import ApprovalState, ResponseApprovalEngine
from aegis.response.executor import ExecutionStatus, ResponseExecutionEngine
from aegis.response.store import PersistentResponseStore


def test_phase7_response_orchestration_e2e(tmp_path: Path) -> None:
    storage = TelemetryStore(str(tmp_path / "phase7_e2e.db"))

    # 1. Create Response Plan
    response_store = PersistentResponseStore(storage)
    plan = response_store.create_plan(
        incident_id="inc-e2e-777",
        case_id="case-e2e-777",
        technique_ids=("T0831",),
        risk_score=0.90,
        affected_assets=["plc-01", "hmi-01"],
    )

    assert plan.plan_id.startswith("resp-")
    assert len(plan.playbooks) >= 1
    assert len(plan.actions) >= 2

    # 2. Check pending approval for high severity action
    approval_engine = ResponseApprovalEngine(storage)
    action_to_approve = next(a for a in plan.actions if a.requires_approval)

    # Find the auto-generated approval request for this action
    with approval_engine._connect() as conn:
        row = conn.execute(
            "SELECT request_id FROM response_approvals WHERE action_id = ?",
            (action_to_approve.action_id,),
        ).fetchone()

    request_id = str(row["request_id"])
    req = approval_engine.get(request_id)
    assert req.state == ApprovalState.PENDING

    # 3. Grant Human Approval
    granted = approval_engine.grant(request_id, approver="soc_lead_01", reason="Confirmed attack mitigation")
    assert granted.state == ApprovalState.APPROVED

    # 4. Execute Response Action
    executor = ResponseExecutionEngine(storage)
    res = executor.execute(
        plan_id=plan.plan_id,
        action=action_to_approve,
        approval_request_id=request_id,
    )
    assert res.status == ExecutionStatus.SUCCESS
    assert res.output["target_id"] == action_to_approve.target_id

    # 5. Roll back Response Action if reversible
    if action_to_approve.reversible:
        rolled_back = executor.rollback(res.execution_id)
        assert rolled_back.status == ExecutionStatus.ROLLED_BACK
