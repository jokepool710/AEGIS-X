from aegis.correlation.attack_graph import AttackGraph, AttackGraphEdge, AttackGraphNode, GraphEdgeType, GraphNodeType
from aegis.correlation.attack_mapping import ICSMapping
from aegis.correlation.incidents import Incident
from aegis.correlation.risk import RiskAssessment, RiskEvidence
from aegis.investigation.evidence import EvidenceBundleBuilder, EvidenceKind


def test_builds_provenance_preserving_evidence_bundle() -> None:
    incident = Incident(
        "inc-1", ("a1",), ("plc-1",), ("temporal",),
        "2026-07-08T10:00:00+00:00", "2026-07-08T10:01:00+00:00", 0.9, "critical",
        "investigating", "2026-07-08T10:02:00+00:00", "triage started",
    )
    graph = AttackGraph(
        "inc-1",
        (
            AttackGraphNode("alert:a1", GraphNodeType.ALERT, "a1", {
                "metric": "pressure", "severity": "critical", "attack_family": "temporal",
                "unified_score": 0.94, "created_at": "2026-07-08T10:00:00+00:00",
            }),
            AttackGraphNode("asset:plc-1", GraphNodeType.ASSET, "PLC 1", {
                "asset_id": "plc-1", "asset_type": "plc", "criticality": 0.95, "zone": "cell-a",
            }),
        ),
        (AttackGraphEdge("alert:a1", "asset:plc-1", GraphEdgeType.OBSERVED_ON, 1.0, {}),),
    )
    mappings = (ICSMapping("T0855", "Unauthorized Command Message", "Impair Process Control", 0.9,
                           ("attack_family=temporal", "asset_type=plc")),)
    risk = RiskAssessment(
        "inc-1", 0.88, "critical", 1,
        RiskEvidence(0.9, 0.95, 0.2, 1, 0.1, 60.0, 1.0, 0.9, 0.0, 0),
        ("critical industrial asset affected",),
    )

    bundle = EvidenceBundleBuilder().build(incident, graph, mappings, risk)

    assert bundle.incident_id == "inc-1"
    assert bundle.schema_version == "1.0"
    assert len(bundle.evidence_ids) == len(bundle.evidence)
    assert bundle.get("alert:a1").source == "attack_graph.alert_node"
    assert bundle.get("asset:plc-1").payload["criticality"] == 0.95
    assert bundle.get("attack:T0855").payload["confidence"] == 0.9
    assert bundle.get("risk:inc-1").payload["risk_score"] == 0.88
    assert bundle.get("lifecycle:inc-1").payload["note"] == "triage started"
    assert len(bundle.by_kind(EvidenceKind.GRAPH_EDGE)) == 1
    assert bundle.to_dict()["evidence"]


def test_rejects_cross_incident_evidence() -> None:
    incident = Incident("inc-1", (), (), (), "2026-07-08T10:00:00+00:00",
                        "2026-07-08T10:00:00+00:00", 0.5, "medium")
    graph = AttackGraph("inc-other", (), ())
    risk = RiskAssessment(
        "inc-1", 0.2, "low", 4,
        RiskEvidence(0.5, 0.5, 0.0, 0, 0.0, 0.0, 0.45, 0.0, 0.0, 0), (),
    )
    try:
        EvidenceBundleBuilder().build(incident, graph, (), risk)
    except ValueError as exc:
        assert "same incident" in str(exc)
    else:
        raise AssertionError("cross-incident evidence must be rejected")
