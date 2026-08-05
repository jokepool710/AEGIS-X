from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from aegis.common.storage import TelemetryStore
from aegis.response.actions import ResponseAction
from aegis.response.approvals import ResponseApprovalEngine
from aegis.response.playbooks import PlaybookEngine, ResponsePlaybook


@dataclass(frozen=True)
class ResponsePlan:
    plan_id: str
    incident_id: str
    case_id: str | None
    playbooks: tuple[ResponsePlaybook, ...]
    actions: tuple[ResponseAction, ...]
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "incident_id": self.incident_id,
            "case_id": self.case_id,
            "playbooks": [pb.to_dict() for pb in self.playbooks],
            "actions": [act.to_dict() for act in self.actions],
            "created_at": self.created_at,
        }


class PersistentResponseStore:
    """Persist and query response plans, playbooks, and execution histories."""

    def __init__(self, storage: TelemetryStore) -> None:
        self.storage = storage
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
                CREATE TABLE IF NOT EXISTS response_plans (
                    plan_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    case_id TEXT,
                    plan_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_plan_incident ON response_plans(incident_id)"
            )

    def create_plan(self, incident_id: str, case_id: str | None = None,
                    technique_ids: tuple[str, ...] = ("T0831",),
                    risk_score: float = 0.75,
                    affected_assets: list[str] | None = None) -> ResponsePlan:
        plan_id = f"resp-{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC).isoformat()
        assets = affected_assets or ["plc-01", "pump-01"]

        playbooks = tuple(
            PlaybookEngine.generate_playbook(incident_id, tech_id, risk_score, assets)
            for tech_id in technique_ids
        )
        actions = tuple(
            action
            for pb in playbooks
            for action in pb.recommended_actions
        )

        plan = ResponsePlan(
            plan_id=plan_id,
            incident_id=incident_id,
            case_id=case_id,
            playbooks=playbooks,
            actions=actions,
            created_at=now,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO response_plans (plan_id, incident_id, case_id, plan_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (plan.plan_id, plan.incident_id, plan.case_id, json.dumps(plan.to_dict()), plan.created_at),
            )

        # Pre-create approval requests for actions requiring approval
        approval_engine = ResponseApprovalEngine(self.storage)
        for action in actions:
            approval_engine.request_approval(plan.plan_id, action)

        return plan

    def get_plan(self, plan_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT plan_json FROM response_plans WHERE plan_id = ?", (plan_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"response plan not found: {plan_id}")
        return json.loads(str(row["plan_json"]))
