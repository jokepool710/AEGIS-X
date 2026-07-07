import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from aegis.correlation.engine import CorrelationEdge
from aegis.correlation.enrichment import EnrichedAlert

INCIDENT_STATUSES = {"open", "investigating", "contained", "resolved", "dismissed"}
INCIDENT_TRANSITIONS = {
    "open": {"investigating", "contained", "resolved", "dismissed"},
    "investigating": {"contained", "resolved", "dismissed"},
    "contained": {"investigating", "resolved"},
    "resolved": set(),
    "dismissed": set(),
}
SEVERITY_RANK = {"normal": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True)
class Incident:
    incident_id: str
    alert_ids: tuple[str, ...]
    affected_assets: tuple[str, ...]
    attack_families: tuple[str, ...]
    first_seen: str
    last_seen: str
    confidence: float
    severity: str
    status: str = "open"
    updated_at: str | None = None
    status_note: str | None = None


class IncidentClusterer:
    """Build incidents as connected components of accepted correlation edges."""

    @staticmethod
    def _timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _severity(alerts: list[EnrichedAlert]) -> str:
        return max((alert.severity for alert in alerts), key=lambda value: SEVERITY_RANK.get(value, 0))

    @staticmethod
    def _confidence(alert_ids: set[str], edges: list[CorrelationEdge]) -> float:
        internal = [edge.score for edge in edges if edge.source_alert_id in alert_ids and edge.target_alert_id in alert_ids]
        if not internal:
            return 0.0
        density_denominator = max(1, len(alert_ids) * (len(alert_ids) - 1) / 2)
        density = len(internal) / density_denominator
        mean_edge = sum(internal) / len(internal)
        return min(1.0, 0.75 * mean_edge + 0.25 * density)

    def cluster(self, alerts: list[EnrichedAlert], edges: list[CorrelationEdge]) -> list[Incident]:
        by_id = {alert.alert_id: alert for alert in alerts}
        adjacency: dict[str, set[str]] = {alert_id: set() for alert_id in by_id}
        for edge in edges:
            if not edge.correlated or edge.source_alert_id not in by_id or edge.target_alert_id not in by_id:
                continue
            adjacency[edge.source_alert_id].add(edge.target_alert_id)
            adjacency[edge.target_alert_id].add(edge.source_alert_id)

        incidents = []
        visited: set[str] = set()
        for start in sorted(adjacency):
            if start in visited or not adjacency[start]:
                continue
            component: set[str] = set()
            stack = [start]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                stack.extend(adjacency[current] - visited)

            members = [by_id[alert_id] for alert_id in component]
            ordered = sorted(members, key=lambda alert: self._timestamp(alert.created_at))
            incidents.append(Incident(
                incident_id=str(uuid.uuid4()),
                alert_ids=tuple(alert.alert_id for alert in ordered),
                affected_assets=tuple(sorted({alert.asset_id for alert in members})),
                attack_families=tuple(sorted({alert.attack_family for alert in members})),
                first_seen=ordered[0].created_at,
                last_seen=ordered[-1].created_at,
                confidence=round(self._confidence(component, edges), 6),
                severity=self._severity(members),
            ))
        return sorted(incidents, key=lambda incident: incident.last_seen, reverse=True)


class IncidentLifecycle:
    def transition(self, incident: Incident, new_status: str, note: str | None = None) -> Incident:
        if new_status not in INCIDENT_STATUSES:
            raise ValueError(f"unknown incident status: {new_status}")
        if new_status == incident.status:
            return incident
        if new_status not in INCIDENT_TRANSITIONS[incident.status]:
            raise ValueError(f"cannot transition incident from {incident.status} to {new_status}")
        return replace(
            incident,
            status=new_status,
            updated_at=datetime.now(timezone.utc).isoformat(),
            status_note=note,
        )
