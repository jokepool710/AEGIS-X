from collections import defaultdict, deque
from dataclasses import dataclass

from aegis.common.models import TelemetryEvent
from aegis.detection.features import FeatureExtractor, WindowFeatures
from aegis.detection.model_cache import IsolationForestModelCache
from aegis.detection.scoring import ScoreWeights, UnifiedScoreCalibrator
from aegis.detection.temporal import TemporalAttackDetector


@dataclass(frozen=True)
class DetectionResult:
    z_score: float
    ewma_score: float
    isolation_score: float
    unified_score: float
    anomalous: bool
    sample_count: int
    features: WindowFeatures
    model_generation: int
    severity: str


class DetectionPipeline:
    def __init__(
        self,
        window_size: int = 60,
        warmup: int = 20,
        threshold: float = 0.70,
        retrain_interval: int = 20,
        score_weights: ScoreWeights | None = None,
        agreement_bonus: float = 0.08,
    ) -> None:
        self.window_size = window_size
        self.warmup = warmup
        self.threshold = threshold
        self.windows: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.ewma: dict[tuple[str, str], float] = {}
        self.stream_event_counts: dict[tuple[str, str], int] = defaultdict(int)
        self.feature_extractor = FeatureExtractor()
        self.temporal_detector = TemporalAttackDetector()
        self.model_cache = IsolationForestModelCache(retrain_interval=retrain_interval)
        self.score_calibrator = UnifiedScoreCalibrator(
            weights=score_weights, threshold=threshold, agreement_bonus=agreement_bonus
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    def process(self, event: TelemetryEvent) -> DetectionResult:
        key = (event.device_id, event.metric)
        self.stream_event_counts[key] += 1
        event_count = self.stream_event_counts[key]
        window = self.windows[key]
        history = list(window)
        features = self.feature_extractor.extract(history, event.value)

        if len(history) < self.warmup:
            window.append(event.value)
            self.ewma[key] = event.value if key not in self.ewma else 0.2 * event.value + 0.8 * self.ewma[key]
            return DetectionResult(0.0, 0.0, 0.0, 0.0, False, event_count, features, 0, "normal")

        std = features.std or 1e-9
        z_score = self._clamp((abs(event.value - features.mean) / std) / 6.0)
        previous_ewma = self.ewma.get(key, features.mean)
        ewma_score = self._clamp((abs(event.value - previous_ewma) / std) / 6.0)

        decision, cached_model = self.model_cache.score(
            key=key, history=history, current_value=event.value, sample_count=event_count
        )
        isolation_score = self._clamp(0.5 - decision)
        temporal = self.temporal_detector.score(history, event.value)

        calibrated = self.score_calibrator.calibrate(
            z_score=z_score,
            ewma_score=ewma_score,
            isolation_score=isolation_score,
            temporal_score=temporal.score,
        )

        window.append(event.value)
        self.ewma[key] = 0.2 * event.value + 0.8 * previous_ewma
        return DetectionResult(
            z_score, ewma_score, isolation_score, calibrated.unified_score,
            calibrated.anomalous, event_count, features, cached_model.generation,
            calibrated.severity,
        )
