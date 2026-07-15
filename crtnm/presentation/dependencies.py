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

