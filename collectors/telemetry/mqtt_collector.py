import json
import os
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from aegis.common.models import TelemetryEvent
from aegis.common.storage import TelemetryStore

store: TelemetryStore | None = None


def normalize(topic: str, payload: bytes) -> TelemetryEvent:
    raw = json.loads(payload.decode("utf-8"))
    return TelemetryEvent(
        event_id=str(uuid.uuid4()),
        device_id=raw["device_id"],
        device_type=raw["device_type"],
        site_id=raw["site_id"],
        timestamp=raw["timestamp"],
        sequence=raw["sequence"],
        metric=raw["metric"],
        value=raw["value"],
        unit=raw["unit"],
        quality=raw.get("quality", "good"),
        source_topic=topic,
        ingested_at=datetime.now(timezone.utc),
    )


def on_connect(client: mqtt.Client, userdata: object, flags: object, reason_code: object, properties: object) -> None:
    topic = os.getenv("MQTT_TOPIC", "aegis/telemetry/#")
    print(f"connected reason={reason_code}; subscribing to {topic}")
    client.subscribe(topic, qos=1)


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    try:
        event = normalize(message.topic, message.payload)
        if store is None:
            raise RuntimeError("telemetry store is not initialized")
        inserted = store.insert(event)
        if inserted:
            print(f"stored {event.model_dump_json()}")
        else:
            print(
                f"duplicate rejected device={event.device_id} "
                f"sequence={event.sequence} metric={event.metric}"
            )
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValidationError) as exc:
        print(f"rejected topic={message.topic}: {exc}")


def main() -> None:
    global store
    store = TelemetryStore()
    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="aegis-telemetry-collector")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
