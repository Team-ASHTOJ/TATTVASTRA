"""Persist optional analysis status on existing reports."""

import sqlalchemy as sa
from alembic import op

revision = "0009_report_hypotheses"
down_revision = "0008_hunt_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.add_column(sa.Column("analysis_status", sa.String(16), nullable=True))
        batch.add_column(sa.Column("analysis_model", sa.String(128), nullable=True))
        batch.add_column(sa.Column("analysis_document", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("analysis_generated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("analysis_input_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("analysis_error", sa.String(256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        for name in (
            "analysis_error",
            "analysis_input_hash",
            "analysis_generated_at",
            "analysis_document",
            "analysis_model",
            "analysis_status",
        ):
            batch.drop_column(name)
