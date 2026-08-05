from aegis.response.actions import ActionSeverity, ActionType, ResponseAction


def test_response_action_serialization() -> None:
    action = ResponseAction(
        action_id="act-123",
        target_id="plc-01",
        action_type=ActionType.ISOLATE_ASSET,
        severity=ActionSeverity.HIGH,
        description="Isolate PLC-01 from network",
        parameters={"asset_id": "plc-01"},
        reversible=True,
        requires_approval=True,
    )
    d = action.to_dict()
    assert d["action_id"] == "act-123"
    assert d["action_type"] == "isolate_asset"
    assert d["severity"] == "high"
    assert d["reversible"] is True
    assert d["requires_approval"] is True
