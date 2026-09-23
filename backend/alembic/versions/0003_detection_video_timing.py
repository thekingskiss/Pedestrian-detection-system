"""Add source video timing to detection events."""

from alembic import op
import sqlalchemy as sa


revision = "0003_detection_video_timing"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "detection_events",
        sa.Column("frame_index", sa.Integer(), nullable=True),
    )

    op.add_column(
        "detection_events",
        sa.Column("source_timestamp", sa.Float(), nullable=True),
    )

    op.create_index(
        "ix_detection_events_frame_index",
        "detection_events",
        ["frame_index"],
    )

    op.create_index(
        "ix_detection_events_source_timestamp",
        "detection_events",
        ["source_timestamp"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_detection_events_source_timestamp",
        table_name="detection_events",
    )

    op.drop_index(
        "ix_detection_events_frame_index",
        table_name="detection_events",
    )

    op.drop_column(
        "detection_events",
        "source_timestamp",
    )

    op.drop_column(
        "detection_events",
        "frame_index",
    )