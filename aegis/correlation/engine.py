from dataclasses import dataclass
from datetime import datetime

from aegis.correlation.enrichment import EnrichedAlert
from aegis.correlation.topology import AssetTopology


@dataclass(frozen=True)
class CorrelationWeights:
    temporal: float = 0.30
    same_asset: float = 0.20
    topology: float = 0.20
    same_zone: float = 0.10
    metric: float = 0.10
    attack_family: float = 0.10

    def normalized(self) -> "CorrelationWeights":
        values = (self.temporal, self.same_asset, self.topology, self.same_zone, self.metric, self.attack_family)
        if min(values) < 0 or sum(values) <= 0:
            raise ValueError("correlation weights must be non-negative and sum positive")
        total = sum(values)
        return CorrelationWeights(*(value / total for value in values))


@dataclass(frozen=True)
class CorrelationEvidence:
    time_delta_seconds: float
    temporal_score: float
    same_asset: bool
    topology_distance: int | None
    topology_score: float
    same_zone: bool
    metric_score: float
    same_attack_family: bool


@dataclass(frozen=True)
class CorrelationEdge:
    source_alert_id: str
    target_alert_id: str
    score: float
    correlated: bool
    evidence: CorrelationEvidence


class CorrelationEngine:
    def __init__(self, topology: AssetTopology, max_time_delta_seconds: float = 300.0,
                 max_topology_hops: int = 3, threshold: float = 0.55,
                 weights: CorrelationWeights | None = None) -> None:
        if max_time_delta_seconds <= 0 or max_topology_hops < 1:
            raise ValueError("invalid correlation window")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.topology = topology
        self.max_time_delta_seconds = max_time_delta_seconds
        self.max_topology_hops = max_topology_hops
        self.threshold = threshold
        self.weights = (weights or CorrelationWeights()).normalized()

    @staticmethod
    def _timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _metric_score(left: str, right: str) -> float:
        if left == right:
            return 1.0
        process_pairs = {
            frozenset(("pressure", "flow")),
            frozenset(("temperature", "pressure")),
            frozenset(("current", "vibration")),
            frozenset(("speed", "vibration")),
        }
        return 0.6 if frozenset((left.lower(), right.lower())) in process_pairs else 0.0

    def correlate(self, left: EnrichedAlert, right: EnrichedAlert) -> CorrelationEdge:
        delta = abs((self._timestamp(left.created_at) - self._timestamp(right.created_at)).total_seconds())
        temporal_score = max(0.0, 1.0 - delta / self.max_time_delta_seconds)
        same_asset = left.asset_id == right.asset_id
        distance = self.topology.shortest_distance(left.asset_id, right.asset_id, self.max_topology_hops)
        topology_score = 0.0 if distance is None else max(0.0, 1.0 - (distance - 1) / self.max_topology_hops)
        same_zone = bool(left.zone and right.zone and left.zone == right.zone)
        metric_score = self._metric_score(left.metric, right.metric)
        same_family = left.attack_family == right.attack_family

        score = (
            self.weights.temporal * temporal_score
            + self.weights.same_asset * float(same_asset)
            + self.weights.topology * topology_score
            + self.weights.same_zone * float(same_zone)
            + self.weights.metric * metric_score
            + self.weights.attack_family * float(same_family)
        )
        score = max(0.0, min(1.0, score))
        evidence = CorrelationEvidence(
            time_delta_seconds=delta,
            temporal_score=temporal_score,
            same_asset=same_asset,
            topology_distance=distance,
            topology_score=topology_score,
            same_zone=same_zone,
            metric_score=metric_score,
            same_attack_family=same_family,
        )
        return CorrelationEdge(left.alert_id, right.alert_id, score, score >= self.threshold, evidence)

    def build_edges(self, alerts: list[EnrichedAlert]) -> list[CorrelationEdge]:
        edges = []
        for index, left in enumerate(alerts):
            for right in alerts[index + 1:]:
                edge = self.correlate(left, right)
                if edge.correlated:
                    edges.append(edge)
        return sorted(edges, key=lambda edge: edge.score, reverse=True)
