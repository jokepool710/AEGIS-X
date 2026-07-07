from dataclasses import dataclass

from aegis.correlation.attack_graph import AttackGraph, AttackGraphEngine
from aegis.correlation.attack_mapping import ICSAttackMapper, ICSMapping
from aegis.correlation.engine import CorrelationEdge, CorrelationEngine
from aegis.correlation.enrichment import AlertEnricher, EnrichedAlert
from aegis.correlation.incident_store import PersistentIncidentStore
from aegis.correlation.incidents import Incident, IncidentClusterer
from aegis.correlation.risk import RiskAssessment, RiskPrioritizationEngine
from aegis.correlation.topology import AssetTopology


@dataclass(frozen=True)
class IncidentAnalysis:
    incident: Incident
    graph: AttackGraph
    mappings: tuple[ICSMapping, ...]
    risk: RiskAssessment


class Phase3Pipeline:
    def __init__(self, topology: AssetTopology, incident_store: PersistentIncidentStore) -> None:
        self.topology = topology
        self.incident_store = incident_store
        self.enricher = AlertEnricher(topology)
        self.correlator = CorrelationEngine(topology)
        self.clusterer = IncidentClusterer()
        self.graph_engine = AttackGraphEngine(topology)
        self.mapper = ICSAttackMapper()
        self.risk_engine = RiskPrioritizationEngine()

    def run(self, raw_alerts: list[dict[str, object]]) -> list[IncidentAnalysis]:
        enriched = [self.enricher.enrich(alert) for alert in raw_alerts]
        edges = self.correlator.build_edges(enriched)
        candidates = self.clusterer.cluster(enriched, edges)
        analyses = []
        for candidate in candidates:
            incident = self.incident_store.upsert_cluster(candidate)
            member_alerts = [alert for alert in enriched if alert.alert_id in incident.alert_ids]
            member_edges = [
                edge for edge in edges
                if edge.source_alert_id in incident.alert_ids and edge.target_alert_id in incident.alert_ids
            ]
            graph = self.graph_engine.build(incident, member_alerts, member_edges)
            mappings = tuple(self.mapper.map(graph))
            risk = self.risk_engine.assess(incident, graph, list(mappings))
            analyses.append(IncidentAnalysis(incident, graph, mappings, risk))
        return self.risk_engine.rank_analyses(analyses) if hasattr(self.risk_engine, "rank_analyses") else sorted(
            analyses, key=lambda item: (-item.risk.risk_score, item.incident.incident_id)
        )
