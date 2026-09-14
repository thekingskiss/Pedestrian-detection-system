import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DetectionEvent(Base):
    """
    FR-09: persistent log of every detection event that survives confidence
    filtering (FR-04). Deliberately does NOT store raw frame imagery in the
    relational DB — only geometry + metadata — per NFR-07 data-minimisation;
    an optional clip_uri points at short-retention encrypted object storage
    if a visual record is required for audit purposes.
    """

    __tablename__ = "detection_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camera_feeds.id", ondelete="CASCADE"), nullable=False
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_zones.id", ondelete="SET NULL"), nullable=True
    )
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FR-05 identity continuity
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {x1,y1,x2,y2} normalised
    distance_estimate_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification: Mapped[str] = mapped_column(String(16), nullable=False)  # safe|caution|critical
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    # XAI-lite audit trail (Section 5.6): which rule fired and the threshold
    # values it was compared against, e.g. {"rule_fired": "closing_speed_exceeded",
    # "occluded": false, "lighting_condition": "low_light", ...} — see
    # risk_classifier.RiskAssessment.reasoning and pipeline_orchestrator.py.
    reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
