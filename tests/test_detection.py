from datetime import datetime, timezone

from aegis.common.models import TelemetryEvent
from aegis.detection.pipeline import DetectionPipeline


def event(sequence: int, value: float) -> TelemetryEvent:
    now = datetime.now(timezone.utc)
    return TelemetryEvent(
        event_id=f"event-{sequence}", device_id="pump-01", device_type="industrial_pump",
        site_id="lab-01", timestamp=now, sequence=sequence, metric="temperature",
        value=value, unit="celsius", quality="good", source_topic="test", ingested_at=now,
    )


def test_detector_warms_up_before_scoring() -> None:
    detector = DetectionPipeline(window_size=10, warmup=5)
    for sequence in range(5):
        result = detector.process(event(sequence, 24.0 + sequence * 0.01))
        assert result.anomalous is False
        assert result.unified_score == 0.0


def test_extreme_value_scores_higher_than_normal_value() -> None:
    detector = DetectionPipeline(window_size=30, warmup=10, threshold=0.5)
    for sequence in range(20):
        detector.process(event(sequence, 24.0 + (sequence % 3) * 0.05))
    normal = detector.process(event(21, 24.05))
    extreme = detector.process(event(22, 60.0))
    assert extreme.unified_score > normal.unified_score
    assert extreme.anomalous is True
