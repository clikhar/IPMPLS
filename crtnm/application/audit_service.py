"""Centralized audit trail writer."""
from sqlalchemy.orm import Session
from crtnm.infrastructure.models import AuditLog


class AuditService:
    """Records security-relevant actions without exposing secrets."""

    def record(self, session: Session, actor: str, action: str, target: str, detail: str | None = None) -> None:
        session.add(AuditLog(username=actor, action=action, resource_name=target))

