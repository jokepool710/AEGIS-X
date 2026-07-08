from dataclasses import asdict, dataclass

from aegis.investigation.evidence import EvidenceBundle
from aegis.investigation.narrative import GroundedNarrative
from aegis.investigation.uncertainty import UncertaintyAssessment


@dataclass(frozen=True)
class NarrativeClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]
    supported: bool


@dataclass(frozen=True)
class FaithfulnessReport:
    incident_id: str
    total_claims: int
    supported_claims: int
    unsupported_claim_rate: float
    citation_validity: float
    evidence_coverage: float
    contradiction_handling: float
    narrative_consistency: float
    faithfulness_score: float
    invalid_citation_ids: tuple[str, ...]
    unaddressed_contradictions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FaithfulnessEvaluator:
    """Evaluate measurable grounding properties without using a model as its own judge."""

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)

    def evaluate(self, narrative: GroundedNarrative, bundle: EvidenceBundle,
                 claims: tuple[NarrativeClaim, ...] | list[NarrativeClaim],
                 assessments: tuple[UncertaintyAssessment, ...] | list[UncertaintyAssessment] = (),
                 addressed_contradictions: tuple[str, ...] = ()) -> FaithfulnessReport:
        if narrative.incident_id != bundle.incident_id:
            raise ValueError("narrative and evidence bundle must refer to the same incident")

        claims = tuple(claims)
        total = len(claims)
        supported = sum(claim.supported for claim in claims)
        unsupported_rate = self._clamp((total - supported) / max(1, total))

        all_citations = tuple(dict.fromkeys(
            evidence_id
            for claim in claims
            for evidence_id in claim.evidence_ids
        ))
        valid_citations = tuple(evidence_id for evidence_id in all_citations if evidence_id in bundle.evidence_ids)
        invalid_citations = tuple(evidence_id for evidence_id in all_citations if evidence_id not in bundle.evidence_ids)
        citation_validity = self._clamp(len(valid_citations) / max(1, len(all_citations)))

        narrative_citations = set(narrative.cited_evidence_ids)
        evidence_coverage = self._clamp(len(narrative_citations & bundle.evidence_ids) / max(1, len(bundle.evidence_ids)))

        contradictions = tuple(dict.fromkeys(
            contradiction
            for assessment in assessments
            for contradiction in assessment.contradictions
        ))
        addressed = set(addressed_contradictions)
        unaddressed = tuple(item for item in contradictions if item not in addressed)
        contradiction_handling = self._clamp(
            1.0 if not contradictions else (len(contradictions) - len(unaddressed)) / len(contradictions)
        )

        duplicate_texts = total - len({claim.text.strip().lower() for claim in claims})
        consistency_penalty = duplicate_texts / max(1, total)
        narrative_consistency = self._clamp(1.0 - consistency_penalty - unsupported_rate * 0.5)

        score = self._clamp(
            (1.0 - unsupported_rate) * 0.35
            + citation_validity * 0.20
            + evidence_coverage * 0.15
            + contradiction_handling * 0.15
            + narrative_consistency * 0.15
        )
        return FaithfulnessReport(
            bundle.incident_id,
            total,
            supported,
            unsupported_rate,
            citation_validity,
            evidence_coverage,
            contradiction_handling,
            narrative_consistency,
            score,
            invalid_citations,
            unaddressed,
        )
