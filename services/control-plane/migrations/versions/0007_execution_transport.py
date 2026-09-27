"""Observed authenticated transport, independent of connection freshness."""

import sqlalchemy as sa
from alembic import op

revision = "0007_execution_transport"
down_revision = "0006_build_forge"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "endpoints",
        sa.Column("transport_mode", sa.String(32), nullable=False, server_default="UNKNOWN"),
    )


def downgrade():
    op.drop_column("endpoints", "transport_mode")
