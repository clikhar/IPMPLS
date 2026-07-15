"""Persistence models; kept separate from API schemas."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from crtnm.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StationModel(Base):
    __tablename__ = "stations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    division: Mapped[str] = mapped_column(String(120), index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeviceModel(Base):
    __tablename__ = "devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    device_type: Mapped[str] = mapped_column(String(30))
    vendor: Mapped[str] = mapped_column(String(60))
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    management_ip: Mapped[str] = mapped_column(String(45), unique=True)
    protocol: Mapped[str] = mapped_column(String(10), default="ssh")
    connection_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    credential_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConfigurationBackupModel(Base):
    """Immutable sanitized running-configuration snapshot."""

    __tablename__ = "configuration_backups"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(30), default="running")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecoverySimulationModel(Base):
    """Audit record for an explicitly non-executing recovery simulation."""

    __tablename__ = "recovery_simulations"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    failure_type: Mapped[str] = mapped_column(String(40))
    backup_id: Mapped[int | None] = mapped_column(ForeignKey("configuration_backups.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="simulated")
    execution_plan: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NetworkChangePlanModel(Base):
    """A validated command preview that is deliberately not executable yet."""

    __tablename__ = "network_change_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    operation: Mapped[str] = mapped_column(String(50), index=True)
    commands: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="preview")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HealthSnapshotModel(Base):
    __tablename__ = "health_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    cpu_percent: Mapped[float | None] = mapped_column(nullable=True)
    memory_percent: Mapped[float | None] = mapped_column(nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(nullable=True)
    reachable: Mapped[bool] = mapped_column(default=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterfaceStatusModel(Base):
    __tablename__ = "interface_statuses"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    interface_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LldpNeighborModel(Base):
    __tablename__ = "lldp_neighbors"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    local_interface: Mapped[str] = mapped_column(String(80))
    neighbor_name: Mapped[str] = mapped_column(String(120))
    neighbor_interface: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AlarmModel(Base):
    __tablename__ = "alarms"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    metric: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
