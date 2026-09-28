"""Preinstalled Windows supervisor registration and bounded lifecycle."""

import sqlalchemy as sa
from alembic import op

revision = "0008_windows_bootstrap"
down_revision = "0007_execution_transport"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "windows_bootstraps",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("simulation", sa.Boolean(), nullable=False),
        sa.Column("simulation_label", sa.String(128)),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("credential_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("desired_state", sa.String(32), nullable=False),
        sa.Column("reported_state", sa.String(32), nullable=False),
        sa.Column("activation_id", sa.Uuid()),
        sa.Column("endpoint_id", sa.Uuid(), sa.ForeignKey("endpoints.id")),
        sa.Column("enrollment_id", sa.Uuid(), sa.ForeignKey("endpoint_enrollments.id")),
        sa.Column("last_poll_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("organization_id", "hostname"),
    )
    op.create_index(
        "ix_windows_bootstraps_organization_id", "windows_bootstraps", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_windows_bootstraps_organization_id", table_name="windows_bootstraps")
    op.drop_table("windows_bootstraps")
