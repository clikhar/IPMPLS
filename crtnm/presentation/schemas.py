"""Request and response models. Credentials are write-only."""
from datetime import datetime
from pydantic import BaseModel, Field, IPvAnyAddress
from crtnm.domain.enums import DeviceType, UserRole


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


class ConnectionCommand(BaseModel):
    """Read-only command request; only the driver can authorize commands."""

    command: str = Field(default="show version", min_length=1, max_length=100)


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
