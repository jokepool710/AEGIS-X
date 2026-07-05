# AEGIS-X

**Autonomous Cyber-Physical Security Platform**

AEGIS-X is a research-driven platform for attack emulation, multimodal anomaly detection, attack-path reasoning, AI-assisted investigation, and human-approved response orchestration across IT, IoT, OT, and cyber-physical environments.

## First Vertical Slice

`MQTT sensor simulator -> telemetry collector -> anomaly detector -> FastAPI alert API -> dashboard`

## Core Domains

- Cyber range
- Telemetry collection
- Anomaly detection
- Multimodal fusion
- Attack graph reasoning
- Evidence-grounded AI investigation
- Human-approved response orchestration

## Engineering Principles

1. Build measurable vertical slices before adding complexity.
2. Keep attack execution isolated to controlled lab environments.
3. Separate deterministic detection evidence from generative explanations.
4. Require explicit human approval for disruptive response actions.
5. Reproduce experiments with versioned data, configurations, and metrics.

## Roadmap

- [x] Phase 0 — Foundation and architecture
- [x] Phase 1 — MQTT simulator and telemetry ingestion
- [ ] Phase 2 — Baseline anomaly detection and alert API
- [ ] Phase 3 — Operator dashboard and experiment harness
- [ ] Phase 4 — Multimodal event fusion
- [ ] Phase 5 — Attack graph and path reasoning
- [ ] Phase 6 — Evidence-grounded AI investigator
- [ ] Phase 7 — Human-approved response orchestration
- [ ] Phase 8 — Benchmarking and research evaluation

## Responsible Use

AEGIS-X is intended for defensive security research, authorized testing, and isolated cyber-range experimentation. Attack scenarios must only be executed against systems you own or are explicitly authorized to test.

## License

Apache License 2.0.
