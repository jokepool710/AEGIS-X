from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from aegis.investigation.evidence import EvidenceBundle, EvidenceKind


@dataclass(frozen=True)
class TimelineEvent:
    sequence: int
    timestamp: str
    event_type: str
    summary: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class InvestigationTimeline:
    incident_id: str
    events: tuple[TimelineEvent, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "incident_id": self.incident_id,
            "events": [asdict(event) for event in self.events],
        }


class TimelineReconstructor:
    """Build a stable chronological timeline using only timestamped evidence."""

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _summary(kind: EvidenceKind, payload: dict[str, object]) -> str:
        if kind == EvidenceKind.ALERT:
            return (
                f"Alert {payload.get('label', 'unknown')} observed on metric "
                f"{payload.get('metric', 'unknown')} with severity {payload.get('severity', 'unknown')}"
            )
        if kind == EvidenceKind.INCIDENT:
            return f"Incident opened with severity {payload.get('severity', 'unknown')}"
        if kind == EvidenceKind.RISK:
            return (
                f"Risk assessed as {payload.get('risk_level', 'unknown')} "
                f"with score {payload.get('risk_score', 'unknown')}"
            )
        if kind == EvidenceKind.LIFECYCLE:
            return f"Incident status changed to {payload.get('status', 'unknown')}"
        return f"{kind.value} evidence observed"

    def reconstruct(self, bundle: EvidenceBundle) -> InvestigationTimeline:
        candidates = []
        for item in bundle.evidence:
            if item.observed_at is None:
                continue
            timestamp = self._parse_timestamp(item.observed_at)
            candidates.append((timestamp, item.evidence_id, item))

        candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
        events = tuple(
            TimelineEvent(
                sequence=index,
                timestamp=timestamp.isoformat(),
                event_type=item.kind.value,
                summary=self._summary(item.kind, item.payload),
                evidence_ids=(item.evidence_id,),
            )
            for index, (timestamp, _, item) in enumerate(candidates, start=1)
        )
        return InvestigationTimeline(bundle.incident_id, events)
