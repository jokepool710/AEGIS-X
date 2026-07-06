from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from aegis.common.models import TelemetryEvent
from aegis.detection.features import FeatureExtractor, WindowFeatures


@dataclass(frozen=True)
class DetectionResult:
    z_score: float
    ewma_score: float
    isolation_score: float
    unified_score: float
    anomalous: bool
    sample_count: int
    features: WindowFeatures


class DetectionPipeline:
    def __init__(self, window_size: int = 60, warmup: int = 20, threshold: float = 0.70) -> None:
        self.window_size = window_size
        self.warmup = warmup
        self.threshold = threshold
        self.windows: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.ewma: dict[tuple[str, str], float] = {}
        self.feature_extractor = FeatureExtractor()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def process(self, event: TelemetryEvent) -> DetectionResult:
        key = (event.device_id, event.metric)
        window = self.windows[key]
        history = list(window)
        features = self.feature_extractor.extract(history, event.value)

        if len(history) < self.warmup:
            window.append(event.value)
            self.ewma[key] = (
                event.value
                if key not in self.ewma
                else 0.2 * event.value + 0.8 * self.ewma[key]
            )
            return DetectionResult(0.0, 0.0, 0.0, 0.0, False, len(window), features)

        std = features.std or 1e-9
        raw_z = abs(event.value - features.mean) / std
        z_score = self._clamp(raw_z / 6.0)

        previous_ewma = self.ewma.get(key, features.mean)
        ewma_deviation = abs(event.value - previous_ewma) / std
        ewma_score = self._clamp(ewma_deviation / 6.0)

        model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
        training = np.asarray(history, dtype=float).reshape(-1, 1)
        model.fit(training)
        decision = float(model.decision_function([[event.value]])[0])
        isolation_score = self._clamp(0.5 - decision)

        unified = self._clamp(
            0.35 * z_score + 0.25 * ewma_score + 0.40 * isolation_score
        )
        anomalous = unified >= self.threshold

        window.append(event.value)
        self.ewma[key] = 0.2 * event.value + 0.8 * previous_ewma
        return DetectionResult(
            z_score,
            ewma_score,
            isolation_score,
            unified,
            anomalous,
            len(window),
            features,
        )
