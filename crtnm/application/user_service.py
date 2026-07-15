"""Administrative user lifecycle use cases."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.core.security import hash_password
from crtnm.domain.enums import UserRole
from crtnm.infrastructure.models import UserModel


class UserService:
    """Creates accounts while preserving the no-plaintext-password rule."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    def create(self, session: Session, actor: str, username: str, password: str, role: UserRole) -> UserModel:
        """Create a role-based account with a securely derived password hash."""
        if session.scalar(select(UserModel).where(UserModel.username == username)):
            raise ValueError("Username already exists")
        user = UserModel(username=username, password_hash=hash_password(password), role=role.value)
        session.add(user); self._audit.record(session, actor, "user.create", username, f"Role: {role.value}"); session.commit(); session.refresh(user)
        return user

    @staticmethod
    def list_users(session: Session) -> list[UserModel]:
        """Return user metadata only; hashes are never exposed."""
        return list(session.scalars(select(UserModel).order_by(UserModel.username)))
