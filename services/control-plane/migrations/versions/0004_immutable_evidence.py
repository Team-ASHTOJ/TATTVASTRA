"""Protect append-only evidence and audit records in PostgreSQL."""

from alembic import op

revision = "0004_immutable_evidence"
down_revision = "44b0cc037309"
branch_labels = None
depends_on = None

TABLES = (
    "audit_events",
    "event_outbox",
    "observations",
    "script_versions",
    "evidence_manifests",
    "agent_receipts",
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""CREATE FUNCTION jocky_reject_evidence_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'JOCKY immutable record: %', TG_TABLE_NAME; END;
        $$ LANGUAGE plpgsql""")
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION jocky_reject_evidence_mutation()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
    op.execute("DROP FUNCTION jocky_reject_evidence_mutation()")
