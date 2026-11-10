# Deployment Guide

## Environments

- local
- dev
- stg
- prd

## Required Environment Variables

| Name | Purpose |
|---|---|
| CURRENT_ENVIRONMENT | Runtime environment selector |
| SECRET_KEY | JWT signing secret |
| POSTGRES_* | Database connection settings |

<!-- --- FEATURE[redis] START --- -->
Also set `REDIS_HOST`, `REDIS_PORT`, `REDIS_USER` and `REDIS_PASS` for the Redis-backed services.
<!-- --- FEATURE[redis] END --- -->
Every optional service's variables are listed in `.env.example`.

## Deploy Steps

1. Build and release application artifact/container.
2. Apply migrations: alembic upgrade head.
3. Restart application process.
4. Run smoke checks.

## Smoke Checks

- GET /health -> 200
- GET /v1/openapi.json (non-prd) -> 200
<!-- --- FEATURE[api_v2] START --- -->
- GET /v2/openapi.json (non-prd) -> 200
<!-- --- FEATURE[api_v2] END --- -->

## Rollback

1. Redeploy previous artifact/container.
2. Roll back schema only if migration requires it.
3. Re-run smoke checks.
