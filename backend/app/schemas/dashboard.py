import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    """FR-10: analytics dashboard summary payload."""

    window_start: datetime
    window_end: datetime
    total_detections: int
    total_critical_alerts: int
    total_caution_alerts: int
    active_cameras: int
    hotspots: list["HotspotEntry"]
    # Live pipeline performance, averaged across active cameras reporting
    # metrics (NULL if none have processed a metrics window yet) — see
    # CameraPipeline._record_frame_latency() in pipeline_orchestrator.py.
    avg_processing_latency_ms: float | None = None
    avg_observed_fps: float | None = None


class HotspotEntry(BaseModel):
    zone_id: uuid.UUID | None
    zone_name: str | None
    camera_id: uuid.UUID
    camera_name: str
    detection_count: int
    critical_count: int


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    weights_path: str
    trained_on: str | None
    map50: float | None
    map50_95: float | None
    avg_inference_latency_ms: float | None
    benchmark_fps: float | None
    latency_type: str | None
    latency_hardware: str | None
    is_active: bool
    created_at: datetime


class ModelVersionCreate(BaseModel):
    name: str
    weights_path: str
    trained_on: str | None = None
    map50: float | None = None
    map50_95: float | None = None
    avg_inference_latency_ms: float | None = None
    benchmark_fps: float | None = None
    latency_type: str | None = None  # single_image | batched_throughput — see ModelVersion model docstring
    latency_hardware: str | None = None
