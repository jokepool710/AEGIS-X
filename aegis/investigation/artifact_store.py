import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from aegis.common.storage import TelemetryStore
from aegis.correlation.attack_graph import (
    AttackGraph,
    AttackGraphEdge,
    AttackGraphNode,
    GraphEdgeType,
    GraphNodeType,
)
from aegis.correlation.attack_mapping import ICSMapping
from aegis.correlation.incidents import Incident
from aegis.correlation.pipeline import IncidentAnalysis
from aegis.correlation.risk import RiskAssessment, RiskEvidence


class InvestigationArtifactNotFoundError(KeyError):
    pass


class InvestigationArtifactStore:
    """Durably persist the complete Phase 3 analysis required by Phase 4."""

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
                CREATE TABLE IF NOT EXISTS investigation_artifacts (
                    incident_id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    persisted_at TEXT NOT NULL
                )
                """
            )

    def save(self, analysis: IncidentAnalysis) -> None:
        payload = {
            "incident": asdict(analysis.incident),
            "graph": analysis.graph.to_dict(),
            "mappings": [asdict(item) for item in analysis.mappings],
            "risk": asdict(analysis.risk),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO investigation_artifacts
                    (incident_id, schema_version, payload_json, persisted_at)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    schema_version=excluded.schema_version,
                    payload_json=excluded.payload_json,
                    persisted_at=excluded.persisted_at
                """,
                (
                    analysis.incident.incident_id,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get(self, incident_id: str) -> IncidentAnalysis:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM investigation_artifacts WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
        if row is None:
            raise InvestigationArtifactNotFoundError(incident_id)
        return self._decode(json.loads(str(row["payload_json"])))

    @staticmethod
    def _decode(payload: dict[str, object]) -> IncidentAnalysis:
        incident_data = dict(payload["incident"])  # type: ignore[arg-type]
        for key in ("alert_ids", "affected_assets", "attack_families"):
            incident_data[key] = tuple(incident_data[key])
        incident = Incident(**incident_data)

        graph_data = dict(payload["graph"])  # type: ignore[arg-type]
        nodes = tuple(
            AttackGraphNode(
                str(item["node_id"]), GraphNodeType(str(item["node_type"])),
                str(item["label"]), dict(item["attributes"]),
            )
            for item in graph_data["nodes"]
        )
        edges = tuple(
            AttackGraphEdge(
                str(item["source_id"]), str(item["target_id"]),
                GraphEdgeType(str(item["edge_type"])), float(item["confidence"]),
                dict(item["attributes"]),
            )
            for item in graph_data["edges"]
        )
        graph = AttackGraph(str(graph_data["incident_id"]), nodes, edges)

        mappings = [
            ICSMapping(
                str(item["technique_id"]), str(item["technique_name"]),
                str(item["tactic"]), float(item["confidence"]), tuple(item["evidence"]),
            )
            for item in payload["mappings"]  # type: ignore[union-attr]
        ]
        risk_data = dict(payload["risk"])  # type: ignore[arg-type]
        evidence = RiskEvidence(**dict(risk_data.pop("evidence")))
        risk_data["reasons"] = tuple(risk_data["reasons"])
        risk = RiskAssessment(evidence=evidence, **risk_data)
        return IncidentAnalysis(incident, graph, mappings, risk)
