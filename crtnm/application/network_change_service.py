"""Validated dry-run plans for MPLS, VLAN, interface, and route operations."""
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.infrastructure.models import DeviceModel, NetworkChangePlanModel


class NetworkChangeService:
    """Produces vendor-neutral reviewed plans with no device side effects."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    def create_plan(self, session: Session, actor: str, device_id: int, operation: str, commands: list[str], summary: str) -> NetworkChangePlanModel:
        """Persist an immutable preview for later change-window approval."""
        device = session.get(DeviceModel, device_id)
        if device is None:
            raise LookupError("Device does not exist")
        plan = NetworkChangePlanModel(device_id=device_id, operation=operation, commands=json.dumps(commands), summary=summary, created_by=actor)
        session.add(plan)
        self._audit.record(session, actor, "network.change_preview", device.name, f"Operation: {operation}")
        session.commit(); session.refresh(plan)
        return plan

    @staticmethod
    def list_plans(session: Session, device_id: int) -> list[NetworkChangePlanModel]:
        """Return stored previews for review, newest first."""
        return list(session.scalars(select(NetworkChangePlanModel).where(NetworkChangePlanModel.device_id == device_id).order_by(NetworkChangePlanModel.id.desc())))
