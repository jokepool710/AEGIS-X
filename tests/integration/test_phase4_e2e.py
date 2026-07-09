from fastapi.testclient import TestClient

from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import PersistentIncidentStore
from aegis.correlation.pipeline import Phase3Pipeline
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType
from apps.api.main import app, register_incident_analysis


def topology() -> AssetTopology:
    result = AssetTopology()
    result.add_asset(Asset("gw-01", AssetType.GATEWAY, "Gateway", 0.85, "cell-a"))
    result.add_asset(Asset("plc-01", AssetType.PLC, "PLC", 0.95, "cell-a"))
    result.add_asset(Asset("pump-01", AssetType.ACTUATOR, "Pump", 1.0, "cell-a"))
    result.add_relationship(AssetRelationship("gw-01", "plc-01", RelationshipType.CONNECTS_TO))
    result.add_relationship(AssetRelationship("plc-01", "pump-01", RelationshipType.CONTROLS))
    return result


def alert(alert_id: str, device_id: str, metric: str, timestamp: str) -> dict[str, object]:
    return {
        "alert_id": alert_id, "event_id": f"event-{alert_id}", "device_id": device_id,
        "metric": metric, "value": 95.0, "unified_score": 0.96, "severity": "critical",
        "status": "open", "created_at": timestamp,
        "detector_scores": {
            "z_score": 0.8, "ewma_score": 0.7, "isolation_score": 0.6,
            "temporal_score": 0.98, "contextual_score": 0.4, "model_generation": 3,
        },
    }


def test_phase3_incident_to_grounded_phase4_investigation_api(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "phase4-e2e.db"
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(db_path))
    store = TelemetryStore(str(db_path))
    phase3 = Phase3Pipeline(topology(), PersistentIncidentStore(store))
    analysis = phase3.run([
        alert("a1", "gw-01", "pressure", "2026-07-09T10:00:00+00:00"),
        alert("a2", "plc-01", "pressure", "2026-07-09T10:00:20+00:00"),
        alert("a3", "pump-01", "flow", "2026-07-09T10:00:40+00:00"),
    ])[0]
    register_incident_analysis(analysis)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/incidents/{analysis.incident.incident_id}/investigation")

    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"] == analysis.incident.incident_id
    assert body["evidence"]["evidence"]
    assert body["timeline"]["events"]
    assert body["hypotheses"]
    assert len(body["hypotheses"]) == len(body["uncertainty"])
    assert body["narrative"]["cited_evidence_ids"]
    assert body["faithfulness"]["citation_validity"] == 1.0
    assert body["faithfulness"]["unsupported_claim_rate"] == 0.0
    available = {item["evidence_id"] for item in body["evidence"]["evidence"]}
    assert set(body["narrative"]["cited_evidence_ids"]) <= available


def test_investigation_api_rejects_unavailable_analysis() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/incidents/inc-missing/investigation")

    assert response.status_code == 404
    assert response.json()["detail"] == "incident analysis not available"
