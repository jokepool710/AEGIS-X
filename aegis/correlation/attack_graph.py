from dataclasses import asdict, dataclass
from enum import Enum

from aegis.correlation.engine import CorrelationEdge
from aegis.correlation.enrichment import EnrichedAlert
from aegis.correlation.incidents import Incident
from aegis.correlation.topology import AssetTopology


class GraphNodeType(str, Enum):
    ASSET = "asset"
    ALERT = "alert"


class GraphEdgeType(str, Enum):
    OBSERVED_ON = "observed_on"
    TOPOLOGY = "topology"
    CORRELATED_WITH = "correlated_with"
    PROGRESSES_TO = "progresses_to"


@dataclass(frozen=True)
class AttackGraphNode:
    node_id: str
    node_type: GraphNodeType
    label: str
    attributes: dict[str, object]


@dataclass(frozen=True)
class AttackGraphEdge:
    source_id: str
    target_id: str
    edge_type: GraphEdgeType
    confidence: float
    attributes: dict[str, object]


@dataclass(frozen=True)
class AttackGraph:
    incident_id: str
    nodes: tuple[AttackGraphNode, ...]
    edges: tuple[AttackGraphEdge, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "nodes": [
                {**asdict(node), "node_type": node.node_type.value}
                for node in self.nodes
            ],
            "edges": [
                {**asdict(edge), "edge_type": edge.edge_type.value}
                for edge in self.edges
            ],
        }


class AttackGraphEngine:
    """Construct an explainable incident graph from alerts, topology and correlations."""

    def __init__(self, topology: AssetTopology) -> None:
        self.topology = topology

    def build(self, incident: Incident, alerts: list[EnrichedAlert],
              correlations: list[CorrelationEdge]) -> AttackGraph:
        members = {alert.alert_id: alert for alert in alerts if alert.alert_id in incident.alert_ids}
        nodes: dict[str, AttackGraphNode] = {}
        edges: dict[tuple[str, str, GraphEdgeType], AttackGraphEdge] = {}

        for alert in members.values():
            alert_node_id = f"alert:{alert.alert_id}"
            asset_node_id = f"asset:{alert.asset_id}"
            nodes[alert_node_id] = AttackGraphNode(
                alert_node_id, GraphNodeType.ALERT, alert.alert_id,
                {
                    "metric": alert.metric,
                    "severity": alert.severity,
                    "attack_family": alert.attack_family,
                    "unified_score": alert.unified_score,
                    "created_at": alert.created_at,
                },
            )
            asset = self.topology.get_asset(alert.asset_id)
            nodes[asset_node_id] = AttackGraphNode(
                asset_node_id, GraphNodeType.ASSET,
                asset.name if asset else alert.asset_id,
                {
                    "asset_id": alert.asset_id,
                    "asset_type": asset.asset_type.value if asset else alert.asset_type,
                    "criticality": asset.criticality if asset else alert.asset_criticality,
                    "zone": asset.zone if asset else alert.zone,
                },
            )
            edges[(alert_node_id, asset_node_id, GraphEdgeType.OBSERVED_ON)] = AttackGraphEdge(
                alert_node_id, asset_node_id, GraphEdgeType.OBSERVED_ON, 1.0, {}
            )

        incident_assets = set(incident.affected_assets)
        snapshot = self.topology.snapshot()
        for relation in snapshot["relationships"]:
            source = str(relation["source_id"])
            target = str(relation["target_id"])
            if source in incident_assets and target in incident_assets:
                source_id, target_id = f"asset:{source}", f"asset:{target}"
                if source_id in nodes and target_id in nodes:
                    edges[(source_id, target_id, GraphEdgeType.TOPOLOGY)] = AttackGraphEdge(
                        source_id, target_id, GraphEdgeType.TOPOLOGY, 1.0,
                        {"relationship": relation["relationship"]},
                    )

        for correlation in correlations:
            if not correlation.correlated or correlation.source_alert_id not in members or correlation.target_alert_id not in members:
                continue
            source_id = f"alert:{correlation.source_alert_id}"
            target_id = f"alert:{correlation.target_alert_id}"
            edges[(source_id, target_id, GraphEdgeType.CORRELATED_WITH)] = AttackGraphEdge(
                source_id, target_id, GraphEdgeType.CORRELATED_WITH, correlation.score,
                {"evidence": asdict(correlation.evidence)},
            )

        ordered = sorted(members.values(), key=lambda alert: alert.created_at)
        for left, right in zip(ordered, ordered[1:]):
            if left.alert_id == right.alert_id:
                continue
            source_id = f"alert:{left.alert_id}"
            target_id = f"alert:{right.alert_id}"
            related = any(
                correlation.correlated
                and {correlation.source_alert_id, correlation.target_alert_id} == {left.alert_id, right.alert_id}
                for correlation in correlations
            )
            topology_distance = self.topology.shortest_distance(left.asset_id, right.asset_id, max_hops=4)
            if related or topology_distance is not None or left.asset_id == right.asset_id:
                confidence = 0.8 if related else 0.6
                edges[(source_id, target_id, GraphEdgeType.PROGRESSES_TO)] = AttackGraphEdge(
                    source_id, target_id, GraphEdgeType.PROGRESSES_TO, confidence,
                    {"topology_distance": topology_distance, "time_ordered": True},
                )

        return AttackGraph(
            incident_id=incident.incident_id,
            nodes=tuple(sorted(nodes.values(), key=lambda node: node.node_id)),
            edges=tuple(sorted(edges.values(), key=lambda edge: (edge.edge_type.value, edge.source_id, edge.target_id))),
        )
