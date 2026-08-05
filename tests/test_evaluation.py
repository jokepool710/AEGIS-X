from aegis.evaluation.metrics import attack_episode_delays, evaluate_predictions


def test_classification_metrics_are_computed_correctly() -> None:
    labels = [True, True, False, False, True, False]
    predictions = [True, False, True, False, True, False]

    metrics = evaluate_predictions(labels, predictions)

    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.true_negatives == 2
    assert metrics.false_negatives == 1
    assert metrics.precision == 2 / 3
    assert metrics.recall == 2 / 3
    assert metrics.f1 == 2 / 3
    assert metrics.false_positive_rate == 1 / 3


def test_detection_delay_is_measured_from_attack_episode_start() -> None:
    labels = [False, True, True, True, False, True, True, False]
    predictions = [False, False, False, True, False, False, True, False]

    delays, episodes = attack_episode_delays(labels, predictions)

    assert episodes == 2
    assert delays == [2, 1]


def test_undetected_episode_is_counted_but_has_no_delay() -> None:
    labels = [True, True, False, True, True]
    predictions = [False, True, False, False, False]

    metrics = evaluate_predictions(labels, predictions)

    assert metrics.total_attack_episodes == 2
    assert metrics.detected_attack_episodes == 1
    assert metrics.mean_detection_delay == 1.0


def test_zero_denominators_are_safe() -> None:
    metrics = evaluate_predictions([False, False], [False, False])

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.mean_detection_delay is None
