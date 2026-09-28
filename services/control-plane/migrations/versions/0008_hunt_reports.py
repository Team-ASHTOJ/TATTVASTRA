"""Associate forensic reports with an investigation while preserving case reports."""

import sqlalchemy as sa
from alembic import op

revision = "0008_hunt_reports"
down_revision = "0007_execution_transport"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.add_column(sa.Column("hunt_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_reports_hunt", "hunts", ["hunt_id"], ["id"])
        batch.create_index("ix_reports_hunt_id", ["hunt_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_index("ix_reports_hunt_id")
        batch.drop_constraint("fk_reports_hunt", type_="foreignkey")
        batch.drop_column("hunt_id")
