"""Create immutable configuration backups and recovery simulation records."""
from alembic import op
import sqlalchemy as sa

revision = "0003_configuration_recovery"
down_revision = "0002_connection_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("configuration_backups", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("source", sa.String(30), nullable=False), sa.Column("created_by", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("recovery_simulations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("failure_type", sa.String(40), nullable=False), sa.Column("backup_id", sa.Integer(), sa.ForeignKey("configuration_backups.id")), sa.Column("status", sa.String(30), nullable=False), sa.Column("execution_plan", sa.Text(), nullable=False), sa.Column("created_by", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("recovery_simulations")
    op.drop_table("configuration_backups")
