from aegis.detection.model_cache import IsolationForestModelCache


def test_reuses_model_before_retrain_interval() -> None:
    cache = IsolationForestModelCache(retrain_interval=5, n_estimators=10)
    key = ("pump-01", "temperature")
    history = [24.0, 24.1, 23.9, 24.2, 24.0]

    first = cache.get_or_train(key, history, sample_count=5)
    second = cache.get_or_train(key, history + [24.1], sample_count=6)

    assert first is second
    assert cache.fit_count(key) == 1
    assert second.generation == 1


def test_retrains_after_interval() -> None:
    cache = IsolationForestModelCache(retrain_interval=5, n_estimators=10)
    key = ("pump-01", "temperature")
    history = [24.0, 24.1, 23.9, 24.2, 24.0]

    first = cache.get_or_train(key, history, sample_count=5)
    second = cache.get_or_train(key, history + [24.1] * 5, sample_count=10)

    assert first is not second
    assert cache.fit_count(key) == 2
    assert second.generation == 2
    assert second.trained_at_sample == 10


def test_models_are_independent_per_stream() -> None:
    cache = IsolationForestModelCache(retrain_interval=5, n_estimators=10)
    temperature = ("pump-01", "temperature")
    vibration = ("pump-01", "vibration")

    cache.get_or_train(temperature, [24.0, 24.1, 24.2], sample_count=3)
    cache.get_or_train(vibration, [0.3, 0.4, 0.35], sample_count=3)

    assert cache.fit_count(temperature) == 1
    assert cache.fit_count(vibration) == 1
    assert cache.metadata(temperature)["generation"] == 1
    assert cache.metadata(vibration)["generation"] == 1


def test_score_returns_cached_model_metadata() -> None:
    cache = IsolationForestModelCache(retrain_interval=10, n_estimators=10)
    key = ("pump-01", "pressure")

    decision, model = cache.score(
        key,
        [5.0, 5.1, 4.9, 5.05, 5.0],
        current_value=7.0,
        sample_count=5,
    )

    assert isinstance(decision, float)
    assert model.generation == 1
    assert model.training_size == 5
