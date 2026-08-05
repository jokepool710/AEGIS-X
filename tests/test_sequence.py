from aegis.common.sequence import SequenceTracker


def test_contiguous_sequence_has_no_gap() -> None:
    tracker = SequenceTracker()
    assert tracker.observe("pump-01", "temperature", 10) is None
    assert tracker.observe("pump-01", "temperature", 11) is None


def test_detects_sequence_gap() -> None:
    tracker = SequenceTracker()
    tracker.observe("pump-01", "temperature", 10)
    gap = tracker.observe("pump-01", "temperature", 14)
    assert gap is not None
    assert gap.missing_from == 11
    assert gap.missing_to == 13
    assert gap.missing_count == 3


def test_tracks_metrics_independently() -> None:
    tracker = SequenceTracker()
    tracker.observe("pump-01", "temperature", 5)
    assert tracker.observe("pump-01", "vibration", 20) is None
    assert tracker.observe("pump-01", "temperature", 6) is None


def test_out_of_order_event_does_not_move_tracker_backwards() -> None:
    tracker = SequenceTracker()
    tracker.observe("pump-01", "temperature", 10)
    assert tracker.observe("pump-01", "temperature", 8) is None
    gap = tracker.observe("pump-01", "temperature", 12)
    assert gap is not None
    assert gap.missing_from == 11
    assert gap.missing_count == 1
