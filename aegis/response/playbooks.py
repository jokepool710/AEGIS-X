from __future__ import annotations

import uuid
from dataclasses import dataclass

from aegis.response.actions import ActionSeverity, ActionType, ResponseAction


@dataclass(frozen=True)
class ResponsePlaybook:
    playbook_id: str
    name: str
    target_technique: str
    applicable_severity: ActionSeverity
    recommended_actions: tuple[ResponseAction, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "target_technique": self.target_technique,
            "applicable_severity": self.applicable_severity.value,
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
        }


class PlaybookEngine:
    """Generate recommended response playbooks based on incident risk, attack techniques, and asset targets."""

    @staticmethod
    def generate_playbook(incident_id: str, technique_id: str,
                          risk_score: float, affected_assets: list[str]) -> ResponsePlaybook:
        severity = (
            ActionSeverity.CRITICAL if risk_score >= 0.85
            else ActionSeverity.HIGH if risk_score >= 0.65
            else ActionSeverity.MEDIUM if risk_score >= 0.40
            else ActionSeverity.LOW
        )

        actions: list[ResponseAction] = []
        target_asset = affected_assets[0] if affected_assets else "unknown-asset"

        # Forensic snapshot for all incidents
        actions.append(ResponseAction(
            action_id=f"act-{uuid.uuid4().hex[:8]}",
            target_id=target_asset,
            action_type=ActionType.TAKE_FORENSIC_SNAPSHOT,
            severity=ActionSeverity.LOW,
            description=f"Capture volatile memory and logs for asset {target_asset}",
            parameters={"asset_id": target_asset},
            reversible=False,
            requires_approval=False,
        ))

        # Technique-specific containment
        if technique_id in {"T0831", "T0855", "T0832"}:
            actions.append(ResponseAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                target_id=target_asset,
                action_type=ActionType.SET_SAFE_STATE,
                severity=ActionSeverity.HIGH,
                description=f"Force asset {target_asset} into safe operational state",
                parameters={"asset_id": target_asset, "safe_mode": "manual_override"},
                reversible=True,
                requires_approval=True,
            ))
        else:
            actions.append(ResponseAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                target_id=target_asset,
                action_type=ActionType.ISOLATE_ASSET,
                severity=ActionSeverity.MEDIUM,
                description=f"Isolate network communications for asset {target_asset}",
                parameters={"asset_id": target_asset},
                reversible=True,
                requires_approval=True,
            ))

        # Emergency stop for critical operational risk
        if severity == ActionSeverity.CRITICAL:
            actions.append(ResponseAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                target_id=target_asset,
                action_type=ActionType.TRIGGER_EMERGENCY_STOP,
                severity=ActionSeverity.CRITICAL,
                description=f"Trigger emergency stop gate for critical asset {target_asset}",
                parameters={"asset_id": target_asset, "safety_interlock": True},
                reversible=True,
                requires_approval=True,
            ))

        return ResponsePlaybook(
            playbook_id=f"pb-{incident_id}-{technique_id}",
            name=f"Playbook for {technique_id} Containment",
            target_technique=technique_id,
            applicable_severity=severity,
            recommended_actions=tuple(actions),
        )
