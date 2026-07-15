"""Centralized audit trail writer."""
from sqlalchemy.orm import Session
from crtnm.infrastructure.models import AuditLogModel


class AuditService:
    """Records security-relevant actions without exposing secrets."""

    def record(self, session: Session, actor: str, action: str, target: str, detail: str | None = None) -> None:
        session.add(AuditLogModel(actor=actor, action=action, target=target, detail=detail))

