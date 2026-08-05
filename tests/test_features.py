import pytest

from aegis.detection.features import FeatureExtractor


def test_extracts_window_statistics_and_dynamics() -> None:
    features = FeatureExtractor().extract([10.0, 11.0, 12.0, 13.0], 15.0)

    assert features.current_value == 15.0
    assert features.mean == 11.5
    assert features.minimum == 10.0
    assert features.maximum == 13.0
    assert features.median == 11.5
    assert features.range == 3.0
    assert features.slope == pytest.approx(1.0)
    assert features.delta == 2.0
    assert features.mean_abs_change == 1.0
    assert features.sample_count == 4
    assert len(features.as_vector()) == 11


def test_empty_history_returns_safe_features() -> None:
    features = FeatureExtractor().extract([], 24.5)

    assert features.mean == 24.5
    assert features.std == 0.0
    assert features.range == 0.0
    assert features.slope == 0.0
    assert features.delta == 0.0
    assert features.sample_count == 1


def test_constant_window_has_zero_variability_and_slope() -> None:
    features = FeatureExtractor().extract([5.0, 5.0, 5.0, 5.0], 5.0)

    assert features.std == 0.0
    assert features.range == 0.0
    assert features.slope == pytest.approx(0.0, abs=1e-12)
    assert features.mean_abs_change == 0.0
