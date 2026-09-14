import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class CameraFeed(Base):
    """
    FR-01: video/frame source registration. NFR-04: the schema deliberately
    treats cameras as a plain list of rows so adding a new feed/node is an
    INSERT, not a schema or pipeline redesign.
    """

    __tablename__ = "camera_feeds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # rtsp | file | upload
    source_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    location_label: Mapped[str] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    target_fps: Mapped[int] = mapped_column(default=15)  # NFR-01
    # Live, measured pipeline performance (updated by CameraPipeline.run() —
    # see pipeline_orchestrator.py), as opposed to a model card's offline
    # benchmark number. NULL until the worker has processed at least one
    # metrics window for this camera.
    avg_processing_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
