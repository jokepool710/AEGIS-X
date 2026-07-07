from aegis.correlation.attack_graph import AttackGraph, AttackGraphEdge, AttackGraphNode, GraphEdgeType, GraphNodeType
from aegis.correlation.attack_mapping import ICSMapping
from aegis.correlation.incidents import Incident
from aegis.correlation.risk import RiskPrioritizationEngine


def incident(incident_id: str, confidence: float, severity: str, first: str, last: str) -> Incident:
    return Incident(incident_id, ("a1", "a2"), ("plc", "pump"), ("temporal",), first, last, confidence, severity)


def graph(incident_id: str, criticalities: tuple[float, ...], progression_edges: int) -> AttackGraph:
    nodes = tuple(
        AttackGraphNode(f"asset:{i}", GraphNodeType.ASSET, f"asset-{i}",
                        {"asset_id": f"asset-{i}", "criticality": criticality})
        for i, criticality in enumerate(criticalities)
    )
    edges = tuple(
        AttackGraphEdge(f"alert:{i}", f"alert:{i+1}", GraphEdgeType.PROGRESSES_TO, 0.8, {})
        for i in range(progression_edges)
    )
    return AttackGraph(incident_id, nodes, edges)


def test_high_impact_incident_receives_high_risk_and_reasons() -> None:
    inc = incident("inc-high", 0.92, "critical", "2026-07-07T10:00:00+00:00", "2026-07-07T10:20:00+00:00")
    mappings = [ICSMapping("T0831", "Manipulation of Control", "Impair Process Control", 0.9, ("evidence",))]
    assessment = RiskPrioritizationEngine().assess(inc, graph("inc-high", (1.0, 0.95, 0.8), 2), mappings)
    assert assessment.risk_score >= 0.65
    assert assessment.risk_level in {"high", "critical"}
    assert assessment.priority <= 2
    assert "critical industrial asset affected" in assessment.reasons
    assert "strong ATT&CK for ICS technique evidence" in assessment.reasons
    assert "attack progression observed in incident graph" in assessment.reasons


def test_low_impact_incident_remains_low_priority() -> None:
    inc = incident("inc-low", 0.2, "medium", "2026-07-07T10:00:00+00:00", "2026-07-07T10:00:10+00:00")
    assessment = RiskPrioritizationEngine().assess(inc, graph("inc-low", (0.2,), 0), [])
    assert assessment.risk_level == "low"
    assert assessment.priority == 4
    assert assessment.evidence.progression_score == 0.0


def test_rank_orders_incidents_by_descending_risk() -> None:
    engine = RiskPrioritizationEngine()
    low = engine.assess(
        incident("low", 0.2, "medium", "2026-07-07T10:00:00+00:00", "2026-07-07T10:00:10+00:00"),
        graph("low", (0.2,), 0), [],
    )
    high = engine.assess(
        incident("high", 0.95, "critical", "2026-07-07T10:00:00+00:00", "2026-07-07T10:30:00+00:00"),
        graph("high", (1.0, 0.9, 0.8, 0.7), 3),
        [ICSMapping("T0831", "Manipulation of Control", "Impair Process Control", 0.95, ())],
    )
    ranked = engine.rank([low, high])
    assert [item.incident_id for item in ranked] == ["high", "low"]


def test_risk_score_is_bounded() -> None:
    inc = incident("bounded", 2.0, "critical", "2026-07-07T10:00:00+00:00", "2026-07-08T10:00:00+00:00")
    assessment = RiskPrioritizationEngine().assess(
        inc, graph("bounded", (2.0,) * 10, 20),
        [ICSMapping("T0831", "Manipulation of Control", "Impair Process Control", 2.0, ())],
    )
    assert 0.0 <= assessment.risk_score <= 1.0
