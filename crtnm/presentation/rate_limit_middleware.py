"""HTTP enforcement for authentication endpoint abuse."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from crtnm.infrastructure.rate_limiter import RateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limits login/bootstrap attempts by source address."""

    def __init__(self, app: object, limiter: RateLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: object) -> object:
        if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/bootstrap"}:
            host = request.client.host if request.client else "unknown"
            if not self._limiter.allow(f"auth:{host}"):
                return JSONResponse(status_code=429, content={"detail": "Too many authentication attempts; try again shortly"}, headers={"Retry-After": "60"})
        return await call_next(request)  # type: ignore[operator]
