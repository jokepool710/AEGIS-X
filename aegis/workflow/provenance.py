from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from aegis.common.storage import TelemetryStore
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem


@dataclass(frozen=True)
class ProvenanceRecord:
    evidence_id: str
    kind: str
    source: str
    observed_at: str | None
    payload_hash: str
    custodian: str
    recorded_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CaseEvidenceProvenance:
    case_id: str
    incident_id: str
    evidence_count: int
    records: tuple[ProvenanceRecord, ...]
    is_valid: bool
    verification_note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "incident_id": self.incident_id,
            "evidence_count": self.evidence_count,
            "records": [record.to_dict() for record in self.records],
            "is_valid": self.is_valid,
            "verification_note": self.verification_note,
        }


class EvidenceChainOfCustody:
    """Track evidence provenance and compute SHA-256 chain-of-custody records for investigation cases."""

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
                CREATE TABLE IF NOT EXISTS evidence_provenance (
                    record_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    incident_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT,
                    payload_hash TEXT NOT NULL,
                    custodian TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_provenance_case ON evidence_provenance(case_id)"
            )

    @staticmethod
    def hash_item(item: EvidenceItem) -> str:
        content = f"{item.evidence_id}|{item.kind.value}|{item.source}|{item.observed_at}|{json.dumps(item.payload, sort_keys=True)}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def record_bundle(self, case_id: str, bundle: EvidenceBundle, custodian: str = "system.investigator") -> CaseEvidenceProvenance:
        records: list[ProvenanceRecord] = []
        now = datetime.now(UTC).isoformat()

        with self._connect() as connection:
            for item in bundle.evidence:
                payload_hash = self.hash_item(item)
                record_id = f"prv:{case_id}:{item.evidence_id}"
                record = ProvenanceRecord(
                    evidence_id=item.evidence_id,
                    kind=item.kind.value,
                    source=item.source,
                    observed_at=item.observed_at,
                    payload_hash=payload_hash,
                    custodian=custodian,
                    recorded_at=now,
                )
                connection.execute(
                    """
                    INSERT OR REPLACE INTO evidence_provenance (
                        record_id, case_id, incident_id, evidence_id, kind,
                        source, observed_at, payload_hash, custodian, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id, case_id, bundle.incident_id, record.evidence_id,
                        record.kind, record.source, record.observed_at,
                        record.payload_hash, record.custodian, record.recorded_at,
                    ),
                )
                records.append(record)

        return self.verify(case_id, bundle)

    def verify(self, case_id: str, bundle: EvidenceBundle) -> CaseEvidenceProvenance:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence_provenance WHERE case_id = ? ORDER BY evidence_id ASC",
                (case_id,),
            ).fetchall()

        if not rows:
            return CaseEvidenceProvenance(
                case_id=case_id,
                incident_id=bundle.incident_id,
                evidence_count=len(bundle.evidence),
                records=(),
                is_valid=False,
                verification_note="no provenance records found for case",
            )

        stored_map = {row["evidence_id"]: row["payload_hash"] for row in rows}
        records = tuple(
            ProvenanceRecord(
                evidence_id=str(row["evidence_id"]),
                kind=str(row["kind"]),
                source=str(row["source"]),
                observed_at=str(row["observed_at"]) if row["observed_at"] else None,
                payload_hash=str(row["payload_hash"]),
                custodian=str(row["custodian"]),
                recorded_at=str(row["recorded_at"]),
            )
            for row in rows
        )

        for item in bundle.evidence:
            current_hash = self.hash_item(item)
            expected_hash = stored_map.get(item.evidence_id)
            if expected_hash is None:
                return CaseEvidenceProvenance(
                    case_id=case_id,
                    incident_id=bundle.incident_id,
                    evidence_count=len(bundle.evidence),
                    records=records,
                    is_valid=False,
                    verification_note=f"unregistered evidence item: {item.evidence_id}",
                )
            if current_hash != expected_hash:
                return CaseEvidenceProvenance(
                    case_id=case_id,
                    incident_id=bundle.incident_id,
                    evidence_count=len(bundle.evidence),
                    records=records,
                    is_valid=False,
                    verification_note=f"tampered evidence payload hash for item: {item.evidence_id}",
                )

        return CaseEvidenceProvenance(
            case_id=case_id,
            incident_id=bundle.incident_id,
            evidence_count=len(bundle.evidence),
            records=records,
            is_valid=True,
            verification_note="all evidence items verified against tamper-evident provenance log",
        )
