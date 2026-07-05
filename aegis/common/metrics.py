import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class IngestionSnapshot:
    received: int = 0
    stored: int = 0
    duplicates: int = 0
    rejected: int = 0
    sequence_gaps: int = 0
    missing_events: int = 0
    last_received_at: str | None = None
    last_stored_at: str | None = None


class IngestionMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snapshot = IngestionSnapshot()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_received(self) -> None:
        with self._lock:
            self._snapshot.received += 1
            self._snapshot.last_received_at = self._now()

    def record_stored(self) -> None:
        with self._lock:
            self._snapshot.stored += 1
            self._snapshot.last_stored_at = self._now()

    def record_duplicate(self) -> None:
        with self._lock:
            self._snapshot.duplicates += 1

    def record_rejected(self) -> None:
        with self._lock:
            self._snapshot.rejected += 1

    def record_gap(self, missing_count: int) -> None:
        with self._lock:
            self._snapshot.sequence_gaps += 1
            self._snapshot.missing_events += missing_count

    def snapshot(self) -> dict[str, int | str | None]:
        with self._lock:
            return asdict(self._snapshot)
