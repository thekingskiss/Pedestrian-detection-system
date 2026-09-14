import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ZoneBase(BaseModel):
    camera_id: uuid.UUID
    name: str
    polygon: list[list[float]] = Field(
        ..., description="Ordered [[x,y], ...] points, normalised 0-1 in frame space"
    )
    safe_distance_meters: float = 3.0


class ZoneCreate(ZoneBase):
    pass


class ZoneUpdate(BaseModel):
    name: str | None = None
    polygon: list[list[float]] | None = None
    safe_distance_meters: float | None = None


class ZoneOut(ZoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
