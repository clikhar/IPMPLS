"""SQLAlchemy ORM models for CRTNM."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, relationship, validates
import uuid
import hashlib

from crtnm.domain.enums import (
    AlarmSeverity,
    AlarmStatus,
    ConfigSourceType,
    DeviceStatus,
    DeviceType,
    DiscoveryStatus,
    EventType,
    InterfaceStatus,
    JobStatus,
    NotificationChannelType,
    ProtocolType,
    SnmpV3AuthProtocol,
    SnmpV3PrivProtocol,
    SnmpVersion,
    TopologyLayer,
    UserRole,
)
from crtnm.infrastructure.database import Base


def _utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.utcnow()


class BaseModel(Base):
    """Base model with common fields."""
    
    __abstract__ = True
    
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), 
        default=_utc_now, 
        server_default="CURRENT_TIMESTAMP"
    )
    updated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        default=_utc_now, 
        onupdate=_utc_now
    )


# ============================================================================
# RBAC Models
# ============================================================================

class Permission(BaseModel):
    """Granular permission definitions."""
    
    __tablename__ = "permissions"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = Column(String(255))
    resource: Mapped[str] = Column(String(50), nullable=False, index=True)  # device, config, alarm, user, etc.
    action: Mapped[str] = Column(String(50), nullable=False, index=True)  # read, create, update, delete, execute
    
    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions",
        back_populates="permissions"
    )


class Role(BaseModel):
    """Role definitions for RBAC."""
    
    __tablename__ = "roles"
    
    name: Mapped[str] = Column(Enum(UserRole), nullable=False, unique=True)
    description: Mapped[Optional[str]] = Column(String(255))
    is_system: Mapped[bool] = Column(Boolean, default=False)  # System roles cannot be deleted
    
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions",
        back_populates="roles"
    )
    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        back_populates="roles"
    )


class RolePermission(Base):
    """Association table for role-permission many-to-many."""
    
    __tablename__ = "role_permissions"
    
    role_id: Mapped[int] = Column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = Column(ForeignKey("permissions.id"), primary_key=True)
    
    __table_args__ = (
        Index("idx_role_permission", "role_id", "permission_id"),
    )


class User(BaseModel):
    """User accounts with authentication."""
    
    __tablename__ = "users"
    
    username: Mapped[str] = Column(String(80), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = Column(String(256), nullable=False)
    email: Mapped[Optional[str]] = Column(String(120), unique=True, index=True)
    full_name: Mapped[Optional[str]] = Column(String(120))
    is_active: Mapped[bool] = Column(Boolean, default=True)
    is_superuser: Mapped[bool] = Column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = Column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    mfa_enabled: Mapped[bool] = Column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = Column(String(256))
    
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class UserRoleLink(Base):
    """Association table for user-role many-to-many."""
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[int] = Column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = Column(ForeignKey("roles.id"), primary_key=True)
    
    __table_args__ = (
        Index("idx_user_role", "user_id", "role_id"),
    )


class UserSession(BaseModel):
    """User session tracking."""
    
    __tablename__ = "user_sessions"
    
    user_id: Mapped[int] = Column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = Column(String(256), nullable=False, unique=True)
    ip_address: Mapped[Optional[str]] = Column(String(45))
    user_agent: Mapped[Optional[str]] = Column(String(255))
    expires_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = Column(Boolean, default=False)
    
    user: Mapped["User"] = relationship(back_populates="sessions")


# ============================================================================
# Organizational Hierarchy Models
# ============================================================================

class Organization(BaseModel):
    """Top-level organization."""
    
    __tablename__ = "organizations"
    
    name: Mapped[str] = Column(String(120), nullable=False, unique=True)
    description: Mapped[Optional[str]] = Column(Text)
    contact_email: Mapped[Optional[str]] = Column(String(120))
    contact_phone: Mapped[Optional[str]] = Column(String(20))
    
    zones: Mapped[list["Zone"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Zone(BaseModel):
    """Geographic or administrative zone."""
    
    __tablename__ = "zones"
    
    organization_id: Mapped[int] = Column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_zone_org_name"),
        Index("idx_zone_name", "name"),
    )
    
    organization: Mapped["Organization"] = relationship(back_populates="zones")
    divisions: Mapped[list["Division"]] = relationship(back_populates="zone", cascade="all, delete-orphan")


class Division(BaseModel):
    """Administrative division within a zone."""
    
    __tablename__ = "divisions"
    
    zone_id: Mapped[int] = Column(ForeignKey("zones.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    
    __table_args__ = (
        UniqueConstraint("zone_id", "name", name="uq_division_zone_name"),
        Index("idx_division_name", "name"),
    )
    
    zone: Mapped["Zone"] = relationship(back_populates="divisions")
    sections: Mapped[list["Section"]] = relationship(back_populates="division", cascade="all, delete-orphan")


class Section(BaseModel):
    """Section within a division."""
    
    __tablename__ = "sections"
    
    division_id: Mapped[int] = Column(ForeignKey("divisions.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    
    __table_args__ = (
        UniqueConstraint("division_id", "name", name="uq_section_division_name"),
        Index("idx_section_name", "name"),
    )
    
    division: Mapped["Division"] = relationship(back_populates="sections")
    stations: Mapped[list["Station"]] = relationship(back_populates="section", cascade="all, delete-orphan")


class Station(BaseModel):
    """Station/site location (e.g., railway station)."""
    
    __tablename__ = "stations"
    
    section_id: Mapped[int] = Column(ForeignKey("sections.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False, index=True)
    code: Mapped[Optional[str]] = Column(String(20), unique=True, index=True)
    latitude: Mapped[Optional[float]] = Column(Float)
    longitude: Mapped[Optional[float]] = Column(Float)
    address: Mapped[Optional[str]] = Column(String(255))
    type: Mapped[Optional[str]] = Column(String(50))  # junction, terminal, halt, etc.
    
    __table_args__ = (
        UniqueConstraint("section_id", "name", name="uq_station_section_name"),
    )
    
    section: Mapped["Section"] = relationship(back_populates="stations")
    sites: Mapped[list["Site"]] = relationship(back_populates="station", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="station")


class Site(BaseModel):
    """Physical site within a station (e.g., telecom room, data center)."""
    
    __tablename__ = "sites"
    
    station_id: Mapped[int] = Column(ForeignKey("stations.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    type: Mapped[Optional[str]] = Column(String(50))  # telecom_room, data_center, outdoor, etc.
    building: Mapped[Optional[str]] = Column(String(120))
    floor: Mapped[Optional[str]] = Column(String(20))
    room: Mapped[Optional[str]] = Column(String(50))
    rack_count: Mapped[Optional[int]] = Column(Integer)
    
    __table_args__ = (
        UniqueConstraint("station_id", "name", name="uq_site_station_name"),
    )
    
    station: Mapped["Station"] = relationship(back_populates="sites")
    devices: Mapped[list["Device"]] = relationship(back_populates="site")


# ============================================================================
# Device Inventory Models
# ============================================================================

class Vendor(BaseModel):
    """Device vendor/manufacturer."""
    
    __tablename__ = "vendors"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    display_name: Mapped[Optional[str]] = Column(String(120))
    support_url: Mapped[Optional[str]] = Column(String(255))
    notes: Mapped[Optional[str]] = Column(Text)
    
    models: Mapped[list["DeviceModel"]] = relationship(back_populates="vendor")


class DeviceModel(BaseModel):
    """Device model definitions."""
    
    __tablename__ = "device_models"
    
    vendor_id: Mapped[int] = Column(ForeignKey("vendors.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(120), nullable=False)
    part_number: Mapped[Optional[str]] = Column(String(100))
    device_type: Mapped[Optional[DeviceType]] = Column(Enum(DeviceType))
    end_of_life: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    specs: Mapped[Optional[dict]] = Column(JSONB)  # Storage capacity, port count, etc.
    
    __table_args__ = (
        UniqueConstraint("vendor_id", "name", name="uq_model_vendor_name"),
        Index("idx_model_name", "name"),
    )
    
    vendor: Mapped["Vendor"] = relationship(back_populates="models")
    devices: Mapped[list["Device"]] = relationship(back_populates="model")


class DeviceCredential(BaseModel):
    """Encrypted device credentials."""
    
    __tablename__ = "device_credentials"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = Column(String(255))
    
    # SNMP credentials
    snmp_version: Mapped[Optional[SnmpVersion]] = Column(Enum(SnmpVersion))
    snmp_community: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    snmp_v3_username: Mapped[Optional[str]] = Column(String(100))
    snmp_v3_auth_protocol: Mapped[Optional[SnmpV3AuthProtocol]] = Column(Enum(SnmpV3AuthProtocol))
    snmp_v3_auth_password: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    snmp_v3_priv_protocol: Mapped[Optional[SnmpV3PrivProtocol]] = Column(Enum(SnmpV3PrivProtocol))
    snmp_v3_priv_password: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    
    # SSH/Telnet credentials
    ssh_username: Mapped[Optional[str]] = Column(String(100))
    ssh_password: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    ssh_key: Mapped[Optional[str]] = Column(Text)  # Encrypted private key
    enable_password: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    telnet_username: Mapped[Optional[str]] = Column(String(100))
    telnet_password: Mapped[Optional[str]] = Column(String(256))  # Encrypted
    
    # Encryption metadata
    encryption_algorithm: Mapped[Optional[str]] = Column(String(50))
    encryption_key_id: Mapped[Optional[str]] = Column(String(100))
    
    devices: Mapped[list["Device"]] = relationship(back_populates="credentials")


class DeviceGroup(BaseModel):
    """Logical grouping of devices."""
    
    __tablename__ = "device_groups"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = Column(Text)
    group_type: Mapped[Optional[str]] = Column(String(50))  # functional, geographic, custom
    
    devices: Mapped[list["Device"]] = relationship(
        secondary="device_group_members",
        back_populates="groups"
    )


class DeviceGroupMember(Base):
    """Association table for device-group many-to-many."""
    
    __tablename__ = "device_group_members"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), primary_key=True)
    group_id: Mapped[int] = Column(ForeignKey("device_groups.id"), primary_key=True)
    added_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    __table_args__ = (
        Index("idx_device_group", "device_id", "group_id"),
    )


class Device(BaseModel):
    """Network device inventory."""
    
    __tablename__ = "devices"
    
    # Basic identification
    name: Mapped[str] = Column(String(120), nullable=False, unique=True, index=True)
    hostname: Mapped[Optional[str]] = Column(String(120), index=True)
    
    # Location hierarchy
    station_id: Mapped[Optional[int]] = Column(ForeignKey("stations.id"), index=True)
    site_id: Mapped[Optional[int]] = Column(ForeignKey("sites.id"), index=True)
    
    # Device type
    device_type: Mapped[DeviceType] = Column(Enum(DeviceType), nullable=False, index=True)
    vendor_id: Mapped[Optional[int]] = Column(ForeignKey("vendors.id"), index=True)
    model_id: Mapped[Optional[int]] = Column(ForeignKey("device_models.id"), index=True)
    serial_number: Mapped[Optional[str]] = Column(String(100), index=True)
    firmware_version: Mapped[Optional[str]] = Column(String(100))
    hardware_version: Mapped[Optional[str]] = Column(String(50))
    
    # Network configuration
    management_ip: Mapped[str] = Column(String(45), nullable=False, unique=True, index=True)
    management_port: Mapped[Optional[int]] = Column(Integer)
    connection_username: Mapped[Optional[str]] = Column(String(80))
    protocol: Mapped[ProtocolType] = Column(Enum(ProtocolType), default=ProtocolType.SSH)
    
    # Credentials reference
    credential_id: Mapped[Optional[int]] = Column(ForeignKey("device_credentials.id"), index=True)
    
    # Physical location
    latitude: Mapped[Optional[float]] = Column(Float)
    longitude: Mapped[Optional[float]] = Column(Float)
    rack: Mapped[Optional[str]] = Column(String(50))
    rack_position: Mapped[Optional[int]] = Column(Integer)
    height_units: Mapped[Optional[int]] = Column(Integer)  # Rack units
    
    # Monitoring configuration
    polling_interval: Mapped[int] = Column(Integer, default=300)  # seconds
    polling_timeout: Mapped[int] = Column(Integer, default=30)  # seconds
    polling_retries: Mapped[int] = Column(Integer, default=3)
    is_monitored: Mapped[bool] = Column(Boolean, default=True)
    
    # Status tracking
    status: Mapped[DeviceStatus] = Column(Enum(DeviceStatus), default=DeviceStatus.UNKNOWN)
    availability: Mapped[Optional[float]] = Column(Float)  # Percentage
    last_poll: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    last_seen: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    
    # Metadata
    description: Mapped[Optional[str]] = Column(Text)
    tags: Mapped[Optional[dict]] = Column(JSONB)
    custom_fields: Mapped[Optional[dict]] = Column(JSONB)
    
    # Relationships
    station: Mapped["Station"] = relationship(back_populates="devices", foreign_keys=[station_id])
    site: Mapped["Site"] = relationship(back_populates="devices", foreign_keys=[site_id])
    vendor: Mapped["Vendor"] = relationship(back_populates="devices")
    model: Mapped["DeviceModel"] = relationship(back_populates="devices")
    credentials: Mapped["DeviceCredential"] = relationship(back_populates="devices")
    groups: Mapped[list["DeviceGroup"]] = relationship(
        secondary="device_group_members",
        back_populates="devices"
    )
    
    interfaces: Mapped[list["Interface"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    metrics: Mapped[list["DeviceMetric"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    alarms: Mapped[list["Alarm"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    configurations: Mapped[list["ConfigurationBackup"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    traps: Mapped[list["SnmpTrap"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    mac_addresses: Mapped[list["MacAddressEntry"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    arp_entries: Mapped[list["ArpEntry"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    routing_neighbors: Mapped[list["RoutingNeighbor"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    bgp_neighbors: Mapped[list["BgpNeighbor"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    ospf_neighbors: Mapped[list["OspfNeighbor"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    isis_neighbors: Mapped[list["IsisNeighbor"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    mpls_lsps: Mapped[list["MplsLsp"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    vlans: Mapped[list["Vlan"]] = relationship(
        back_populates="device", 
        cascade="all, delete-orphan"
    )
    topology_links: Mapped[list["TopologyLink"]] = relationship(
        foreign_keys="TopologyLink.source_device_id",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_device_location", "station_id", "site_id"),
        Index("idx_device_status", "status", "is_monitored"),
    )
    
    @validates('management_ip')
    def validate_ip(self, key, value):
        """Basic IP validation."""
        if not value:
            raise ValueError("Management IP is required")
        return value.strip()


# ============================================================================
# Interface Models
# ============================================================================

class Interface(BaseModel):
    """Network interface on a device."""
    
    __tablename__ = "interfaces"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    name: Mapped[str] = Column(String(80), nullable=False, index=True)
    description: Mapped[Optional[str]] = Column(String(255))
    
    # Interface properties
    if_index: Mapped[Optional[int]] = Column(Integer)
    type: Mapped[Optional[str]] = Column(String(50))  # ethernet, vlan, tunnel, etc.
    speed: Mapped[Optional[int]] = Column(Integer)  # bits per second
    mtu: Mapped[Optional[int]] = Column(Integer)
    mac_address: Mapped[Optional[str]] = Column(String(17))
    
    # Status
    admin_status: Mapped[InterfaceStatus] = Column(Enum(InterfaceStatus), default=InterfaceStatus.UNKNOWN)
    oper_status: Mapped[InterfaceStatus] = Column(Enum(InterfaceStatus), default=InterfaceStatus.UNKNOWN)
    last_change: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    
    # Layer 2/Layer 3
    vlan_id: Mapped[Optional[int]] = Column(Integer)
    ip_address: Mapped[Optional[str]] = Column(String(45))
    subnet_mask: Mapped[Optional[str]] = Column(String(15))
    ipv6_address: Mapped[Optional[str]] = Column(String(45))
    
    # Optical/PoE
    sfp_present: Mapped[Optional[bool]] = Column(Boolean)
    sfp_type: Mapped[Optional[str]] = Column(String(50))
    tx_power: Mapped[Optional[float]] = Column(Float)  # dBm
    rx_power: Mapped[Optional[float]] = Column(Float)  # dBm
    temperature: Mapped[Optional[float]] = Column(Float)  # Celsius
    voltage: Mapped[Optional[float]] = Column(Float)  # Volts
    bias_current: Mapped[Optional[float]] = Column(Float)  # mA
    poe_enabled: Mapped[Optional[bool]] = Column(Boolean)
    poe_power: Mapped[Optional[float]] = Column(Float)  # Watts
    poe_voltage: Mapped[Optional[float]] = Column(Float)  # Volts
    poe_current: Mapped[Optional[float]] = Column(Float)  # Amps
    
    # Statistics (cached from last poll)
    in_octets: Mapped[Optional[int]] = Column(Integer)
    out_octets: Mapped[Optional[int]] = Column(Integer)
    in_packets: Mapped[Optional[int]] = Column(Integer)
    out_packets: Mapped[Optional[int]] = Column(Integer)
    in_errors: Mapped[Optional[int]] = Column(Integer)
    out_errors: Mapped[Optional[int]] = Column(Integer)
    in_discards: Mapped[Optional[int]] = Column(Integer)
    out_discards: Mapped[Optional[int]] = Column(Integer)
    crc_errors: Mapped[Optional[int]] = Column(Integer)
    
    device: Mapped["Device"] = relationship(back_populates="interfaces")
    metrics: Mapped[list["InterfaceMetric"]] = relationship(
        back_populates="interface", 
        cascade="all, delete-orphan"
    )
    alarms: Mapped[list["Alarm"]] = relationship(
        back_populates="interface", 
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        UniqueConstraint("device_id", "name", name="uq_interface_device_name"),
        Index("idx_interface_oper_status", "oper_status"),
    )


# ============================================================================
# Time-Series Metrics Models
# ============================================================================

class DeviceMetric(BaseModel):
    """Device-level performance metrics."""
    
    __tablename__ = "device_metrics"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, index=True, default=_utc_now)
    
    # Resource utilization
    cpu_usage: Mapped[Optional[float]] = Column(Float)  # Percentage
    memory_usage: Mapped[Optional[float]] = Column(Float)  # Percentage
    memory_total: Mapped[Optional[int]] = Column(Integer)  # Bytes
    memory_used: Mapped[Optional[int]] = Column(Integer)  # Bytes
    
    # Environmental
    temperature: Mapped[Optional[float]] = Column(Float)  # Celsius
    fan_status: Mapped[Optional[str]] = Column(String(50))  # ok, warning, critical
    power_supply_status: Mapped[Optional[str]] = Column(String(50))
    
    # System
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    processes: Mapped[Optional[int]] = Column(Integer)
    
    # Custom OIDs
    custom_metrics: Mapped[Optional[dict]] = Column(JSONB)
    
    device: Mapped["Device"] = relationship(back_populates="metrics")
    
    __table_args__ = (
        Index("idx_device_metric_ts", "device_id", "timestamp"),
    )


class InterfaceMetric(BaseModel):
    """Interface-level performance metrics."""
    
    __tablename__ = "interface_metrics"
    
    interface_id: Mapped[int] = Column(ForeignKey("interfaces.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, index=True, default=_utc_now)
    
    # Traffic counters
    in_octets: Mapped[Optional[int]] = Column(Integer)
    out_octets: Mapped[Optional[int]] = Column(Integer)
    in_packets: Mapped[Optional[int]] = Column(Integer)
    out_packets: Mapped[Optional[int]] = Column(Integer)
    in_broadcast: Mapped[Optional[int]] = Column(Integer)
    out_broadcast: Mapped[Optional[int]] = Column(Integer)
    in_multicast: Mapped[Optional[int]] = Column(Integer)
    out_multicast: Mapped[Optional[int]] = Column(Integer)
    
    # Error counters
    in_errors: Mapped[Optional[int]] = Column(Integer)
    out_errors: Mapped[Optional[int]] = Column(Integer)
    in_discards: Mapped[Optional[int]] = Column(Integer)
    out_discards: Mapped[Optional[int]] = Column(Integer)
    crc_errors: Mapped[Optional[int]] = Column(Integer)
    
    # Calculated
    in_rate_bps: Mapped[Optional[float]] = Column(Float)  # Bits per second
    out_rate_bps: Mapped[Optional[float]] = Column(Float)
    in_utilization: Mapped[Optional[float]] = Column(Float)  # Percentage
    out_utilization: Mapped[Optional[float]] = Column(Float)
    
    interface: Mapped["Interface"] = relationship(back_populates="metrics")
    
    __table_args__ = (
        Index("idx_interface_metric_ts", "interface_id", "timestamp"),
    )


# ============================================================================
# Alarm & Event Models
# ============================================================================

class Alarm(BaseModel):
    """Active alarm with lifecycle management."""
    
    __tablename__ = "alarms"
    
    # Identification
    title: Mapped[str] = Column(String(200), nullable=False)
    message: Mapped[Optional[str]] = Column(Text)
    event_type: Mapped[EventType] = Column(Enum(EventType), nullable=False, index=True)
    
    # Severity & Status
    severity: Mapped[AlarmSeverity] = Column(Enum(AlarmSeverity), nullable=False, index=True)
    status: Mapped[AlarmStatus] = Column(Enum(AlarmStatus), default=AlarmStatus.ACTIVE, index=True)
    
    # Target
    device_id: Mapped[Optional[int]] = Column(ForeignKey("devices.id"), index=True)
    interface_id: Mapped[Optional[int]] = Column(ForeignKey("interfaces.id"), index=True)
    
    # Root cause analysis
    root_cause_alarm_id: Mapped[Optional[int]] = Column(ForeignKey("alarms.id"), index=True)
    is_root_cause: Mapped[bool] = Column(Boolean, default=False)
    
    # Lifecycle
    first_occurred: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    last_occurred: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    occurrence_count: Mapped[int] = Column(Integer, default=1)
    
    acknowledged_by: Mapped[Optional[int]] = Column(ForeignKey("users.id"))
    acknowledged_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    acknowledged_note: Mapped[Optional[str]] = Column(Text)
    
    resolved_by: Mapped[Optional[int]] = Column(ForeignKey("users.id"))
    resolved_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    resolution_note: Mapped[Optional[str]] = Column(Text)
    
    suppressed_until: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    suppression_reason: Mapped[Optional[str]] = Column(String(255))
    
    # Context
    additional_info: Mapped[Optional[dict]] = Column(JSONB)
    correlated_events: Mapped[Optional[list]] = Column(JSONB)
    
    # Relationships
    device: Mapped["Device"] = relationship(back_populates="alarms", foreign_keys=[device_id])
    interface: Mapped["Interface"] = relationship(back_populates="alarms", foreign_keys=[interface_id])
    root_cause_alarm: Mapped[Optional["Alarm"]] = relationship(
        back_populates="child_alarms",
        remote_side="Alarm.id",
        foreign_keys=[root_cause_alarm_id]
    )
    child_alarms: Mapped[list["Alarm"]] = relationship(
        back_populates="root_cause_alarm",
        foreign_keys=[root_cause_alarm_id]
    )
    acknowledger: Mapped["User"] = relationship(
        foreign_keys=[acknowledged_by],
        backref="acknowledged_alarms"
    )
    resolver: Mapped["User"] = relationship(
        foreign_keys=[resolved_by],
        backref="resolved_alarms"
    )
    
    __table_args__ = (
        Index("idx_alarm_active", "status", "severity"),
        Index("idx_alarm_device_status", "device_id", "status"),
    )


class Event(BaseModel):
    """Raw events from various sources."""
    
    __tablename__ = "events"
    
    # Source
    source_type: Mapped[str] = Column(String(50), nullable=False, index=True)  # snmp_trap, syslog, polling, system
    source_ip: Mapped[Optional[str]] = Column(String(45), index=True)
    
    # Identification
    event_type: Mapped[EventType] = Column(Enum(EventType), nullable=False, index=True)
    raw_data: Mapped[Optional[dict]] = Column(JSONB)
    
    # Target
    device_id: Mapped[Optional[int]] = Column(ForeignKey("devices.id"), index=True)
    interface_id: Mapped[Optional[int]] = Column(ForeignKey("interfaces.id"), index=True)
    
    # Content
    severity: Mapped[AlarmSeverity] = Column(Enum(AlarmSeverity), default=AlarmSeverity.INFO)
    message: Mapped[str] = Column(Text, nullable=False)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, index=True, default=_utc_now)
    
    # Processing
    processed: Mapped[bool] = Column(Boolean, default=False)
    alarm_id: Mapped[Optional[int]] = Column(ForeignKey("alarms.id"), index=True)
    
    device: Mapped["Device"] = relationship(back_populates="events")
    interface: Mapped["Interface"] = relationship(back_populates="events")
    alarm: Mapped["Alarm"] = relationship(back_populates="events")


# ============================================================================
# Configuration Management Models
# ============================================================================

class ConfigurationBackup(BaseModel):
    """Device configuration backup."""
    
    __tablename__ = "configuration_backups"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    version: Mapped[int] = Column(Integer, default=1)
    
    content: Mapped[str] = Column(Text, nullable=False)
    checksum: Mapped[str] = Column(String(64), nullable=False)  # SHA-256
    size_bytes: Mapped[Optional[int]] = Column(Integer)
    
    source_type: Mapped[ConfigSourceType] = Column(Enum(ConfigSourceType), default=ConfigSourceType.RUNNING)
    
    created_by: Mapped[str] = Column(String(80), nullable=False)
    backup_method: Mapped[Optional[str]] = Column(String(50))  # ssh, telnet, netconf, scp
    compression: Mapped[Optional[str]] = Column(String(20))  # gzip, none
    
    notes: Mapped[Optional[str]] = Column(Text)
    is_baseline: Mapped[bool] = Column(Boolean, default=False)
    
    device: Mapped["Device"] = relationship(back_populates="configurations")
    change_jobs: Mapped[list["ConfigurationJob"]] = relationship(
        back_populates="backup",
        foreign_keys="ConfigurationJob.backup_id"
    )
    
    __table_args__ = (
        UniqueConstraint("device_id", "version", name="uq_config_device_version"),
        Index("idx_config_device_created", "device_id", "created_at"),
    )


class ConfigurationJob(BaseModel):
    """Configuration deployment job."""
    
    __tablename__ = "configuration_jobs"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    backup_id: Mapped[Optional[int]] = Column(ForeignKey("configuration_backups.id"), index=True)
    
    job_type: Mapped[str] = Column(String(50), nullable=False)  # deploy, restore, compare
    commands: Mapped[list] = Column(JSONB, nullable=False)
    
    status: Mapped[JobStatus] = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    scheduled_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    
    result: Mapped[Optional[dict]] = Column(JSONB)
    error_message: Mapped[Optional[str]] = Column(Text)
    
    created_by: Mapped[str] = Column(String(80), nullable=False)
    approved_by: Mapped[Optional[str]] = Column(String(80))
    approved_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    
    rollback_job_id: Mapped[Optional[int]] = Column(ForeignKey("configuration_jobs.id"))
    
    backup: Mapped["ConfigurationBackup"] = relationship(back_populates="change_jobs")
    rollback_job: Mapped[Optional["ConfigurationJob"]] = relationship(
        back_populates="rollback_job",
        remote_side="ConfigurationJob.id",
        foreign_keys=[rollback_job_id]
    )


# ============================================================================
# SNMP Trap & Syslog Models
# ============================================================================

class SnmpTrap(BaseModel):
    """Received SNMP trap."""
    
    __tablename__ = "snmp_traps"
    
    source_device_id: Mapped[Optional[int]] = Column(ForeignKey("devices.id"), index=True)
    source_ip: Mapped[str] = Column(String(45), nullable=False, index=True)
    
    enterprise_oid: Mapped[Optional[str]] = Column(String(128))
    generic_trap_type: Mapped[Optional[int]] = Column(Integer)
    specific_trap_code: Mapped[Optional[int]] = Column(Integer)
    trap_oid: Mapped[Optional[str]] = Column(String(128), index=True)
    
    varbinds: Mapped[Optional[dict]] = Column(JSONB)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, index=True, default=_utc_now)
    received_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    
    processed: Mapped[bool] = Column(Boolean, default=False)
    alarm_id: Mapped[Optional[int]] = Column(ForeignKey("alarms.id"), index=True)
    
    device: Mapped["Device"] = relationship(back_populates="traps", foreign_keys=[source_device_id])


class SyslogMessage(BaseModel):
    """Received syslog message."""
    
    __tablename__ = "syslog_messages"
    
    source_device_id: Mapped[Optional[int]] = Column(ForeignKey("devices.id"), index=True)
    source_ip: Mapped[str] = Column(String(45), nullable=False, index=True)
    hostname: Mapped[Optional[str]] = Column(String(120), index=True)
    
    facility: Mapped[Optional[int]] = Column(Integer)
    severity: Mapped[Optional[int]] = Column(Integer)
    priority: Mapped[Optional[int]] = Column(Integer)
    
    message: Mapped[str] = Column(Text, nullable=False)
    structured_data: Mapped[Optional[dict]] = Column(JSONB)
    
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, index=True, default=_utc_now)
    received_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    
    processed: Mapped[bool] = Column(Boolean, default=False)
    event_id: Mapped[Optional[int]] = Column(ForeignKey("events.id"), index=True)
    alarm_id: Mapped[Optional[int]] = Column(ForeignKey("alarms.id"), index=True)
    
    device: Mapped["Device"] = relationship(foreign_keys=[source_device_id])


# ============================================================================
# Topology Models
# ============================================================================

class TopologyLink(BaseModel):
    """Discovered link between devices."""
    
    __tablename__ = "topology_links"
    
    source_device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    source_interface: Mapped[Optional[str]] = Column(String(80))
    
    target_device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    target_interface: Mapped[Optional[str]] = Column(String(80))
    
    discovery_protocol: Mapped[Optional[str]] = Column(String(20))  # lldp, cdp, manual
    link_type: Mapped[TopologyLayer] = Column(Enum(TopologyLayer), default=TopologyLayer.LAYER2)
    
    is_active: Mapped[bool] = Column(Boolean, default=True)
    bandwidth: Mapped[Optional[int]] = Column(Integer)  # bits per second
    latency_ms: Mapped[Optional[float]] = Column(Float)
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    last_verified: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    
    source_device: Mapped["Device"] = relationship(
        foreign_keys=[source_device_id],
        backref="outgoing_links"
    )
    target_device: Mapped["Device"] = relationship(
        foreign_keys=[target_device_id],
        backref="incoming_links"
    )
    
    __table_args__ = (
        Index("idx_topology_link_pair", "source_device_id", "target_device_id"),
    )


class Vlan(BaseModel):
    """VLAN configuration on a device."""
    
    __tablename__ = "vlans"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    vlan_id: Mapped[int] = Column(Integer, nullable=False)
    name: Mapped[Optional[str]] = Column(String(100))
    
    status: Mapped[Optional[str]] = Column(String(20))  # active, suspended
    ports: Mapped[Optional[list]] = Column(JSONB)  # List of interface names
    
    device: Mapped["Device"] = relationship(back_populates="vlans")
    
    __table_args__ = (
        UniqueConstraint("device_id", "vlan_id", name="uq_vlan_device_vlan"),
    )


class MacAddressEntry(BaseModel):
    """MAC address table entry."""
    
    __tablename__ = "mac_addresses"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    mac_address: Mapped[str] = Column(String(17), nullable=False, index=True)
    interface: Mapped[Optional[str]] = Column(String(80))
    vlan_id: Mapped[Optional[int]] = Column(Integer)
    entry_type: Mapped[Optional[str]] = Column(String(20))  # dynamic, static, secure
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="mac_addresses")
    
    __table_args__ = (
        Index("idx_mac_device_mac", "device_id", "mac_address"),
    )


class ArpEntry(BaseModel):
    """ARP table entry."""
    
    __tablename__ = "arp_entries"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    ip_address: Mapped[str] = Column(String(45), nullable=False, index=True)
    mac_address: Mapped[Optional[str]] = Column(String(17))
    interface: Mapped[Optional[str]] = Column(String(80))
    entry_type: Mapped[Optional[str]] = Column(String(20))  # dynamic, static, incomplete
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="arp_entries")


class RoutingNeighbor(BaseModel):
    """Generic routing neighbor."""
    
    __tablename__ = "routing_neighbors"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    protocol: Mapped[str] = Column(String(20), nullable=False, index=True)  # bgp, ospf, isis, static
    neighbor_address: Mapped[str] = Column(String(45), nullable=False)
    local_interface: Mapped[Optional[str]] = Column(String(80))
    
    state: Mapped[Optional[str]] = Column(String(50))
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    
    additional_info: Mapped[Optional[dict]] = Column(JSONB)
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="routing_neighbors")


class BgpNeighbor(BaseModel):
    """BGP neighbor information."""
    
    __tablename__ = "bgp_neighbors"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    neighbor_ip: Mapped[str] = Column(String(45), nullable=False)
    remote_as: Mapped[int] = Column(Integer, nullable=False)
    local_as: Mapped[Optional[int]] = Column(Integer)
    
    state: Mapped[str] = Column(String(50), nullable=False)  # idle, connect, active, opensent, openconfirm, established
    admin_state: Mapped[Optional[str]] = Column(String(20))  # enabled, disabled
    
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    prefixes_received: Mapped[Optional[int]] = Column(Integer)
    prefixes_sent: Mapped[Optional[int]] = Column(Integer)
    
    local_ip: Mapped[Optional[str]] = Column(String(45))
    local_interface: Mapped[Optional[str]] = Column(String(80))
    
    last_error: Mapped[Optional[str]] = Column(String(255))
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="bgp_neighbors")
    
    __table_args__ = (
        UniqueConstraint("device_id", "neighbor_ip", name="uq_bgp_device_neighbor"),
    )


class OspfNeighbor(BaseModel):
    """OSPF neighbor information."""
    
    __tablename__ = "ospf_neighbors"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    neighbor_ip: Mapped[str] = Column(String(45), nullable=False)
    neighbor_id: Mapped[Optional[str]] = Column(String(15))  # Router ID
    area: Mapped[Optional[str]] = Column(String(15))
    
    state: Mapped[str] = Column(String(50), nullable=False)  # down, init, 2-way, exstart, exchange, loading, full
    priority: Mapped[Optional[int]] = Column(Integer)
    
    local_interface: Mapped[Optional[str]] = Column(String(80))
    local_ip: Mapped[Optional[str]] = Column(String(45))
    
    dead_timer: Mapped[Optional[int]] = Column(Integer)
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="ospf_neighbors")
    
    __table_args__ = (
        UniqueConstraint("device_id", "neighbor_ip", name="uq_ospf_device_neighbor"),
    )


class IsisNeighbor(BaseModel):
    """IS-IS neighbor information."""
    
    __tablename__ = "isis_neighbors"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    system_id: Mapped[str] = Column(String(20), nullable=False)
    circuit_id: Mapped[Optional[str]] = Column(String(50))
    level: Mapped[Optional[str]] = Column(String(10))  # L1, L2, L1L2
    
    state: Mapped[str] = Column(String(50), nullable=False)  # up, down, initializing
    interface: Mapped[Optional[str]] = Column(String(80))
    
    snpa: Mapped[Optional[str]] = Column(String(17))  # SNPA address
    uptime_seconds: Mapped[Optional[int]] = Column(Integer)
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="isis_neighbors")


class MplsLsp(BaseModel):
    """MPLS Label Switched Path."""
    
    __tablename__ = "mpls_lsps"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    lsp_name: Mapped[str] = Column(String(100), nullable=False)
    destination: Mapped[str] = Column(String(45), nullable=False)
    
    tunnel_id: Mapped[Optional[int]] = Column(Integer)
    lsp_id: Mapped[Optional[int]] = Column(Integer)
    
    state: Mapped[str] = Column(String(50), nullable=False)  # up, down, admindown
    path_type: Mapped[Optional[str]] = Column(String(20))  # primary, secondary, standby
    
    in_label: Mapped[Optional[int]] = Column(Integer)
    out_label: Mapped[Optional[int]] = Column(Integer)
    next_hop: Mapped[Optional[str]] = Column(String(45))
    
    bandwidth: Mapped[Optional[int]] = Column(Integer)  # bits per second
    priority_setup: Mapped[Optional[int]] = Column(Integer)
    priority_hold: Mapped[Optional[int]] = Column(Integer)
    
    discovered_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    device: Mapped["Device"] = relationship(back_populates="mpls_lsps")
    
    __table_args__ = (
        UniqueConstraint("device_id", "lsp_name", name="uq_mpls_device_lsp"),
    )


# ============================================================================
# Notification Models
# ============================================================================

class NotificationChannel(BaseModel):
    """Notification channel configuration."""
    
    __tablename__ = "notification_channels"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True, index=True)
    channel_type: Mapped[NotificationChannelType] = Column(Enum(NotificationChannelType), nullable=False)
    
    # Channel-specific configuration (encrypted where needed)
    config: Mapped[dict] = Column(JSONB, nullable=False)
    is_enabled: Mapped[bool] = Column(Boolean, default=True)
    
    # Rate limiting
    rate_limit_per_minute: Mapped[Optional[int]] = Column(Integer)
    
    notifications_sent: Mapped[list["Notification"]] = relationship(
        back_populates="channel", 
        cascade="all, delete-orphan"
    )


class NotificationRule(BaseModel):
    """Rules for when to send notifications."""
    
    __tablename__ = "notification_rules"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = Column(Text)
    is_enabled: Mapped[bool] = Column(Boolean, default=True)
    
    # Conditions
    severities: Mapped[Optional[list]] = Column(JSONB)  # List of AlarmSeverity values
    event_types: Mapped[Optional[list]] = Column(JSONB)  # List of EventType values
    device_groups: Mapped[Optional[list]] = Column(JSONB)  # List of device group IDs
    time_restrictions: Mapped[Optional[dict]] = Column(JSONB)  # Maintenance windows, business hours
    
    # Actions
    channels: Mapped[list["NotificationChannel"]] = relationship(
        secondary="notification_rule_channels",
        back_populates="rules"
    )
    
    # Deduplication
    dedup_window_minutes: Mapped[Optional[int]] = Column(Integer)
    max_notifications_per_hour: Mapped[Optional[int]] = Column(Integer)


class NotificationRuleChannel(Base):
    """Association table for notification rule-channel many-to-many."""
    
    __tablename__ = "notification_rule_channels"
    
    rule_id: Mapped[int] = Column(ForeignKey("notification_rules.id"), primary_key=True)
    channel_id: Mapped[int] = Column(ForeignKey("notification_channels.id"), primary_key=True)
    
    __table_args__ = (
        Index("idx_rule_channel", "rule_id", "channel_id"),
    )


class Notification(BaseModel):
    """Sent notification record."""
    
    __tablename__ = "notifications"
    
    channel_id: Mapped[int] = Column(ForeignKey("notification_channels.id"), nullable=False, index=True)
    rule_id: Mapped[Optional[int]] = Column(ForeignKey("notification_rules.id"), index=True)
    
    alarm_id: Mapped[Optional[int]] = Column(ForeignKey("alarms.id"), index=True)
    event_id: Mapped[Optional[int]] = Column(ForeignKey("events.id"), index=True)
    
    subject: Mapped[Optional[str]] = Column(String(200))
    message: Mapped[str] = Column(Text, nullable=False)
    
    status: Mapped[str] = Column(String(20), default="pending")  # pending, sent, failed
    sent_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = Column(Text)
    
    recipients: Mapped[Optional[list]] = Column(JSONB)
    
    channel: Mapped["NotificationChannel"] = relationship(back_populates="notifications_sent")


class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window."""
    
    __tablename__ = "maintenance_windows"
    
    name: Mapped[str] = Column(String(100), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    
    start_time: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    
    # Scope
    device_ids: Mapped[Optional[list]] = Column(JSONB)
    device_group_ids: Mapped[Optional[list]] = Column(JSONB)
    alarm_severities: Mapped[Optional[list]] = Column(JSONB)
    
    # Behavior during maintenance
    suppress_notifications: Mapped[bool] = Column(Boolean, default=True)
    suppress_alarms: Mapped[bool] = Column(Boolean, default=False)
    mark_devices_unmonitored: Mapped[bool] = Column(Boolean, default=False)
    
    created_by: Mapped[str] = Column(String(80), nullable=False)
    is_recurring: Mapped[bool] = Column(Boolean, default=False)
    recurrence_pattern: Mapped[Optional[dict]] = Column(JSONB)
    
    is_active: Mapped[bool] = Column(Boolean, default=True)


# ============================================================================
# Audit & Discovery Models
# ============================================================================

class AuditLog(BaseModel):
    """Audit trail for all significant actions."""
    
    __tablename__ = "audit_logs"
    
    user_id: Mapped[Optional[int]] = Column(ForeignKey("users.id"), index=True)
    username: Mapped[str] = Column(String(80), nullable=False, index=True)
    
    action: Mapped[str] = Column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = Column(String(50), nullable=False, index=True)
    resource_id: Mapped[Optional[int]] = Column(Integer)
    resource_name: Mapped[Optional[str]] = Column(String(200))
    
    # Change details
    old_values: Mapped[Optional[dict]] = Column(JSONB)
    new_values: Mapped[Optional[dict]] = Column(JSONB)
    
    # Context
    ip_address: Mapped[Optional[str]] = Column(String(45))
    user_agent: Mapped[Optional[str]] = Column(String(255))
    session_id: Mapped[Optional[str]] = Column(String(100))
    
    result: Mapped[str] = Column(String(20), default="success")  # success, failure, partial
    error_message: Mapped[Optional[str]] = Column(Text)
    
    user: Mapped["User"] = relationship(back_populates="audit_logs")


class DiscoveryJob(BaseModel):
    """Network discovery job."""
    
    __tablename__ = "discovery_jobs"
    
    name: Mapped[str] = Column(String(100), nullable=False)
    description: Mapped[Optional[str]] = Column(Text)
    
    # Discovery targets
    ip_ranges: Mapped[Optional[list]] = Column(JSONB)  # List of CIDR strings
    start_ip: Mapped[Optional[str]] = Column(String(45))
    end_ip: Mapped[Optional[str]] = Column(String(45))
    
    # Methods
    use_icmp: Mapped[bool] = Column(Boolean, default=True)
    use_snmp: Mapped[bool] = Column(Boolean, default=True)
    use_lldp: Mapped[bool] = Column(Boolean, default=True)
    use_cdp: Mapped[bool] = Column(Boolean, default=False)
    
    # Credentials
    credential_id: Mapped[Optional[int]] = Column(ForeignKey("device_credentials.id"))
    
    # Status
    status: Mapped[JobStatus] = Column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    progress: Mapped[Optional[int]] = Column(Integer)  # Percentage
    total_ips: Mapped[Optional[int]] = Column(Integer)
    discovered_count: Mapped[Optional[int]] = Column(Integer)
    
    started_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = Column(Text)
    
    created_by: Mapped[str] = Column(String(80), nullable=False)
    
    results: Mapped[Optional[dict]] = Column(JSONB)  # Summary of discovered devices


class MonitoringProfile(BaseModel):
    """Monitoring profile/templates."""
    
    __tablename__ = "monitoring_profiles"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = Column(Text)
    
    # Polling settings
    polling_interval: Mapped[int] = Column(Integer, default=300)
    timeout: Mapped[int] = Column(Integer, default=30)
    retries: Mapped[int] = Column(Integer, default=3)
    
    # What to monitor
    monitor_availability: Mapped[bool] = Column(Boolean, default=True)
    monitor_cpu: Mapped[bool] = Column(Boolean, default=True)
    monitor_memory: Mapped[bool] = Column(Boolean, default=True)
    monitor_temperature: Mapped[bool] = Column(Boolean, default=False)
    monitor_interfaces: Mapped[bool] = Column(Boolean, default=True)
    monitor_optical: Mapped[bool] = Column(Boolean, default=False)
    monitor_poe: Mapped[bool] = Column(Boolean, default=False)
    
    # Thresholds
    cpu_warning_threshold: Mapped[Optional[int]] = Column(Integer, default=70)
    cpu_critical_threshold: Mapped[Optional[int]] = Column(Integer, default=90)
    memory_warning_threshold: Mapped[Optional[int]] = Column(Integer, default=70)
    memory_critical_threshold: Mapped[Optional[int]] = Column(Integer, default=90)
    temperature_warning_threshold: Mapped[Optional[int]] = Column(Integer, default=60)
    temperature_critical_threshold: Mapped[Optional[int]] = Column(Integer, default=80)
    
    # Custom OIDs
    custom_oids: Mapped[Optional[list]] = Column(JSONB)
    
    device_count: Mapped[int] = Column(Integer, default=0)


# ============================================================================
# Tagging System
# ============================================================================

class Tag(BaseModel):
    """Reusable tags for categorization."""
    
    __tablename__ = "tags"
    
    name: Mapped[str] = Column(String(50), nullable=False, unique=True, index=True)
    color: Mapped[Optional[str]] = Column(String(20))  # Hex color
    description: Mapped[Optional[str]] = Column(String(255))


class DeviceTag(Base):
    """Association table for device-tag many-to-many."""
    
    __tablename__ = "device_tags"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), primary_key=True)
    tag_id: Mapped[int] = Column(ForeignKey("tags.id"), primary_key=True)
    added_by: Mapped[str] = Column(String(80))
    added_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)
    
    __table_args__ = (
        Index("idx_device_tag", "device_id", "tag_id"),
    )


# ============================================================================
# Legacy compatibility tables (from initial migrations)
# ============================================================================

class HealthSnapshot(BaseModel):
    """Legacy health snapshot - superseded by DeviceMetric."""
    
    __tablename__ = "health_snapshots"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    cpu_percent: Mapped[Optional[float]] = Column(Float)
    memory_percent: Mapped[Optional[float]] = Column(Float)
    temperature_celsius: Mapped[Optional[float]] = Column(Float)
    reachable: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    collected_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utc_now)


class InterfaceStatus(BaseModel):
    """Legacy interface status - superseded by Interface updates."""
    
    __tablename__ = "interface_statuses"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    interface_name: Mapped[str] = Column(String(80), nullable=False)
    status: Mapped[str] = Column(String(40), nullable=False)
    description: Mapped[Optional[str]] = Column(String(255))


class LldpNeighbor(BaseModel):
    """Legacy LLDP neighbor - superseded by TopologyLink."""
    
    __tablename__ = "lldp_neighbors"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    local_interface: Mapped[str] = Column(String(80), nullable=False)
    neighbor_name: Mapped[str] = Column(String(120), nullable=False)
    neighbor_interface: Mapped[Optional[str]] = Column(String(80))


class RecoverySimulation(BaseModel):
    """Recovery simulation record."""
    
    __tablename__ = "recovery_simulations"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    failure_type: Mapped[str] = Column(String(40), nullable=False)
    backup_id: Mapped[Optional[int]] = Column(ForeignKey("configuration_backups.id"))
    status: Mapped[str] = Column(String(30), nullable=False)
    execution_plan: Mapped[str] = Column(Text, nullable=False)
    created_by: Mapped[str] = Column(String(80), nullable=False)


class NetworkChangePlan(BaseModel):
    """Network change plan."""
    
    __tablename__ = "network_change_plans"
    
    device_id: Mapped[int] = Column(ForeignKey("devices.id"), nullable=False, index=True)
    operation: Mapped[str] = Column(String(50), nullable=False)
    commands: Mapped[str] = Column(Text, nullable=False)
    summary: Mapped[str] = Column(String(255), nullable=False)
    status: Mapped[str] = Column(String(30), nullable=False)
    created_by: Mapped[str] = Column(String(80), nullable=False)


# ============================================================================
# Event Rules for Alarm Correlation
# ============================================================================

class EventRule(BaseModel):
    """Rules for event-to-alarm correlation."""
    
    __tablename__ = "event_rules"
    
    name: Mapped[str] = Column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = Column(Text)
    is_enabled: Mapped[bool] = Column(Boolean, default=True)
    
    # Trigger conditions
    event_type: Mapped[EventType] = Column(Enum(EventType), nullable=False)
    source_types: Mapped[Optional[list]] = Column(JSONB)  # snmp_trap, syslog, polling
    match_pattern: Mapped[Optional[str]] = Column(String(255))  # Regex pattern for message matching
    
    # Action
    create_alarm: Mapped[bool] = Column(Boolean, default=True)
    alarm_severity: Mapped[AlarmSeverity] = Column(Enum(AlarmSeverity), default=AlarmSeverity.WARNING)
    alarm_title_template: Mapped[Optional[str]] = Column(String(200))
    alarm_message_template: Mapped[Optional[str]] = Column(Text)
    
    # Correlation
    correlation_window_minutes: Mapped[Optional[int]] = Column(Integer)
    auto_resolve_on_clear: Mapped[bool] = Column(Boolean, default=True)
    
    # Scope
    device_groups: Mapped[Optional[list]] = Column(JSONB)
    severities: Mapped[Optional[list]] = Column(JSONB)


# Add missing relationships to Device model
@event.listens_for(Device, 'before_insert')
def set_defaults(mapper, connection, target):
    """Set default values before insert."""
    if target.status is None:
        target.status = DeviceStatus.UNKNOWN
    if target.protocol is None:
        target.protocol = ProtocolType.SSH
