import argparse
import json
import math
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def reading(step: int, anomaly: bool) -> dict[str, float]:
    temperature = 24.0 + 1.5 * math.sin(step / 15) + random.gauss(0, 0.2)
    vibration = 0.35 + random.gauss(0, 0.03)
    pressure = 5.0 + random.gauss(0, 0.05)
    if anomaly:
        temperature += random.uniform(10, 18)
        vibration += random.uniform(1.5, 3.0)
        pressure += random.uniform(1.0, 2.5)
    return {"temperature": temperature, "vibration": vibration, "pressure": pressure}


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS-X MQTT sensor simulator")
    parser.add_argument("--device-id", default="pump-01")
    parser.add_argument("--site-id", default="lab-01")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--anomaly-rate", type=float, default=0.03)
    args = parser.parse_args()

    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{args.device_id}")
    client.connect(host, port, 60)
    client.loop_start()

    units = {"temperature": "celsius", "vibration": "g", "pressure": "bar"}
    sequence = 0
    try:
        while True:
            anomalous = random.random() < args.anomaly_rate
            timestamp = datetime.now(timezone.utc).isoformat()
            for metric, value in reading(sequence, anomalous).items():
                payload = {
                    "device_id": args.device_id,
                    "device_type": "industrial_pump",
                    "site_id": args.site_id,
                    "timestamp": timestamp,
                    "sequence": sequence,
                    "metric": metric,
                    "value": round(value, 4),
                    "unit": units[metric],
                    "quality": "good",
                    "simulation_label": "anomaly" if anomalous else "normal",
                }
                topic = f"aegis/telemetry/{args.site_id}/{args.device_id}/{metric}"
                client.publish(topic, json.dumps(payload), qos=1)
                print(topic, payload)
            sequence += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
