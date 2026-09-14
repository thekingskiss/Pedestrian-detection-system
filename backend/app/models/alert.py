import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Alert(Base):
    """FR-08: a Critical/Caution alert raised off the back of a DetectionEvent."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    detection_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("detection_events.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # caution|critical
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    # Denormalised copy of the triggering DetectionEvent.reasoning, so an
    # officer reviewing an alert can see *why* it fired without a join.
    reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # NFR-10: interoperability — the outbound webhook this alert was pushed to, if any.
    dispatched_to_external: Mapped[bool] = mapped_column(Boolean, default=False)


class AlertRule(Base):
    """
    FR-11: administrator-configurable thresholds driving the risk classifier.
    A single active row per camera (or a NULL camera_id row = global default).
    """

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camera_feeds.id", ondelete="CASCADE"), nullable=True
    )
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    low_light_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.4)
    safe_distance_meters: Mapped[float] = mapped_column(Float, default=3.0)
    closing_speed_critical_mps: Mapped[float] = mapped_column(Float, default=2.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
