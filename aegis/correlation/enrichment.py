from dataclasses import asdict, dataclass
from datetime import datetime

from aegis.correlation.topology import AssetTopology


@dataclass(frozen=True)
class DetectorEvidence:
    z_score: float = 0.0
    ewma_score: float = 0.0
    isolation_score: float = 0.0
    temporal_score: float = 0.0
    contextual_score: float = 0.0
    model_generation: int = 0


@dataclass(frozen=True)
class EnrichedAlert:
    alert_id: str
    event_id: str
    asset_id: str
    asset_type: str
    metric: str
    value: float
    unified_score: float
    severity: str
    status: str
    created_at: str
    attack_family: str
    evidence: DetectorEvidence
    asset_criticality: float
    zone: str | None
    related_assets: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        item = asdict(self)
        item["related_assets"] = list(self.related_assets)
        return item


class AlertEnricher:
    def __init__(self, topology: AssetTopology, relationship_hops: int = 2) -> None:
        self.topology = topology
        self.relationship_hops = relationship_hops

    @staticmethod
    def _attack_family(scores: dict[str, object]) -> str:
        temporal = float(scores.get("temporal_score", 0.0))
        contextual = float(scores.get("contextual_score", 0.0))
        point = max(
            float(scores.get("z_score", 0.0)),
            float(scores.get("ewma_score", 0.0)),
            float(scores.get("isolation_score", 0.0)),
        )
        strongest = max((point, "point"), (temporal, "temporal"), (contextual, "contextual"))
        return strongest[1]

    def enrich(self, alert: dict[str, object]) -> EnrichedAlert:
        asset_id = str(alert["device_id"])
        asset = self.topology.get_asset(asset_id)
        scores = dict(alert.get("detector_scores", {}))
        evidence = DetectorEvidence(
            z_score=float(scores.get("z_score", 0.0)),
            ewma_score=float(scores.get("ewma_score", 0.0)),
            isolation_score=float(scores.get("isolation_score", 0.0)),
            temporal_score=float(scores.get("temporal_score", 0.0)),
            contextual_score=float(scores.get("contextual_score", 0.0)),
            model_generation=int(scores.get("model_generation", 0)),
        )
        created_at = str(alert["created_at"])
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return EnrichedAlert(
            alert_id=str(alert["alert_id"]),
            event_id=str(alert["event_id"]),
            asset_id=asset_id,
            asset_type=asset.asset_type.value if asset else "unknown",
            metric=str(alert["metric"]),
            value=float(alert["value"]),
            unified_score=float(alert["unified_score"]),
            severity=str(alert["severity"]),
            status=str(alert["status"]),
            created_at=created_at,
            attack_family=self._attack_family(scores),
            evidence=evidence,
            asset_criticality=asset.criticality if asset else 0.5,
            zone=asset.zone if asset else None,
            related_assets=tuple(sorted(self.topology.neighbors(asset_id, self.relationship_hops))),
        )
