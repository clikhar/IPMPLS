"""Persist monitoring state, LLDP neighbors, and alarms."""
from alembic import op
import sqlalchemy as sa

revision = "0005_monitoring"
down_revision = "0004_network_change_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("health_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("cpu_percent", sa.Float()), sa.Column("memory_percent", sa.Float()), sa.Column("temperature_celsius", sa.Float()), sa.Column("reachable", sa.Boolean(), nullable=False), sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("interface_statuses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("interface_name", sa.String(80), nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("description", sa.String(255)))
    op.create_table("lldp_neighbors", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("local_interface", sa.String(80), nullable=False), sa.Column("neighbor_name", sa.String(120), nullable=False), sa.Column("neighbor_interface", sa.String(80)))
    op.create_table("alarms", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False), sa.Column("metric", sa.String(40), nullable=False), sa.Column("severity", sa.String(20), nullable=False), sa.Column("message", sa.String(255), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("alarms"); op.drop_table("lldp_neighbors"); op.drop_table("interface_statuses"); op.drop_table("health_snapshots")
