from fastapi.testclient import TestClient

from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import PersistentIncidentStore
from aegis.correlation.pipeline import Phase3Pipeline
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType
from apps.api.main import app


def build_topology() -> AssetTopology:
    topology = AssetTopology()
    topology.add_asset(Asset("gw-01", AssetType.GATEWAY, "Gateway 01", 0.85, "cell-a"))
    topology.add_asset(Asset("plc-01", AssetType.PLC, "PLC 01", 0.95, "cell-a"))
    topology.add_asset(Asset("pump-01", AssetType.ACTUATOR, "Pump 01", 1.0, "cell-a"))
    topology.add_relationship(AssetRelationship("gw-01", "plc-01", RelationshipType.CONNECTS_TO))
    topology.add_relationship(AssetRelationship("plc-01", "pump-01", RelationshipType.CONTROLS))
    return topology


def raw_alert(alert_id: str, device_id: str, metric: str, created_at: str,
              temporal: float, z_score: float = 0.2) -> dict[str, object]:
    return {
        "alert_id": alert_id, "event_id": f"event-{alert_id}", "device_id": device_id,
        "metric": metric, "value": 90.0, "unified_score": 0.92,
        "severity": "critical", "status": "open", "created_at": created_at,
        "detector_scores": {
            "z_score": z_score, "ewma_score": 0.3, "isolation_score": 0.4,
            "temporal_score": temporal, "contextual_score": 0.0, "model_generation": 2,
        },
    }


def test_phase3_alerts_to_correlation_graph_mapping_risk_persistence_and_api(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "phase3-e2e.db"
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(db_path))
    telemetry_store = TelemetryStore(str(db_path))
    incident_store = PersistentIncidentStore(telemetry_store)
    pipeline = Phase3Pipeline(build_topology(), incident_store)

    alerts = [
        raw_alert("a1", "gw-01", "pressure", "2026-07-07T10:00:00+00:00", 0.95),
        raw_alert("a2", "plc-01", "pressure", "2026-07-07T10:00:20+00:00", 0.96),
        raw_alert("a3", "pump-01", "flow", "2026-07-07T10:00:40+00:00", 0.94),
    ]
    analyses = pipeline.run(alerts)
    assert len(analyses) == 1
    analysis = analyses[0]
    assert set(analysis.incident.alert_ids) == {"a1", "a2", "a3"}
    assert set(analysis.incident.affected_assets) == {"gw-01", "plc-01", "pump-01"}
    assert len(analysis.graph.nodes) == 6
    assert analysis.mappings
    assert analysis.risk.risk_score > 0.0
    assert analysis.risk.risk_level in {"medium", "high", "critical"}

    persisted = incident_store.get(analysis.incident.incident_id)
    assert persisted.incident_id == analysis.incident.incident_id

    with TestClient(app) as client:
        listing = client.get("/api/v1/incidents")
        assert listing.status_code == 200
        assert listing.json()["count"] == 1
        detail = client.get(f"/api/v1/incidents/{analysis.incident.incident_id}")
        assert detail.status_code == 200
        assert set(detail.json()["alert_ids"]) == {"a1", "a2", "a3"}
        transition = client.patch(
            f"/api/v1/incidents/{analysis.incident.incident_id}/status",
            json={"status": "investigating", "note": "phase3 e2e triage"},
        )
        assert transition.status_code == 200
        assert transition.json()["status"] == "investigating"
        assert transition.json()["status_note"] == "phase3 e2e triage"

    rerun = pipeline.run(alerts)[0]
    assert rerun.incident.incident_id == analysis.incident.incident_id
    assert len(incident_store.list()) == 1
