# Phase 5 Architecture: Autonomous Investigation Orchestration and Decision Auditability

## Status

Phase 5 is implementation-complete and CI-validated. The end-to-end orchestration pipeline and tamper-evident decision ledger integrity are validated by `tests/integration/test_phase5_orchestration_e2e.py`.

## Objective

Phase 5 bridges static evidence-grounded AI investigations (Phase 4) and dynamic analyst-assisted security response. It introduces autonomous investigation plan generation, evidence acquisition loops, hypothesis re-evaluation, decision support recommendations, approval policy gates, and a tamper-evident decision ledger.

## End-to-end flow

```text
Phase 4 InvestigationResult
        |
        v
Investigation Policy Engine (Plan Generation)
        |
        v
Evidence Acquisition Loop (Safe Tool Execution)
        |
        v
Hypothesis Re-evaluation Loop (Dynamic Calibration)
        |
        v
Analyst Decision Support Engine (Action Ranking)
        |
        v
Approval Policy Gates (Human-in-the-Loop Safeguards)
        |
        v
Tamper-Evident Decision Ledger (Cryptographic Audit Trail)
```

## Components

### Investigation Planning & DAG (`aegis/orchestration/planning.py`)

Generates structured investigation task plans represented as Directed Acyclic Graphs (DAGs). Defines dependency resolution, task typing (`QUERY_EVIDENCE`, `EXPAND_TIMELINE`, `VALIDATE_HYPOTHESIS`, `CHECK_CONTRADICTION`, `INSPECT_ASSET`, `REEVALUATE_RISK`), and execution readiness.

### Investigation Policy Engine (`aegis/orchestration/policy.py`)

Evaluates Phase 4 uncertainty assessments, missing evidence indicators, and contradictions to formulate targeted investigation objectives under configurable execution modes (`CONSERVATIVE`, `BALANCED`, `AGGRESSIVE`).

### Safe Tool Registry & Execution (`aegis/orchestration/tools.py`)

Maintains an allowlisted registry of tool specifications (`ToolSpec`) mapping task types to safe execution handlers. Enforces operational boundaries, input schema validation, and approval requirements (`ToolApprovalRequiredError`).

### Evidence Acquisition Loop (`aegis/orchestration/acquisition.py`)

Executes dependency-ready investigation tasks against registered tools, converts outputs into provenance-bound `EvidenceItem` records (`EvidenceKind.LIFECYCLE`), and safely merges new evidence into the active `EvidenceBundle`.

### Hypothesis Re-evaluation Loop (`aegis/orchestration/reevaluation.py`)

Re-runs timeline reconstruction, hypothesis generation, and uncertainty calibration over expanded evidence bundles. Computes `HypothesisDelta` tracking confidence shifts and contradiction resolution across acquisition waves.

### Analyst Decision Support Engine (`aegis/orchestration/decision_support.py`)

Ranks ready investigative actions for human analyst review by scoring expected information gain, uncertainty reduction potential, operational risk, and investigation cost under declared `ActionRisk` levels.

### Approval Policy Gates (`aegis/orchestration/approvals.py`)

Enforces mandatory human-in-the-loop approval gates (`ApprovalStatus.PENDING`, `APPROVED`, `REJECTED`) for high-risk tools, disruptive actions, or policy-bounded operational thresholds.

### Tamper-Evident Decision Ledger (`aegis/orchestration/ledger.py`)

Persists an append-only cryptographic event hash chain (`SHA-256`) in SQLite for all orchestration events (`PLAN_CREATED`, `EVIDENCE_ACQUIRED`, `CONFIDENCE_CHANGED`, `RECOMMENDATION_CREATED`, `APPROVAL_GRANTED`, `TOOL_EXECUTED`). Verifies full chain integrity to prevent audit tampering.

### Phase 5 Orchestrator (`aegis/orchestration/orchestrator.py`)

Coordinates the unified Phase 5 cycle from a Phase 4 `InvestigationResult` input to structured `OrchestrationOutcome` output.

## Validation gates

Phase 5 validation covers lint (`ruff check .`), unit test suite, and the Phase 5 end-to-end integration test (`tests/integration/test_phase5_orchestration_e2e.py`).

The Phase 5 E2E test verifies:
- Plan generation from Phase 4 investigation baseline
- Safe tool execution and evidence acquisition loop
- Hypothesis re-evaluation and confidence calibration tracking
- Analyst decision support ranking
- Cryptographic hash-chain integrity of the persistent decision ledger

## Phase 5 closure criteria

Phase 5 is closed when the end-to-end orchestration pipeline, decision ledger integrity, and architecture documentation are fully validated and merged into `main` with passing CI checks.
