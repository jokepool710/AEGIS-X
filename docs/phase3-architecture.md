# Phase 3 Architecture — Incident Correlation and Attack-Path Reasoning

Phase 3 converts independent anomaly alerts into persistent, prioritized cyber-physical incidents. It is the reasoning layer between Phase 2 detection and later AI-assisted investigation.

## Pipeline

```text
Raw anomaly alerts
        |
        v
+-------------------+
| Alert Enrichment  |  asset type, cell/zone, criticality, topology context
+-------------------+
        |
        v
+-------------------+
| Correlation Engine|  temporal, asset/topology, metric and detector evidence
+-------------------+
        |
        v
+-------------------+
| Incident Clusterer|  connected alert groups -> incident candidates
+-------------------+
        |
        v
+------------------------+
| Persistent Incident DB |  stable identity, alert membership, lifecycle state
+------------------------+
        |
        +--------------------+
        |                    |
        v                    v
+-------------------+  +-------------------+
| Attack Graph      |  | ATT&CK for ICS    |
| Engine            |->| Mapping Layer     |
+-------------------+  +-------------------+
        |                    |
        +---------+----------+
                  v
        +-------------------+
        | Risk Prioritizer  |  score, level, ranked incident analyses
        +-------------------+
                  |
                  v
        +-------------------+
        | Incident API      |  list, detail, lifecycle transition
        +-------------------+
```

## Core components

| Component | Responsibility |
| --- | --- |
| `AssetTopology` | Models assets, criticality, zones/cells, and directed relationships such as connectivity and control. |
| `AlertEnricher` | Adds cyber-physical asset and topology context to raw anomaly alerts. |
| `CorrelationEngine` | Produces evidence-backed edges between related enriched alerts. |
| `IncidentClusterer` | Converts correlated alert graphs into incident candidates. |
| `PersistentIncidentStore` | Persists incidents and alert membership, merges overlaps, maintains stable incident identity, and enforces lifecycle transitions. |
| `AttackGraphEngine` | Builds incident-scoped attack graphs from assets, alerts, and correlation edges. |
| `ICSAttackMapper` | Maps graph evidence to ATT&CK for ICS-aligned techniques. |
| `RiskPrioritizationEngine` | Combines incident severity, confidence, topology/criticality, graph evidence, and mappings into prioritized risk assessments. |
| `Phase3Pipeline` | Orchestrates enrichment, correlation, clustering, persistence, graph construction, mapping, and risk assessment. |
| Incident API | Exposes incident listing, detail retrieval, and controlled status transitions. |

## Phase 3 E2E contract

The integration test `tests/integration/test_phase3_e2e.py` validates the complete incident path using a three-asset cyber-physical topology:

```text
Gateway 01 --connects_to--> PLC 01 --controls--> Pump 01
```

The test asserts all of the following:

1. Three related alerts become exactly one incident.
2. The incident retains all three alert IDs.
3. The incident identifies all three affected assets.
4. An attack graph is constructed with the expected node population.
5. ATT&CK for ICS mappings are produced.
6. A positive risk score and actionable risk level are produced.
7. The incident can be reloaded from persistent storage with stable identity.
8. `GET /api/v1/incidents` exposes the persisted incident.
9. `GET /api/v1/incidents/{incident_id}` returns its alert membership.
10. `PATCH /api/v1/incidents/{incident_id}/status` transitions the incident to `investigating` and persists the triage note.
11. Reprocessing the same alerts preserves the incident ID.
12. Reprocessing is idempotent at the incident-store level: only one incident remains.

## CI validation

The main CI workflow runs the following gates in order:

```text
Ruff lint
  -> Unit tests
  -> MQTT telemetry E2E
  -> Phase 3 incident E2E
```

Phase 3 is considered complete only when the full CI job passes, because the final integration test depends on the persistence and API layers as well as the correlation pipeline.

## Phase boundary

Phase 3 owns deterministic incident construction and prioritization. Generative AI must not replace or silently modify this evidence chain. The next phase may consume incident analyses, graph evidence, ATT&CK mappings, risk assessments, and persisted lifecycle state to produce evidence-grounded investigation assistance with explicit provenance.
