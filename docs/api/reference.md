# API Reference

## Base URLs

- Service base: <http://localhost:8799>
- Root operational endpoint: /health
- Versioned API base: /v1
<!-- --- FEATURE[api_v2] START --- -->
- Second API version (empty scaffold): /v2
<!-- --- FEATURE[api_v2] END --- -->

## Documentation Endpoints

When environment is LOCAL, DEV, or STG:

- /v1/docs
- /v1/redoc
- /v1/openapi.json
<!-- --- FEATURE[api_v2] START --- -->
- /v2/docs
- /v2/redoc
- /v2/openapi.json
<!-- --- FEATURE[api_v2] END --- -->

Root /docs, /redoc, and /openapi.json are intentionally disabled.

## Authentication Endpoints (v1)

- POST /v1/auth/login
- POST /v1/auth/signup
- POST /v1/auth/refresh-token
- POST /v1/auth/logout

## User Endpoints (v1)

- GET /v1/users/me

## Health Endpoint

- GET /health

## Auth Header

Use bearer token for protected routes:

- Authorization: Bearer <access_token>

## Error Format

Errors follow FastAPI/HTTP exception responses with a detail field.

Example:

```json
{
  "detail": "Unauthorized"
}
```

## Status Code Conventions

- 200: Success
- 201: Created
- 400: Bad request/domain validation failure mapping
- 401: Authentication failure
- 403: Forbidden/CSRF violations
- 404: Not found
<!-- --- FEATURE[redis_rate_limit] START --- -->
- 429: Rate limited
<!-- --- FEATURE[redis_rate_limit] END --- -->
- 500: Unexpected server error
