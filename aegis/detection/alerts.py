import json
import sqlite3
import uuid
from datetime import datetime, timezone

from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore
from aegis.detection.pipeline import DetectionResult

ALERT_STATUSES = {"open", "acknowledged", "investigating", "resolved", "dismissed"}
ALLOWED_TRANSITIONS = {
    "open": {"acknowledged", "investigating", "resolved", "dismissed"},
    "acknowledged": {"investigating", "resolved", "dismissed"},
    "investigating": {"resolved", "dismissed"},
    "resolved": set(),
    "dismissed": set(),
}


class AlertNotFoundError(LookupError):
    pass


class InvalidAlertTransitionError(ValueError):
    pass


class AlertStore:
    def __init__(self, telemetry_store: TelemetryStore) -> None:
        self.db_path = telemetry_store.db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    unified_score REAL NOT NULL,
                    detector_scores TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    updated_at TEXT,
                    status_note TEXT
                )
                """
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(alerts)").fetchall()
            }
            migrations = {
                "status": "ALTER TABLE alerts ADD COLUMN status TEXT NOT NULL DEFAULT 'open'",
                "updated_at": "ALTER TABLE alerts ADD COLUMN updated_at TEXT",
                "status_note": "ALTER TABLE alerts ADD COLUMN status_note TEXT",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_alert_created ON alerts(created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status)")

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> dict[str, object]:
        item = dict(row)
        item["detector_scores"] = json.loads(str(item["detector_scores"]))
        return item

    def create(self, event: TelemetryEvent, result: DetectionResult) -> str:
        alert_id = str(uuid.uuid4())
        scores = json.dumps(
            {
                "z_score": result.z_score,
                "ewma_score": result.ewma_score,
                "isolation_score": result.isolation_score,
                "model_generation": result.model_generation,
            }
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO alerts (
                    alert_id, event_id, device_id, metric, value, unified_score,
                    detector_scores, severity, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                """,
                (
                    alert_id, event.event_id, event.device_id, event.metric, event.value,
                    result.unified_score, scores, result.severity,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return alert_id

    def get(self, alert_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)
            ).fetchone()
        if row is None:
            raise AlertNotFoundError(alert_id)
        return self._deserialize(row)

    def list(self, limit: int = 100, status: str | None = None) -> list[dict[str, object]]:
        if status is not None and status not in ALERT_STATUSES:
            raise ValueError(f"unknown alert status: {status}")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM alerts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
        return [self._deserialize(row) for row in rows]

    def transition(self, alert_id: str, new_status: str, note: str | None = None) -> dict[str, object]:
        if new_status not in ALERT_STATUSES:
            raise InvalidAlertTransitionError(f"unknown status: {new_status}")
        current = self.get(alert_id)
        current_status = str(current["status"])
        if new_status == current_status:
            return current
        if new_status not in ALLOWED_TRANSITIONS[current_status]:
            raise InvalidAlertTransitionError(
                f"cannot transition alert from {current_status} to {new_status}"
            )
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE alerts SET status = ?, updated_at = ?, status_note = ? WHERE alert_id = ?",
                (new_status, now, note, alert_id),
            )
        return self.get(alert_id)
