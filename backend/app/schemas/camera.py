import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CameraBase(BaseModel):
    name: str
    source_type: str  # rtsp | file | upload
    source_uri: str
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    target_fps: int = 15


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    target_fps: int | None = None
    source_type: str | None = None
    source_uri: str | None = None


class CameraOut(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    avg_processing_latency_ms: float | None = None
    observed_fps: float | None = None
