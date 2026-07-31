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
  -> evidence-grounded investigation
  -> governed investigation orchestration
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
- [x] Phase 4 — Evidence-grounded AI incident investigator
- [x] Phase 5 — Autonomous investigation orchestration, human approval gates, decision auditability, and Phase 5 E2E CI validation
- [ ] Phase 6 — Human-approved response orchestration: response playbooks, simulation, safety validation, controlled execution, rollback, and recovery verification
- [ ] Phase 7 — Research benchmarking, comparative evaluation, and publication artifacts

## Architecture

- [Phase 3: Incident correlation and attack-path reasoning](docs/phase3-architecture.md)
- [Phase 4: Evidence-grounded AI incident investigator](docs/PHASE4_ARCHITECTURE.md)
- [Phase 5: Autonomous investigation orchestration](docs/PHASE5_ARCHITECTURE.md)

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

## Responsible Use

AEGIS-X is intended for defensive security research, authorized testing, and isolated cyber-range experimentation. Attack scenarios must only be executed against systems you own or are explicitly authorized to test.

## License

Apache License 2.0.
