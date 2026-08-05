from dataclasses import asdict, dataclass
from enum import Enum

from aegis.investigation.citations import ClaimType
from aegis.investigation.evidence import EvidenceBundle, EvidenceKind
from aegis.investigation.hypotheses import InvestigationHypothesis


class ConfidenceBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class UncertaintyAssessment:
    hypothesis_id: str
    calibrated_confidence: float
    confidence_band: ConfidenceBand
    evidence_diversity: float
    citation_coverage: float
    contradiction_penalty: float
    missing_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "confidence_band": self.confidence_band.value}


class ConfidenceUncertaintyModel:
    """Calibrate hypothesis confidence from provenance coverage, diversity and contradictions."""

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)

    @staticmethod
    def _band(value: float) -> ConfidenceBand:
        if value >= 0.75:
            return ConfidenceBand.HIGH
        if value >= 0.45:
            return ConfidenceBand.MODERATE
        return ConfidenceBand.LOW

    def assess(self, hypothesis: InvestigationHypothesis,
               bundle: EvidenceBundle) -> UncertaintyAssessment:
        cited_ids = set(hypothesis.evidence_ids)
        if not cited_ids <= bundle.evidence_ids:
            raise ValueError("hypothesis cites evidence outside the active incident bundle")

        cited_items = [bundle.get(evidence_id) for evidence_id in sorted(cited_ids)]
        kinds = {item.kind for item in cited_items}
        source_count = len({item.source for item in cited_items})
        evidence_diversity = self._clamp((len(kinds) / 5.0) * 0.7 + min(1.0, source_count / 3.0) * 0.3)

        claim_citations = {
            evidence_id
            for grounded in hypothesis.claims
            for evidence_id in grounded.citations.resolved_evidence_ids
        }
        citation_coverage = self._clamp(len(claim_citations & cited_ids) / max(1, len(cited_ids)))

        contradictions: list[str] = []
        incident_items = bundle.by_kind(EvidenceKind.INCIDENT)
        risk_items = bundle.by_kind(EvidenceKind.RISK)
        if incident_items and risk_items:
            incident_severity = str(incident_items[0].payload.get("severity", "unknown"))
            risk_level = str(risk_items[0].payload.get("risk_level", "unknown"))
            severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            if abs(severity_rank.get(incident_severity, 0) - severity_rank.get(risk_level, 0)) >= 2:
                contradictions.append(
                    f"incident severity {incident_severity} conflicts with risk level {risk_level}"
                )

        attack_mappings = bundle.by_kind(EvidenceKind.ATTACK_MAPPING)
        if hypothesis.hypothesis_id.startswith("hyp-") and hypothesis.hypothesis_id not in {
            "hyp-topology", "hyp-impact"
        } and not attack_mappings:
            contradictions.append("ATT&CK-oriented hypothesis has no mapping evidence")

        missing: list[str] = []
        if not bundle.by_kind(EvidenceKind.ALERT):
            missing.append("alert evidence")
        if not bundle.by_kind(EvidenceKind.ASSET):
            missing.append("asset context")
        if not bundle.by_kind(EvidenceKind.GRAPH_EDGE):
            missing.append("graph relationship evidence")
        if not bundle.by_kind(EvidenceKind.ATTACK_MAPPING):
            missing.append("ATT&CK mapping evidence")
        if not bundle.by_kind(EvidenceKind.RISK):
            missing.append("risk assessment evidence")

        inference_ratio = sum(
            grounded.claim.claim_type != ClaimType.OBSERVATION
            for grounded in hypothesis.claims
        ) / max(1, len(hypothesis.claims))
        contradiction_penalty = self._clamp(min(0.6, len(contradictions) * 0.25))
        missing_penalty = min(0.35, len(missing) * 0.07)
        inference_penalty = 0.08 * inference_ratio

        calibrated = self._clamp(
            hypothesis.confidence * 0.55
            + evidence_diversity * 0.25
            + citation_coverage * 0.20
            - contradiction_penalty
            - missing_penalty
            - inference_penalty
        )
        return UncertaintyAssessment(
            hypothesis.hypothesis_id,
            calibrated,
            self._band(calibrated),
            evidence_diversity,
            citation_coverage,
            contradiction_penalty,
            tuple(missing),
            tuple(contradictions),
        )

    def assess_many(self, hypotheses: tuple[InvestigationHypothesis, ...] | list[InvestigationHypothesis],
                    bundle: EvidenceBundle) -> tuple[UncertaintyAssessment, ...]:
        assessments = [self.assess(hypothesis, bundle) for hypothesis in hypotheses]
        return tuple(sorted(assessments, key=lambda item: (-item.calibrated_confidence, item.hypothesis_id)))
