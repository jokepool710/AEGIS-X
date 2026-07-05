from datetime import datetime, timezone

from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore


def make_event(event_id: str = "event-1") -> TelemetryEvent:
    now = datetime.now(timezone.utc)
    return TelemetryEvent(
        event_id=event_id,
        device_id="pump-01",
        device_type="industrial_pump",
        site_id="lab-01",
        timestamp=now,
        sequence=1,
        metric="temperature",
        value=24.5,
        unit="celsius",
        quality="good",
        source_topic="aegis/telemetry/lab-01/pump-01/temperature",
        ingested_at=now,
    )


def test_persists_event(tmp_path) -> None:
    store = TelemetryStore(str(tmp_path / "telemetry.db"))
    assert store.insert(make_event()) is True
    assert store.count() == 1


def test_rejects_duplicate_device_sequence_metric(tmp_path) -> None:
    store = TelemetryStore(str(tmp_path / "telemetry.db"))
    assert store.insert(make_event("event-1")) is True
    assert store.insert(make_event("event-2")) is False
    assert store.count() == 1
