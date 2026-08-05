from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class ActionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    ISOLATE_ASSET = "isolate_asset"
    BLOCK_IP = "block_ip"
    SET_SAFE_STATE = "set_safe_state"
    TRIGGER_EMERGENCY_STOP = "trigger_emergency_stop"
    REVOKE_CREDENTIALS = "revoke_credentials"
    TAKE_FORENSIC_SNAPSHOT = "take_forensic_snapshot"
    DISABLE_PORT = "disable_port"


@dataclass(frozen=True)
class ResponseAction:
    action_id: str
    target_id: str
    action_type: ActionType
    severity: ActionSeverity
    description: str
    parameters: dict[str, object]
    reversible: bool
    requires_approval: bool

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "action_type": self.action_type.value,
            "severity": self.severity.value,
        }
