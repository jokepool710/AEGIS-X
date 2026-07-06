from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from aegis.common.storage import TelemetryStore
from aegis.detection.alerts import (
    AlertNotFoundError,
    AlertStore,
    InvalidAlertTransitionError,
)

app = FastAPI(title="AEGIS-X API", version="0.3.0")

AlertStatus = Literal["open", "acknowledged", "investigating", "resolved", "dismissed"]


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    note: str | None = None


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
    return {
        "status": "receiving" if stats["last_ingested_at"] is not None else "waiting_for_telemetry",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": stats,
    }


@app.get("/api/v1/alerts")
def list_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    status: AlertStatus | None = None,
) -> dict[str, object]:
    alerts = AlertStore(TelemetryStore()).list(limit, status)
    return {"count": len(alerts), "alerts": alerts}


@app.get("/api/v1/alerts/{alert_id}")
def get_alert(alert_id: str) -> dict[str, object]:
    try:
        return AlertStore(TelemetryStore()).get(alert_id)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail="alert not found") from exc


@app.patch("/api/v1/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, update: AlertStatusUpdate) -> dict[str, object]:
    try:
        return AlertStore(TelemetryStore()).transition(alert_id, update.status, update.note)
    except AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail="alert not found") from exc
    except InvalidAlertTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X",
        "phase": "anomaly-detection",
        "components": {
            "api": "online",
            "telemetry": "active",
            "detection": "active",
            "attack_graph": "planned",
            "investigator": "planned",
            "response": "planned",
        },
    }
