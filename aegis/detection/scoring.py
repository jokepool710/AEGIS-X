from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreWeights:
    z_score: float = 0.35
    ewma_score: float = 0.25
    isolation_score: float = 0.40

    def normalized(self) -> "ScoreWeights":
        total = self.z_score + self.ewma_score + self.isolation_score
        if total <= 0:
            raise ValueError("score weights must sum to a positive value")
        if min(self.z_score, self.ewma_score, self.isolation_score) < 0:
            raise ValueError("score weights cannot be negative")
        return ScoreWeights(
            self.z_score / total,
            self.ewma_score / total,
            self.isolation_score / total,
        )


@dataclass(frozen=True)
class CalibratedScore:
    unified_score: float
    anomalous: bool
    severity: str
    threshold: float


class UnifiedScoreCalibrator:
    def __init__(
        self,
        weights: ScoreWeights | None = None,
        threshold: float = 0.70,
        agreement_bonus: float = 0.08,
        detector_vote_threshold: float = 0.60,
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not 0.0 <= agreement_bonus <= 1.0:
            raise ValueError("agreement_bonus must be between 0 and 1")
        if not 0.0 <= detector_vote_threshold <= 1.0:
            raise ValueError("detector_vote_threshold must be between 0 and 1")
        self.weights = (weights or ScoreWeights()).normalized()
        self.threshold = threshold
        self.agreement_bonus = agreement_bonus
        self.detector_vote_threshold = detector_vote_threshold

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def calibrate(
        self,
        z_score: float,
        ewma_score: float,
        isolation_score: float,
        temporal_score: float = 0.0,
    ) -> CalibratedScore:
        scores = [self._clamp(z_score), self._clamp(ewma_score), self._clamp(isolation_score)]
        weighted = (
            self.weights.z_score * scores[0]
            + self.weights.ewma_score * scores[1]
            + self.weights.isolation_score * scores[2]
        )
        votes = sum(score >= self.detector_vote_threshold for score in scores)
        consensus_bonus = self.agreement_bonus if votes >= 2 else 0.0
        point_score = self._clamp(weighted + consensus_bonus)
        unified = max(point_score, self._clamp(temporal_score))
        anomalous = unified >= self.threshold

        if unified >= 0.90:
            severity = "critical"
        elif unified >= 0.80:
            severity = "high"
        elif anomalous:
            severity = "medium"
        else:
            severity = "normal"
        return CalibratedScore(unified, anomalous, severity, self.threshold)
