"""CRTNM ASGI application entry point."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from crtnm.core.config import get_settings
from crtnm.infrastructure.database import Base, engine
from crtnm.presentation.routes import router
from crtnm.presentation.rate_limit_middleware import RateLimitMiddleware
from crtnm.infrastructure.rate_limiter import RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
app = FastAPI(title="CRTNM", version="0.1.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware, limiter=RateLimiter())
app.include_router(router)


@app.on_event("startup")
def create_development_tables() -> None:
    """Provide a frictionless SQLite development startup; production uses Alembic."""
    if settings.environment == "development":
        Base.metadata.create_all(engine)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness endpoint for deployment platforms."""
    return {"status": "ok", "service": "crtnm"}
