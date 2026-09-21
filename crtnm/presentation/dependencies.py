"""HTTP security dependencies."""
from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from crtnm.core.security import decode_access_token
from crtnm.domain.enums import UserRole
from crtnm.presentation.schemas import CurrentUser

bearer = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> CurrentUser:
    """Extract the authenticated principal from an Authorization header."""
    try:
        payload = decode_access_token(credentials.credentials)
        return CurrentUser(id=int(payload["sub"]), role=UserRole(payload["role"]))
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from error


def require_role(*roles: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    """Create a dependency that permits only the supplied roles."""
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker


def require_permissions(*permissions: str) -> Callable[[CurrentUser], CurrentUser]:
    """Create a dependency that requires specific permissions.
    
    For now, this is a simplified implementation that checks role-based access.
    In production, this would check against actual permission assignments.
    """
    # Role hierarchy for permission mapping
    role_permissions = {
        UserRole.SUPER_ADMIN: set([
            "device.read", "device.create", "device.update", "device.delete", "device.command",
            "config.read", "config.backup", "config.deploy",
            "alarm.ack", "alarm.resolve", "alarm.suppress",
            "user.manage", "user.create", "user.delete",
            "notification.manage", "maintenance.manage",
        ]),
        UserRole.NETWORK_ADMIN: set([
            "device.read", "device.create", "device.update", "device.delete", "device.command",
            "config.read", "config.backup", "config.deploy",
            "alarm.ack", "alarm.resolve", "alarm.suppress",
            "user.manage", "user.create",
            "notification.manage", "maintenance.manage",
        ]),
        UserRole.NETWORK_ENGINEER: set([
            "device.read", "device.create", "device.update", "device.command",
            "config.read", "config.backup", "config.deploy",
            "alarm.ack", "alarm.resolve",
        ]),
        UserRole.OPERATOR: set([
            "device.read", "device.command",
            "config.read", "config.backup",
            "alarm.ack",
        ]),
        UserRole.VIEWER: set([
            "device.read", "config.read",
        ]),
        UserRole.AUDITOR: set([
            "device.read", "config.read", "alarm.ack",
        ]),
    }
    
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_permissions = role_permissions.get(user.role, set())
        
        # Check if user has at least one of the required permissions
        # or if they're SUPER_ADMIN (full access)
        if user.role == UserRole.SUPER_ADMIN:
            return user
        
        for perm in permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {perm}"
                )
        
        return user
    
    return checker

