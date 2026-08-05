from __future__ import annotations

import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum

from aegis.common.storage import TelemetryStore


class FeedbackType(str, Enum):
    ACCEPT_HYPOTHESIS = "accept_hypothesis"
    REJECT_HYPOTHESIS = "reject_hypothesis"
    ADJUST_CONFIDENCE = "adjust_confidence"
    FLAG_CONTRADICTION = "flag_contradiction"
    ADD_NOTE = "add_note"


@dataclass(frozen=True)
class AnalystFeedback:
    feedback_id: str
    case_id: str
    incident_id: str
    analyst_id: str
    feedback_type: FeedbackType
    target_id: str
    adjusted_confidence: float | None
    comment: str | None
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "feedback_type": self.feedback_type.value}


class FeedbackEngine:
    """Collect, persist, and aggregate human analyst feedback over investigation cases."""

    def __init__(self, storage: TelemetryStore) -> None:
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
                CREATE TABLE IF NOT EXISTS analyst_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    incident_id TEXT NOT NULL,
                    analyst_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    adjusted_confidence REAL,
                    comment TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_case ON analyst_feedback(case_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_incident ON analyst_feedback(incident_id)"
            )

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> AnalystFeedback:
        item = dict(row)
        return AnalystFeedback(
            feedback_id=str(item["feedback_id"]),
            case_id=str(item["case_id"]),
            incident_id=str(item["incident_id"]),
            analyst_id=str(item["analyst_id"]),
            feedback_type=FeedbackType(str(item["feedback_type"])),
            target_id=str(item["target_id"]),
            adjusted_confidence=float(item["adjusted_confidence"]) if item["adjusted_confidence"] is not None else None,
            comment=str(item["comment"]) if item["comment"] is not None else None,
            created_at=str(item["created_at"]),
        )

    def submit(self, case_id: str, incident_id: str, analyst_id: str,
               feedback_type: FeedbackType, target_id: str,
               adjusted_confidence: float | None = None,
               comment: str | None = None) -> AnalystFeedback:
        if adjusted_confidence is not None and not (0.0 <= adjusted_confidence <= 1.0):
            raise ValueError("adjusted confidence must be between 0.0 and 1.0")

        feedback_id = f"fbk-{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        feedback = AnalystFeedback(
            feedback_id, case_id, incident_id, analyst_id,
            feedback_type, target_id, adjusted_confidence, comment, now,
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analyst_feedback (
                    feedback_id, case_id, incident_id, analyst_id, feedback_type,
                    target_id, adjusted_confidence, comment, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.feedback_id, feedback.case_id, feedback.incident_id,
                    feedback.analyst_id, feedback.feedback_type.value, feedback.target_id,
                    feedback.adjusted_confidence, feedback.comment, feedback.created_at,
                ),
            )
        return feedback

    def list_by_case(self, case_id: str) -> tuple[AnalystFeedback, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analyst_feedback WHERE case_id = ? ORDER BY created_at ASC",
                (case_id,),
            ).fetchall()
        return tuple(self._deserialize(row) for row in rows)

    def list_by_incident(self, incident_id: str) -> tuple[AnalystFeedback, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM analyst_feedback WHERE incident_id = ? ORDER BY created_at ASC",
                (incident_id,),
            ).fetchall()
        return tuple(self._deserialize(row) for row in rows)

    def aggregate_hypothesis_score(self, case_id: str, hypothesis_id: str,
                                   base_confidence: float) -> float:
        feedback_list = [
            item for item in self.list_by_case(case_id)
            if item.target_id == hypothesis_id
        ]
        if not feedback_list:
            return round(base_confidence, 4)

        scores: list[float] = []
        for item in feedback_list:
            if item.feedback_type == FeedbackType.ACCEPT_HYPOTHESIS:
                scores.append(min(1.0, base_confidence + 0.15))
            elif item.feedback_type == FeedbackType.REJECT_HYPOTHESIS:
                scores.append(max(0.0, base_confidence - 0.35))
            elif item.feedback_type == FeedbackType.ADJUST_CONFIDENCE and item.adjusted_confidence is not None:
                scores.append(item.adjusted_confidence)

        if not scores:
            return round(base_confidence, 4)
        return round(sum(scores) / len(scores), 4)
