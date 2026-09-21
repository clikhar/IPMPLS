"""Request and response models. Credentials are write-only."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, IPvAnyAddress
from crtnm.domain.enums import (
    DeviceType, 
    UserRole, 
    AlarmSeverity, 
    AlarmStatus, 
    EventType,
    NotificationChannelType,
)


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    division: str = Field(min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=255)


class StationRead(StationCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceCreate(BaseModel):
    station_id: int
    name: str = Field(min_length=2, max_length=120)
    device_type: DeviceType
    vendor: str = Field(min_length=2, max_length=60)
    model: str | None = Field(default=None, max_length=120)
    management_ip: IPvAnyAddress
    protocol: str = Field(default="ssh", pattern="^(ssh|telnet)$")
    connection_username: str | None = Field(default=None, min_length=1, max_length=80)
    password: str | None = Field(default=None, min_length=1, max_length=256)
    enable_password: str | None = Field(default=None, min_length=1, max_length=256)


class DeviceRead(BaseModel):
    id: int
    station_id: int
    name: str
    device_type: DeviceType
    vendor: str
    model: str | None
    management_ip: str
    protocol: str
    created_at: datetime

    model_config = {"from_attributes": True}

class DeviceUpdate(BaseModel):
    station_id: int
    name: str
    device_type: str
    vendor: str
    management_ip: str
    protocol: str
    connection_username: str
    password: str | None = None
    enable_password: str | None = None
    port: int | None = None
    
class ConnectionCommand(BaseModel):
    """Read-only command request; only the driver can authorize commands."""

    command: str = Field(default="show version", min_length=1, max_length=100)

class ConnectionCommand(BaseModel):
    """Read-only command request; only the driver can authorize commands."""

    command: str = Field(
        default="show version",
        min_length=1,
        max_length=100
    )


class ExecuteCommandsRequest(BaseModel):
    """Batch of read-only commands to execute on a network device."""

    commands: list[str] = Field(
        min_length=1,
        max_length=10
    )


class ExecuteCommandResult(BaseModel):
    """Result of one read-only command."""

    command: str

    success: bool

    output: str = ""

    error: str | None = None


class ExecuteCommandsRead(BaseModel):
    """Response from a batch read-only command execution."""

    device_id: int

    success: bool

    results: list[ExecuteCommandResult]

    execution_time: float
    
class ConnectionTestRead(BaseModel):
    device_id: int
    hostname: str
    prompt: str
    version: str | None


class CommandOutput(BaseModel):
    device_id: int
    output: str


class BackupRead(BaseModel):
    id: int
    device_id: int
    checksum: str
    source: str
    created_by: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ComparisonRead(BaseModel):
    diff: str


class RestorePreviewRead(BaseModel):
    device_id: int
    backup_id: int
    checksum: str
    commands: list[str]
    configuration: str


class RecoverySimulationCreate(BaseModel):
    failure_type: str = Field(pattern="^(switch_failure|ler_failure|fiber_failure)$")
    backup_id: int | None = None


class RecoverySimulationRead(BaseModel):
    id: int
    device_id: int
    failure_type: str
    backup_id: int | None
    status: str
    execution_plan: list[str]
    created_at: datetime


class VlanPlanCreate(BaseModel):
    vlan_id: int = Field(ge=1, le=4094)
    name: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    interface: str | None = Field(default=None, pattern=r"^[A-Za-z0-9/.-]+$")
    mode: str = Field(default="access", pattern="^(access|trunk)$")


class InterfacePlanCreate(BaseModel):
    interface: str = Field(pattern=r"^[A-Za-z0-9/.-]+$")
    action: str = Field(pattern="^(shutdown|no_shutdown|description|access|trunk)$")
    value: str | None = Field(default=None, max_length=120)


class StaticRoutePlanCreate(BaseModel):
    destination: str = Field(pattern=r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")
    next_hop: IPvAnyAddress
    vrf: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+$")


class MplsPlanCreate(BaseModel):
    service: str = Field(pattern="^(l2vpn|l3vpn|vrf|isis|bgp|ldp|pseudowire|loopback)$")
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    value: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_.:/ -]+$")


class NetworkPlanRead(BaseModel):
    id: int
    device_id: int
    operation: str
    commands: list[str]
    summary: str
    status: str
    created_at: datetime


class HealthSnapshotRead(BaseModel):
    id: int
    device_id: int
    cpu_percent: float | None
    memory_percent: float | None
    temperature_celsius: float | None
    reachable: bool
    collected_at: datetime
    model_config = {"from_attributes": True}


class DashboardSummaryRead(BaseModel):
    devices: int
    connected: int
    disconnected: int
    open_alarms: int


class InterfaceStatusRead(BaseModel):
    id: int
    device_id: int
    interface_name: str
    status: str
    description: str | None
    model_config = {"from_attributes": True}


class AlarmRead(BaseModel):
    id: int
    device_id: int
    metric: str
    severity: str
    message: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class TopologyNodeRead(BaseModel):
    id: int
    name: str
    vendor: str
    type: str
    ip: str


class TopologyEdgeRead(BaseModel):
    source: int
    target: int
    label: str


class TopologyRead(BaseModel):
    nodes: list[TopologyNodeRead]
    edges: list[TopologyEdgeRead]


class UserCreate(Credentials):
    role: UserRole


class UserRead(BaseModel):
    id: int
    username: str
    role: UserRole
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditLogRead(BaseModel):
    id: int
    actor: str
    action: str
    target: str
    detail: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class CurrentUser(BaseModel):
    id: int
    role: UserRole


# ============================================================================
# Alarm Schemas
# ============================================================================

class AlarmCreate(BaseModel):
    """Schema for creating a new alarm."""
    
    event_type: EventType
    severity: AlarmSeverity
    title: str = Field(min_length=1, max_length=200)
    message: Optional[str] = None
    device_id: Optional[int] = None
    interface_id: Optional[int] = None
    additional_info: Optional[Dict[str, Any]] = None


class AlarmUpdate(BaseModel):
    """Schema for updating an alarm."""
    
    status: Optional[AlarmStatus] = None
    severity: Optional[AlarmSeverity] = None
    acknowledged_note: Optional[str] = None
    resolution_note: Optional[str] = None


class AlarmAcknowledge(BaseModel):
    """Schema for acknowledging an alarm."""
    
    note: Optional[str] = None


class AlarmResolve(BaseModel):
    """Schema for resolving an alarm."""
    
    note: Optional[str] = None
    resolve_children: bool = True


class AlarmSuppress(BaseModel):
    """Schema for suppressing an alarm."""
    
    until: datetime
    reason: str = Field(min_length=1, max_length=255)


class AlarmRead(BaseModel):
    """Schema for reading alarm details."""
    
    id: int
    title: str
    message: Optional[str]
    event_type: EventType
    severity: AlarmSeverity
    status: AlarmStatus
    device_id: Optional[int]
    interface_id: Optional[int]
    root_cause_alarm_id: Optional[int]
    is_root_cause: bool
    first_occurred: datetime
    last_occurred: datetime
    occurrence_count: int
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    acknowledged_note: Optional[str]
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    resolution_note: Optional[str]
    suppressed_until: Optional[datetime]
    suppression_reason: Optional[str]
    additional_info: Optional[Dict[str, Any]]
    correlated_events: Optional[List[Any]]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AlarmStatistics(BaseModel):
    """Schema for alarm statistics."""
    
    active_total: int
    active_by_severity: Dict[str, int]
    new_24h: int
    resolved_24h: int
    mtta_seconds: Optional[float]
    mttr_seconds: Optional[float]


# ============================================================================
# Event Schemas
# ============================================================================

class EventRead(BaseModel):
    """Schema for reading event details."""
    
    id: int
    source_type: str
    source_ip: Optional[str]
    event_type: EventType
    device_id: Optional[int]
    interface_id: Optional[int]
    severity: AlarmSeverity
    message: str
    timestamp: datetime
    processed: bool
    alarm_id: Optional[int]
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationChannelCreate(BaseModel):
    """Schema for creating a notification channel."""
    
    name: str = Field(min_length=1, max_length=100)
    channel_type: NotificationChannelType
    config: Dict[str, Any]
    is_enabled: bool = True
    rate_limit_per_minute: Optional[int] = None


class NotificationChannelUpdate(BaseModel):
    """Schema for updating a notification channel."""
    
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = None


class NotificationChannelRead(BaseModel):
    """Schema for reading notification channel details."""
    
    id: int
    name: str
    channel_type: NotificationChannelType
    config: Dict[str, Any]
    is_enabled: bool
    rate_limit_per_minute: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class NotificationRuleCreate(BaseModel):
    """Schema for creating a notification rule."""
    
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    severities: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    device_groups: Optional[List[int]] = None
    time_restrictions: Optional[Dict[str, Any]] = None
    channel_ids: List[int] = []
    dedup_window_minutes: Optional[int] = None
    max_notifications_per_hour: Optional[int] = None


class NotificationRuleUpdate(BaseModel):
    """Schema for updating a notification rule."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    severities: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    device_groups: Optional[List[int]] = None
    time_restrictions: Optional[Dict[str, Any]] = None
    channel_ids: Optional[List[int]] = None
    dedup_window_minutes: Optional[int] = None
    max_notifications_per_hour: Optional[int] = None
    is_enabled: Optional[bool] = None


class NotificationRuleRead(BaseModel):
    """Schema for reading notification rule details."""
    
    id: int
    name: str
    description: Optional[str]
    is_enabled: bool
    severities: Optional[List[str]]
    event_types: Optional[List[str]]
    device_groups: Optional[List[int]]
    time_restrictions: Optional[Dict[str, Any]]
    channels: List[NotificationChannelRead] = []
    dedup_window_minutes: Optional[int]
    max_notifications_per_hour: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class NotificationRead(BaseModel):
    """Schema for reading notification details."""
    
    id: int
    channel_id: int
    rule_id: Optional[int]
    alarm_id: Optional[int]
    event_id: Optional[int]
    subject: Optional[str]
    message: str
    status: str
    sent_at: Optional[datetime]
    error_message: Optional[str]
    recipients: Optional[List[Any]]
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Maintenance Window Schemas
# ============================================================================

class MaintenanceWindowCreate(BaseModel):
    """Schema for creating a maintenance window."""
    
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    device_ids: Optional[List[int]] = None
    device_group_ids: Optional[List[int]] = None
    alarm_severities: Optional[List[str]] = None
    suppress_notifications: bool = True
    suppress_alarms: bool = False
    mark_devices_unmonitored: bool = False
    is_recurring: bool = False
    recurrence_pattern: Optional[Dict[str, Any]] = None


class MaintenanceWindowUpdate(BaseModel):
    """Schema for updating a maintenance window."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    device_ids: Optional[List[int]] = None
    device_group_ids: Optional[List[int]] = None
    alarm_severities: Optional[List[str]] = None
    suppress_notifications: Optional[bool] = None
    suppress_alarms: Optional[bool] = None
    mark_devices_unmonitored: Optional[bool] = None
    is_active: Optional[bool] = None


class MaintenanceWindowRead(BaseModel):
    """Schema for reading maintenance window details."""
    
    id: int
    name: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    device_ids: Optional[List[int]]
    device_group_ids: Optional[List[int]]
    alarm_severities: Optional[List[str]]
    suppress_notifications: bool
    suppress_alarms: bool
    mark_devices_unmonitored: bool
    created_by: str
    is_recurring: bool
    recurrence_pattern: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}
