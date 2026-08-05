from dataclasses import dataclass


@dataclass(frozen=True)
class SlowBurnScore:
    score: float
    positive_cusum: float
    negative_cusum: float
    drift_score: float


class SlowBurnDetector:
    """Detect persistent low-amplitude process shifts missed by point detectors.

    Combines standardized two-sided CUSUM accumulation with a long-vs-short
    mean residual. The detector is stateless: state is represented by the
    telemetry window, which keeps experiment runs deterministic and isolated.
    """

    def __init__(self, reference: float = 0.35, decision_interval: float = 8.0) -> None:
        if reference < 0 or decision_interval <= 0:
            raise ValueError("invalid slow-burn detector parameters")
        self.reference = reference
        self.decision_interval = decision_interval

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def score(self, history: list[float], current_value: float) -> SlowBurnScore:
        values = history + [current_value]
        if len(values) < 12:
            return SlowBurnScore(0.0, 0.0, 0.0, 0.0)

        baseline_size = max(6, len(values) // 3)
        baseline = values[:baseline_size]
        mean = sum(baseline) / len(baseline)
        variance = sum((value - mean) ** 2 for value in baseline) / len(baseline)
        std = max(variance ** 0.5, 1e-6)

        positive = 0.0
        negative = 0.0
        max_positive = 0.0
        max_negative = 0.0
        for value in values[baseline_size:]:
            residual = (value - mean) / std
            positive = max(0.0, positive + residual - self.reference)
            negative = max(0.0, negative - residual - self.reference)
            max_positive = max(max_positive, positive)
            max_negative = max(max_negative, negative)

        recent_size = max(4, len(values) // 5)
        recent_mean = sum(values[-recent_size:]) / recent_size
        drift_z = abs(recent_mean - mean) / std
        drift_score = self._clamp(drift_z / 4.0)
        cusum_score = self._clamp(max(max_positive, max_negative) / self.decision_interval)
        combined = self._clamp(0.65 * cusum_score + 0.35 * drift_score)
        return SlowBurnScore(combined, max_positive, max_negative, drift_score)
