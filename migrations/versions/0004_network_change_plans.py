"""Store non-executing network change previews."""
from alembic import op
import sqlalchemy as sa

revision = "0004_network_change_plans"
down_revision = "0003_configuration_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("network_change_plans", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("operation", sa.String(50), nullable=False), sa.Column("commands", sa.Text(), nullable=False), sa.Column("summary", sa.String(255), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("created_by", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("network_change_plans")
