# Auth & Security

Source: `docs/backend-architecture.md` ("Middleware Layer" section) plus the real
`app/middleware/{csrf,security_headers,rate_limit}.py` and
`app/api/v1/deps/rate_limit.py` (all snapshotted in `../assets/`), and
`app/services/auth_service.py` / `app/services/cache/token_blacklist.py` (described here
from repository inspection — read those two files directly before modifying auth logic,
since they aren't snapshotted in `assets/`).

## JWT authentication

Only in projects generated with `include_auth` (check that `app/services/auth_service.py`
exists). The minimal base has **no authentication**: no User model, no `/auth` or
`/users` routes and no `get_current_user`, so every route is public until the project
adds its own access checks. The token blacklist, per-user rate limits
(`app/api/v1/deps/rate_limit_user.py`) and the Celery user-seeding task all require it.

- Access + refresh tokens, each carrying a `jti` claim (enables per-token revocation),
  `iat`, a `type` claim (`"access"` vs `"refresh"` — checked on validation so a refresh
  token can't be used where an access token is expected), and `sub`.
- `AuthService.create_access_token` / `create_refresh_token` build these; token
  encoding/decoding uses `python-jose`.
- `get_current_user` (in `app/api/v1/deps/auth.py`) validates signature, expiry,
  `type == "access"`, that the token isn't revoked, and that the user still exists —
  translating `ValidationError`/`ResourceNotFoundError` into `UnauthorizedException`.
  `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")`.

## Password hashing and the timing-attack guard

- `pwdlib[argon2]`, `PasswordHash.recommended()` — Argon2, not bcrypt directly.
- Login pre-computes a dummy hash and verifies against it when the user doesn't exist, so
  a nonexistent-user login attempt takes the same time as a wrong-password attempt on a
  real user — this prevents timing-based user-enumeration (OWASP-referenced in the real
  code). **Don't "simplify" a login flow by early-returning on user-not-found** — that
  reintroduces the timing leak.
- `tests/conftest.py` (`../assets/tests/conftest.py`) pre-computes the test password hash
  **once**, session-scoped (`pre_hashed_password` fixture), specifically to avoid paying
  the Argon2 cost repeatedly across hundreds of tests. Follow this pattern for any new
  test fixtures that need a hashed password.

## Token blacklist (Redis-backed revocation)

Present only in projects generated with the `include_redis_token_blacklist` Copier
toggle (guide: `docs/integrations/token-revocation.md`). **Without it, logout cannot
revoke anything:** `POST /v1/auth/logout` still validates the token but returns
`revoked: false`, and the access token stays valid until it expires. Say so when a
user asks about logout or session security in such a project, and recommend short
token lifetimes or adding the blacklist.

`app/services/cache/token_blacklist.py` exposes `revoke_token(jti, ttl)`,
`is_revoked(jti)`, `revoke_all_user_tokens(user_id, ttl)` (marker-based — for
password-change-triggered mass revocation), and `get_user_revocation_time`. It's a
**no-op in the `LOCAL` environment** (Redis isn't assumed to be running locally by
default) — don't write a test that asserts revocation actually blocks a token unless the
test environment is non-`LOCAL` or Redis is genuinely available.

## CSRF — double-submit cookie pattern

Only in projects generated with `include_csrf` (check that `app/middleware/csrf.py`
exists). A project without it has no CSRF check at all: that is fine for an API whose
clients send a bearer token in the `Authorization` header, and a gap to close before
browser clients authenticate with cookies.

Real code in `../assets/app/middleware/csrf.py`:

- Safe methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`) skip validation entirely.
- **Skipped entirely in `LOCAL`** — don't expect CSRF enforcement when developing locally.
- Exempt paths: the four auth endpoints (`/v1/auth/login`, `/signup`, `/refresh-token`,
  `/logout`), `/health`, and all docs/OpenAPI paths for both versions (exact + prefix
  match, so `/v1/docs/oauth2-redirect` etc. are covered too).
- Validation: `X-CSRF-Token` header must match the `csrf_token` cookie, compared with
  `secrets.compare_digest` (constant-time, prevents timing attacks on the comparison
  itself).
- Cookie is `samesite="strict"`, `secure=True` only in `{STG, PRD}` (not `LOCAL`/`DEV`,
  where the app usually isn't served over HTTPS), `httponly=False` (must be readable by
  JS to be echoed back in the header — that's the point of double-submit).
- If you add a new endpoint that legitimately needs to be CSRF-exempt (e.g. a webhook
  receiver), add its exact path or a prefix to `EXEMPT_PATHS`/the prefix tuple — don't
  disable the middleware wholesale.

## Security headers + dual CSP

Real code in `../assets/app/middleware/security_headers.py`. Every response gets OWASP
baseline headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, a
restrictive `Permissions-Policy`, and (only in `{STG, PRD}`) HSTS with
`includeSubDomains; preload`.

**Two different Content-Security-Policy values**, chosen by path:

- `DOCS_CSP` — looser, allows `cdn.jsdelivr.net`/`unpkg.com`/Google Fonts, applied only
  to `/v{1,2}/docs` and `/v{1,2}/redoc` (Swagger UI and ReDoc need external script/style
  sources to render).
- `DEFAULT_CSP` — strict, `'self'`-only, applied to everything else.

If you add a new docs-like UI that needs relaxed CSP, extend `DOCS_PATH_PREFIXES` rather
than loosening `DEFAULT_CSP` globally.

## Rate limiting — sliding window over Redis

Present only in projects generated with the `include_redis_rate_limit` Copier toggle
(guide: `docs/integrations/rate-limiting.md`). Without it no route has a request
limit, so recommend a limit at the reverse proxy or gateway instead.

`app/api/v1/deps/rate_limit.py` (`../assets/`) implements a **sliding-window algorithm**
via Redis sorted sets (`ZADD`/`ZREMRANGEBYSCORE`/`ZCARD`, microsecond-precision scores).
Named tiers, each a FastAPI dependency:

| Dependency | Limit | Key basis | Use case |
|---|---|---|---|
| `rate_limit_auth` | 10/min | IP | Login/signup — brute-force protection |
| `rate_limit_api` | 100/min | IP | General API protection |
| `rate_limit_public` | 1000/min | IP | Health checks, public/read endpoints |
| `rate_limit_user` (in `deps/rate_limit_user.py`, only with auth) | 300/min | user ID | Authenticated endpoints, fair per-user limits |

Plus **factory functions** for custom limiters when the named tiers don't fit:
`create_rate_limit_ip_only(limit, window, prefix)` in `deps/rate_limit.py`, and, in
`deps/rate_limit_user.py` (only with auth),
`create_rate_limit_user_only(limit, window, prefix)`,
`create_rate_limit_user_and_ip(limit, window, prefix)` and the dispatcher
`create_rate_limit(limit, window, prefix, user_based=False)`. Use these instead of
writing a new ad-hoc limiter when an endpoint needs a limit the named tiers don't cover
(the module's own docstrings show export examples, e.g. a 5-per-5-minutes export
limiter).

Each limiter stores its result in `request.state.rate_limit_info` and raises
`TooManyRequestsException` (429) with `X-RateLimit-*` headers pre-populated when the
limit is exceeded. **Fails open** on Redis unavailability — a Redis outage doesn't take
down the API, it just stops rate-limiting (a documented, deliberate trade-off).

`RateLimitHeaderMiddleware` (`../assets/app/middleware/rate_limit.py`) is the other half
of this design: it's a thin middleware that just copies whatever `request.state.
rate_limit_info` a dependency already set into `X-RateLimit-{Limit,Remaining,Reset}`
response headers. This split (dependency does the check + raises on violation, middleware
only adds headers) means the header injection is automatic on any route with a rate-limit
dependency, with zero duplicated header-setting code per endpoint.

## Middleware registration order

See [api-governance.md](api-governance.md) — `CORSMiddleware` → `SecurityHeadersMiddleware`
→ `CSRFMiddleware` → `RateLimitHeaderMiddleware` → `LoggingMiddleware`, outermost first
(`CSRFMiddleware` and `RateLimitHeaderMiddleware` only where the project has them).
