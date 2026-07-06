import json
import sqlite3
import uuid
from datetime import datetime, timezone

from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore
from aegis.detection.pipeline import DetectionResult


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
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_alert_created ON alerts(created_at)")

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
                "INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    alert_id,
                    event.event_id,
                    event.device_id,
                    event.metric,
                    event.value,
                    result.unified_score,
                    scores,
                    result.severity,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return alert_id

    def list(self, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["detector_scores"] = json.loads(str(item["detector_scores"]))
            result.append(item)
        return result
