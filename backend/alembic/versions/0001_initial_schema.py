"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-02
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="officer"),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "camera_feeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_uri", sa.String(1024), nullable=False),
        sa.Column("location_label", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("target_fps", sa.Integer, server_default="15"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "risk_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("camera_feeds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("polygon", postgresql.JSONB, nullable=False),
        sa.Column("safe_distance_meters", sa.Float, server_default="3.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("weights_path", sa.String(1024), nullable=False),
        sa.Column("trained_on", sa.String(255), nullable=True),
        sa.Column("map50", sa.Float, nullable=True),
        sa.Column("map50_95", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "detection_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("camera_feeds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("track_id", sa.Integer, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("bbox", postgresql.JSONB, nullable=False),
        sa.Column("distance_estimate_m", sa.Float, nullable=True),
        sa.Column("closing_speed_mps", sa.Float, nullable=True),
        sa.Column("classification", sa.String(16), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
    )
    op.create_index("ix_detection_events_timestamp", "detection_events", ["timestamp"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "detection_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged", sa.Boolean, server_default=sa.false()),
        sa.Column(
            "acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("dispatched_to_external", sa.Boolean, server_default=sa.false()),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("camera_feeds.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("confidence_threshold", sa.Float, server_default="0.5"),
        sa.Column("low_light_confidence_threshold", sa.Float, server_default="0.4"),
        sa.Column("safe_distance_meters", sa.Float, server_default="3.0"),
        sa.Column("closing_speed_critical_mps", sa.Float, server_default="2.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("alert_rules")
    op.drop_table("alerts")
    op.drop_table("detection_events")
    op.drop_table("model_versions")
    op.drop_table("risk_zones")
    op.drop_table("camera_feeds")
    op.drop_table("users")
