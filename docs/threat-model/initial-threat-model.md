# Initial Threat Model

## Scope

This document covers the initial MQTT-based vertical slice of AEGIS-X.

## Assets

- Telemetry integrity
- Alert integrity
- Detector configuration and model artifacts
- Experiment labels and benchmark results
- Operator approval decisions
- Audit records

## Trust Boundaries

1. Simulated device to MQTT broker
2. MQTT broker to telemetry collector
3. Collector to detection engine
4. Detection engine to API and dashboard
5. Investigator output to operator decision
6. Operator approval to response executor

## Initial Threats

- Spoofed device telemetry
- Replay of previously valid telemetry
- Malformed payloads causing parser failure
- Broker abuse or unauthorized publishing
- Alert flooding and denial of service
- Poisoned training or calibration data
- Model evasion through slow behavioral drift
- Hallucinated or unsupported investigator conclusions
- Unauthorized or unsafe response execution

## Initial Controls

- Schema validation and payload size limits
- Device identity strategy before non-lab deployment
- Event timestamps, sequence tracking, and replay detection
- Rate limits and bounded queues
- Immutable experiment metadata and dataset hashes
- Evidence references for generated investigation output
- Policy checks and explicit approval gates for disruptive actions
- Structured audit logging

## Non-Goals for Phase 1

Phase 1 does not claim production-ready OT deployment, autonomous containment, or zero-day detection guarantees. The objective is a reproducible research platform and measurable end-to-end prototype.
