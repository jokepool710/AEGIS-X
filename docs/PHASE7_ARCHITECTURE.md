# Phase 7 Architecture: Human-Approved Response Orchestration

## Status

Phase 7 is implementation-complete and CI-validated. Human-approved response orchestration, playbook generation, mandatory approval request gates, execution handlers, and action rollbacks are validated by `tests/integration/test_phase7_response_e2e.py`.

## Objective

Phase 7 enforces Engineering Principle #4: **No disruptive response action executes without explicit human authorization.** It provides structured response playbooks, mandatory approval request lifecycle state machines, execution engines with rollback handlers, and REST API endpoints.

## End-to-End Flow

```text
Incident / Case / ATT&CK Mapping
        |
        v
Playbook Engine (Generates ResponsePlan & recommended ResponseActions)
        |
        v
Response Approval Engine (Creates mandatory pending ResponseApprovalRequests)
        |
        v
Human Approval Gate (Grant / Reject Authorization)
        |
        v
Response Execution Engine (Executes authorized actions & logs outcome)
        |
        v
Rollback Engine (Reverses execution for reversible actions)
```

## Components

### Response Actions & Playbooks (`aegis/response/actions.py`, `playbooks.py`)

- `ResponseAction`: Standardized representation of containment, isolation, safe state, emergency stop, credential revocation, forensic snapshot, or port disabling actions.
- `PlaybookEngine`: Maps incident risk scores, ATT&CK for ICS techniques, and target assets into prioritized response playbooks (`ResponsePlaybook`).

### Human Approval Safeguard Engine (`aegis/response/approvals.py`)

- `ResponseApprovalEngine`: Manages approval requests (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`).
- Enforces strict human-in-the-loop validation: actions requiring approval cannot be executed without an `APPROVED` request ID.

### Response Execution Engine & Rollback (`aegis/response/executor.py`)

- `ResponseExecutionEngine`: Executes approved response actions, records execution status (`SUCCESS`, `FAILED`), and produces structured outputs.
- `rollback`: Reverses executed actions for reversible types (e.g. restoring network access or resetting safe states).

### Persistent Response Store (`aegis/response/store.py`)

- `PersistentResponseStore`: SQLite-backed persistence for response plans, playbooks, approval requests, execution logs, and rollback records.

### REST API Endpoints (`apps/api/main.py`)

- `POST /api/v1/response/plans`: Generate a response plan for an incident
- `GET /api/v1/response/plans/{plan_id}`: Retrieve a response plan
- `POST /api/v1/response/requests/{request_id}/grant`: Grant human approval
- `POST /api/v1/response/requests/{request_id}/reject`: Reject human approval
- `POST /api/v1/response/actions/execute`: Execute an approved response action
- `POST /api/v1/response/executions/{execution_id}/rollback`: Roll back a previously executed response action

## Validation Gates

Phase 7 validation covers lint (`ruff check .`), unit test suite, and the Phase 7 end-to-end integration test (`tests/integration/test_phase7_response_e2e.py`).

The Phase 7 E2E test verifies:
- Response plan generation from incident risk and ATT&CK techniques
- Mandatory pending human approval requests for disruptive actions
- Human authorization grant workflows
- Authorized execution of response actions
- Reversible action rollback workflows

## Phase 7 Closure Criteria

Phase 7 is closed when human-approved response orchestration, playbooks, approval state machines, execution engines, and API endpoints pass end-to-end CI validation and are merged into `main`.
