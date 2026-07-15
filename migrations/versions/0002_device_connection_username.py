"""Add a non-secret device connection username."""
from alembic import op
import sqlalchemy as sa

revision = "0002_connection_username"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("connection_username", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "connection_username")
