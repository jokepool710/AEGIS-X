from datetime import datetime, timezone

import pytest

from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore
from aegis.detection.alerts import InvalidAlertTransitionError, AlertStore
from aegis.detection.features import FeatureExtractor
from aegis.detection.pipeline import DetectionResult


def make_event() -> TelemetryEvent:
    now = datetime.now(timezone.utc)
    return TelemetryEvent(
        event_id="alert-event-1", device_id="pump-01", device_type="industrial_pump",
        site_id="lab-01", timestamp=now, sequence=1, metric="temperature",
        value=60.0, unit="celsius", quality="good", source_topic="test", ingested_at=now,
    )


def make_result() -> DetectionResult:
    features = FeatureExtractor().extract([24.0, 24.1, 24.2], 60.0)
    return DetectionResult(1.0, 1.0, 0.9, 0.96, True, 21, features, 1, "critical")


def test_alert_starts_open_and_can_progress_to_resolved(tmp_path) -> None:
    store = AlertStore(TelemetryStore(db_path=tmp_path / "alerts.db"))
    alert_id = store.create(make_event(), make_result())

    assert store.get(alert_id)["status"] == "open"
    acknowledged = store.transition(alert_id, "acknowledged", "SOC analyst accepted")
    investigating = store.transition(alert_id, "investigating", "checking pump telemetry")
    resolved = store.transition(alert_id, "resolved", "confirmed and contained")

    assert acknowledged["status"] == "acknowledged"
    assert investigating["status"] == "investigating"
    assert resolved["status"] == "resolved"
    assert resolved["status_note"] == "confirmed and contained"
    assert resolved["updated_at"] is not None


def test_terminal_alert_cannot_be_reopened(tmp_path) -> None:
    store = AlertStore(TelemetryStore(db_path=tmp_path / "alerts.db"))
    alert_id = store.create(make_event(), make_result())
    store.transition(alert_id, "dismissed", "false positive")

    with pytest.raises(InvalidAlertTransitionError):
        store.transition(alert_id, "investigating")


def test_alert_list_can_filter_by_status(tmp_path) -> None:
    store = AlertStore(TelemetryStore(db_path=tmp_path / "alerts.db"))
    alert_id = store.create(make_event(), make_result())
    store.transition(alert_id, "resolved", "handled")

    assert len(store.list(status="resolved")) == 1
    assert store.list(status="open") == []
