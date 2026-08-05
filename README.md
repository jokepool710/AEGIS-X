# AEGIS-X

**Autonomous Cyber-Physical Security Platform**

AEGIS-X is a research-driven platform for attack emulation, telemetry ingestion, anomaly detection, cyber-physical incident correlation, attack-graph reasoning, AI-assisted investigation, and human-approved response orchestration across IT, IoT, OT, and cyber-physical environments.

## Implemented Vertical Slice

```text
MQTT sensor simulation
  -> telemetry ingestion and persistence
  -> sliding-window feature extraction
  -> statistical + Isolation Forest detection
  -> unified anomaly scoring
  -> persistent alert lifecycle
  -> asset/topology enrichment
  -> alert correlation and incident clustering
  -> persistent incident lifecycle
  -> attack graph construction
  -> ATT&CK for ICS mapping
  -> risk prioritization
  -> Incident API
  -> evidence bundle construction
  -> timeline reconstruction
  -> hypothesis generation and uncertainty quantification
  -> grounded narrative synthesis
  -> faithfulness evaluation
  -> persistent investigation artifacts
  -> investigation task planning (DAG)
  -> safe tool registry & execution
  -> evidence acquisition loop
  -> hypothesis re-evaluation loop
  -> analyst decision support engine
  -> approval policy gates
  -> tamper-evident decision ledger
```

## Core Domains

- Cyber-range attack scenario generation
- Telemetry collection and persistence
- Anomaly detection and evaluation
- Cyber-physical asset topology
- Alert correlation and incident clustering
- Attack graph reasoning
- ATT&CK for ICS mapping
- Risk prioritization
- Evidence-grounded AI investigation
- Autonomous investigation orchestration
- Human-approved response orchestration

## Engineering Principles

1. Build measurable vertical slices before adding complexity.
2. Keep attack execution isolated to controlled lab environments.
3. Separate deterministic detection evidence from generative explanations.
4. Require explicit human approval for disruptive response actions.
5. Reproduce experiments with versioned data, configurations, and metrics.
6. Treat end-to-end CI validation as a phase completion gate.

## Roadmap

- [x] Phase 0 — Foundation and architecture
- [x] Phase 1 — MQTT simulator, telemetry ingestion, persistence, and telemetry E2E validation
- [x] Phase 2 — Anomaly detection, unified scoring, alert lifecycle, labelled attack scenarios, evaluation harness, and benchmarking
- [x] Phase 3 — Asset topology, alert enrichment, correlation, incident clustering, persistent incidents, attack graphs, ATT&CK for ICS mapping, risk prioritization, Incident API, and Phase 3 E2E validation
- [x] Phase 4 — Evidence-grounded AI incident investigator, faithfulness evaluation, and Phase 4 E2E validation
- [x] Phase 5 — Autonomous investigation orchestration, human approval gates, decision auditability, and Phase 5 E2E validation
- [ ] Phase 6 — Investigation workflow, analyst feedback, and case evidence provenance *(in progress)*
- [ ] Phase 7 — Human-approved response orchestration
- [ ] Phase 8 — Research benchmarking, comparative evaluation, and publication artifacts

## Phase 3 Architecture

Phase 3 turns isolated anomaly alerts into persistent and prioritized cyber-physical incidents:

```text
Raw Alerts
  -> Asset/Topology Enrichment
  -> Correlation Engine
  -> Incident Clustering
  -> Persistent Incident Store
  -> Attack Graph Engine
  -> ATT&CK for ICS Mapping
  -> Risk Prioritization
  -> Incident API
```

The full architecture, component responsibilities, and E2E completion contract are documented in `docs/phase3-architecture.md`.

## Phase 4 Architecture

Phase 4 grounds AI-generated incident narratives in hard evidence:

```text
Incident (Phase 3 output)
  -> Evidence Bundle construction (alerts, assets, risk)
  -> Timeline reconstruction (chronological event ordering)
  -> Hypothesis generation (attack scenario candidates)
  -> Uncertainty quantification (confidence bands)
  -> Grounded narrative synthesis (citation-anchored explanation)
  -> Faithfulness evaluation (citation validity, evidence coverage)
  -> Persistent investigation artifacts (SQLite store)
  -> Investigation API (GET /api/v1/incidents/{id}/investigation)
```

The full architecture, component responsibilities, and E2E completion contract are documented in `docs/PHASE4_ARCHITECTURE.md`.

## Phase 5 Architecture

Phase 5 introduces autonomous investigation orchestration and cryptographic decision auditability:

```text
Phase 4 InvestigationResult
  -> Policy Engine (Plan generation & task DAG)
  -> Evidence Acquisition Loop (Safe tool execution)
  -> Hypothesis Re-evaluation Loop (Dynamic calibration)
  -> Analyst Decision Support Engine (Action ranking)
  -> Approval Policy Gates (Human-in-the-loop safeguards)
  -> Tamper-Evident Decision Ledger (Cryptographic SHA-256 audit trail)
```

The full architecture, component responsibilities, and E2E completion contract are documented in `docs/PHASE5_ARCHITECTURE.md`.

## Validation

The main CI pipeline validates:

```text
Ruff lint
  -> Unit tests
  -> MQTT telemetry E2E
  -> Phase 3 incident E2E
  -> Phase 4 investigator E2E
  -> Phase 5 orchestration E2E
```

The Phase 3 E2E contract verifies incident clustering, alert and asset membership, attack-graph generation, ATT&CK for ICS mappings, risk scoring, persistence, API listing/detail retrieval, lifecycle transition, stable incident identity, and idempotent reruns.

The Phase 4 E2E contract verifies evidence bundle construction from Phase 3 output, timeline reconstruction, hypothesis generation, uncertainty quantification, grounded narrative synthesis, faithfulness scoring, persistent artifact storage, and API retrieval.

The Phase 5 E2E contract verifies autonomous investigation task planning, safe tool execution, evidence acquisition, dynamic hypothesis re-evaluation, analyst decision support ranking, and cryptographic hash-chain integrity of the persistent decision ledger.

## Responsible Use

AEGIS-X is intended for defensive security research, authorized testing, and isolated cyber-range experimentation. Attack scenarios must only be executed against systems you own or are explicitly authorized to test.

## License

Apache License 2.0.
