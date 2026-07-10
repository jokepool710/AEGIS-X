from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.timeline import TimelineReconstructor


def item(evidence_id: str, kind: EvidenceKind, observed_at: str | None,
         payload: dict[str, object]) -> EvidenceItem:
    return EvidenceItem(evidence_id, kind, "test", observed_at, payload)


def test_reconstructs_chronological_timeline_with_evidence_references() -> None:
    bundle = EvidenceBundle(
        "inc-1", "1.0",
        (
            item("risk:inc-1", EvidenceKind.RISK, "2026-07-08T10:02:00+00:00",
                 {"risk_level": "critical", "risk_score": 0.91}),
            item("alert:a2", EvidenceKind.ALERT, "2026-07-08T10:01:00Z",
                 {"label": "a2", "metric": "pressure", "severity": "critical"}),
            item("asset:plc-1", EvidenceKind.ASSET, None, {"asset_id": "plc-1"}),
            item("alert:a1", EvidenceKind.ALERT, "2026-07-08T10:00:00+00:00",
                 {"label": "a1", "metric": "temperature", "severity": "high"}),
        ),
    )

    timeline = TimelineReconstructor().reconstruct(bundle)

    assert [event.sequence for event in timeline.events] == [1, 2, 3]
    assert [event.evidence_ids for event in timeline.events] == [
        ("alert:a1",), ("alert:a2",), ("risk:inc-1",),
    ]
    assert timeline.events[0].timestamp == "2026-07-08T10:00:00+00:00"
    assert "temperature" in timeline.events[0].summary
    assert timeline.to_dict()["incident_id"] == "inc-1"


def test_equal_timestamps_are_ordered_by_evidence_id() -> None:
    timestamp = "2026-07-08T10:00:00+00:00"
    bundle = EvidenceBundle(
        "inc-1", "1.0",
        (
            item("alert:z", EvidenceKind.ALERT, timestamp,
                 {"label": "z", "metric": "flow", "severity": "high"}),
            item("alert:a", EvidenceKind.ALERT, timestamp,
                 {"label": "a", "metric": "pressure", "severity": "high"}),
        ),
    )

    timeline = TimelineReconstructor().reconstruct(bundle)

    assert [event.evidence_ids for event in timeline.events] == [("alert:a",), ("alert:z",)]


def test_ignores_untimestamped_context_without_losing_bundle_provenance() -> None:
    bundle = EvidenceBundle(
        "inc-1", "1.0",
        (item("asset:plc-1", EvidenceKind.ASSET, None, {"asset_id": "plc-1"}),),
    )

    timeline = TimelineReconstructor().reconstruct(bundle)

    assert timeline.incident_id == "inc-1"
    assert timeline.events == ()
