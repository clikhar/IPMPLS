"""Initial CRTNM inventory and audit schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(80), nullable=False, unique=True), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("stations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("division", sa.String(120), nullable=False), sa.Column("location", sa.String(255)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("devices", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id"), nullable=False), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("device_type", sa.String(30), nullable=False), sa.Column("vendor", sa.String(60), nullable=False), sa.Column("model", sa.String(120)), sa.Column("management_ip", sa.String(45), nullable=False, unique=True), sa.Column("protocol", sa.String(10), nullable=False), sa.Column("credential_ciphertext", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor", sa.String(80), nullable=False), sa.Column("action", sa.String(120), nullable=False), sa.Column("target", sa.String(255), nullable=False), sa.Column("detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("devices")
    op.drop_table("stations")
    op.drop_table("users")
