from aegis.detection.slow_burn import SlowBurnDetector


def test_persistent_drift_scores_higher_than_stable_process() -> None:
    detector = SlowBurnDetector()
    stable_history = [24.0 + ((i % 5) - 2) * 0.02 for i in range(40)]
    stable = detector.score(stable_history, 24.01)

    drift_history = [24.0 + ((i % 5) - 2) * 0.02 for i in range(15)]
    drift_history += [24.0 + 0.035 * i for i in range(25)]
    drift = detector.score(drift_history, 24.9)

    assert drift.score > stable.score
    assert drift.score >= 0.75


def test_negative_degradation_is_detected_symmetrically() -> None:
    history = [100.0 + ((i % 3) - 1) * 0.05 for i in range(15)]
    history += [100.0 - 0.08 * i for i in range(25)]
    result = SlowBurnDetector().score(history, 97.9)

    assert result.negative_cusum > result.positive_cusum
    assert result.score >= 0.75


def test_short_history_does_not_emit_contextual_score() -> None:
    result = SlowBurnDetector().score([1.0, 1.1, 0.9], 1.0)
    assert result.score == 0.0
