import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RiskZone(Base):
    """
    FR-06 / FR-11: an administrator-configurable polygon (in normalised
    frame coordinates, [[x, y], ...]) defining a road/crossing risk area for
    a given camera, plus the safe-distance threshold used by the Section 9
    decision tree for that zone.
    """

    __tablename__ = "risk_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camera_feeds.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    polygon: Mapped[list] = mapped_column(JSONB, nullable=False)  # [[x,y], [x,y], ...]
    safe_distance_meters: Mapped[float] = mapped_column(Float, default=3.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
