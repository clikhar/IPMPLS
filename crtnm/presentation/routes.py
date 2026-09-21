"""Versioned CRTNM REST endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from crtnm.application.audit_service import AuditService
from crtnm.application.auth_service import AuthService
from crtnm.application.inventory_service import InventoryService
from crtnm.application.configuration_service import ConfigurationService
from crtnm.application.network_change_service import NetworkChangeService
from crtnm.application.network_command_factory import NetworkCommandFactory
from crtnm.application.monitoring_service import MonitoringService
from crtnm.application.report_service import ReportService
from crtnm.application.user_service import UserService
from crtnm.domain.enums import UserRole, AlarmSeverity, AlarmStatus, EventType
from crtnm.drivers import registry
from crtnm.drivers.exceptions import DriverError
from crtnm.drivers.neon import NeonDriver
from crtnm.infrastructure.database import get_session, get_async_session
from crtnm.infrastructure.models import AuditLog
from crtnm.presentation.dependencies import get_current_user, require_role, require_permissions
from crtnm.presentation.schemas import (AlarmAcknowledge, AlarmRead, AlarmResolve, AlarmSuppress, AlarmStatistics, EventRead, NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelRead, NotificationRuleCreate, NotificationRuleUpdate, NotificationRuleRead, NotificationRead, MaintenanceWindowCreate, MaintenanceWindowUpdate, MaintenanceWindowRead, AuditLogRead, BackupRead, 
                                        CommandOutput, ComparisonRead, ConnectionCommand, 
                                        ConnectionTestRead, Credentials, CurrentUser, DashboardSummaryRead, 
                                        DeviceCreate, DeviceRead, DeviceUpdate, ExecuteCommandsRequest,ExecuteCommandsRead,
                                        ExecuteCommandResult,HealthSnapshotRead, 
                                        InterfacePlanCreate, InterfaceStatusRead, MplsPlanCreate, 
                                        NetworkPlanRead, RecoverySimulationCreate, RecoverySimulationRead, 
                                        RestorePreviewRead, StaticRoutePlanCreate, StationCreate, StationRead, 
                                        TokenResponse, TopologyRead, UserCreate, UserRead, VlanPlanCreate,)

import json
import traceback

router = APIRouter(prefix="/api/v1")
audit = AuditService()
auth = AuthService(audit)
inventory = InventoryService(audit)
configuration = ConfigurationService(audit)
network_changes = NetworkChangeService(audit)
monitoring = MonitoringService(audit)
users = UserService(audit)
registry.register(NeonDriver())


@router.post("/auth/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap(payload: Credentials, session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        auth.bootstrap(session, payload.username, payload.password)
        return {"message": "Administrator created"}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: Credentials, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        return TokenResponse(access_token=auth.login(session, payload.username, payload.password))
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@router.get("/auth/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user


@router.get("/stations", response_model=list[StationRead])
def list_stations(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[StationRead]:
    return inventory.list_stations(session)


@router.post("/stations", response_model=StationRead, status_code=201)
def create_station(payload: StationCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> StationRead:
    try:
        return inventory.create_station(session, str(user.id), **payload.model_dump())
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Station name already exists") from error


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[DeviceRead]:
    return inventory.list_devices(session)


@router.post("/devices", response_model=DeviceRead, status_code=201)
def create_device(payload: DeviceCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> DeviceRead:
    try:
        return inventory.create_device(session, str(user.id), payload.model_dump(mode="json"))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Device name or management IP already exists") from error

@router.put("/devices/{device_id}",response_model=DeviceRead,)
def update_device(device_id: int,payload: DeviceUpdate,user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)),session: Session = Depends(get_session),):
    return inventory.update_device(
        session,
        str(user.id),
        device_id,
        payload.model_dump(mode="json"),
    )

@router.get("/devices/{device_id}",response_model=DeviceRead,)
def get_device(
    device_id: int,
    user=Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
    session: Session = Depends(get_session),
):
    return inventory.get_device(session, device_id)

@router.delete(
    "/devices/{device_id}",
    status_code=204,
)
def delete_device(
    device_id: int,
    user=Depends(require_role(UserRole.NETWORK_ADMIN)),
    session: Session = Depends(get_session),
):
    inventory.delete_device(
        session,
        str(user.id),
        device_id,
    )
    
@router.post("/devices/{device_id}/connection-test", response_model=ConnectionTestRead)
def connection_test(device_id: int,  user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> ConnectionTestRead:
    """Perform a safe `show version` connectivity test; arbitrary commands are not accepted."""
    try:
        facts = inventory.test_device(session, str(user.id), device_id, registry)
        return ConnectionTestRead(device_id=device_id, **facts.__dict__)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.get("/devices/{device_id}/facts", )
def get_device_facts(
    device_id: int,
    user: CurrentUser = Depends(
        require_role(
            UserRole.NETWORK_ADMIN,
            UserRole.OPERATOR,
            UserRole.VIEWER,
        )
    ),
    session: Session = Depends(get_session),
    ):
    """
    Collect structured operational facts from a device.

    The vendor driver controls which read-only commands are executed.
    """

    try:
        return inventory.collect_facts(
            session,
            str(user.id),
            device_id,
            registry,
        )

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except (
        ValueError,
        DriverError,
        RuntimeError,
    ) as error:
        traceback.print_exc()

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

@router.post("/devices/{device_id}/execute",response_model=ExecuteCommandsRead,)
def execute_commands(device_id: int,payload: ExecuteCommandsRequest,
                     user: CurrentUser = Depends(require_role
                                                 (UserRole.NETWORK_ADMIN,UserRole.OPERATOR)),
                                                 session: Session = Depends(get_session),
                                                 ) -> ExecuteCommandsRead:
     """"
     Execute a batch of driver-approved read-only commands.
    Configuration-changing commands are not accepted by this endpoint.
    """
     try:
        results, execution_time = (
            inventory.execute_readonly_many(
                session,
                str(user.id),
                device_id,
                payload.commands,
                registry,
            )
        )

        result_objects = [
            ExecuteCommandResult(
                command=str(result["command"]),
                success=bool(result["success"]),
                output=str(result.get("output") or ""),
                error=(
                    str(result["error"])
                    if result.get("error")
                    else None
                ),
            )
            for result in results
        ]

        return ExecuteCommandsRead(
            device_id=device_id,
            success=all(
                result.success
                for result in result_objects
            ),
            results=result_objects,
            execution_time=execution_time,
        )
     except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error
     
     except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        ) from error
     
     except DriverError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        ) from error

@router.post("/devices/{device_id}/commands/read-only", response_model=CommandOutput)
def execute_readonly_command(device_id: int, payload: ConnectionCommand, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> CommandOutput:
    """Run one driver-vetted show command and record its execution."""
    try:
        return CommandOutput(device_id=device_id, output=inventory.execute_readonly(session, str(user.id), device_id, payload.command, registry))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/devices/{device_id}/backups", response_model=BackupRead, status_code=201)
def capture_backup(device_id: int, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> BackupRead:
    try:
        return configuration.capture_running(session, str(user.id), device_id, registry)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/devices/{device_id}/backups", response_model=list[BackupRead])
def list_backups(device_id: int, _: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[BackupRead]:
    try:
        return configuration.list_backups(session, device_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/backups/{left_id}/compare/{right_id}", response_model=ComparisonRead)
def compare_backups(left_id: int, right_id: int, _: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> ComparisonRead:
    try:
        return ComparisonRead(diff=configuration.compare(session, left_id, right_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/backups/{backup_id}/restore-preview", response_model=RestorePreviewRead)
def restore_preview(backup_id: int, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN)), session: Session = Depends(get_session)) -> RestorePreviewRead:
    try:
        return RestorePreviewRead(**configuration.restore_preview(session, str(user.id), backup_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/recovery-simulations", response_model=RecoverySimulationRead, status_code=201)
def simulate_recovery(device_id: int, payload: RecoverySimulationCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN)), session: Session = Depends(get_session)) -> RecoverySimulationRead:
    try:
        result = configuration.simulate_recovery(session, str(user.id), device_id, payload.failure_type, payload.backup_id)
        return RecoverySimulationRead(id=result.id, device_id=result.device_id, failure_type=result.failure_type, backup_id=result.backup_id, status=result.status, execution_plan=json.loads(result.execution_plan), created_at=result.created_at)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _plan_response(device_id: int, actor: str, operation: str, commands: list[str], summary: str, session: Session) -> NetworkPlanRead:
    plan = network_changes.create_plan(session, actor, device_id, operation, commands, summary)
    return NetworkPlanRead(id=plan.id, device_id=plan.device_id, operation=plan.operation, commands=json.loads(plan.commands), summary=plan.summary, status=plan.status, created_at=plan.created_at)


@router.post("/devices/{device_id}/plans/vlan", response_model=NetworkPlanRead, status_code=201)
def plan_vlan(device_id: int, payload: VlanPlanCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.vlan(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/interface", response_model=NetworkPlanRead, status_code=201)
def plan_interface(device_id: int, payload: InterfacePlanCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.interface(payload), session)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=422 if isinstance(error, ValueError) else 404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/static-route", response_model=NetworkPlanRead, status_code=201)
def plan_route(device_id: int, payload: StaticRoutePlanCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.static_route(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/mpls", response_model=NetworkPlanRead, status_code=201)
def plan_mpls(device_id: int, payload: MplsPlanCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.mpls(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/devices/{device_id}/plans", response_model=list[NetworkPlanRead])
def list_network_plans(device_id: int, _: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[NetworkPlanRead]:
    """Return all non-executing change previews for a device."""
    return [NetworkPlanRead(id=item.id, device_id=item.device_id, operation=item.operation, commands=json.loads(item.commands), summary=item.summary, status=item.status, created_at=item.created_at) for item in network_changes.list_plans(session, device_id)]


@router.post("/devices/{device_id}/monitoring/poll", response_model=HealthSnapshotRead, status_code=201)
def poll_device(device_id: int, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> HealthSnapshotRead:
    """Run a read-only monitoring collection for one device."""
    try:
        return monitoring.poll(session, str(user.id), device_id, registry)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/monitoring/summary", response_model=DashboardSummaryRead)
def monitoring_summary(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> DashboardSummaryRead:
    """Return the persisted counts displayed on the dashboard."""
    return DashboardSummaryRead(**monitoring.summary(session))


@router.get("/devices/{device_id}/interfaces", response_model=list[InterfaceStatusRead])
def device_interfaces(device_id: int, _: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[InterfaceStatusRead]:
    """Return latest discovered interfaces for a device."""
    return monitoring.interfaces(session, device_id)


@router.get("/alarms", response_model=list[AlarmRead])
def list_alarms(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[AlarmRead]:
    """Return unresolved monitoring alarms."""
    return monitoring.alarms(session)


@router.get("/topology", response_model=TopologyRead)
def topology(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> TopologyRead:
    """Return current LLDP-derived topology relationships."""
    return TopologyRead(**monitoring.topology(session))


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(_: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN)), session: Session = Depends(get_session)) -> list[AuditLogRead]:
    """Return the latest audit events for security review."""
    return list(session.query(AuditLog).order_by(AuditLog.id.desc()).limit(500))


@router.get("/reports/inventory/{format}")
def export_inventory(format: str, _: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> Response:
    """Download a device inventory in CSV, Excel, or PDF format."""
    rows, headers = ReportService.inventory_rows(session), ReportService.INVENTORY_HEADERS
    if format == "csv":
        return Response(ReportService.to_csv(headers, rows), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=crtnm-inventory.csv"})
    if format == "xlsx":
        return Response(ReportService.to_xlsx(headers, rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=crtnm-inventory.xlsx"})
    if format == "pdf":
        return Response(ReportService.inventory_pdf(session), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=crtnm-inventory.pdf"})
    raise HTTPException(status_code=404, detail="Supported report formats: csv, xlsx, pdf")


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, user: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN)), session: Session = Depends(get_session)) -> UserRead:
    """Create a role-based CRTNM user."""
    try:
        return users.create(session, str(user.id), payload.username, payload.password, payload.role)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/users", response_model=list[UserRead])
def list_users(_: CurrentUser = Depends(require_role(UserRole.NETWORK_ADMIN)), session: Session = Depends(get_session)) -> list[UserRead]:
    """List user metadata, never password material."""
    return users.list_users(session)


# ============================================================================
# Alarm Management Routes
# ============================================================================

@router.get("/alarms", response_model=list[AlarmRead])
async def get_alarms(
    device_id: Optional[int] = None,
    severity: Optional[AlarmSeverity] = None,
    status: Optional[AlarmStatus] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get active alarms with filtering and pagination."""
    alarm_service = AlarmService(session)
    alarms, total = await alarm_service.get_active_alarms(
        device_id=device_id,
        severity=severity,
        status=status,
        limit=limit,
        offset=offset,
    )
    return alarms


@router.get("/alarms/statistics", response_model=AlarmStatistics)
async def get_alarm_statistics(
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get alarm statistics for dashboard."""
    alarm_service = AlarmService(session)
    return await alarm_service.get_alarm_statistics()


@router.post("/alarms/{alarm_id}/acknowledge", response_model=AlarmRead)
async def acknowledge_alarm(
    alarm_id: int,
    payload: AlarmAcknowledge,
    current_user: CurrentUser = Depends(require_permissions("alarm.ack")),
    session: AsyncSession = Depends(get_async_session),
):
    """Acknowledge an alarm."""
    alarm_service = AlarmService(session)
    alarm = await alarm_service.acknowledge_alarm(
        alarm_id=alarm_id,
        user_id=current_user.id,
        note=payload.note,
    )
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    # Audit log
    audit_service = AuditService(session)
    await audit_service.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action="alarm_acknowledge",
        resource_type="alarm",
        resource_id=alarm_id,
    )
    
    return alarm


@router.post("/alarms/{alarm_id}/resolve", response_model=AlarmRead)
async def resolve_alarm(
    alarm_id: int,
    payload: AlarmResolve,
    current_user: CurrentUser = Depends(require_permissions("alarm.ack")),
    session: AsyncSession = Depends(get_async_session),
):
    """Resolve an alarm."""
    alarm_service = AlarmService(session)
    alarm = await alarm_service.resolve_alarm(
        alarm_id=alarm_id,
        user_id=current_user.id,
        note=payload.note,
        resolve_children=payload.resolve_children,
    )
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    # Audit log
    audit_service = AuditService(session)
    await audit_service.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action="alarm_resolve",
        resource_type="alarm",
        resource_id=alarm_id,
    )
    
    return alarm


@router.post("/alarms/{alarm_id}/suppress", response_model=AlarmRead)
async def suppress_alarm(
    alarm_id: int,
    payload: AlarmSuppress,
    current_user: CurrentUser = Depends(require_permissions("alarm.ack")),
    session: AsyncSession = Depends(get_async_session),
):
    """Suppress an alarm temporarily."""
    alarm_service = AlarmService(session)
    alarm = await alarm_service.suppress_alarm(
        alarm_id=alarm_id,
        until=payload.until,
        reason=payload.reason,
    )
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return alarm


@router.post("/alarms/{alarm_id}/unsuppress", response_model=AlarmRead)
async def unsuppress_alarm(
    alarm_id: int,
    current_user: CurrentUser = Depends(require_permissions("alarm.ack")),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove suppression from an alarm."""
    alarm_service = AlarmService(session)
    alarm = await alarm_service.unsuppress_alarm(alarm_id=alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return alarm


# ============================================================================
# Notification Channel Routes
# ============================================================================

@router.post("/notification/channels", response_model=NotificationChannelRead, status_code=201)
async def create_notification_channel(
    payload: NotificationChannelCreate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new notification channel."""
    channel = NotificationChannel(
        name=payload.name,
        channel_type=payload.channel_type,
        config=payload.config,
        is_enabled=payload.is_enabled,
        rate_limit_per_minute=payload.rate_limit_per_minute,
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    
    # Audit log
    audit_service = AuditService(session)
    await audit_service.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action="notification_channel_create",
        resource_type="notification_channel",
        resource_id=channel.id,
    )
    
    return channel


@router.get("/notification/channels", response_model=list[NotificationChannelRead])
async def list_notification_channels(
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """List all notification channels."""
    result = await session.execute(select(NotificationChannel))
    return result.scalars().all()


@router.get("/notification/channels/{channel_id}", response_model=NotificationChannelRead)
async def get_notification_channel(
    channel_id: int,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific notification channel."""
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/notification/channels/{channel_id}", response_model=NotificationChannelRead)
async def update_notification_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a notification channel."""
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if payload.name:
        channel.name = payload.name
    if payload.config is not None:
        channel.config = payload.config
    if payload.is_enabled is not None:
        channel.is_enabled = payload.is_enabled
    if payload.rate_limit_per_minute is not None:
        channel.rate_limit_per_minute = payload.rate_limit_per_minute
    
    await session.commit()
    await session.refresh(channel)
    return channel


@router.delete("/notification/channels/{channel_id}")
async def delete_notification_channel(
    channel_id: int,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a notification channel."""
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    await session.delete(channel)
    await session.commit()
    return {"message": "Channel deleted"}


@router.post("/notification/channels/{channel_id}/test", response_model=dict)
async def test_notification_channel(
    channel_id: int,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Test a notification channel."""
    notification_service = NotificationService(session)
    return await notification_service.test_channel(channel_id)


# ============================================================================
# Notification Rule Routes
# ============================================================================

@router.post("/notification/rules", response_model=NotificationRuleRead, status_code=201)
async def create_notification_rule(
    payload: NotificationRuleCreate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new notification rule."""
    # Get channels
    channel_result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.id.in_(payload.channel_ids))
    )
    channels = list(channel_result.scalars().all())
    
    rule = NotificationRule(
        name=payload.name,
        description=payload.description,
        severities=payload.severities,
        event_types=payload.event_types,
        device_groups=payload.device_groups,
        time_restrictions=payload.time_restrictions,
        dedup_window_minutes=payload.dedup_window_minutes,
        max_notifications_per_hour=payload.max_notifications_per_hour,
        channels=channels,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("/notification/rules", response_model=list[NotificationRuleRead])
async def list_notification_rules(
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """List all notification rules."""
    result = await session.execute(
        select(NotificationRule).options(selectinload(NotificationRule.channels))
    )
    return result.scalars().all()


@router.get("/notification/rules/{rule_id}", response_model=NotificationRuleRead)
async def get_notification_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific notification rule."""
    result = await session.execute(
        select(NotificationRule)
        .options(selectinload(NotificationRule.channels))
        .where(NotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/notification/rules/{rule_id}", response_model=NotificationRuleRead)
async def update_notification_rule(
    rule_id: int,
    payload: NotificationRuleUpdate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a notification rule."""
    result = await session.execute(
        select(NotificationRule).where(NotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if payload.name:
        rule.name = payload.name
    if payload.description is not None:
        rule.description = payload.description
    if payload.severities is not None:
        rule.severities = payload.severities
    if payload.event_types is not None:
        rule.event_types = payload.event_types
    if payload.device_groups is not None:
        rule.device_groups = payload.device_groups
    if payload.time_restrictions is not None:
        rule.time_restrictions = payload.time_restrictions
    if payload.dedup_window_minutes is not None:
        rule.dedup_window_minutes = payload.dedup_window_minutes
    if payload.max_notifications_per_hour is not None:
        rule.max_notifications_per_hour = payload.max_notifications_per_hour
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled
    
    if payload.channel_ids is not None:
        channel_result = await session.execute(
            select(NotificationChannel).where(NotificationChannel.id.in_(payload.channel_ids))
        )
        rule.channels = list(channel_result.scalars().all())
    
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/notification/rules/{rule_id}")
async def delete_notification_rule(
    rule_id: int,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a notification rule."""
    result = await session.execute(
        select(NotificationRule).where(NotificationRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await session.delete(rule)
    await session.commit()
    return {"message": "Rule deleted"}


# ============================================================================
# Maintenance Window Routes
# ============================================================================

@router.post("/maintenance-windows", response_model=MaintenanceWindowRead, status_code=201)
async def create_maintenance_window(
    payload: MaintenanceWindowCreate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new maintenance window."""
    window = MaintenanceWindow(
        name=payload.name,
        description=payload.description,
        start_time=payload.start_time,
        end_time=payload.end_time,
        device_ids=payload.device_ids,
        device_group_ids=payload.device_group_ids,
        alarm_severities=payload.alarm_severities,
        suppress_notifications=payload.suppress_notifications,
        suppress_alarms=payload.suppress_alarms,
        mark_devices_unmonitored=payload.mark_devices_unmonitored,
        created_by=current_user.username,
        is_recurring=payload.is_recurring,
        recurrence_pattern=payload.recurrence_pattern,
    )
    session.add(window)
    await session.commit()
    await session.refresh(window)
    
    # Audit log
    audit_service = AuditService(session)
    await audit_service.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action="maintenance_window_create",
        resource_type="maintenance_window",
        resource_id=window.id,
    )
    
    return window


@router.get("/maintenance-windows", response_model=list[MaintenanceWindowRead])
async def list_maintenance_windows(
    active_only: bool = False,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """List maintenance windows."""
    query = select(MaintenanceWindow)
    if active_only:
        now = datetime.utcnow()
        query = query.where(
            and_(
                MaintenanceWindow.is_active == True,
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now,
            )
        )
    result = await session.execute(query.order_by(MaintenanceWindow.start_time.desc()))
    return result.scalars().all()


@router.get("/maintenance-windows/{window_id}", response_model=MaintenanceWindowRead)
async def get_maintenance_window(
    window_id: int,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific maintenance window."""
    result = await session.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    return window


@router.put("/maintenance-windows/{window_id}", response_model=MaintenanceWindowRead)
async def update_maintenance_window(
    window_id: int,
    payload: MaintenanceWindowUpdate,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a maintenance window."""
    result = await session.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    if payload.name:
        window.name = payload.name
    if payload.description is not None:
        window.description = payload.description
    if payload.start_time:
        window.start_time = payload.start_time
    if payload.end_time:
        window.end_time = payload.end_time
    if payload.device_ids is not None:
        window.device_ids = payload.device_ids
    if payload.device_group_ids is not None:
        window.device_group_ids = payload.device_group_ids
    if payload.alarm_severities is not None:
        window.alarm_severities = payload.alarm_severities
    if payload.suppress_notifications is not None:
        window.suppress_notifications = payload.suppress_notifications
    if payload.suppress_alarms is not None:
        window.suppress_alarms = payload.suppress_alarms
    if payload.mark_devices_unmonitored is not None:
        window.mark_devices_unmonitored = payload.mark_devices_unmonitored
    if payload.is_active is not None:
        window.is_active = payload.is_active
    
    await session.commit()
    await session.refresh(window)
    return window


@router.delete("/maintenance-windows/{window_id}")
async def delete_maintenance_window(
    window_id: int,
    current_user: CurrentUser = Depends(require_permissions("user.manage")),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a maintenance window."""
    result = await session.execute(
        select(MaintenanceWindow).where(MaintenanceWindow.id == window_id)
    )
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")
    
    await session.delete(window)
    await session.commit()
    
    # Audit log
    audit_service = AuditService(session)
    await audit_service.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action="maintenance_window_delete",
        resource_type="maintenance_window",
        resource_id=window_id,
    )
    
    return {"message": "Maintenance window deleted"}


# ============================================================================
# Event Routes
# ============================================================================

@router.get("/events", response_model=list[EventRead])
async def get_events(
    device_id: Optional[int] = None,
    event_type: Optional[EventType] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(require_permissions("device.read")),
    session: AsyncSession = Depends(get_async_session),
):
    """Get events with filtering."""
    query = select(Event)
    
    if device_id:
        query = query.where(Event.device_id == device_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    
    query = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()
