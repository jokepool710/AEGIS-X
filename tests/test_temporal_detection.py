from aegis.detection.temporal import TemporalAttackDetector


def test_detects_frozen_sensor_run() -> None:
    detector = TemporalAttackDetector(freeze_run=6)
    result = detector.score([24.0, 24.0, 24.0, 24.0, 24.0], 24.0)
    assert result.repeated_value_score == 1.0
    assert result.score == 1.0


def test_detects_replayed_pattern() -> None:
    detector = TemporalAttackDetector()
    pattern = [24.0, 24.2, 23.9, 24.1, 24.3]
    result = detector.score(pattern + pattern[:-1], pattern[-1])
    assert result.replay_score > 0.95


def test_normal_noisy_signal_is_not_frozen() -> None:
    detector = TemporalAttackDetector(freeze_run=6)
    result = detector.score([24.0, 24.1, 23.9, 24.2, 24.05], 23.95)
    assert result.repeated_value_score == 0.0
