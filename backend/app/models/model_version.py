import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ModelVersion(Base):
    """
    FR-13: registry of trained YOLO weight artifacts, so the system can
    support periodic retraining/updating without redeploying the whole
    service — the active row is what ml/model_registry.py loads at startup
    and what alert_service attaches to each DetectionEvent for traceability.
    """

    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. yolov8n-pedestrian-v3
    weights_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    trained_on: Mapped[str] = mapped_column(String(255), nullable=True)  # dataset description
    map50: Mapped[float | None] = mapped_column(Float, nullable=True)  # mAP@0.5 (NFR-02 target 0.75)
    map50_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Real-time suitability metadata. A headline speed number is meaningless
    # without knowing how it was measured: single-image latency on a target
    # device is the only figure that supports a real-time claim, whereas
    # batched/TensorRT throughput can look fast while still missing a
    # single-stream latency budget. `latency_type` records which one this
    # row's numbers are, so the API can't accidentally conflate them.
    avg_inference_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # single_image | batched_throughput
    latency_hardware: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "Jetson Nano", "CPU"
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
