from aegis.correlation.attack_graph import AttackGraphEngine, GraphEdgeType, GraphNodeType
from aegis.correlation.engine import CorrelationEdge, CorrelationEvidence
from aegis.correlation.enrichment import DetectorEvidence, EnrichedAlert
from aegis.correlation.incidents import Incident
from aegis.correlation.topology import Asset, AssetRelationship, AssetTopology, AssetType, RelationshipType


def topology() -> AssetTopology:
    graph = AssetTopology()
    graph.add_asset(Asset("gw", AssetType.GATEWAY, "Gateway", 0.8, "dmz"))
    graph.add_asset(Asset("plc", AssetType.PLC, "PLC", 0.95, "cell-a"))
    graph.add_asset(Asset("pump", AssetType.ACTUATOR, "Pump", 1.0, "cell-a"))
    graph.add_relationship(AssetRelationship("gw", "plc", RelationshipType.CONNECTS_TO))
    graph.add_relationship(AssetRelationship("plc", "pump", RelationshipType.CONTROLS))
    return graph


def alert(alert_id: str, asset_id: str, created_at: str, family: str) -> EnrichedAlert:
    return EnrichedAlert(alert_id, f"e-{alert_id}", asset_id, "plc", "pressure", 1.0, 0.9,
                         "high", "open", created_at, family, DetectorEvidence(temporal_score=0.9),
                         0.9, "cell-a", ())


def correlation(left: str, right: str, score: float = 0.85) -> CorrelationEdge:
    evidence = CorrelationEvidence(20.0, 0.93, False, 1, 1.0, True, 0.6, True)
    return CorrelationEdge(left, right, score, True, evidence)


def test_builds_asset_alert_topology_correlation_and_progression_edges() -> None:
    alerts = [
        alert("a1", "gw", "2026-07-07T10:00:00+00:00", "temporal"),
        alert("a2", "plc", "2026-07-07T10:00:20+00:00", "temporal"),
        alert("a3", "pump", "2026-07-07T10:00:40+00:00", "point"),
    ]
    incident = Incident("inc-1", ("a1", "a2", "a3"), ("gw", "plc", "pump"),
                        ("point", "temporal"), alerts[0].created_at, alerts[-1].created_at, 0.86, "critical")
    graph = AttackGraphEngine(topology()).build(
        incident, alerts, [correlation("a1", "a2"), correlation("a2", "a3", 0.78)]
    )
    assert len([n for n in graph.nodes if n.node_type == GraphNodeType.ALERT]) == 3
    assert len([n for n in graph.nodes if n.node_type == GraphNodeType.ASSET]) == 3
    edge_types = {edge.edge_type for edge in graph.edges}
    assert GraphEdgeType.OBSERVED_ON in edge_types
    assert GraphEdgeType.TOPOLOGY in edge_types
    assert GraphEdgeType.CORRELATED_WITH in edge_types
    assert GraphEdgeType.PROGRESSES_TO in edge_types


def test_graph_excludes_alerts_outside_incident() -> None:
    member = alert("a1", "gw", "2026-07-07T10:00:00+00:00", "temporal")
    outsider = alert("outside", "pump", "2026-07-07T10:00:10+00:00", "point")
    incident = Incident("inc-1", ("a1",), ("gw",), ("temporal",), member.created_at, member.created_at, 0.8, "high")
    graph = AttackGraphEngine(topology()).build(incident, [member, outsider], [])
    assert all("outside" not in node.node_id for node in graph.nodes)


def test_graph_serializes_enum_values_for_api_consumers() -> None:
    member = alert("a1", "gw", "2026-07-07T10:00:00+00:00", "temporal")
    incident = Incident("inc-1", ("a1",), ("gw",), ("temporal",), member.created_at, member.created_at, 0.8, "high")
    payload = AttackGraphEngine(topology()).build(incident, [member], []).to_dict()
    assert payload["nodes"][0]["node_type"] in {"alert", "asset"}
    assert all(edge["edge_type"] in {item.value for item in GraphEdgeType} for edge in payload["edges"])
