# Architecture Overview

## System Purpose

FastAPI Template provides a reusable backend foundation for authenticated APIs with layered architecture, async persistence, Redis-backed operational capabilities, and production-oriented middleware.

## Component Map

| Component | Responsibility | Notes |
|---|---|---|
| API Layer (app/api) | Route definitions and HTTP contracts | Thin endpoints; domain errors translated to HTTP |
| Dependency Layer (app/api/*/deps) | Session-bound wiring and orchestration | Creates repositories/services per request |
| Service Layer (app/services) | Business rules and use-case logic | Raises domain exceptions, returns typed contracts |
| Repository Layer (app/repos) | Persistence and query abstraction | SQLAlchemy async CRUD and domain queries |
| Model Layer (app/models) | ORM table mapping | Shared base model and entity models |
| Schema Layer (app/schemas) | Validation and serialization | Pydantic request/response contracts |
| Core Layer (app/core) | Config, db setup, HTTP exceptions, utilities | Lowest dependency layer |
| Middleware Layer (app/middleware) | Security, CSRF, logging, rate limit headers | Applied in root app order |

## Tech Stack

| Area | Choice |
|---|---|
| Language | Python 3.13 |
| Web Framework | FastAPI |
| ASGI Server | Uvicorn (and Gunicorn in production) |
| ORM | SQLAlchemy 2 async |
| Database | PostgreSQL |
| Migrations | Alembic |
| Cache / Rate Limit / Token Revocation | Redis |
| Background Jobs | Celery |
| Auth | JWT + refresh tokens + blacklist |
| Testing | pytest + anyio |

## API Versioning and Docs Isolation

The application uses a mounted-subapp versioning model:

- Root app in app/main.py exposes operational endpoints only (for example /health).
- Root app does not expose global /docs, /redoc, or /openapi.json.
- Version app mounts:
  - /v1 -> /v1/docs, /v1/redoc, /v1/openapi.json
  - /v2 -> /v2/docs, /v2/redoc, /v2/openapi.json

This keeps OpenAPI schemas isolated by version and allows independent evolution of each API surface.

## Request Data Flow

1. Request reaches root app middleware chain (security headers, CSRF, rate-limit headers, logging).
2. Request is routed to root endpoints (for example /health) or a mounted version app (/v1 or /v2).
3. Endpoint dependencies assemble service objects and repositories with request-scoped session.
4. Service executes business logic and calls repositories as needed.
5. API layer maps domain exceptions to HTTP responses and returns schema-validated output.

## Middleware Notes

- SecurityHeadersMiddleware uses route-aware CSP so Swagger/ReDoc can load safely on versioned docs paths.
- CSRFMiddleware exempts auth and versioned docs/openapi paths.
- RateLimitHeaderMiddleware injects rate-limit headers when dependency state exists.
- LoggingMiddleware records request lifecycle metadata.

## Current Constraints

- Version 2 is scaffolded and mounted; endpoint surface is intentionally minimal at this stage.
- Compatibility aliases for legacy /api/v1 paths are not enabled.
- Production docs remain environment-gated through app configuration.
