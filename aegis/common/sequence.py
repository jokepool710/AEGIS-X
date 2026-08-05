from dataclasses import dataclass


@dataclass(frozen=True)
class SequenceGap:
    device_id: str
    metric: str
    previous_sequence: int
    current_sequence: int
    missing_from: int
    missing_to: int
    missing_count: int


class SequenceTracker:
    def __init__(self) -> None:
        self._last_seen: dict[tuple[str, str], int] = {}

    def observe(self, device_id: str, metric: str, sequence: int) -> SequenceGap | None:
        key = (device_id, metric)
        previous = self._last_seen.get(key)

        if previous is None:
            self._last_seen[key] = sequence
            return None

        if sequence <= previous:
            return None

        self._last_seen[key] = sequence
        if sequence == previous + 1:
            return None

        return SequenceGap(
            device_id=device_id,
            metric=metric,
            previous_sequence=previous,
            current_sequence=sequence,
            missing_from=previous + 1,
            missing_to=sequence - 1,
            missing_count=sequence - previous - 1,
        )
