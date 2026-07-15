"""Authentication use cases."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from crtnm.application.audit_service import AuditService
from crtnm.core.security import create_access_token, hash_password, verify_password
from crtnm.domain.enums import UserRole
from crtnm.infrastructure.models import UserModel


class AuthService:
    """Manages account bootstrap and credential verification."""

    def __init__(self, audit: AuditService) -> None:
        self._audit = audit

    def bootstrap(self, session: Session, username: str, password: str) -> UserModel:
        """Create the first administrative account once."""
        if session.scalar(select(UserModel.id).limit(1)) is not None:
            raise ValueError("Bootstrap is no longer available")
        user = UserModel(username=username, password_hash=hash_password(password), role=UserRole.ADMIN.value)
        session.add(user)
        self._audit.record(session, username, "auth.bootstrap", "user", "Initial administrator created")
        session.commit()
        return user

    def login(self, session: Session, username: str, password: str) -> str:
        """Authenticate a user and issue an access token."""
        user = session.scalar(select(UserModel).where(UserModel.username == username))
        if user is None or not verify_password(password, user.password_hash):
            self._audit.record(session, username, "auth.login_failed", "session")
            session.commit()
            raise PermissionError("Invalid username or password")
        self._audit.record(session, user.username, "auth.login", "session")
        session.commit()
        return create_access_token(str(user.id), user.role)

