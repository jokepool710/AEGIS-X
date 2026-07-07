import json
import sqlite3
from datetime import datetime, timezone

from aegis.common.storage import TelemetryStore
from aegis.correlation.incidents import Incident, INCIDENT_STATUSES, INCIDENT_TRANSITIONS, SEVERITY_RANK


class IncidentNotFoundError(LookupError):
    pass


class PersistentIncidentStore:
    def __init__(self, telemetry_store: TelemetryStore) -> None:
        self.db_path = telemetry_store.db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    affected_assets TEXT NOT NULL,
                    attack_families TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    updated_at TEXT,
                    status_note TEXT
                );
                CREATE TABLE IF NOT EXISTS incident_alerts (
                    incident_id TEXT NOT NULL,
                    alert_id TEXT NOT NULL UNIQUE,
                    PRIMARY KEY (incident_id, alert_id),
                    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_incident_last_seen ON incidents(last_seen);
                CREATE INDEX IF NOT EXISTS idx_incident_status ON incidents(status);
                CREATE INDEX IF NOT EXISTS idx_incident_alert ON incident_alerts(alert_id);
                """
            )

    def _deserialize(self, connection: sqlite3.Connection, row: sqlite3.Row) -> Incident:
        alert_rows = connection.execute(
            "SELECT alert_id FROM incident_alerts WHERE incident_id = ? ORDER BY rowid", (row["incident_id"],)
        ).fetchall()
        return Incident(
            incident_id=str(row["incident_id"]),
            alert_ids=tuple(str(item["alert_id"]) for item in alert_rows),
            affected_assets=tuple(json.loads(str(row["affected_assets"]))),
            attack_families=tuple(json.loads(str(row["attack_families"]))),
            first_seen=str(row["first_seen"]), last_seen=str(row["last_seen"]),
            confidence=float(row["confidence"]), severity=str(row["severity"]), status=str(row["status"]),
            updated_at=row["updated_at"], status_note=row["status_note"],
        )

    def get(self, incident_id: str) -> Incident:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
            if row is None:
                raise IncidentNotFoundError(incident_id)
            return self._deserialize(connection, row)

    def list(self, status: str | None = None, limit: int = 100) -> list[Incident]:
        if status is not None and status not in INCIDENT_STATUSES:
            raise ValueError(f"unknown incident status: {status}")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute("SELECT * FROM incidents ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM incidents WHERE status = ? ORDER BY last_seen DESC LIMIT ?", (status, limit)
                ).fetchall()
            return [self._deserialize(connection, row) for row in rows]

    def _find_overlaps(self, connection: sqlite3.Connection, alert_ids: tuple[str, ...]) -> list[str]:
        if not alert_ids:
            return []
        placeholders = ",".join("?" for _ in alert_ids)
        rows = connection.execute(
            f"SELECT DISTINCT incident_id FROM incident_alerts WHERE alert_id IN ({placeholders})", alert_ids
        ).fetchall()
        return [str(row["incident_id"]) for row in rows]

    def upsert_cluster(self, candidate: Incident) -> Incident:
        with self._connect() as connection:
            overlaps = self._find_overlaps(connection, candidate.alert_ids)
            existing = []
            for incident_id in overlaps:
                row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
                if row is not None:
                    existing.append(self._deserialize(connection, row))

            target_id = existing[0].incident_id if existing else candidate.incident_id
            all_alerts = set(candidate.alert_ids)
            all_assets = set(candidate.affected_assets)
            all_families = set(candidate.attack_families)
            first_seen = candidate.first_seen
            last_seen = candidate.last_seen
            confidence_values = [candidate.confidence]
            severities = [candidate.severity]
            status = "open"
            status_note = None
            for incident in existing:
                all_alerts.update(incident.alert_ids)
                all_assets.update(incident.affected_assets)
                all_families.update(incident.attack_families)
                first_seen = min(first_seen, incident.first_seen)
                last_seen = max(last_seen, incident.last_seen)
                confidence_values.append(incident.confidence)
                severities.append(incident.severity)
                if incident.status not in {"resolved", "dismissed"}:
                    status = incident.status
                    status_note = incident.status_note

            confidence = max(confidence_values)
            severity = max(severities, key=lambda value: SEVERITY_RANK.get(value, 0))
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """INSERT INTO incidents (incident_id, affected_assets, attack_families, first_seen, last_seen,
                   confidence, severity, status, updated_at, status_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(incident_id) DO UPDATE SET affected_assets=excluded.affected_assets,
                   attack_families=excluded.attack_families, first_seen=excluded.first_seen, last_seen=excluded.last_seen,
                   confidence=excluded.confidence, severity=excluded.severity, status=excluded.status,
                   updated_at=excluded.updated_at, status_note=excluded.status_note""",
                (target_id, json.dumps(sorted(all_assets)), json.dumps(sorted(all_families)), first_seen, last_seen,
                 confidence, severity, status, now, status_note),
            )
            for incident in existing[1:]:
                connection.execute("UPDATE incident_alerts SET incident_id = ? WHERE incident_id = ?", (target_id, incident.incident_id))
                connection.execute("DELETE FROM incidents WHERE incident_id = ?", (incident.incident_id,))
            for alert_id in all_alerts:
                connection.execute(
                    "INSERT OR IGNORE INTO incident_alerts (incident_id, alert_id) VALUES (?, ?)", (target_id, alert_id)
                )
        return self.get(target_id)

    def transition(self, incident_id: str, new_status: str, note: str | None = None) -> Incident:
        current = self.get(incident_id)
        if new_status not in INCIDENT_STATUSES:
            raise ValueError(f"unknown incident status: {new_status}")
        if new_status == current.status:
            return current
        if new_status not in INCIDENT_TRANSITIONS[current.status]:
            raise ValueError(f"cannot transition incident from {current.status} to {new_status}")
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE incidents SET status = ?, updated_at = ?, status_note = ? WHERE incident_id = ?",
                (new_status, now, note, incident_id),
            )
        return self.get(incident_id)
