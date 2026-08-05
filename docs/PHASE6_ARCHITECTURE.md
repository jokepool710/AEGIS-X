# Phase 6 Architecture: Investigation Workflow, Analyst Feedback, and Case Evidence Provenance

## Status

Phase 6 is implementation-complete and CI-validated. The end-to-end investigation case workflow, analyst feedback engine, and case evidence provenance verification are validated by `tests/integration/test_phase6_workflow_e2e.py`.

## Objective

Phase 6 introduces structured security investigation case management, human analyst feedback loops, case dossier aggregation, and cryptographic evidence chain-of-custody provenance tracking.

## End-to-end flow

```text
Phase 4 InvestigationResult + Phase 5 Orchestration
        |
        v
Investigation Case Store (Case Creation & Lifecycle)
        |
        v
Evidence Chain of Custody (SHA-256 Provenance Logging)
        |
        v
Analyst Feedback Engine (Human Consensus & Adjustments)
        |
        v
Unified Case Dossier (Aggregated Case Evidence Package)
        |
        v
Case Workflow API (/api/v1/cases)
```

## Components

### Investigation Case Store (`aegis/workflow/case.py`)

Manages case lifecycle (`DRAFT`, `IN_REVIEW`, `APPROVED`, `CLOSED`, `ARCHIVED`) and valid state transitions. Aggregates Phase 4 investigation results, Phase 5 orchestration outcomes, analyst feedback records, and tamper-evident evidence provenance into a unified `CaseDossier`.

### Analyst Feedback Engine (`aegis/workflow/feedback.py`)

Collects, persists, and aggregates analyst feedback (`ACCEPT_HYPOTHESIS`, `REJECT_HYPOTHESIS`, `ADJUST_CONFIDENCE`, `FLAG_CONTRADICTION`, `ADD_NOTE`). Computes consensus confidence scores for hypotheses based on human feedback.

### Evidence Chain of Custody (`aegis/workflow/provenance.py`)

Logs cryptographic SHA-256 payload hashes for all evidence items in an investigation case bundle. Verifies evidence integrity on retrieval to detect payload tampering or unregistered evidence insertion.

### Workflow & Case API (`apps/api/main.py`)

Exposes RESTful endpoints for case management:
- `POST /api/v1/cases`: Create a new investigation case from an incident
- `GET /api/v1/cases`: List investigation cases with status filtering
- `GET /api/v1/cases/{case_id}`: Retrieve full case dossier
- `PATCH /api/v1/cases/{case_id}/status`: Transition case status
- `POST /api/v1/cases/{case_id}/feedback`: Submit analyst feedback
- `GET /api/v1/cases/{case_id}/provenance`: Get evidence provenance verification report

## Validation gates

Phase 6 validation covers lint (`ruff check .`), unit test suite, and the Phase 6 end-to-end integration test (`tests/integration/test_phase6_workflow_e2e.py`).

The Phase 6 E2E test verifies:
- End-to-end telemetry anomaly processing, correlation, attack-graph generation, and incident analysis persistence
- Investigation case creation and status transitions
- Case dossier aggregation over Phase 4 and Phase 5 artifacts
- Analyst feedback submission and hypothesis confidence score adjustment
- SHA-256 evidence chain-of-custody verification

## Phase 6 closure criteria

Phase 6 is closed when case management, analyst feedback loops, evidence chain-of-custody provenance, and API endpoints pass end-to-end CI validation and are merged into `main`.
