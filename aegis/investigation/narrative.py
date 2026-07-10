from dataclasses import asdict, dataclass
from typing import Protocol

from aegis.investigation.evidence import EvidenceBundle
from aegis.investigation.hypotheses import InvestigationHypothesis
from aegis.investigation.timeline import InvestigationTimeline
from aegis.investigation.uncertainty import UncertaintyAssessment


@dataclass(frozen=True)
class NarrativeRequest:
    incident_id: str
    evidence_ids: tuple[str, ...]
    prompt: str


@dataclass(frozen=True)
class NarrativeDraft:
    summary: str
    key_findings: tuple[str, ...]
    next_questions: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class GroundedNarrative:
    incident_id: str
    summary: str
    key_findings: tuple[str, ...]
    next_questions: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]
    provider: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class NarrativeProvider(Protocol):
    name: str

    def generate(self, request: NarrativeRequest) -> NarrativeDraft:
        ...


class NarrativeGroundingError(ValueError):
    pass


class GenerativeNarrativeLayer:
    """Render a narrative through an injected provider, then enforce evidence grounding."""

    def __init__(self, provider: NarrativeProvider) -> None:
        self.provider = provider

    @staticmethod
    def _build_prompt(bundle: EvidenceBundle, timeline: InvestigationTimeline,
                      hypotheses: tuple[InvestigationHypothesis, ...],
                      assessments: tuple[UncertaintyAssessment, ...]) -> NarrativeRequest:
        assessment_by_id = {item.hypothesis_id: item for item in assessments}
        lines = [
            "Produce a concise incident investigation narrative using only the supplied facts.",
            "Do not introduce entities, causes, techniques, or actions not supported by evidence.",
            "Return citations as exact evidence IDs.",
            f"Incident: {bundle.incident_id}",
            "Timeline:",
        ]
        for event in timeline.events:
            lines.append(
                f"- {event.timestamp} | {event.summary} | evidence={','.join(event.evidence_ids)}"
            )
        lines.append("Hypotheses:")
        for hypothesis in hypotheses:
            assessment = assessment_by_id.get(hypothesis.hypothesis_id)
            confidence = assessment.calibrated_confidence if assessment else hypothesis.confidence
            lines.append(
                f"- {hypothesis.title} | confidence={confidence:.4f} | "
                f"evidence={','.join(hypothesis.evidence_ids)}"
            )
        lines.append("Available evidence IDs: " + ",".join(sorted(bundle.evidence_ids)))
        return NarrativeRequest(bundle.incident_id, tuple(sorted(bundle.evidence_ids)), "\n".join(lines))

    def generate(self, bundle: EvidenceBundle, timeline: InvestigationTimeline,
                 hypotheses: tuple[InvestigationHypothesis, ...],
                 assessments: tuple[UncertaintyAssessment, ...]) -> GroundedNarrative:
        if timeline.incident_id != bundle.incident_id:
            raise NarrativeGroundingError("timeline and bundle incident IDs differ")
        hypothesis_ids = {item.hypothesis_id for item in hypotheses}
        if any(item.hypothesis_id not in hypothesis_ids for item in assessments):
            raise NarrativeGroundingError("uncertainty assessment has no matching hypothesis")

        request = self._build_prompt(bundle, timeline, hypotheses, assessments)
        draft = self.provider.generate(request)
        cited = tuple(dict.fromkeys(draft.cited_evidence_ids))
        if not cited:
            raise NarrativeGroundingError("generated narrative has no evidence citations")
        invalid = tuple(evidence_id for evidence_id in cited if evidence_id not in bundle.evidence_ids)
        if invalid:
            raise NarrativeGroundingError(
                "generated narrative cites evidence outside the active bundle: " + ", ".join(invalid)
            )
        if not draft.summary.strip():
            raise NarrativeGroundingError("generated narrative summary is empty")

        return GroundedNarrative(
            bundle.incident_id,
            draft.summary.strip(),
            tuple(item.strip() for item in draft.key_findings if item.strip()),
            tuple(item.strip() for item in draft.next_questions if item.strip()),
            cited,
            self.provider.name,
        )
