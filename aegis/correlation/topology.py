from dataclasses import dataclass, field
from enum import Enum


class AssetType(str, Enum):
    GATEWAY = "gateway"
    PLC = "plc"
    HMI = "hmi"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    PROCESS = "process"
    OTHER = "other"


class RelationshipType(str, Enum):
    CONNECTS_TO = "connects_to"
    CONTROLS = "controls"
    MONITORS = "monitors"
    FEEDS = "feeds"
    DEPENDS_ON = "depends_on"


@dataclass(frozen=True)
class Asset:
    asset_id: str
    asset_type: AssetType
    name: str
    criticality: float = 0.5
    zone: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.asset_id or not self.name:
            raise ValueError("asset_id and name are required")
        if not 0.0 <= self.criticality <= 1.0:
            raise ValueError("criticality must be between 0 and 1")


@dataclass(frozen=True)
class AssetRelationship:
    source_id: str
    target_id: str
    relationship: RelationshipType


class AssetTopology:
    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}
        self._edges: set[AssetRelationship] = set()

    def add_asset(self, asset: Asset) -> None:
        self._assets[asset.asset_id] = asset

    def add_relationship(self, relationship: AssetRelationship) -> None:
        if relationship.source_id not in self._assets or relationship.target_id not in self._assets:
            raise ValueError("both relationship endpoints must exist")
        self._edges.add(relationship)

    def get_asset(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def neighbors(self, asset_id: str, hops: int = 1) -> set[str]:
        if hops < 1:
            return set()
        visited = {asset_id}
        frontier = {asset_id}
        for _ in range(hops):
            next_frontier: set[str] = set()
            for edge in self._edges:
                if edge.source_id in frontier and edge.target_id not in visited:
                    next_frontier.add(edge.target_id)
                if edge.target_id in frontier and edge.source_id not in visited:
                    next_frontier.add(edge.source_id)
            visited.update(next_frontier)
            frontier = next_frontier
        visited.discard(asset_id)
        return visited

    def shortest_distance(self, source_id: str, target_id: str, max_hops: int = 8) -> int | None:
        if source_id == target_id:
            return 0
        for hops in range(1, max_hops + 1):
            if target_id in self.neighbors(source_id, hops):
                return hops
        return None

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        return {
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type.value,
                    "name": asset.name,
                    "criticality": asset.criticality,
                    "zone": asset.zone,
                    "metadata": asset.metadata,
                }
                for asset in self._assets.values()
            ],
            "relationships": [
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relationship": edge.relationship.value,
                }
                for edge in self._edges
            ],
        }
