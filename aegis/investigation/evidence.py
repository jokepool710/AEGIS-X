from dataclasses import asdict, dataclass
from enum import Enum

from aegis.correlation.attack_graph import AttackGraph, GraphNodeType
from aegis.correlation.attack_mapping import ICSMapping
from aegis.correlation.incidents import Incident
from aegis.correlation.risk import RiskAssessment


class EvidenceKind(str, Enum):
    INCIDENT = "incident"
    ALERT = "alert"
    ASSET = "asset"
    GRAPH_EDGE = "graph_edge"
    ATTACK_MAPPING = "attack_mapping"
    RISK = "risk"
    LIFECYCLE = "lifecycle"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    kind: EvidenceKind
    source: str
    observed_at: str | None
    payload: dict[str, object]


@dataclass(frozen=True)
class EvidenceBundle:
    incident_id: str
    schema_version: str
    evidence: tuple[EvidenceItem, ...]

    @property
    def evidence_ids(self) -> frozenset[str]:
        return frozenset(item.evidence_id for item in self.evidence)

    def get(self, evidence_id: str) -> EvidenceItem:
        for item in self.evidence:
            if item.evidence_id == evidence_id:
                return item
        raise KeyError(evidence_id)

    def by_kind(self, kind: EvidenceKind) -> tuple[EvidenceItem, ...]:
        return tuple(item for item in self.evidence if item.kind == kind)

    def to_dict(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "schema_version": self.schema_version,
            "evidence": [
                {**asdict(item), "kind": item.kind.value}
                for item in self.evidence
            ],
        }


class EvidenceBundleBuilder:
    SCHEMA_VERSION = "1.0"

    @staticmethod
    def _item(evidence_id: str, kind: EvidenceKind, source: str,
              payload: dict[str, object], observed_at: str | None = None) -> EvidenceItem:
        return EvidenceItem(evidence_id, kind, source, observed_at, payload)

    def build(self, incident: Incident, graph: AttackGraph,
              mappings: tuple[ICSMapping, ...] | list[ICSMapping],
              risk: RiskAssessment) -> EvidenceBundle:
        if graph.incident_id != incident.incident_id or risk.incident_id != incident.incident_id:
            raise ValueError("incident, graph and risk assessment must refer to the same incident")

        items: list[EvidenceItem] = []
        items.append(self._item(
            f"incident:{incident.incident_id}", EvidenceKind.INCIDENT, "persistent_incident_store",
            {
                "alert_ids": list(incident.alert_ids),
                "affected_assets": list(incident.affected_assets),
                "attack_families": list(incident.attack_families),
                "first_seen": incident.first_seen,
                "last_seen": incident.last_seen,
                "confidence": incident.confidence,
                "severity": incident.severity,
                "status": incident.status,
            }, incident.first_seen,
        ))

        for node in graph.nodes:
            if node.node_type == GraphNodeType.ALERT:
                observed_at = str(node.attributes.get("created_at")) if node.attributes.get("created_at") else None
                items.append(self._item(
                    f"alert:{node.label}", EvidenceKind.ALERT, "attack_graph.alert_node",
                    {"label": node.label, **node.attributes}, observed_at,
                ))
            elif node.node_type == GraphNodeType.ASSET:
                asset_id = str(node.attributes.get("asset_id", node.label))
                items.append(self._item(
                    f"asset:{asset_id}", EvidenceKind.ASSET, "asset_topology",
                    {"label": node.label, **node.attributes},
                ))

        for index, edge in enumerate(graph.edges):
            items.append(self._item(
                f"edge:{index:04d}", EvidenceKind.GRAPH_EDGE, "attack_graph.edge",
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type.value,
                    "confidence": edge.confidence,
                    "attributes": edge.attributes,
                },
            ))

        for mapping in mappings:
            items.append(self._item(
                f"attack:{mapping.technique_id}", EvidenceKind.ATTACK_MAPPING, "ics_attack_mapper",
                {
                    "technique_id": mapping.technique_id,
                    "technique_name": mapping.technique_name,
                    "tactic": mapping.tactic,
                    "confidence": mapping.confidence,
                    "supporting_evidence": list(mapping.evidence),
                },
            ))

        items.append(self._item(
            f"risk:{incident.incident_id}", EvidenceKind.RISK, "risk_prioritization_engine",
            {
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "priority": risk.priority,
                "reasons": list(risk.reasons),
                "evidence": asdict(risk.evidence),
            }, incident.last_seen,
        ))

        if incident.updated_at or incident.status_note:
            items.append(self._item(
                f"lifecycle:{incident.incident_id}", EvidenceKind.LIFECYCLE, "persistent_incident_store",
                {"status": incident.status, "note": incident.status_note}, incident.updated_at,
            ))

        ordered = tuple(sorted(items, key=lambda item: item.evidence_id))
        if len({item.evidence_id for item in ordered}) != len(ordered):
            raise ValueError("evidence IDs must be unique")
        return EvidenceBundle(incident.incident_id, self.SCHEMA_VERSION, ordered)
