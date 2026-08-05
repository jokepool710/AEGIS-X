import os
import sqlite3
from pathlib import Path

from aegis.common.models import TelemetryEvent


class TelemetryStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("TELEMETRY_DB_PATH", "data/aegis_telemetry.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    event_timestamp TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    source_topic TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    UNIQUE(device_id, sequence, metric)
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry_events(device_id, event_timestamp)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_metric_time ON telemetry_events(metric, event_timestamp)")

    def insert(self, event: TelemetryEvent) -> bool:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO telemetry_events (
                        event_id, device_id, device_type, site_id, event_timestamp,
                        sequence, metric, value, unit, quality, source_topic, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id, event.device_id, event.device_type, event.site_id,
                        event.timestamp.isoformat(), event.sequence, event.metric, event.value,
                        event.unit, event.quality, event.source_topic, event.ingested_at.isoformat(),
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM telemetry_events").fetchone()
            return int(row["count"])

    def health_stats(self) -> dict[str, int | str | None]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS stored_events,
                    COUNT(DISTINCT device_id) AS active_devices,
                    COUNT(DISTINCT metric) AS metric_streams,
                    MIN(ingested_at) AS first_ingested_at,
                    MAX(ingested_at) AS last_ingested_at
                FROM telemetry_events
                """
            ).fetchone()
            return {
                "stored_events": int(row["stored_events"]),
                "active_devices": int(row["active_devices"]),
                "metric_streams": int(row["metric_streams"]),
                "first_ingested_at": row["first_ingested_at"],
                "last_ingested_at": row["last_ingested_at"],
            }
