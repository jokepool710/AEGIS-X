from aegis.common.storage import TelemetryStore
from aegis.investigation.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from aegis.workflow.provenance import EvidenceChainOfCustody


def bundle() -> EvidenceBundle:
    return EvidenceBundle(
        "inc-prov-1", "1.0",
        (
            EvidenceItem("alert:a10", EvidenceKind.ALERT, "detector", "2026-07-11T12:00:00Z", {"val": 42}),
            EvidenceItem("asset:plc1", EvidenceKind.ASSET, "topology", None, {"asset": "plc1"}),
        ),
    )


def test_record_and_verify_evidence_provenance(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_provenance.db"))
    custody = EvidenceChainOfCustody(storage)
    b = bundle()

    provenance = custody.record_bundle("case-prov-100", b)

    assert provenance.case_id == "case-prov-100"
    assert provenance.evidence_count == 2
    assert provenance.is_valid is True
    assert len(provenance.records) == 2
    assert provenance.records[0].payload_hash != ""


def test_tampered_evidence_payload_fails_verification(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_provenance_tamper.db"))
    custody = EvidenceChainOfCustody(storage)
    b = bundle()

    custody.record_bundle("case-prov-101", b)

    # Modify evidence payload in bundle
    tampered_items = (
        EvidenceItem("alert:a10", EvidenceKind.ALERT, "detector", "2026-07-11T12:00:00Z", {"val": 999}),
        b.evidence[1],
    )
    tampered_bundle = EvidenceBundle("inc-prov-1", "1.0", tampered_items)

    verified = custody.verify("case-prov-101", tampered_bundle)
    assert verified.is_valid is False
    assert "tampered" in verified.verification_note
