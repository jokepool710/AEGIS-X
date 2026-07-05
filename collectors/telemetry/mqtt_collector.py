import json
import os
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from aegis.common.metrics import IngestionMetrics
from aegis.common.models import TelemetryEvent
from aegis.common.sequence import SequenceTracker
from aegis.common.storage import TelemetryStore
from aegis.detection.alerts import AlertStore
from aegis.detection.pipeline import DetectionPipeline

store: TelemetryStore | None = None
alert_store: AlertStore | None = None
sequence_tracker = SequenceTracker()
metrics = IngestionMetrics()
detector = DetectionPipeline()


def normalize(topic: str, payload: bytes) -> TelemetryEvent:
    raw = json.loads(payload.decode("utf-8"))
    return TelemetryEvent(
        event_id=str(uuid.uuid4()), device_id=raw["device_id"], device_type=raw["device_type"],
        site_id=raw["site_id"], timestamp=raw["timestamp"], sequence=raw["sequence"],
        metric=raw["metric"], value=raw["value"], unit=raw["unit"],
        quality=raw.get("quality", "good"), source_topic=topic,
        ingested_at=datetime.now(timezone.utc),
    )


def on_connect(client: mqtt.Client, userdata: object, flags: object, reason_code: object, properties: object) -> None:
    topic = os.getenv("MQTT_TOPIC", "aegis/telemetry/#")
    print(f"connected reason={reason_code}; subscribing to {topic}")
    client.subscribe(topic, qos=1)


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    metrics.record_received()
    try:
        event = normalize(message.topic, message.payload)
        if store is None or alert_store is None:
            raise RuntimeError("collector stores are not initialized")
        if not store.insert(event):
            metrics.record_duplicate()
            print(f"duplicate rejected device={event.device_id} sequence={event.sequence} metric={event.metric}")
            return

        metrics.record_stored()
        gap = sequence_tracker.observe(event.device_id, event.metric, event.sequence)
        if gap is not None:
            metrics.record_gap(gap.missing_count)
            print(f"sequence_gap device={gap.device_id} metric={gap.metric} missing={gap.missing_from}-{gap.missing_to} count={gap.missing_count}")

        result = detector.process(event)
        print(f"detection device={event.device_id} metric={event.metric} score={result.unified_score:.4f} anomalous={result.anomalous}")
        if result.anomalous:
            alert_id = alert_store.create(event, result)
            print(f"alert_created id={alert_id} score={result.unified_score:.4f}")
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValidationError) as exc:
        metrics.record_rejected()
        print(f"rejected topic={message.topic}: {exc}")


def main() -> None:
    global store, alert_store
    store = TelemetryStore()
    alert_store = AlertStore(store)
    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aegis-telemetry-collector")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
