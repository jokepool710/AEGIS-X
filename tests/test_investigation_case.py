import pytest

from aegis.common.storage import TelemetryStore
from aegis.workflow.case import CaseStatus, InvestigationCaseStore


def test_create_get_list_case_transitions(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_case.db"))
    store = InvestigationCaseStore(storage)

    case = store.create("inc-99", title="Critical OT Pump Incident Case", assignee="analyst-lead")
    assert case.case_id.startswith("case-")
    assert case.status == CaseStatus.DRAFT
    assert case.assignee == "analyst-lead"

    retrieved = store.get(case.case_id)
    assert retrieved.title == "Critical OT Pump Incident Case"

    updated = store.transition(case.case_id, CaseStatus.IN_REVIEW, note="Submitted for peer review")
    assert updated.status == CaseStatus.IN_REVIEW
    assert len(updated.notes) == 1
    assert "Submitted for peer review" in updated.notes[0]

    cases = store.list(status=CaseStatus.IN_REVIEW)
    assert len(cases) == 1
    assert cases[0].case_id == case.case_id


def test_invalid_case_transition_raises_error(tmp_path) -> None:
    storage = TelemetryStore(str(tmp_path / "test_case_invalid.db"))
    store = InvestigationCaseStore(storage)

    case = store.create("inc-100")
    # Draft cannot transition directly to Approved
    with pytest.raises(ValueError, match="cannot transition case"):
        store.transition(case.case_id, CaseStatus.APPROVED)
