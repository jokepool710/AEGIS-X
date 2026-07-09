from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import IncidentNotFoundError, PersistentIncidentStore
from aegis.correlation.pipeline import IncidentAnalysis
from aegis.detection.alerts import AlertNotFoundError, AlertStore, InvalidAlertTransitionError
from aegis.investigation.investigator import IncidentInvestigator

app = FastAPI(title="AEGIS-X API", version="0.4.0")

AlertStatus = Literal["open", "acknowledged", "investigating", "resolved", "dismissed"]
IncidentStatus = Literal["open", "investigating", "contained", "resolved", "dismissed"]
_ANALYSES: dict[str, IncidentAnalysis] = {}


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    note: str | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    note: str | None = None


def register_incident_analysis(analysis: IncidentAnalysis) -> None:
    """Publish a completed Phase 3 analysis for Phase 4 investigation."""
    _ANALYSES[analysis.incident.incident_id] = analysis


def _incident_payload(incident: object) -> dict[str, object]:
    return asdict(incident)  # type: ignore[arg-type]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-x-api", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/telemetry/health")
def telemetry_health() -> dict[str, object]:
    stats = TelemetryStore().health_stats()
    return {
        "status": "receiving" if stats["last_ingested_at"] is not None else "waiting_for_telemetry",
        "timestamp": datetime.now(timezone.utc).isoformat(), "storage": stats,
    }


@app.get("/api/v1/alerts")
def list_alerts(limit: int = Query(default=100, ge=1, le=500), status: AlertStatus | None = None) -> dict[str, object]:
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


@app.get("/api/v1/incidents")
def list_incidents(limit: int = Query(default=100, ge=1, le=500), status: IncidentStatus | None = None) -> dict[str, object]:
    incidents = PersistentIncidentStore(TelemetryStore()).list(status, limit)
    return {"count": len(incidents), "incidents": [_incident_payload(item) for item in incidents]}


@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict[str, object]:
    try:
        return _incident_payload(PersistentIncidentStore(TelemetryStore()).get(incident_id))
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc


@app.patch("/api/v1/incidents/{incident_id}/status")
def update_incident_status(incident_id: str, update: IncidentStatusUpdate) -> dict[str, object]:
    try:
        incident = PersistentIncidentStore(TelemetryStore()).transition(incident_id, update.status, update.note)
        return _incident_payload(incident)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/incidents/{incident_id}/investigation")
def investigate_incident(incident_id: str) -> dict[str, object]:
    analysis = _ANALYSES.get(incident_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="incident analysis not available")
    return IncidentInvestigator().investigate(analysis).to_dict()


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X", "phase": "evidence-grounded-investigation",
        "components": {
            "api": "online", "telemetry": "active", "detection": "active",
            "attack_graph": "active", "incident_correlation": "active",
            "investigator": "active", "response": "planned",
        },
    }
