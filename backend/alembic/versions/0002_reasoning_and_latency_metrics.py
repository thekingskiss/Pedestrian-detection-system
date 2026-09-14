"""reasoning trace + latency/FPS metrics

Adds the columns needed for three gaps identified against the pedestrian-
detection literature (occlusion-aware suppression already lives in code,
no schema change needed there):

- detection_events.reasoning / alerts.reasoning: an XAI-lite audit trail of
  which risk-classifier rule fired and the threshold values behind it.
- model_versions.{avg_inference_latency_ms,benchmark_fps,latency_type,
  latency_hardware}: distinguishes a real-time claim (single-image latency
  on named hardware) from batched/TensorRT throughput, which the source
  review is explicit cannot support a real-time claim on its own.
- camera_feeds.{avg_processing_latency_ms,observed_fps}: measured live
  pipeline performance for this deployment, as opposed to a model card's
  offline benchmark number.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("detection_events", sa.Column("reasoning", postgresql.JSONB, nullable=True))
    op.add_column("alerts", sa.Column("reasoning", postgresql.JSONB, nullable=True))

    op.add_column("model_versions", sa.Column("avg_inference_latency_ms", sa.Float, nullable=True))
    op.add_column("model_versions", sa.Column("benchmark_fps", sa.Float, nullable=True))
    op.add_column("model_versions", sa.Column("latency_type", sa.String(32), nullable=True))
    op.add_column("model_versions", sa.Column("latency_hardware", sa.String(128), nullable=True))

    op.add_column("camera_feeds", sa.Column("avg_processing_latency_ms", sa.Float, nullable=True))
    op.add_column("camera_feeds", sa.Column("observed_fps", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("camera_feeds", "observed_fps")
    op.drop_column("camera_feeds", "avg_processing_latency_ms")

    op.drop_column("model_versions", "latency_hardware")
    op.drop_column("model_versions", "latency_type")
    op.drop_column("model_versions", "benchmark_fps")
    op.drop_column("model_versions", "avg_inference_latency_ms")

    op.drop_column("alerts", "reasoning")
    op.drop_column("detection_events", "reasoning")
