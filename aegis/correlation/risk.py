from dataclasses import dataclass
from datetime import datetime

from aegis.correlation.attack_graph import AttackGraph, GraphEdgeType, GraphNodeType
from aegis.correlation.attack_mapping import ICSMapping
from aegis.correlation.incidents import Incident


@dataclass(frozen=True)
class RiskWeights:
    incident_confidence: float = 0.20
    asset_criticality: float = 0.20
    blast_radius: float = 0.15
    persistence: float = 0.10
    severity: float = 0.15
    technique_confidence: float = 0.10
    progression: float = 0.10

    def normalized(self) -> "RiskWeights":
        values = (
            self.incident_confidence, self.asset_criticality, self.blast_radius,
            self.persistence, self.severity, self.technique_confidence, self.progression,
        )
        if min(values) < 0 or sum(values) <= 0:
            raise ValueError("risk weights must be non-negative and sum positive")
        total = sum(values)
        return RiskWeights(*(value / total for value in values))


@dataclass(frozen=True)
class RiskEvidence:
    incident_confidence: float
    max_asset_criticality: float
    blast_radius_score: float
    affected_asset_count: int
    persistence_score: float
    duration_seconds: float
    severity_score: float
    technique_confidence: float
    progression_score: float
    progression_edge_count: int


@dataclass(frozen=True)
class RiskAssessment:
    incident_id: str
    risk_score: float
    risk_level: str
    priority: int
    evidence: RiskEvidence
    reasons: tuple[str, ...]


class RiskPrioritizationEngine:
    def __init__(self, weights: RiskWeights | None = None,
                 blast_radius_saturation: int = 5,
                 persistence_saturation_seconds: float = 1800.0) -> None:
        if blast_radius_saturation < 1 or persistence_saturation_seconds <= 0:
            raise ValueError("risk saturation parameters must be positive")
        self.weights = (weights or RiskWeights()).normalized()
        self.blast_radius_saturation = blast_radius_saturation
        self.persistence_saturation_seconds = persistence_saturation_seconds

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _severity_score(severity: str) -> float:
        return {"normal": 0.0, "medium": 0.45, "high": 0.75, "critical": 1.0}.get(severity, 0.0)

    @staticmethod
    def _level(score: float) -> str:
        if score >= 0.85:
            return "critical"
        if score >= 0.65:
            return "high"
        if score >= 0.40:
            return "medium"
        return "low"

    @staticmethod
    def _priority(level: str) -> int:
        return {"critical": 1, "high": 2, "medium": 3, "low": 4}[level]

    def assess(self, incident: Incident, graph: AttackGraph,
               mappings: list[ICSMapping]) -> RiskAssessment:
        asset_nodes = [node for node in graph.nodes if node.node_type == GraphNodeType.ASSET]
        criticalities = [self._clamp(float(node.attributes.get("criticality", 0.5))) for node in asset_nodes]
        max_criticality = max(criticalities, default=0.5)
        affected_count = len({str(node.attributes.get("asset_id", node.node_id)) for node in asset_nodes})
        blast_radius = self._clamp(affected_count / self.blast_radius_saturation)

        duration = max(0.0, (self._timestamp(incident.last_seen) - self._timestamp(incident.first_seen)).total_seconds())
        persistence = self._clamp(duration / self.persistence_saturation_seconds)
        severity = self._severity_score(incident.severity)
        technique_confidence = max((mapping.confidence for mapping in mappings), default=0.0)
        progression_edges = [edge for edge in graph.edges if edge.edge_type == GraphEdgeType.PROGRESSES_TO]
        progression = self._clamp(len(progression_edges) / max(1, affected_count - 1)) if progression_edges else 0.0

        score = (
            self.weights.incident_confidence * self._clamp(incident.confidence)
            + self.weights.asset_criticality * max_criticality
            + self.weights.blast_radius * blast_radius
            + self.weights.persistence * persistence
            + self.weights.severity * severity
            + self.weights.technique_confidence * technique_confidence
            + self.weights.progression * progression
        )
        score = round(self._clamp(score), 6)
        level = self._level(score)
        evidence = RiskEvidence(
            self._clamp(incident.confidence), max_criticality, blast_radius, affected_count,
            persistence, duration, severity, technique_confidence, progression, len(progression_edges),
        )
        reasons = []
        if max_criticality >= 0.8:
            reasons.append("critical industrial asset affected")
        if blast_radius >= 0.6:
            reasons.append("multi-asset blast radius")
        if persistence >= 0.5:
            reasons.append("persistent attack activity")
        if technique_confidence >= 0.75:
            reasons.append("strong ATT&CK for ICS technique evidence")
        if progression >= 0.5:
            reasons.append("attack progression observed in incident graph")
        if incident.severity == "critical":
            reasons.append("critical alert severity present")
        return RiskAssessment(incident.incident_id, score, level, self._priority(level), evidence, tuple(reasons))

    def rank(self, assessments: list[RiskAssessment]) -> list[RiskAssessment]:
        return sorted(assessments, key=lambda item: (-item.risk_score, item.incident_id))
