from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import IncidentNotFoundError, PersistentIncidentStore
from aegis.correlation.pipeline import IncidentAnalysis
from aegis.detection.alerts import AlertNotFoundError, AlertStore, InvalidAlertTransitionError
from aegis.investigation.artifact_store import (
    InvestigationArtifactNotFoundError,
    InvestigationArtifactStore,
)
from aegis.investigation.investigator import IncidentInvestigator
from aegis.workflow.case import CaseStatus, InvestigationCaseStore
from aegis.workflow.feedback import FeedbackEngine, FeedbackType

app = FastAPI(title="AEGIS-X API", version="0.6.0")

AlertStatus = Literal["open", "acknowledged", "investigating", "resolved", "dismissed"]
IncidentStatus = Literal["open", "investigating", "contained", "resolved", "dismissed"]


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    note: str | None = None


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    note: str | None = None


class CreateCaseRequest(BaseModel):
    incident_id: str
    title: str | None = None
    assignee: str | None = None


class UpdateCaseStatusRequest(BaseModel):
    status: CaseStatus
    note: str | None = None


class SubmitFeedbackRequest(BaseModel):
    analyst_id: str
    feedback_type: FeedbackType
    target_id: str
    adjusted_confidence: float | None = None
    comment: str | None = None


def register_incident_analysis(analysis: IncidentAnalysis) -> None:
    """Durably publish a completed Phase 3 analysis for Phase 4 investigation."""
    InvestigationArtifactStore(TelemetryStore()).save(analysis)


def _incident_payload(incident: object) -> dict[str, object]:
    return asdict(incident)  # type: ignore[arg-type]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aegis-x-api", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/api/v1/telemetry/health")
def telemetry_health() -> dict[str, object]:
    stats = TelemetryStore().health_stats()
    return {
        "status": "receiving" if stats["last_ingested_at"] is not None else "waiting_for_telemetry",
        "timestamp": datetime.now(UTC).isoformat(), "storage": stats,
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
    try:
        analysis = InvestigationArtifactStore(TelemetryStore()).get(incident_id)
    except InvestigationArtifactNotFoundError as exc:
        raise HTTPException(status_code=404, detail="incident analysis not available") from exc
    return IncidentInvestigator().investigate(analysis).to_dict()


# --- Phase 6 Investigation Workflow & Case Management API ---

@app.post("/api/v1/cases")
def create_case(req: CreateCaseRequest) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    case = case_store.create(req.incident_id, req.title, req.assignee)
    return case.to_dict()


@app.get("/api/v1/cases")
def list_cases(limit: int = Query(default=100, ge=1, le=500), status: CaseStatus | None = None) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    cases = case_store.list(status, limit)
    return {"count": len(cases), "cases": [case.to_dict() for case in cases]}


@app.get("/api/v1/cases/{case_id}")
def get_case_dossier(case_id: str) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    try:
        dossier = case_store.build_dossier(case_id)
        return dossier.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="investigation case not found") from exc


@app.patch("/api/v1/cases/{case_id}/status")
def update_case_status(case_id: str, req: UpdateCaseStatusRequest) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    try:
        updated = case_store.transition(case_id, req.status, req.note)
        return updated.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="investigation case not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/cases/{case_id}/feedback")
def submit_case_feedback(case_id: str, req: SubmitFeedbackRequest) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    try:
        case = case_store.get(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="investigation case not found") from exc

    feedback_engine = FeedbackEngine(storage)
    try:
        fb = feedback_engine.submit(
            case_id=case.case_id,
            incident_id=case.incident_id,
            analyst_id=req.analyst_id,
            feedback_type=req.feedback_type,
            target_id=req.target_id,
            adjusted_confidence=req.adjusted_confidence,
            comment=req.comment,
        )
        return fb.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/cases/{case_id}/provenance")
def get_case_provenance(case_id: str) -> dict[str, object]:
    storage = TelemetryStore()
    case_store = InvestigationCaseStore(storage)
    try:
        dossier = case_store.build_dossier(case_id)
        return dossier.provenance.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="investigation case not found") from exc


@app.get("/api/v1/status")
def platform_status() -> dict[str, object]:
    return {
        "platform": "AEGIS-X", "phase": "investigation-workflow-and-feedback",
        "components": {
            "api": "online", "telemetry": "active", "detection": "active",
            "attack_graph": "active", "incident_correlation": "active",
            "investigator": "active", "orchestration": "active",
            "workflow": "active", "provenance": "active", "response": "planned",
        },
    }
