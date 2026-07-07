from aegis.correlation.engine import CorrelationEngine
from aegis.correlation.enrichment import DetectorEvidence, EnrichedAlert
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType


def topology() -> AssetTopology:
    graph = AssetTopology()
    graph.add_asset(Asset("gw", AssetType.GATEWAY, "Gateway", 0.8, "dmz"))
    graph.add_asset(Asset("plc", AssetType.PLC, "PLC", 0.95, "cell-a"))
    graph.add_asset(Asset("pump", AssetType.ACTUATOR, "Pump", 1.0, "cell-a"))
    graph.add_asset(Asset("remote", AssetType.SENSOR, "Remote Sensor", 0.3, "cell-z"))
    graph.add_relationship(AssetRelationship("gw", "plc", RelationshipType.CONNECTS_TO))
    graph.add_relationship(AssetRelationship("plc", "pump", RelationshipType.CONTROLS))
    return graph


def alert(alert_id: str, asset_id: str, metric: str, created_at: str, zone: str, family: str) -> EnrichedAlert:
    return EnrichedAlert(
        alert_id, f"event-{alert_id}", asset_id, "plc", metric, 1.0, 0.9, "high", "open",
        created_at, family, DetectorEvidence(), 0.9, zone, (),
    )


def test_nearby_related_alerts_are_correlated_with_evidence() -> None:
    engine = CorrelationEngine(topology())
    left = alert("a1", "plc", "pressure", "2026-07-07T10:00:00+00:00", "cell-a", "temporal")
    right = alert("a2", "pump", "flow", "2026-07-07T10:00:30+00:00", "cell-a", "temporal")
    edge = engine.correlate(left, right)
    assert edge.correlated
    assert edge.score >= 0.55
    assert edge.evidence.topology_distance == 1
    assert edge.evidence.same_zone
    assert edge.evidence.metric_score == 0.6


def test_distant_unrelated_alerts_are_not_correlated() -> None:
    engine = CorrelationEngine(topology())
    left = alert("a1", "plc", "pressure", "2026-07-07T10:00:00+00:00", "cell-a", "point")
    right = alert("a2", "remote", "humidity", "2026-07-07T11:00:00+00:00", "cell-z", "temporal")
    edge = engine.correlate(left, right)
    assert not edge.correlated
    assert edge.evidence.topology_distance is None
    assert edge.evidence.temporal_score == 0.0


def test_build_edges_returns_only_correlated_pairs_ranked() -> None:
    engine = CorrelationEngine(topology())
    alerts = [
        alert("a1", "plc", "pressure", "2026-07-07T10:00:00+00:00", "cell-a", "temporal"),
        alert("a2", "pump", "flow", "2026-07-07T10:00:20+00:00", "cell-a", "temporal"),
        alert("a3", "remote", "humidity", "2026-07-07T12:00:00+00:00", "cell-z", "point"),
    ]
    edges = engine.build_edges(alerts)
    assert len(edges) == 1
    assert {edges[0].source_alert_id, edges[0].target_alert_id} == {"a1", "a2"}
