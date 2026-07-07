from aegis.correlation.enrichment import AlertEnricher
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType


def build_topology() -> AssetTopology:
    topology = AssetTopology()
    topology.add_asset(Asset("gw-01", AssetType.GATEWAY, "Gateway 01", 0.8, "dmz"))
    topology.add_asset(Asset("plc-01", AssetType.PLC, "PLC 01", 0.95, "cell-a"))
    topology.add_asset(Asset("pump-01", AssetType.ACTUATOR, "Pump 01", 1.0, "cell-a"))
    topology.add_relationship(AssetRelationship("gw-01", "plc-01", RelationshipType.CONNECTS_TO))
    topology.add_relationship(AssetRelationship("plc-01", "pump-01", RelationshipType.CONTROLS))
    return topology


def test_topology_neighbors_and_distance() -> None:
    topology = build_topology()
    assert topology.neighbors("gw-01", 1) == {"plc-01"}
    assert topology.neighbors("gw-01", 2) == {"plc-01", "pump-01"}
    assert topology.shortest_distance("gw-01", "pump-01") == 2


def test_relationship_rejects_unknown_endpoint() -> None:
    topology = build_topology()
    try:
        topology.add_relationship(AssetRelationship("ghost", "pump-01", RelationshipType.FEEDS))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_alert_enrichment_adds_topology_and_detector_evidence() -> None:
    alert = {
        "alert_id": "a-1", "event_id": "e-1", "device_id": "plc-01",
        "metric": "pressure", "value": 92.0, "unified_score": 0.91,
        "severity": "critical", "status": "open", "created_at": "2026-07-07T06:00:00+00:00",
        "detector_scores": {"z_score": 0.4, "ewma_score": 0.5, "isolation_score": 0.6,
                            "temporal_score": 0.92, "model_generation": 4},
    }
    enriched = AlertEnricher(build_topology()).enrich(alert)
    assert enriched.asset_type == "plc"
    assert enriched.asset_criticality == 0.95
    assert enriched.attack_family == "temporal"
    assert set(enriched.related_assets) == {"gw-01", "pump-01"}
    assert enriched.evidence.model_generation == 4
