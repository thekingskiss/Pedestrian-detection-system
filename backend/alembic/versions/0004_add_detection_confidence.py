"""Add confidence score to detection events."""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_detection_confidence"
down_revision = "0003_detection_video_timing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "detection_events",
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
    )

    op.alter_column(
        "detection_events",
        "confidence",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "detection_events",
        "confidence",
    )
