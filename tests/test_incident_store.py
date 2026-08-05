from aegis.common.storage import TelemetryStore
from aegis.correlation.incident_store import PersistentIncidentStore
from aegis.correlation.incidents import Incident


def incident(incident_id: str, alerts: tuple[str, ...], assets: tuple[str, ...], first: str, last: str,
             confidence: float = 0.8, severity: str = "high") -> Incident:
    return Incident(incident_id, alerts, assets, ("temporal",), first, last, confidence, severity)


def store(tmp_path) -> PersistentIncidentStore:
    return PersistentIncidentStore(TelemetryStore(tmp_path / "aegis.db"))


def test_persists_and_reloads_incident(tmp_path) -> None:
    db = store(tmp_path)
    saved = db.upsert_cluster(incident("inc-1", ("a1", "a2"), ("plc", "pump"),
                                       "2026-07-07T10:00:00+00:00", "2026-07-07T10:01:00+00:00"))
    loaded = db.get(saved.incident_id)
    assert loaded.alert_ids == ("a1", "a2")
    assert set(loaded.affected_assets) == {"plc", "pump"}


def test_overlapping_cluster_updates_existing_incident_identity(tmp_path) -> None:
    db = store(tmp_path)
    first = db.upsert_cluster(incident("inc-1", ("a1", "a2"), ("gw", "plc"),
                                       "2026-07-07T10:00:00+00:00", "2026-07-07T10:01:00+00:00"))
    updated = db.upsert_cluster(incident("new-random-id", ("a2", "a3"), ("plc", "pump"),
                                         "2026-07-07T10:00:30+00:00", "2026-07-07T10:02:00+00:00", 0.9, "critical"))
    assert updated.incident_id == first.incident_id
    assert set(updated.alert_ids) == {"a1", "a2", "a3"}
    assert set(updated.affected_assets) == {"gw", "plc", "pump"}
    assert updated.severity == "critical"
    assert updated.confidence == 0.9


def test_bridge_cluster_merges_two_existing_incidents(tmp_path) -> None:
    db = store(tmp_path)
    db.upsert_cluster(incident("inc-1", ("a1", "a2"), ("gw", "plc"),
                               "2026-07-07T10:00:00+00:00", "2026-07-07T10:01:00+00:00"))
    db.upsert_cluster(incident("inc-2", ("a3", "a4"), ("sensor", "pump"),
                               "2026-07-07T10:02:00+00:00", "2026-07-07T10:03:00+00:00"))
    merged = db.upsert_cluster(incident("bridge", ("a2", "a3"), ("plc", "sensor"),
                                        "2026-07-07T10:01:00+00:00", "2026-07-07T10:02:00+00:00"))
    assert set(merged.alert_ids) == {"a1", "a2", "a3", "a4"}
    assert len(db.list()) == 1


def test_persistent_lifecycle_transition(tmp_path) -> None:
    db = store(tmp_path)
    saved = db.upsert_cluster(incident("inc-1", ("a1", "a2"), ("plc",),
                                       "2026-07-07T10:00:00+00:00", "2026-07-07T10:01:00+00:00"))
    investigating = db.transition(saved.incident_id, "investigating", "analyst assigned")
    assert investigating.status == "investigating"
    assert investigating.status_note == "analyst assigned"
    assert db.get(saved.incident_id).status == "investigating"
