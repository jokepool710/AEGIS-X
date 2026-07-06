import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from fastapi.testclient import TestClient

from apps.api.main import app


def wait_for_stored_event(client: TestClient, timeout: float | None = None) -> dict[str, object]:
    timeout = timeout or float(os.getenv("E2E_TIMEOUT", "30"))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get("/api/v1/telemetry/health")
        response.raise_for_status()
        body = response.json()
        if body["storage"]["stored_events"] >= 1:
            return body
        time.sleep(0.25)
    raise AssertionError(f"telemetry event was not persisted within {timeout:.0f}s")


def test_mqtt_to_collector_to_storage_to_health_api(tmp_path: Path) -> None:
    db_path = tmp_path / "e2e_telemetry.db"
    env = os.environ.copy()
    env.update(
        {
            "MQTT_HOST": "127.0.0.1",
            "MQTT_PORT": os.getenv("E2E_MQTT_PORT", "1883"),
            "MQTT_TOPIC": "aegis/telemetry/#",
            "TELEMETRY_DB_PATH": str(db_path),
            "PYTHONUNBUFFERED": "1",
        }
    )

    collector = subprocess.Popen(
        [sys.executable, "-m", "collectors.telemetry.mqtt_collector"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    publisher: mqtt.Client | None = None
    try:
        # Give the collector process time to import dependencies, connect, and subscribe.
        # Repeated QoS 1 publishes below remove dependence on one exact startup instant.
        time.sleep(3.0)

        publisher = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="aegis-e2e-publisher",
        )
        publisher.connect("127.0.0.1", int(env["MQTT_PORT"]), 60)
        publisher.loop_start()

        payload = {
            "device_id": "pump-e2e-01",
            "device_type": "industrial_pump",
            "site_id": "integration-lab",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": 1,
            "metric": "temperature",
            "value": 26.75,
            "unit": "celsius",
            "quality": "good",
            "simulation_label": "normal",
        }
        topic = "aegis/telemetry/integration-lab/pump-e2e-01/temperature"

        for _ in range(3):
            result = publisher.publish(topic, json.dumps(payload), qos=1)
            result.wait_for_publish(timeout=10)
            if db_path.exists():
                break
            time.sleep(1.0)

        os.environ["TELEMETRY_DB_PATH"] = str(db_path)
        try:
            with TestClient(app) as api:
                health = wait_for_stored_event(api)
        finally:
            os.environ.pop("TELEMETRY_DB_PATH", None)

        assert health["status"] == "receiving"
        assert health["storage"]["stored_events"] == 1
        assert health["storage"]["active_devices"] == 1
        assert health["storage"]["metric_streams"] == 1
    finally:
        if publisher is not None:
            publisher.loop_stop()
            publisher.disconnect()

        collector.terminate()
        try:
            output, _ = collector.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            collector.kill()
            output, _ = collector.communicate(timeout=5)

        if output:
            print("collector output:\n", output)
