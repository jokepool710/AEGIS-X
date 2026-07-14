from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aegis.common.storage import TelemetryStore


class DecisionEventType(str, Enum):
    PLAN_CREATED = "plan_created"
    EVIDENCE_ACQUIRED = "evidence_acquired"
    CONFIDENCE_CHANGED = "confidence_changed"
    RECOMMENDATION_CREATED = "recommendation_created"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTHORIZATION_CONSUMED = "authorization_consumed"
    ANALYST_DECISION = "analyst_decision"


@dataclass(frozen=True)
class DecisionEvent:
    sequence: int
    event_id: str
    incident_id: str
    plan_id: str
    event_type: DecisionEventType
    actor_id: str
    payload: dict[str, Any]
    occurred_at: str
    previous_hash: str
    event_hash: str


class DecisionLedgerIntegrityError(RuntimeError):
    pass


class DecisionLedger:
    """Persistent append-only, hash-chained audit ledger for Phase 5 decisions."""

    GENESIS_HASH = "0" * 64

    def __init__(self, storage: TelemetryStore) -> None:
        self.db_path = storage.db_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_ledger (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    incident_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                )
                """
            )

    def append(self, incident_id: str, plan_id: str, event_type: DecisionEventType,
               actor_id: str, payload: dict[str, Any]) -> DecisionEvent:
        if not incident_id or not plan_id or not actor_id:
            raise ValueError("incident_id, plan_id, and actor_id are required")
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        occurred_at = datetime.now(timezone.utc).isoformat()
        event_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT event_hash FROM decision_ledger ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = str(row["event_hash"]) if row else self.GENESIS_HASH
            event_hash = self._hash(
                event_id, incident_id, plan_id, event_type.value, actor_id,
                payload_json, occurred_at, previous_hash,
            )
            cursor = connection.execute(
                """
                INSERT INTO decision_ledger
                    (event_id, incident_id, plan_id, event_type, actor_id,
                     payload_json, occurred_at, previous_hash, event_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, incident_id, plan_id, event_type.value, actor_id,
                 payload_json, occurred_at, previous_hash, event_hash),
            )
            sequence = int(cursor.lastrowid)
        return DecisionEvent(
            sequence, event_id, incident_id, plan_id, event_type, actor_id,
            json.loads(payload_json), occurred_at, previous_hash, event_hash,
        )

    def list(self, incident_id: str | None = None) -> tuple[DecisionEvent, ...]:
        query = "SELECT * FROM decision_ledger"
        params: tuple[object, ...] = ()
        if incident_id is not None:
            query += " WHERE incident_id = ?"
            params = (incident_id,)
        query += " ORDER BY sequence ASC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return tuple(self._decode(row) for row in rows)

    def verify_integrity(self) -> bool:
        events = self.list()
        previous_hash = self.GENESIS_HASH
        for event in events:
            payload_json = json.dumps(event.payload, sort_keys=True, separators=(",", ":"), default=str)
            expected = self._hash(
                event.event_id, event.incident_id, event.plan_id,
                event.event_type.value, event.actor_id, payload_json,
                event.occurred_at, previous_hash,
            )
            if event.previous_hash != previous_hash or event.event_hash != expected:
                raise DecisionLedgerIntegrityError(
                    f"decision ledger integrity failure at sequence {event.sequence}"
                )
            previous_hash = event.event_hash
        return True

    @staticmethod
    def _hash(event_id: str, incident_id: str, plan_id: str, event_type: str,
              actor_id: str, payload_json: str, occurred_at: str,
              previous_hash: str) -> str:
        canonical = "|".join((
            event_id, incident_id, plan_id, event_type, actor_id,
            payload_json, occurred_at, previous_hash,
        ))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(row: sqlite3.Row) -> DecisionEvent:
        return DecisionEvent(
            int(row["sequence"]), str(row["event_id"]), str(row["incident_id"]),
            str(row["plan_id"]), DecisionEventType(str(row["event_type"])),
            str(row["actor_id"]), json.loads(str(row["payload_json"])),
            str(row["occurred_at"]), str(row["previous_hash"]), str(row["event_hash"]),
        )
