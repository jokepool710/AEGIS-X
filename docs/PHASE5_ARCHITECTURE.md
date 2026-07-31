# Phase 5 Architecture — Autonomous Investigation Orchestration

## Objective

Phase 5 turns a Phase 4 investigation result into a controlled, auditable investigation cycle. It may acquire evidence through allowlisted tools and rank analyst actions, but it does not autonomously execute disruptive response actions.

## End-to-end flow

```text
Phase 4 InvestigationResult
  -> Investigation Policy Engine
  -> Dependency-safe Investigation Plan
  -> Ready Task Selection
  -> Allowlisted Tool Execution
  -> Provenance-bound Tool Evidence
  -> Hypothesis Re-evaluation
  -> Analyst Decision Support
  -> Hash-chained Decision Ledger
```

## Components

| Component | Responsibility |
| --- | --- |
| `TaskDAG` | Validates task IDs, dependency references, cycles, ordering, and ready-task selection. |
| `InvestigationPolicyEngine` | Converts uncertainty, contradictions, and evidence gaps into deterministic investigation tasks. |
| `ToolRegistry` and `SafeToolExecutor` | Restrict execution to typed, allowlisted tools and enforce approval requirements for controlled-write tools. |
| `EvidenceAcquisitionLoop` | Executes dependency-ready tasks and adds `tool_result` evidence with task and tool provenance. |
| `HypothesisReevaluationLoop` | Reconstructs the timeline, regenerates hypotheses, calibrates uncertainty, and records confidence/contradiction deltas. |
| `AnalystDecisionSupportEngine` | Ranks dependency-ready next actions by information gain, uncertainty reduction, risk, cost, and priority. |
| `HumanApprovalGate` | Binds approval to the exact task, tool, objective, and parameters; prevents replay. |
| `DecisionLedger` | Persists an append-only, SHA-256 hash-chained decision record in SQLite. |
| `Phase5Orchestrator` | Runs one controlled cycle and records plan, acquisition, confidence, and recommendation events. |

## Safety boundary

Phase 5 tools are not arbitrary command execution. Tool registration is explicit, compatible task types are checked at runtime, and controlled-write tools require approval. Human approval remains the authority boundary for disruptive actions.

## Validation

The Phase 5 E2E test, `tests/integration/test_phase5_orchestration_e2e.py`, verifies:

1. A policy plan is created from a Phase 4 result.
2. A compatible allowlisted tool acquires evidence.
3. The acquired evidence preserves task and tool provenance.
4. Hypotheses and uncertainty are recalculated.
5. Analyst recommendations are created.
6. The decision ledger records plan, acquisition, confidence, and recommendation events.
7. Ledger integrity verifies successfully.

Main CI executes this test after the telemetry, Phase 3, and Phase 4 E2E gates.

## Phase boundary

Phase 5 owns investigation orchestration and analyst decision support. Phase 6 begins only with human-approved response planning and simulation; it must not bypass Phase 5 approval and audit controls.
