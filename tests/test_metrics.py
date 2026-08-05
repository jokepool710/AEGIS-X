from aegis.common.metrics import IngestionMetrics


def test_ingestion_metrics_snapshot() -> None:
    metrics = IngestionMetrics()
    metrics.record_received()
    metrics.record_stored()
    metrics.record_gap(3)
    snapshot = metrics.snapshot()
    assert snapshot["received"] == 1
    assert snapshot["stored"] == 1
    assert snapshot["sequence_gaps"] == 1
    assert snapshot["missing_events"] == 3
    assert snapshot["last_received_at"] is not None
    assert snapshot["last_stored_at"] is not None


def test_rejection_and_duplicate_counters() -> None:
    metrics = IngestionMetrics()
    metrics.record_received()
    metrics.record_duplicate()
    metrics.record_received()
    metrics.record_rejected()
    snapshot = metrics.snapshot()
    assert snapshot["received"] == 2
    assert snapshot["duplicates"] == 1
    assert snapshot["rejected"] == 1
