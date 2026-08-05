from aegis.common.storage import TelemetryStore
from aegis.workflow.feedback import FeedbackEngine, FeedbackType


def test_submit_and_list_analyst_feedback(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_feedback.db"))
    engine = FeedbackEngine(storage)

    fb1 = engine.submit(
        case_id="case-101",
        incident_id="inc-1",
        analyst_id="analyst-sec-1",
        feedback_type=FeedbackType.ACCEPT_HYPOTHESIS,
        target_id="hyp-1",
        comment="Hypothesis aligns with PLC telemetry anomaly",
    )
    fb2 = engine.submit(
        case_id="case-101",
        incident_id="inc-1",
        analyst_id="analyst-sec-2",
        feedback_type=FeedbackType.ADJUST_CONFIDENCE,
        target_id="hyp-1",
        adjusted_confidence=0.88,
        comment="Adjusted based on manual packet analysis",
    )

    assert fb1.feedback_id.startswith("fbk-")
    assert fb2.feedback_id.startswith("fbk-")
    by_case = engine.list_by_case("case-101")
    assert len(by_case) == 2
    assert by_case[0].analyst_id == "analyst-sec-1"
    assert by_case[1].adjusted_confidence == 0.88


def test_hypothesis_confidence_aggregation(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_feedback_agg.db"))
    engine = FeedbackEngine(storage)

    engine.submit("case-102", "inc-2", "analyst-1", FeedbackType.ACCEPT_HYPOTHESIS, "hyp-1")
    engine.submit("case-102", "inc-2", "analyst-2", FeedbackType.ADJUST_CONFIDENCE, "hyp-1", adjusted_confidence=0.90)

    # Base confidence 0.60
    # Accept hypothesis -> min(1.0, 0.60 + 0.15) = 0.75
    # Adjust confidence -> 0.90
    # Average = (0.75 + 0.90) / 2 = 0.825
    aggregated = engine.aggregate_hypothesis_score("case-102", "hyp-1", 0.60)
    assert aggregated == 0.825
