import json

from collectors.telemetry.mqtt_collector import normalize


def test_normalize_valid_payload() -> None:
    payload = {
        "device_id": "pump-01",
        "device_type": "industrial_pump",
        "site_id": "lab-01",
        "timestamp": "2026-07-05T10:00:00+00:00",
        "sequence": 7,
        "metric": "temperature",
        "value": 25.4,
        "unit": "celsius",
        "quality": "good",
    }
    event = normalize("aegis/telemetry/lab-01/pump-01/temperature", json.dumps(payload).encode())
    assert event.device_id == "pump-01"
    assert event.metric == "temperature"
    assert event.sequence == 7
    assert event.source_topic.endswith("temperature")
