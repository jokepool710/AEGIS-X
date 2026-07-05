from datetime import datetime, timezone

from fastapi import FastAPI

from aegis.common.storage import TelemetryStore

app = FastAPI(title="AEGIS-X API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aegis-x-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/telemetry/health")
def telemetry_health() -> dict[str, object]:
    store = TelemetryStore()
    stats = store.health_stats()
    last_ingested = stats["last_ingested_at"]
    status = "receiving" if last_ingested is not None else "waiting_for_telemetry"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": stats,
    }


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X",
        "phase": "telemetry-ingestion",
        "components": {
            "api": "online",
            "telemetry": "active",
            "detection": "planned",
            "attack_graph": "planned",
            "investigator": "planned",
            "response": "planned",
        },
    }
