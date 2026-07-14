import sqlite3

import pytest

from aegis.common.storage import TelemetryStore
from aegis.orchestration.ledger import (
    DecisionEventType,
    DecisionLedger,
    DecisionLedgerIntegrityError,
)


def ledger(tmp_path) -> DecisionLedger:
    return DecisionLedger(TelemetryStore(str(tmp_path / "ledger.db")))


def test_appends_and_reloads_events_in_sequence(tmp_path) -> None:
    first = ledger(tmp_path)
    first.append("inc-1", "plan-1", DecisionEventType.PLAN_CREATED, "system", {"tasks": 4})
    first.append("inc-1", "plan-1", DecisionEventType.APPROVED, "analyst-1", {"task_id": "t1"})

    second = ledger(tmp_path)
    events = second.list("inc-1")

    assert [event.sequence for event in events] == [1, 2]
    assert events[0].event_type is DecisionEventType.PLAN_CREATED
    assert events[1].actor_id == "analyst-1"
    assert events[1].previous_hash == events[0].event_hash


def test_integrity_verification_passes_for_valid_chain(tmp_path) -> None:
    store = ledger(tmp_path)
    store.append("inc-1", "plan-1", DecisionEventType.RECOMMENDATION_CREATED, "system", {"rank": 1})
    store.append("inc-1", "plan-1", DecisionEventType.APPROVAL_REQUESTED, "system", {"task": "inspect"})

    assert store.verify_integrity() is True


def test_payload_tampering_is_detected(tmp_path) -> None:
    store = ledger(tmp_path)
    store.append("inc-1", "plan-1", DecisionEventType.APPROVED, "analyst-1", {"approved": True})

    with sqlite3.connect(store.db_path) as connection:
        connection.execute(
            "UPDATE decision_ledger SET payload_json = ? WHERE sequence = 1",
            ('{"approved":false}',),
        )

    with pytest.raises(DecisionLedgerIntegrityError, match="sequence 1"):
        store.verify_integrity()


def test_chain_link_tampering_is_detected(tmp_path) -> None:
    store = ledger(tmp_path)
    store.append("inc-1", "plan-1", DecisionEventType.PLAN_CREATED, "system", {})
    store.append("inc-1", "plan-1", DecisionEventType.ANALYST_DECISION, "analyst-1", {})

    with sqlite3.connect(store.db_path) as connection:
        connection.execute(
            "UPDATE decision_ledger SET previous_hash = ? WHERE sequence = 2",
            ("f" * 64,),
        )

    with pytest.raises(DecisionLedgerIntegrityError, match="sequence 2"):
        store.verify_integrity()


def test_incident_filter_preserves_global_sequence_numbers(tmp_path) -> None:
    store = ledger(tmp_path)
    store.append("inc-1", "plan-1", DecisionEventType.PLAN_CREATED, "system", {})
    store.append("inc-2", "plan-2", DecisionEventType.PLAN_CREATED, "system", {})
    store.append("inc-1", "plan-1", DecisionEventType.ANALYST_DECISION, "analyst-1", {})

    assert [event.sequence for event in store.list("inc-1")] == [1, 3]
