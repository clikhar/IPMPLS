"""Versioned CRTNM REST endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.application.auth_service import AuthService
from crtnm.application.inventory_service import InventoryService
from crtnm.application.configuration_service import ConfigurationService
from crtnm.application.network_change_service import NetworkChangeService
from crtnm.application.network_command_factory import NetworkCommandFactory
from crtnm.application.monitoring_service import MonitoringService
from crtnm.application.report_service import ReportService
from crtnm.application.user_service import UserService
from crtnm.domain.enums import UserRole
from crtnm.drivers import registry
from crtnm.drivers.exceptions import DriverError
from crtnm.drivers.neon import NeonDriver
from crtnm.infrastructure.database import get_session
from crtnm.infrastructure.models import AuditLogModel
from crtnm.presentation.dependencies import get_current_user, require_role
from crtnm.presentation.schemas import AlarmRead, AuditLogRead, BackupRead, CommandOutput, ComparisonRead, ConnectionCommand, ConnectionTestRead, Credentials, CurrentUser, DashboardSummaryRead, DeviceCreate, DeviceRead, DeviceUpdate, HealthSnapshotRead, InterfacePlanCreate, InterfaceStatusRead, MplsPlanCreate, NetworkPlanRead, RecoverySimulationCreate, RecoverySimulationRead, RestorePreviewRead, StaticRoutePlanCreate, StationCreate, StationRead, TokenResponse, TopologyRead, UserCreate, UserRead, VlanPlanCreate
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
def create_station(payload: StationCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> StationRead:
    try:
        return inventory.create_station(session, str(user.id), **payload.model_dump())
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Station name already exists") from error


@router.get("/devices", response_model=list[DeviceRead])
def list_devices(_: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[DeviceRead]:
    return inventory.list_devices(session)


@router.post("/devices", response_model=DeviceRead, status_code=201)
def create_device(payload: DeviceCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> DeviceRead:
    try:
        return inventory.create_device(session, str(user.id), payload.model_dump(mode="json"))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Device name or management IP already exists") from error

@router.put("/devices/{device_id}",response_model=DeviceRead,)
def update_device(device_id: int,payload: DeviceUpdate,user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),session: Session = Depends(get_session),):
    return inventory.update_device(
        session,
        str(user.id),
        device_id,
        payload.model_dump(mode="json"),
    )

@router.get("/devices/{device_id}",response_model=DeviceRead,)
def get_device(
    device_id: int,
    user=Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER)),
    session: Session = Depends(get_session),
):
    return inventory.get_device(session, device_id)

@router.delete(
    "/devices/{device_id}",
    status_code=204,
)
def delete_device(
    device_id: int,
    user=Depends(require_role(UserRole.ADMIN)),
    session: Session = Depends(get_session),
):
    inventory.delete_device(
        session,
        str(user.id),
        device_id,
    )
    
@router.post("/devices/{device_id}/connection-test", response_model=ConnectionTestRead)
def connection_test(device_id: int,  user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> ConnectionTestRead:
    """Perform a safe `show version` connectivity test; arbitrary commands are not accepted."""
    try:
        facts = inventory.test_device(session, str(user.id), device_id, registry)
        return ConnectionTestRead(device_id=device_id, **facts.__dict__)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/devices/{device_id}/commands/read-only", response_model=CommandOutput)
def execute_readonly_command(device_id: int, payload: ConnectionCommand, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> CommandOutput:
    """Run one driver-vetted show command and record its execution."""
    try:
        return CommandOutput(device_id=device_id, output=inventory.execute_readonly(session, str(user.id), device_id, payload.command, registry))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, DriverError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/devices/{device_id}/backups", response_model=BackupRead, status_code=201)
def capture_backup(device_id: int, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> BackupRead:
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
def restore_preview(backup_id: int, user: CurrentUser = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)) -> RestorePreviewRead:
    try:
        return RestorePreviewRead(**configuration.restore_preview(session, str(user.id), backup_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/recovery-simulations", response_model=RecoverySimulationRead, status_code=201)
def simulate_recovery(device_id: int, payload: RecoverySimulationCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)) -> RecoverySimulationRead:
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
def plan_vlan(device_id: int, payload: VlanPlanCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.vlan(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/interface", response_model=NetworkPlanRead, status_code=201)
def plan_interface(device_id: int, payload: InterfacePlanCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.interface(payload), session)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=422 if isinstance(error, ValueError) else 404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/static-route", response_model=NetworkPlanRead, status_code=201)
def plan_route(device_id: int, payload: StaticRoutePlanCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.static_route(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/devices/{device_id}/plans/mpls", response_model=NetworkPlanRead, status_code=201)
def plan_mpls(device_id: int, payload: MplsPlanCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> NetworkPlanRead:
    try:
        return _plan_response(device_id, str(user.id), *NetworkCommandFactory.mpls(payload), session)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/devices/{device_id}/plans", response_model=list[NetworkPlanRead])
def list_network_plans(device_id: int, _: CurrentUser = Depends(get_current_user), session: Session = Depends(get_session)) -> list[NetworkPlanRead]:
    """Return all non-executing change previews for a device."""
    return [NetworkPlanRead(id=item.id, device_id=item.device_id, operation=item.operation, commands=json.loads(item.commands), summary=item.summary, status=item.status, created_at=item.created_at) for item in network_changes.list_plans(session, device_id)]


@router.post("/devices/{device_id}/monitoring/poll", response_model=HealthSnapshotRead, status_code=201)
def poll_device(device_id: int, user: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> HealthSnapshotRead:
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
def list_audit_logs(_: CurrentUser = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)) -> list[AuditLogRead]:
    """Return the latest audit events for security review."""
    return list(session.query(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(500))


@router.get("/reports/inventory/{format}")
def export_inventory(format: str, _: CurrentUser = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)), session: Session = Depends(get_session)) -> Response:
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
def create_user(payload: UserCreate, user: CurrentUser = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)) -> UserRead:
    """Create a role-based CRTNM user."""
    try:
        return users.create(session, str(user.id), payload.username, payload.password, payload.role)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/users", response_model=list[UserRead])
def list_users(_: CurrentUser = Depends(require_role(UserRole.ADMIN)), session: Session = Depends(get_session)) -> list[UserRead]:
    """List user metadata, never password material."""
    return users.list_users(session)
