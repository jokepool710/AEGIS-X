import pytest

from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.investigation.narrative import (
    GenerativeNarrativeLayer,
    NarrativeDraft,
    NarrativeGroundingError,
    NarrativeRequest,
)
from aegis.investigation.timeline import InvestigationTimeline, TimelineEvent


class StubProvider:
    name = "stub-provider"

    def __init__(self, draft: NarrativeDraft) -> None:
        self.draft = draft
        self.last_request: NarrativeRequest | None = None

    def generate(self, request: NarrativeRequest) -> NarrativeDraft:
        self.last_request = request
        return self.draft


def bundle() -> EvidenceBundle:
    return EvidenceBundle("inc-1", "1.0", (
        EvidenceItem("alert:a1", EvidenceKind.ALERT, "detector",
                     "2026-07-08T10:00:00+00:00", {"metric": "pressure"}),
        EvidenceItem("risk:inc-1", EvidenceKind.RISK, "risk",
                     "2026-07-08T10:01:00+00:00", {"risk_level": "high"}),
    ))


def timeline() -> InvestigationTimeline:
    return InvestigationTimeline("inc-1", (
        TimelineEvent(1, "2026-07-08T10:00:00+00:00", "alert", "Pressure anomaly observed", ("alert:a1",)),
    ))


def test_generates_narrative_and_validates_citations() -> None:
    provider = StubProvider(NarrativeDraft(
        "A pressure anomaly was observed and the incident risk was assessed as high.",
        ("Pressure telemetry requires investigation.",),
        ("Was a control command issued before the anomaly?",),
        ("alert:a1", "risk:inc-1", "alert:a1"),
    ))

    result = GenerativeNarrativeLayer(provider).generate(bundle(), timeline(), (), ())

    assert result.incident_id == "inc-1"
    assert result.cited_evidence_ids == ("alert:a1", "risk:inc-1")
    assert result.provider == "stub-provider"
    assert provider.last_request is not None
    assert "Available evidence IDs" in provider.last_request.prompt
    assert result.to_dict()["summary"]


def test_rejects_uncited_narrative() -> None:
    provider = StubProvider(NarrativeDraft("Unsupported story", (), (), ()))

    with pytest.raises(NarrativeGroundingError, match="no evidence citations"):
        GenerativeNarrativeLayer(provider).generate(bundle(), timeline(), (), ())


def test_rejects_foreign_citation() -> None:
    provider = StubProvider(NarrativeDraft("Foreign evidence", (), (), ("alert:foreign",)))

    with pytest.raises(NarrativeGroundingError, match="outside the active bundle"):
        GenerativeNarrativeLayer(provider).generate(bundle(), timeline(), (), ())


def test_rejects_cross_incident_timeline() -> None:
    provider = StubProvider(NarrativeDraft("Summary", (), (), ("alert:a1",)))
    wrong_timeline = InvestigationTimeline("inc-other", ())

    with pytest.raises(NarrativeGroundingError, match="incident IDs differ"):
        GenerativeNarrativeLayer(provider).generate(bundle(), wrong_timeline, (), ())
