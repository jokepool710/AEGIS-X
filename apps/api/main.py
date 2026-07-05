from datetime import datetime, timezone

from fastapi import FastAPI, Query

from aegis.common.storage import TelemetryStore
from aegis.detection.alerts import AlertStore

app = FastAPI(title="AEGIS-X API", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-x-api", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/telemetry/health")
def telemetry_health() -> dict[str, object]:
    store = TelemetryStore()
    stats = store.health_stats()
    return {
        "status": "receiving" if stats["last_ingested_at"] is not None else "waiting_for_telemetry",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": stats,
    }


@app.get("/api/v1/alerts")
def list_alerts(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    store = TelemetryStore()
    alerts = AlertStore(store).list(limit)
    return {"count": len(alerts), "alerts": alerts}


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X",
        "phase": "anomaly-detection",
        "components": {
            "api": "online", "telemetry": "active", "detection": "active",
            "attack_graph": "planned", "investigator": "planned", "response": "planned",
        },
    }
