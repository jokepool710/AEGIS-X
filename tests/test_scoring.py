import pytest

from aegis.detection.scoring import ScoreWeights, UnifiedScoreCalibrator


def test_weights_are_normalized() -> None:
    weights = ScoreWeights(7.0, 5.0, 8.0).normalized()
    assert weights.z_score + weights.ewma_score + weights.isolation_score == pytest.approx(1.0)


def test_consensus_bonus_rewards_detector_agreement() -> None:
    calibrator = UnifiedScoreCalibrator(
        threshold=0.70,
        agreement_bonus=0.08,
        detector_vote_threshold=0.60,
    )
    single = calibrator.calibrate(0.90, 0.20, 0.20)
    consensus = calibrator.calibrate(0.70, 0.70, 0.20)

    assert consensus.unified_score > single.unified_score


def test_threshold_and_severity_are_consistent() -> None:
    calibrator = UnifiedScoreCalibrator(threshold=0.60, agreement_bonus=0.0)
    result = calibrator.calibrate(0.70, 0.70, 0.70)

    assert result.anomalous is True
    assert result.severity == "medium"
    assert result.threshold == 0.60


def test_invalid_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        ScoreWeights(-1.0, 1.0, 1.0).normalized()
