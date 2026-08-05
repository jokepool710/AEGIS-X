from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore
from aegis.correlation.attack_graph import AttackGraphEngine
from aegis.correlation.attack_mapping import ICSAttackMapper
from aegis.correlation.engine import CorrelationEngine
from aegis.correlation.enrichment import AlertEnricher
from aegis.correlation.incidents import IncidentClusterer
from aegis.correlation.pipeline import IncidentAnalysis
from aegis.correlation.risk import RiskPrioritizationEngine
from aegis.correlation.topology import (
    Asset,
    AssetRelationship,
    AssetTopology,
    AssetType,
    RelationshipType,
)
from aegis.detection.alerts import AlertStore
from aegis.detection.pipeline import DetectionPipeline
from aegis.investigation.artifact_store import InvestigationArtifactStore
from aegis.orchestration.tools import ToolRegistry
from aegis.workflow.case import CaseStatus, InvestigationCaseStore
from aegis.workflow.feedback import FeedbackEngine, FeedbackType


def make_event(event_id: str, device_id: str, metric: str, value: float, timestamp: str) -> TelemetryEvent:
    return TelemetryEvent(
        event_id=event_id,
        device_id=device_id,
        device_type="industrial_pump",
        site_id="site-1",
        timestamp=timestamp,  # type: ignore[arg-type]
        sequence=1,
        metric=metric,
        value=value,
        unit="psi",
        quality="good",
        source_topic="aegis/telemetry/pump",
        ingested_at=timestamp,  # type: ignore[arg-type]
    )


def test_phase6_end_to_end_workflow(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "phase6_e2e.db"))

    # 1. Produce anomaly telemetry & create alerts
    pipeline = DetectionPipeline(30)
    alerts = AlertStore(storage)
    e1 = make_event("e1", "pump-01", "pressure", 150.0, "2026-07-12T10:00:00+00:00")
    e2 = make_event("e2", "pump-01", "flow", 2.0, "2026-07-12T10:00:05+00:00")
    res1 = pipeline.process(e1)
    res2 = pipeline.process(e2)
    a1_id = alerts.create(e1, res1)
    a2_id = alerts.create(e2, res2)

    # 2. Correlate alerts into an incident
    topology = AssetTopology()
    topology.add_asset(Asset("pump-01", AssetType.ACTUATOR, "Pump 01", 1.0, "cell-a"))
    topology.add_asset(Asset("plc-01", AssetType.PLC, "PLC 01", 0.95, "cell-a"))
    topology.add_relationship(AssetRelationship("plc-01", "pump-01", RelationshipType.CONTROLS))
    enricher = AlertEnricher(topology)
    enriched = [enricher.enrich(alerts.get(a1_id)), enricher.enrich(alerts.get(a2_id))]
    edges = CorrelationEngine(topology).build_edges(enriched)
    incidents = IncidentClusterer().cluster(enriched, edges)
    incident = incidents[0]
    graph = AttackGraphEngine(topology).build(incident, enriched, edges)
    mappings = ICSAttackMapper().map(graph)
    risk = RiskPrioritizationEngine().assess(incident, graph, mappings)

    analysis = IncidentAnalysis(incident, graph, tuple(mappings), risk)

    # 3. Save artifact for Phase 4 / Phase 6 consumption
    InvestigationArtifactStore(storage).save(analysis)

    # 4. Phase 6 Case Creation
    case_store = InvestigationCaseStore(storage)
    case = case_store.create(incident.incident_id, title="PLC Pressure Anomaly Investigation", assignee="analyst-alicia")
    assert case.status == CaseStatus.DRAFT

    # 5. Build Case Dossier (aggregating Phase 4 investigation, Phase 5 orchestration, Phase 6 provenance & feedback)
    tools = ToolRegistry()
    dossier = case_store.build_dossier(case.case_id, tools)
    assert dossier.case.case_id == case.case_id
    assert dossier.provenance.is_valid is True
    assert dossier.provenance.evidence_count > 0

    # 6. Submit Analyst Feedback & Update Case Status
    fb_engine = FeedbackEngine(storage)
    fb_engine.submit(case.case_id, incident.incident_id, "analyst-alicia", FeedbackType.ACCEPT_HYPOTHESIS, "hyp-1", comment="Verified via telemetry")

    updated_case = case_store.transition(case.case_id, CaseStatus.IN_REVIEW, note="Reviewed by lead analyst")
    assert updated_case.status == CaseStatus.IN_REVIEW

    # 7. Final Dossier Verification
    final_dossier = case_store.build_dossier(case.case_id, tools)
    assert len(final_dossier.feedback) == 1
    assert final_dossier.feedback[0].comment == "Verified via telemetry"
    assert final_dossier.provenance.is_valid is True
