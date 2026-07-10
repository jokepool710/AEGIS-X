# Phase 4 Architecture: Evidence-Grounded AI Incident Investigator

## Status

Phase 4 is implementation-complete and CI-validated on the feature branch. The restart-survival boundary is validated by CI #117.

## Objective

Phase 4 turns correlated cyber-physical incidents into auditable investigation outputs. Generative output is downstream of deterministic evidence construction, provenance validation, hypothesis generation, confidence calibration, and persistence.

## End-to-end flow

```text
Phase 3 IncidentAnalysis
        |
        v
Persistent Investigation Artifact Store
        |
        v
Incident Evidence Bundle
        |
        +--> Deterministic Timeline Reconstruction
        |
        +--> Evidence Citation Validation
        |
        v
Deterministic Competing Hypothesis Engine
        |
        v
Confidence and Uncertainty Model
        |
        v
Provider-Agnostic Generative Narrative Layer
        |
        v
Faithfulness Evaluation Harness
        |
        v
Investigator API Response
```

## Components

### Persistent Investigation Artifact Store

Persists the complete Phase 3 analysis required by the investigator: incident, attack graph, ATT&CK for ICS mappings, and risk assessment. The API reconstructs the analysis from SQLite rather than relying on process memory.

### Incident Evidence Bundle

Creates a strict evidence contract with stable evidence IDs, source provenance, timestamps, evidence kinds, and structured payloads. Cross-incident evidence contamination and duplicate evidence IDs are rejected.

### Deterministic Timeline Reconstruction

Normalizes timestamped evidence to UTC and orders events chronologically. Equal timestamps use evidence ID as a deterministic tie-break. Untimestamped context remains in the evidence bundle but is excluded from chronological events.

### Evidence Citation Layer

Requires investigative claims to cite evidence IDs from the active incident bundle. Uncited claims, unknown evidence references, foreign evidence references, and duplicate claim IDs are rejected.

### Hypothesis Engine

Generates multiple deterministic investigation paths from ATT&CK mappings, alert evidence, graph relationships, and risk evidence. Hypotheses are ranked by deterministic confidence and every hypothesis claim passes citation validation.

### Confidence and Uncertainty Model

Calibrates hypothesis confidence using evidence diversity, citation coverage, contradictions, missing evidence, and inference penalties. Mapping confidence is not treated as certainty about the complete incident narrative.

### Generative Narrative Layer

Uses an injected provider interface. The default API provider is deterministic and dependency-free. Generated narratives must contain citations that resolve to the active evidence bundle. The provider boundary can later be replaced by an external or local model without changing the investigation pipeline.

### Faithfulness Evaluation Harness

Measures unsupported claim rate, citation validity, evidence coverage, contradiction handling, narrative consistency, and aggregate faithfulness. The evaluator does not use the narrative generator as its own judge.

### Investigator API

```text
GET /api/v1/incidents/{incident_id}/investigation
```

The endpoint loads persisted Phase 3 artifacts and returns evidence, timeline, ranked hypotheses, uncertainty assessments, grounded narrative, and faithfulness metrics.

## Validation gates

Phase 4 validation covers lint, unit tests, telemetry E2E, Phase 3 incident E2E, Phase 4 investigator E2E, and restart-survival persistence validation.

The restart-survival test verifies:

```text
Phase 3 Analysis
  -> SQLite persistence
  -> writer-side objects discarded
  -> fresh storage and artifact-store instances
  -> IncidentAnalysis reconstruction
  -> Investigator API request
  -> grounded investigation response
```

Required invariants include valid evidence reconstruction, non-empty timeline and hypotheses, narrative citations restricted to the active bundle, citation validity of 1.0, and unsupported claim rate of 0.0 for the deterministic validation provider.

## Trust boundary

Phase 4 does not claim semantic entailment merely because a citation ID exists. Citation validity proves provenance membership. The faithfulness harness measures declared claim support and grounding properties, but stronger sentence-level entailment evaluation remains a future research and evaluation concern.

## Phase 4 closure criteria

Phase 4 is ready to close when the architecture documentation commit is green in CI and the Phase 4 pull request is reviewed and merged. A release tag should be created from the validated merged commit, not from an unmerged feature-branch commit.
