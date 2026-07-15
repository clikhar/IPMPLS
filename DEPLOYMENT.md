# CRTNM production deployment

## Prerequisites

- Docker Engine with Compose support
- TLS termination provided by the organisation's approved reverse proxy
- Long random `CRTNM_SECRET_KEY`, `CRTNM_FERNET_KEY`, and `POSTGRES_PASSWORD` values stored in the deployment secret manager

## Deploy

1. Create an environment file from `.env.example`; set `CRTNM_ENVIRONMENT=production`, PostgreSQL password, and all secrets.
2. Build and start the services: `docker compose up -d --build`.
3. Apply migrations from the API image: `docker compose exec api alembic upgrade head`.
4. Verify `/health`, then create the initial administrator using the single-use bootstrap endpoint.

## Operations

- The worker/beat pair polls all registered devices every five minutes using only read-only commands.
- Redis backs Celery and the authentication rate limit. Do not expose Redis or PostgreSQL ports outside the private deployment network.
- Back up PostgreSQL and the managed secrets independently. Configuration backups do not include credentials.
- Use an HTTPS reverse proxy, restrict CORS to the deployed frontend origin, and rotate the JWT/Fernet keys according to Railway policy.
