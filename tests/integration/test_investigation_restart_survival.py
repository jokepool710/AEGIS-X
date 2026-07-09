from fastapi.testclient import TestClient

from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import PersistentIncidentStore
from aegis.correlation.pipeline import Phase3Pipeline
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType
from aegis.investigation.artifact_store import InvestigationArtifactStore
from apps.api.main import app, register_incident_analysis


def topology() -> AssetTopology:
    result = AssetTopology()
    result.add_asset(Asset("gw-01", AssetType.GATEWAY, "Gateway", 0.85, "cell-a"))
    result.add_asset(Asset("plc-01", AssetType.PLC, "PLC", 0.95, "cell-a"))
    result.add_relationship(AssetRelationship("gw-01", "plc-01", RelationshipType.CONNECTS_TO))
    return result


def alert(alert_id: str, device_id: str, timestamp: str) -> dict[str, object]:
    return {
        "alert_id": alert_id,
        "event_id": f"event-{alert_id}",
        "device_id": device_id,
        "metric": "pressure",
        "value": 95.0,
        "unified_score": 0.96,
        "severity": "critical",
        "status": "open",
        "created_at": timestamp,
        "detector_scores": {
            "z_score": 0.8,
            "ewma_score": 0.7,
            "isolation_score": 0.6,
            "temporal_score": 0.98,
            "contextual_score": 0.4,
            "model_generation": 3,
        },
    }


def test_investigation_survives_store_and_api_reconstruction(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "restart-survival.db"
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(db_path))

    writer_storage = TelemetryStore(str(db_path))
    pipeline = Phase3Pipeline(topology(), PersistentIncidentStore(writer_storage))
    original = pipeline.run([
        alert("a1", "gw-01", "2026-07-09T10:00:00+00:00"),
        alert("a2", "plc-01", "2026-07-09T10:00:20+00:00"),
    ])[0]
    register_incident_analysis(original)

    # Simulate a restart boundary: discard writer-side objects and construct a new store.
    incident_id = original.incident.incident_id
    del original, pipeline, writer_storage
    reader_storage = TelemetryStore(str(db_path))
    restored = InvestigationArtifactStore(reader_storage).get(incident_id)

    assert restored.incident.incident_id == incident_id
    assert restored.graph.to_dict()
    assert restored.mappings
    assert restored.risk.incident_id == incident_id

    # The API creates its own storage/artifact-store instances and must reconstruct from disk.
    with TestClient(app) as client:
        response = client.get(f"/api/v1/incidents/{incident_id}/investigation")

    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"] == incident_id
    assert body["evidence"]["evidence"]
    assert body["timeline"]["events"]
    assert body["hypotheses"]
    assert body["narrative"]["cited_evidence_ids"]
    assert body["faithfulness"]["citation_validity"] == 1.0
    assert body["faithfulness"]["unsupported_claim_rate"] == 0.0
