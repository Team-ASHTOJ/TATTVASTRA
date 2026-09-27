"""Persistent compiler build pipeline and variant membership."""

import sqlalchemy as sa
from alembic import op

revision = "0006_build_forge"
down_revision = "0005_phase4_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "build_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("simulation", sa.Boolean(), nullable=False),
        sa.Column("simulation_label", sa.String(128)),
        sa.Column("compilation_id", sa.Uuid(), sa.ForeignKey("compilations.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("seed", sa.String(16), nullable=False),
        sa.Column("variant_count", sa.Integer(), nullable=False),
        sa.Column("target", sa.String(128), nullable=False),
        sa.Column("execution_mode", sa.String(16), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("manifest", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.add_column("variants", sa.Column("build_run_id", sa.Uuid(), nullable=True))
    with op.batch_alter_table("variants") as batch:
        batch.create_foreign_key("fk_variants_build_run", "build_runs", ["build_run_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("variants") as batch:
        batch.drop_constraint("fk_variants_build_run", type_="foreignkey")
        batch.drop_column("build_run_id")
    op.drop_table("build_runs")
