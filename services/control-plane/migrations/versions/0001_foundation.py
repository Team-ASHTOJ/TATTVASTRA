"""Migration baseline only. Domain persistence is not implemented in P0."""

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reserve the schema migration baseline without inventing domain storage."""


def downgrade() -> None:
    """No domain tables exist at the foundation baseline."""
