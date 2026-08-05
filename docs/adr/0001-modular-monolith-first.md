# ADR-0001: Start as a Modular Monolith

- Status: Accepted
- Date: 2026-07-04

## Context

AEGIS-X spans ingestion, detection, fusion, graph reasoning, investigation, response, and user-facing applications. Splitting these into networked microservices at the start would increase deployment and debugging complexity before workload boundaries and scaling requirements are known.

## Decision

Start with a modular Python monolith for core security logic, separate process boundaries only where operationally justified, and define clean interfaces between domains.

The MQTT broker remains an external infrastructure component. The API is an application boundary. Core modules remain importable Python packages during early research phases.

## Consequences

Positive:

- Faster experimentation.
- Easier local debugging.
- Lower infrastructure overhead.
- Simpler reproducibility for academic evaluation.

Trade-offs:

- Module boundaries require discipline.
- Future extraction may require interface migration.

## Review Trigger

Revisit this decision when independent scaling, isolation, or deployment requirements are demonstrated by measurements rather than assumptions.
