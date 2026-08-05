from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    event_id: str
    device_id: str
    device_type: str
    site_id: str
    timestamp: datetime
    sequence: int = Field(ge=0)
    metric: str
    value: float
    unit: str
    quality: Literal["good", "uncertain", "bad"] = "good"
    source_topic: str
    ingested_at: datetime
