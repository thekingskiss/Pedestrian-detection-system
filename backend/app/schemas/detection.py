import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionEventOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )

    id: uuid.UUID
    camera_id: uuid.UUID
    zone_id: uuid.UUID | None
    track_id: int
    frame_index: int
    source_timestamp: float
    timestamp: datetime
    confidence: float
    bbox: dict
    distance_estimate_m: float | None
    closing_speed_mps: float | None
    classification: str
    model_version: str
    reasoning: dict | None = None


class DetectionEventFilter(BaseModel):
    camera_id: uuid.UUID | None = None
    classification: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    source_start: float | None = None
    source_end: float | None = None
    limit: int = 100
    offset: int = 0