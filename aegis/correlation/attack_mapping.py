from dataclasses import dataclass

from aegis.correlation.attack_graph import AttackGraph, GraphEdgeType, GraphNodeType


@dataclass(frozen=True)
class ICSMapping:
    technique_id: str
    technique_name: str
    tactic: str
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class MappingRule:
    technique_id: str
    technique_name: str
    tactic: str
    attack_families: frozenset[str] = frozenset()
    asset_types: frozenset[str] = frozenset()
    metrics: frozenset[str] = frozenset()
    requires_progression: bool = False


DEFAULT_RULES = (
    MappingRule("T0832", "Manipulation of View", "Impair Process Control",
                frozenset({"temporal"}), frozenset({"sensor", "hmi"})),
    MappingRule("T0831", "Manipulation of Control", "Impair Process Control",
                frozenset({"point", "contextual"}), frozenset({"plc", "actuator", "process"}),
                frozenset({"pressure", "flow", "temperature", "speed", "current", "vibration"}), True),
    MappingRule("T0855", "Unauthorized Command Message", "Impair Process Control",
                frozenset({"temporal"}), frozenset({"gateway", "plc", "actuator"}), requires_progression=True),
)


class ICSAttackMapper:
    """Deterministically maps graph evidence to candidate ATT&CK for ICS techniques."""

    def __init__(self, rules: tuple[MappingRule, ...] = DEFAULT_RULES, threshold: float = 0.55) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.rules = rules
        self.threshold = threshold

    @staticmethod
    def _signals(graph: AttackGraph) -> tuple[set[str], set[str], set[str], bool]:
        families: set[str] = set()
        asset_types: set[str] = set()
        metrics: set[str] = set()
        for node in graph.nodes:
            if node.node_type == GraphNodeType.ALERT:
                families.add(str(node.attributes.get("attack_family", "")))
                metrics.add(str(node.attributes.get("metric", "")).lower())
            elif node.node_type == GraphNodeType.ASSET:
                asset_types.add(str(node.attributes.get("asset_type", "")).lower())
        progression = any(edge.edge_type == GraphEdgeType.PROGRESSES_TO for edge in graph.edges)
        return families, asset_types, metrics, progression

    @staticmethod
    def _overlap(observed: set[str], expected: frozenset[str]) -> tuple[float, list[str]]:
        if not expected:
            return 1.0, []
        matches = sorted(observed & set(expected))
        return (1.0 if matches else 0.0), matches

    def map(self, graph: AttackGraph) -> list[ICSMapping]:
        families, asset_types, metrics, progression = self._signals(graph)
        mappings: list[ICSMapping] = []
        for rule in self.rules:
            family_score, family_matches = self._overlap(families, rule.attack_families)
            asset_score, asset_matches = self._overlap(asset_types, rule.asset_types)
            metric_score, metric_matches = self._overlap(metrics, rule.metrics)
            progression_score = 1.0 if (not rule.requires_progression or progression) else 0.0
            confidence = 0.40 * family_score + 0.25 * asset_score + 0.20 * metric_score + 0.15 * progression_score
            confidence = round(min(1.0, confidence), 6)
            if confidence < self.threshold:
                continue
            evidence = []
            if family_matches:
                evidence.append("attack_family=" + ",".join(family_matches))
            if asset_matches:
                evidence.append("asset_type=" + ",".join(asset_matches))
            if metric_matches:
                evidence.append("metric=" + ",".join(metric_matches))
            if rule.requires_progression and progression:
                evidence.append("graph_progression=true")
            mappings.append(ICSMapping(
                rule.technique_id, rule.technique_name, rule.tactic, confidence, tuple(evidence)
            ))
        return sorted(mappings, key=lambda item: (-item.confidence, item.technique_id))
