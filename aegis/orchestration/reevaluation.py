from __future__ import annotations

from dataclasses import dataclass

from aegis.investigation.evidence import EvidenceBundle
from aegis.investigation.hypotheses import HypothesisEngine, InvestigationHypothesis
from aegis.investigation.timeline import TimelineReconstructor
from aegis.investigation.uncertainty import ConfidenceUncertaintyModel, UncertaintyAssessment


@dataclass(frozen=True)
class HypothesisDelta:
    hypothesis_id: str
    previous_confidence: float | None
    current_confidence: float
    confidence_delta: float | None
    previous_contradictions: tuple[str, ...]
    current_contradictions: tuple[str, ...]
    resolved_contradictions: tuple[str, ...]
    new_contradictions: tuple[str, ...]


@dataclass(frozen=True)
class ReevaluationOutcome:
    hypotheses: tuple[InvestigationHypothesis, ...]
    uncertainty: tuple[UncertaintyAssessment, ...]
    deltas: tuple[HypothesisDelta, ...]
    another_acquisition_wave: bool
    reasons: tuple[str, ...]


class HypothesisReevaluationLoop:
    """Rebuild hypotheses after evidence acquisition and decide whether more evidence is justified."""

    def __init__(self, confidence_target: float = 0.75,
                 minimum_gain: float = 0.02) -> None:
        self.confidence_target = confidence_target
        self.minimum_gain = minimum_gain

    def reevaluate(self, bundle: EvidenceBundle,
                   previous: tuple[UncertaintyAssessment, ...] | list[UncertaintyAssessment]) -> ReevaluationOutcome:
        timeline = TimelineReconstructor().reconstruct(bundle)
        hypotheses = HypothesisEngine().generate(bundle, timeline)
        uncertainty = ConfidenceUncertaintyModel().assess_many(hypotheses, bundle)
        previous_by_id = {item.hypothesis_id: item for item in previous}
        deltas = tuple(self._delta(item, previous_by_id.get(item.hypothesis_id)) for item in uncertainty)
        another_wave, reasons = self._should_continue(uncertainty, deltas)
        return ReevaluationOutcome(hypotheses, uncertainty, deltas, another_wave, reasons)

    @staticmethod
    def _delta(current: UncertaintyAssessment,
               previous: UncertaintyAssessment | None) -> HypothesisDelta:
        if previous is None:
            return HypothesisDelta(
                current.hypothesis_id, None, current.calibrated_confidence, None,
                (), current.contradictions, (), current.contradictions,
            )
        old = set(previous.contradictions)
        new = set(current.contradictions)
        return HypothesisDelta(
            current.hypothesis_id,
            previous.calibrated_confidence,
            current.calibrated_confidence,
            round(current.calibrated_confidence - previous.calibrated_confidence, 4),
            previous.contradictions,
            current.contradictions,
            tuple(sorted(old - new)),
            tuple(sorted(new - old)),
        )

    def _should_continue(self, uncertainty: tuple[UncertaintyAssessment, ...],
                         deltas: tuple[HypothesisDelta, ...]) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if not uncertainty:
            return False, ("no hypotheses available for further acquisition",)
        leader = uncertainty[0]
        if leader.calibrated_confidence < self.confidence_target:
            reasons.append("leading hypothesis remains below confidence target")
        if leader.missing_evidence:
            reasons.append("leading hypothesis still has missing evidence")
        if leader.contradictions:
            reasons.append("leading hypothesis still has unresolved contradictions")
        leader_delta = next((item for item in deltas if item.hypothesis_id == leader.hypothesis_id), None)
        if leader_delta and leader_delta.confidence_delta is not None and leader_delta.confidence_delta < self.minimum_gain:
            reasons.append("latest evidence wave produced insufficient confidence gain")
        return bool(reasons), tuple(reasons)
