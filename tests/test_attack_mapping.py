from aegis.correlation.attack_graph import AttackGraph, AttackGraphEdge, AttackGraphNode, GraphEdgeType, GraphNodeType
from aegis.correlation.attack_mapping import ICSAttackMapper


def graph(family: str, asset_type: str, metric: str, progression: bool = True) -> AttackGraph:
    nodes = (
        AttackGraphNode("alert:a1", GraphNodeType.ALERT, "a1", {"attack_family": family, "metric": metric}),
        AttackGraphNode("asset:x", GraphNodeType.ASSET, "x", {"asset_type": asset_type}),
    )
    edges = ()
    if progression:
        edges = (AttackGraphEdge("alert:a1", "alert:a2", GraphEdgeType.PROGRESSES_TO, 0.8, {}),)
    return AttackGraph("inc-1", nodes, edges)


def test_temporal_sensor_behavior_maps_to_manipulation_of_view() -> None:
    mappings = ICSAttackMapper().map(graph("temporal", "sensor", "pressure"))
    ids = {mapping.technique_id for mapping in mappings}
    assert "T0832" in ids
    view = next(mapping for mapping in mappings if mapping.technique_id == "T0832")
    assert "attack_family=temporal" in view.evidence
    assert "asset_type=sensor" in view.evidence


def test_point_process_progression_maps_to_manipulation_of_control() -> None:
    mappings = ICSAttackMapper().map(graph("point", "actuator", "pressure", True))
    control = next(mapping for mapping in mappings if mapping.technique_id == "T0831")
    assert control.confidence >= 0.55
    assert "graph_progression=true" in control.evidence


def test_temporal_plc_progression_maps_to_unauthorized_command_message() -> None:
    mappings = ICSAttackMapper().map(graph("temporal", "plc", "pressure", True))
    assert "T0855" in {mapping.technique_id for mapping in mappings}


def test_weak_unrelated_evidence_is_not_mapped() -> None:
    mappings = ICSAttackMapper().map(graph("unknown", "other", "humidity", False))
    assert mappings == []


def test_results_are_ranked_by_confidence() -> None:
    mappings = ICSAttackMapper().map(graph("temporal", "plc", "pressure", True))
    assert [item.confidence for item in mappings] == sorted(
        [item.confidence for item in mappings], reverse=True
    )
