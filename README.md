# CRTNM — Central Railway Telecom Network Manager

CRTNM is an enterprise network-management platform for railway MPLS infrastructure. This repository currently contains **Milestone 1**, a runnable, secure application foundation.

## What is included

- FastAPI backend structured into domain, application, infrastructure, and presentation layers
- JWT authentication with roles (`admin`, `operator`, `viewer`)
- Encrypted device credentials (Fernet) and immutable audit events
- Station and device inventory APIs with ownership checks
- Pluggable driver registry with NEON SSH/Telnet read-only connectivity checks
- Sanitized, checksummed configuration backups; diff, restore preview, and recovery simulation APIs
- Validated MPLS, VLAN, interface, and static-route change previews with no execution capability
- Read-only health polling with CPU, memory, temperature, interface, LLDP, and threshold-alarm persistence
- Protected inventory downloads in CSV, Excel, and PDF; audit-log and role-based user administration APIs
- Docker Compose production stack with PostgreSQL, Redis, Celery monitoring workers, and auth rate limiting
- Responsive inventory, monitoring, LLDP topology, configuration, administration, and dashboard screens
- Alembic database migration, SQLite development configuration, and PostgreSQL-ready URL configuration
- React/TypeScript dark-theme application shell with protected routes and dashboard

## Start the backend

1. Copy `.env.example` to `.env` and set long random values for `CRTNM_SECRET_KEY` and `CRTNM_FERNET_KEY`.
2. `python -m venv .venv`
3. `.venv\\Scripts\\pip install -e ".[dev]"`
4. `alembic upgrade head`
5. `uvicorn crtnm.main:app --reload`

The first user is created by `POST /api/v1/auth/bootstrap`, which is only available until an account exists.

## Start the frontend

`cd frontend; npm install; npm run dev`

Set `VITE_API_BASE_URL` if the API is not served at `http://localhost:8000/api/v1`.

## Safety model

Passwords never appear in API responses, logs, or audit details. Configuration changes and network commands will be introduced in later milestones with mandatory previews, explicit confirmations, and audit logging.
