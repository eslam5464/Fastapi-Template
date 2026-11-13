# Architecture Overview

## System Purpose

FastAPI Template provides a reusable backend foundation for APIs with layered architecture, async persistence, and production-oriented middleware.

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
| Middleware Layer (app/middleware) | Logging and the other request middleware | Applied in root app order |

## Tech Stack

| Area | Choice |
|---|---|
| Language | Python 3.14 |
| Web Framework | FastAPI |
| ASGI Server | Uvicorn (and Gunicorn in production) |
| ORM | SQLAlchemy 2 async |
| Database | PostgreSQL |
| Migrations | Alembic |
| Testing | pytest + anyio |

<!-- --- FEATURE[auth|example_items|redis|celery] START --- -->
Optional parts of this project:

<!-- --- FEATURE[auth|example_items|redis|celery] END --- -->
<!-- --- FEATURE[auth] START --- -->
- **Authentication** — JWT access and refresh tokens with the User model (`app/services/auth_service.py`)
<!-- --- FEATURE[auth] END --- -->
<!-- --- FEATURE[example_items] START --- -->
- **Example domain** — Items, a complete CRUD slice under `/v1/items` (`app/services/item_service.py`)
<!-- --- FEATURE[example_items] END --- -->
<!-- --- FEATURE[redis] START --- -->
- **Redis** — backs the services below that need it
<!-- --- FEATURE[redis] END --- -->
<!-- --- FEATURE[redis_cache] START --- -->
  - cache (`app/services/cache/manager.py`)
<!-- --- FEATURE[redis_cache] END --- -->
<!-- --- FEATURE[redis_rate_limit] START --- -->
  - rate limiting (`app/services/cache/rate_limiter.py`)
<!-- --- FEATURE[redis_rate_limit] END --- -->
<!-- --- FEATURE[redis_token_blacklist] START --- -->
  - token revocation on logout (`app/services/cache/token_blacklist.py`)
<!-- --- FEATURE[redis_token_blacklist] END --- -->
<!-- --- FEATURE[celery] START --- -->
- **Celery** — background jobs (`app/services/task_queue/`), with Redis as the broker
<!-- --- FEATURE[celery] END --- -->

## API Versioning and Docs Isolation

The application uses a mounted-subapp versioning model:

- Root app in app/main.py exposes operational endpoints only (for example /health).
- Root app does not expose global /docs, /redoc, or /openapi.json.
- Version app mounts:
  - /v1 -> /v1/docs, /v1/redoc, /v1/openapi.json
<!-- --- FEATURE[api_v2] START --- -->
  - /v2 -> /v2/docs, /v2/redoc, /v2/openapi.json
<!-- --- FEATURE[api_v2] END --- -->

This keeps OpenAPI schemas isolated by version and allows independent evolution of each API surface.

## Request Data Flow

1. Request reaches root app middleware chain (logging and the other middleware of this project).
2. Request is routed to root endpoints (for example /health) or a mounted version app (for example /v1).
3. Endpoint dependencies assemble service objects and repositories with request-scoped session.
4. Service executes business logic and calls repositories as needed.
5. API layer maps domain exceptions to HTTP responses and returns schema-validated output.

## Middleware Notes

<!-- --- FEATURE[security_headers] START --- -->
- SecurityHeadersMiddleware uses route-aware CSP so Swagger/ReDoc can load safely on versioned docs paths.
<!-- --- FEATURE[security_headers] END --- -->
<!-- --- FEATURE[csrf] START --- -->
- CSRFMiddleware exempts the versioned docs/openapi paths (and the auth endpoints, where the project has them).
<!-- --- FEATURE[csrf] END --- -->
<!-- --- FEATURE[redis_rate_limit] START --- -->
- RateLimitHeaderMiddleware injects rate-limit headers when dependency state exists.
<!-- --- FEATURE[redis_rate_limit] END --- -->
- LoggingMiddleware records request lifecycle metadata.

## Current Constraints

<!-- --- FEATURE[api_v2] START --- -->
- The second API version (/v2) is scaffolded and mounted; its endpoint surface is intentionally empty at this stage.
<!-- --- FEATURE[api_v2] END --- -->
- Compatibility aliases for legacy /api/v1 paths are not enabled.
- Production docs remain environment-gated through app configuration.
