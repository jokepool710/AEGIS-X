from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum

from aegis.common.storage import TelemetryStore
from aegis.investigation.artifact_store import InvestigationArtifactStore
from aegis.investigation.investigator import IncidentInvestigator
from aegis.orchestration.orchestrator import Phase5Orchestrator
from aegis.orchestration.tools import ToolRegistry
from aegis.workflow.feedback import AnalystFeedback, FeedbackEngine
from aegis.workflow.provenance import CaseEvidenceProvenance, EvidenceChainOfCustody


class CaseStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CLOSED = "closed"
    ARCHIVED = "archived"


CASE_TRANSITIONS = {
    CaseStatus.DRAFT: {CaseStatus.IN_REVIEW, CaseStatus.CLOSED},
    CaseStatus.IN_REVIEW: {CaseStatus.APPROVED, CaseStatus.DRAFT, CaseStatus.CLOSED},
    CaseStatus.APPROVED: {CaseStatus.CLOSED, CaseStatus.ARCHIVED},
    CaseStatus.CLOSED: {CaseStatus.ARCHIVED, CaseStatus.IN_REVIEW},
    CaseStatus.ARCHIVED: set(),
}


@dataclass(frozen=True)
class InvestigationCase:
    case_id: str
    incident_id: str
    title: str
    status: CaseStatus
    assignee: str | None
    created_at: str
    updated_at: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "status": self.status.value,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CaseDossier:
    case: InvestigationCase
    investigation: dict[str, object]
    orchestration: dict[str, object] | None
    feedback: tuple[AnalystFeedback, ...]
    provenance: CaseEvidenceProvenance

    def to_dict(self) -> dict[str, object]:
        return {
            "case": self.case.to_dict(),
            "investigation": self.investigation,
            "orchestration": self.orchestration,
            "feedback": [f.to_dict() for f in self.feedback],
            "provenance": self.provenance.to_dict(),
        }


class InvestigationCaseStore:
    """Manage lifecycle and persistent storage for security investigation cases."""

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
                CREATE TABLE IF NOT EXISTS investigation_cases (
                    case_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    notes_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_case_incident ON investigation_cases(incident_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_case_status ON investigation_cases(status)"
            )

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> InvestigationCase:
        item = dict(row)
        return InvestigationCase(
            case_id=str(item["case_id"]),
            incident_id=str(item["incident_id"]),
            title=str(item["title"]),
            status=CaseStatus(str(item["status"])),
            assignee=str(item["assignee"]) if item["assignee"] else None,
            created_at=str(item["created_at"]),
            updated_at=str(item["updated_at"]),
            notes=tuple(json.loads(str(item["notes_json"]))),
        )

    def create(self, incident_id: str, title: str | None = None, assignee: str | None = None) -> InvestigationCase:
        case_id = f"case-{uuid.uuid4().hex[:10]}"
        case_title = title or f"Investigation Case for Incident {incident_id}"
        now = datetime.now(UTC).isoformat()

        case = InvestigationCase(
            case_id=case_id,
            incident_id=incident_id,
            title=case_title,
            status=CaseStatus.DRAFT,
            assignee=assignee,
            created_at=now,
            updated_at=now,
            notes=(),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO investigation_cases (
                    case_id, incident_id, title, status, assignee,
                    created_at, updated_at, notes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.case_id, case.incident_id, case.title, case.status.value,
                    case.assignee, case.created_at, case.updated_at, json.dumps([]),
                ),
            )
        return case

    def get(self, case_id: str) -> InvestigationCase:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM investigation_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"investigation case not found: {case_id}")
        return self._deserialize(row)

    def list(self, status: CaseStatus | None = None, limit: int = 100) -> tuple[InvestigationCase, ...]:
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM investigation_cases ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM investigation_cases WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status.value, limit),
                ).fetchall()
        return tuple(self._deserialize(row) for row in rows)

    def transition(self, case_id: str, new_status: CaseStatus, note: str | None = None) -> InvestigationCase:
        case = self.get(case_id)
        if new_status == case.status:
            return case
        if new_status not in CASE_TRANSITIONS[case.status]:
            raise ValueError(f"cannot transition case from {case.status.value} to {new_status.value}")

        now = datetime.now(UTC).isoformat()
        notes = list(case.notes)
        if note:
            notes.append(f"[{now}] Transitioned to {new_status.value}: {note}")

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE investigation_cases
                SET status = ?, updated_at = ?, notes_json = ?
                WHERE case_id = ?
                """,
                (new_status.value, now, json.dumps(notes), case_id),
            )
        return self.get(case_id)

    def build_dossier(self, case_id: str, tool_registry: ToolRegistry | None = None) -> CaseDossier:
        case = self.get(case_id)
        artifact_store = InvestigationArtifactStore(self.storage)
        analysis = artifact_store.get(case.incident_id)

        investigation_result = IncidentInvestigator().investigate(analysis)
        investigation_payload = investigation_result.to_dict()

        orchestration_payload: dict[str, object] | None = None
        if tool_registry is not None:
            orchestration_outcome = Phase5Orchestrator(tool_registry, self.storage).run_cycle(investigation_result)
            orchestration_payload = {
                "incident_id": orchestration_outcome.incident_id,
                "plan_id": orchestration_outcome.plan_id,
                "completed_tasks": list(orchestration_outcome.acquisition.completed_task_ids),
                "ledger_integrity": orchestration_outcome.ledger_integrity,
                "recommendations_count": len(orchestration_outcome.recommendations),
            }

        feedback = FeedbackEngine(self.storage).list_by_case(case_id)
        evidence_bundle = Phase5Orchestrator._bundle(investigation_result.evidence)

        chain = EvidenceChainOfCustody(self.storage)
        provenance = chain.record_bundle(case_id, evidence_bundle)

        return CaseDossier(
            case=case,
            investigation=investigation_payload,
            orchestration=orchestration_payload,
            feedback=feedback,
            provenance=provenance,
        )
