from dataclasses import asdict, dataclass

from aegis.investigation.citations import (
    ClaimType,
    EvidenceCitationValidator,
    GroundedClaim,
    InvestigativeClaim,
)
from aegis.investigation.evidence import EvidenceBundle, EvidenceKind
from aegis.investigation.timeline import InvestigationTimeline


@dataclass(frozen=True)
class InvestigationHypothesis:
    hypothesis_id: str
    title: str
    confidence: float
    rationale: str
    claims: tuple[GroundedClaim, ...]
    evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "title": self.title,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "claims": [claim.to_dict() for claim in self.claims],
            "evidence_ids": list(self.evidence_ids),
        }


class HypothesisEngine:
    """Generate deterministic competing hypotheses from grounded incident evidence."""

    def __init__(self) -> None:
        self.citations = EvidenceCitationValidator()

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)

    def generate(self, bundle: EvidenceBundle,
                 timeline: InvestigationTimeline) -> tuple[InvestigationHypothesis, ...]:
        if timeline.incident_id != bundle.incident_id:
            raise ValueError("timeline and evidence bundle must refer to the same incident")

        mappings = bundle.by_kind(EvidenceKind.ATTACK_MAPPING)
        alerts = bundle.by_kind(EvidenceKind.ALERT)
        edges = bundle.by_kind(EvidenceKind.GRAPH_EDGE)
        risk_items = bundle.by_kind(EvidenceKind.RISK)
        hypotheses: list[InvestigationHypothesis] = []

        for index, mapping in enumerate(mappings, start=1):
            technique_id = str(mapping.payload.get("technique_id", "unknown"))
            technique_name = str(mapping.payload.get("technique_name", "Unknown technique"))
            mapping_confidence = float(mapping.payload.get("confidence", 0.0))
            supporting_ids = tuple(
                item.evidence_id for item in alerts[:3]
            ) + (mapping.evidence_id,)
            claim = InvestigativeClaim(
                f"hyp-{index}-claim-1",
                f"Observed incident evidence is consistent with {technique_id} {technique_name}.",
                ClaimType.HYPOTHESIS,
                supporting_ids,
            )
            grounded = self.citations.ground(claim, bundle)
            confidence = self._clamp(0.7 * mapping_confidence + 0.3 * min(1.0, len(alerts) / 3.0))
            hypotheses.append(InvestigationHypothesis(
                f"hyp-{index}",
                f"{technique_id}: {technique_name}",
                confidence,
                "ATT&CK mapping confidence combined with observed alert coverage.",
                (grounded,),
                tuple(dict.fromkeys(supporting_ids)),
            ))

        if alerts and edges:
            evidence_ids = tuple(item.evidence_id for item in alerts[:3]) + tuple(
                item.evidence_id for item in edges[:3]
            )
            claim = InvestigativeClaim(
                "hyp-topology-claim-1",
                "The incident may represent coordinated activity across correlated cyber-physical assets.",
                ClaimType.HYPOTHESIS,
                evidence_ids,
            )
            grounded = self.citations.ground(claim, bundle)
            confidence = self._clamp(0.45 + min(0.35, len(edges) * 0.05) + min(0.2, len(alerts) * 0.04))
            hypotheses.append(InvestigationHypothesis(
                "hyp-topology",
                "Coordinated cyber-physical activity",
                confidence,
                "Multiple alert observations are connected by incident attack-graph evidence.",
                (grounded,),
                tuple(dict.fromkeys(evidence_ids)),
            ))

        if risk_items and alerts:
            risk = risk_items[0]
            risk_score = float(risk.payload.get("risk_score", 0.0))
            evidence_ids = (risk.evidence_id,) + tuple(item.evidence_id for item in alerts[:2])
            claim = InvestigativeClaim(
                "hyp-impact-claim-1",
                "The observed activity may create material operational impact if the affected process remains exposed.",
                ClaimType.HYPOTHESIS,
                evidence_ids,
            )
            grounded = self.citations.ground(claim, bundle)
            hypotheses.append(InvestigationHypothesis(
                "hyp-impact",
                "Operational impact progression",
                self._clamp(0.5 * risk_score + 0.25),
                "Risk assessment and alert evidence support an impact-oriented investigation path.",
                (grounded,),
                evidence_ids,
            ))

        return tuple(sorted(hypotheses, key=lambda item: (-item.confidence, item.hypothesis_id)))
