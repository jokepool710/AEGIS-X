# AEGIS-X Architecture Overview

## Objective

AEGIS-X is structured as a modular research platform for observing, detecting, correlating, explaining, and responding to security-relevant behavior in controlled cyber-physical environments.

## High-Level Flow

1. Cyber-range workloads and device simulators generate normal and anomalous behavior.
2. Collectors ingest network, log, protocol, and sensor telemetry.
3. Detection modules produce scored anomaly events with evidence.
4. Fusion correlates events across modalities and time windows.
5. Attack-graph reasoning maps observations to assets and possible paths.
6. The investigator generates evidence-grounded hypotheses and summaries.
7. Response policies propose actions.
8. Disruptive actions require explicit human approval.

## Initial Vertical Slice

The first implementation slice uses MQTT telemetry because it provides a compact way to model cyber and physical state together.

Components:

- MQTT broker
- sensor simulator
- telemetry collector
- baseline anomaly detector
- alert API
- minimal operator dashboard

## Boundaries

Attack emulation is restricted to isolated lab infrastructure. The investigator must not be treated as an authority: generated explanations are hypotheses linked to deterministic evidence. Response actions are policy constrained and human approved.
