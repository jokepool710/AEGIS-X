from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TemporalDetection:
    score: float
    repeated_value_score: float
    replay_score: float


class TemporalAttackDetector:
    """Detect frozen sensors and repeated telemetry patterns missed by point detectors."""

    def __init__(self, freeze_run: int = 6, replay_period_max: int = 12, tolerance: float = 1e-9) -> None:
        self.freeze_run = freeze_run
        self.replay_period_max = replay_period_max
        self.tolerance = tolerance

    def score(self, history: list[float], current_value: float) -> TemporalDetection:
        values = history + [current_value]
        repeated = self._repeated_value_score(values)
        replay = self._replay_score(values)
        return TemporalDetection(max(repeated, replay), repeated, replay)

    def _repeated_value_score(self, values: list[float]) -> float:
        if len(values) < self.freeze_run:
            return 0.0
        tail = values[-self.freeze_run :]
        spread = max(tail) - min(tail)
        return 1.0 if spread <= self.tolerance else 0.0

    def _replay_score(self, values: list[float]) -> float:
        if len(values) < 8:
            return 0.0
        array = np.asarray(values, dtype=float)
        best = 0.0
        max_period = min(self.replay_period_max, len(array) // 2)
        for period in range(2, max_period + 1):
            recent = array[-period:]
            previous = array[-2 * period : -period]
            scale = max(float(np.std(array[-2 * period :])), 1e-6)
            error = float(np.mean(np.abs(recent - previous))) / scale
            similarity = max(0.0, 1.0 - error)
            best = max(best, similarity)
        return best
