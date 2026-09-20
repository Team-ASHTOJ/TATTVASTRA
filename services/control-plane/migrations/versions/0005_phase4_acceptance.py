"""Per-endpoint execution policy and immutable artifact membership."""

import sqlalchemy as sa
from alembic import op

revision = "0005_phase4_acceptance"
down_revision = "0004_immutable_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hunts", sa.Column("endpoint_modes", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "hunts",
        sa.Column("enforcement_mode", sa.String(16), nullable=False, server_default="MONITORED"),
    )
    with op.batch_alter_table("compatibility_runs") as batch:
        batch.add_column(sa.Column("endpoint_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_compatibility_endpoint", "endpoints", ["endpoint_id"], ["id"])
    # Preserve existing historical artifacts, including duplicate-content metadata;
    # new uploads are idempotent under the tenant lock. Do not delete evidence to
    # introduce a uniqueness constraint on databases created by earlier versions.
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_artifacts BEFORE UPDATE OR DELETE ON artifacts "
            "FOR EACH ROW EXECUTE FUNCTION jocky_reject_evidence_mutation()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER immutable_artifacts ON artifacts")
    with op.batch_alter_table("compatibility_runs") as batch:
        batch.drop_constraint("fk_compatibility_endpoint", type_="foreignkey")
        batch.drop_column("endpoint_id")
    op.drop_column("hunts", "enforcement_mode")
    op.drop_column("hunts", "endpoint_modes")
