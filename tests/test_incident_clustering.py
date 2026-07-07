from aegis.correlation.engine import CorrelationEdge, CorrelationEvidence
from aegis.correlation.enrichment import DetectorEvidence, EnrichedAlert
from aegis.correlation.incidents import IncidentClusterer, IncidentLifecycle


def alert(alert_id: str, asset: str, time: str, severity: str = "high", family: str = "temporal") -> EnrichedAlert:
    return EnrichedAlert(alert_id, f"e-{alert_id}", asset, "plc", "pressure", 1.0, 0.9,
                         severity, "open", time, family, DetectorEvidence(), 0.9, "cell-a", ())


def edge(left: str, right: str, score: float, correlated: bool = True) -> CorrelationEdge:
    evidence = CorrelationEvidence(10.0, 0.9, False, 1, 1.0, True, 0.6, True)
    return CorrelationEdge(left, right, score, correlated, evidence)


def test_connected_alerts_form_one_incident() -> None:
    alerts = [
        alert("a1", "gw", "2026-07-07T10:00:00+00:00"),
        alert("a2", "plc", "2026-07-07T10:00:10+00:00", "critical"),
        alert("a3", "pump", "2026-07-07T10:00:20+00:00"),
    ]
    incidents = IncidentClusterer().cluster(alerts, [edge("a1", "a2", 0.8), edge("a2", "a3", 0.7)])
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.alert_ids == ("a1", "a2", "a3")
    assert set(incident.affected_assets) == {"gw", "plc", "pump"}
    assert incident.severity == "critical"
    assert incident.first_seen.endswith("10:00:00+00:00")
    assert incident.last_seen.endswith("10:00:20+00:00")
    assert 0.0 < incident.confidence <= 1.0


def test_disconnected_groups_form_separate_incidents_and_singletons_are_ignored() -> None:
    alerts = [
        alert("a1", "gw", "2026-07-07T10:00:00+00:00"),
        alert("a2", "plc", "2026-07-07T10:00:10+00:00"),
        alert("a3", "sensor", "2026-07-07T11:00:00+00:00", family="point"),
        alert("a4", "pump", "2026-07-07T11:00:10+00:00", family="point"),
        alert("a5", "isolated", "2026-07-07T12:00:00+00:00"),
    ]
    incidents = IncidentClusterer().cluster(alerts, [edge("a1", "a2", 0.8), edge("a3", "a4", 0.75)])
    assert len(incidents) == 2
    assert all(len(incident.alert_ids) == 2 for incident in incidents)


def test_rejected_edge_does_not_create_incident() -> None:
    alerts = [alert("a1", "gw", "2026-07-07T10:00:00+00:00"), alert("a2", "plc", "2026-07-07T10:00:10+00:00")]
    assert IncidentClusterer().cluster(alerts, [edge("a1", "a2", 0.4, False)]) == []


def test_incident_lifecycle_enforces_transitions() -> None:
    alerts = [alert("a1", "gw", "2026-07-07T10:00:00+00:00"), alert("a2", "plc", "2026-07-07T10:00:10+00:00")]
    incident = IncidentClusterer().cluster(alerts, [edge("a1", "a2", 0.8)])[0]
    investigating = IncidentLifecycle().transition(incident, "investigating", "triage started")
    assert investigating.status == "investigating"
    resolved = IncidentLifecycle().transition(investigating, "resolved", "contained")
    assert resolved.status == "resolved"
    try:
        IncidentLifecycle().transition(resolved, "open")
        assert False, "expected invalid transition"
    except ValueError:
        pass
