from dataclasses import asdict, dataclass

from aegis.correlation.pipeline import IncidentAnalysis
from aegis.investigation.evidence import EvidenceBundleBuilder
from aegis.investigation.faithfulness import FaithfulnessEvaluator, NarrativeClaim
from aegis.investigation.hypotheses import HypothesisEngine
from aegis.investigation.narrative import (
    GenerativeNarrativeLayer,
    GroundedNarrative,
    NarrativeDraft,
    NarrativeRequest,
)
from aegis.investigation.timeline import TimelineReconstructor
from aegis.investigation.uncertainty import ConfidenceUncertaintyModel


class DeterministicNarrativeProvider:
    """Safe default provider for API operation without external model dependencies."""

    name = "aegis-deterministic"

    def generate(self, request: NarrativeRequest) -> NarrativeDraft:
        cited = request.evidence_ids[: min(5, len(request.evidence_ids))]
        return NarrativeDraft(
            summary=f"Incident {request.incident_id} has evidence-backed investigative findings requiring review.",
            key_findings=("Competing hypotheses were generated and confidence-calibrated from incident evidence.",),
            next_questions=("What additional telemetry would best discriminate between the leading hypotheses?",),
            cited_evidence_ids=cited,
        )


@dataclass(frozen=True)
class InvestigationResult:
    incident_id: str
    evidence: dict[str, object]
    timeline: dict[str, object]
    hypotheses: tuple[dict[str, object], ...]
    uncertainty: tuple[dict[str, object], ...]
    narrative: dict[str, object]
    faithfulness: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class IncidentInvestigator:
    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider or DeterministicNarrativeProvider()

    def investigate(self, analysis: IncidentAnalysis) -> InvestigationResult:
        bundle = EvidenceBundleBuilder().build(
            analysis.incident, analysis.graph, analysis.mappings, analysis.risk,
        )
        timeline = TimelineReconstructor().reconstruct(bundle)
        hypotheses = HypothesisEngine().generate(bundle, timeline)
        uncertainty = ConfidenceUncertaintyModel().assess_many(hypotheses, bundle)
        narrative = GenerativeNarrativeLayer(self.provider).generate(
            bundle, timeline, hypotheses, uncertainty,
        )
        claims = self._evaluation_claims(narrative, bundle.evidence_ids)
        faithfulness = FaithfulnessEvaluator().evaluate(
            narrative, bundle, claims, uncertainty,
        )
        return InvestigationResult(
            analysis.incident.incident_id,
            bundle.to_dict(),
            timeline.to_dict(),
            tuple(item.to_dict() for item in hypotheses),
            tuple(item.to_dict() for item in uncertainty),
            narrative.to_dict(),
            faithfulness.to_dict(),
        )

    @staticmethod
    def _evaluation_claims(narrative: GroundedNarrative,
                           available_ids: frozenset[str]) -> tuple[NarrativeClaim, ...]:
        citations = narrative.cited_evidence_ids
        supported = bool(citations) and set(citations) <= available_ids
        texts = (narrative.summary,) + narrative.key_findings
        return tuple(
            NarrativeClaim(f"narrative-claim-{index}", text, citations, supported)
            for index, text in enumerate(texts, start=1)
        )
