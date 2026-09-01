# API Governance

Source: `docs/backend-architecture.md` ("API Governance", "Repository Profile Appendix")
plus the real `app/main.py` (snapshotted in `../assets/`).

## The dual mounted-sub-app pattern — this repo's actual routing shape

`app/main.py` builds three separate FastAPI instances:

```python
app = FastAPI(title=..., openapi_url=None, docs_url=None, redoc_url=None, lifespan=lifespan, ...)

def _create_versioned_app(version: str) -> FastAPI:
    docs_enabled = settings.current_environment in {Environment.LOCAL, Environment.DEV, Environment.STG}
    return FastAPI(
        title=f"{settings.app_title} {version.upper()}",
        openapi_url="/openapi.json" if docs_enabled else None,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}",
    )

v1_app = _create_versioned_app("v1")
v1_app.include_router(api_v1_router)
v2_app = _create_versioned_app("v2")
v2_app.include_router(api_v2_router)

app.mount("/v1", v1_app)
app.mount("/v2", v2_app)
```

Consequences that matter every time you touch routing or write tests:

- **Root app never exposes docs** (`openapi_url=docs_url=redoc_url=None`, unconditionally)
  — only `GET /health` lives on root, via `app/api/routes.py`.
- **Docs are only enabled in `{LOCAL, DEV, STG}`, never `PRD`** — don't "fix" a missing
  `/v1/docs` in production; that's intentional.
- Every route path is prefixed by its mount point: `/v1/...`, `/v2/...`. There is no
  bare, unversioned `/api/...` path — if you see one referenced (some legacy docs still
  do), it's stale.
- `generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}"` gives clean
  OpenAPI `operationId`s per version instead of FastAPI's default (which stringifies the
  full function path and gets unreadable fast).
- **v2 exists today as an empty stub router** (`app/api/v2/router.py` — just an
  `APIRouter()` with nothing included) — it demonstrates the versioning pattern without
  duplicating v1's logic yet. Don't assume v2 has parity with v1's endpoints.

### The test-override gotcha (this trips people up constantly)

Because there are three separate FastAPI app instances, **a dependency override on `app`
does not propagate to `v1_app` or `v2_app`**. Every test fixture that overrides
`get_session` (or any other dependency reachable from versioned routes) must apply the
override to all three explicitly:

```python
app.dependency_overrides[get_session] = override_get_session
v1_app.dependency_overrides[get_session] = override_get_session
v2_app.dependency_overrides[get_session] = override_get_session
```

The real `tests/conftest.py` (`../assets/tests/conftest.py`) does exactly this in its
`test_app` fixture — use it as the reference, not the simplified single-`app` examples
that show up in generic FastAPI testing tutorials.

## Middleware registration order (outermost first)

From `app/main.py`, in this exact order:

1. `CORSMiddleware`
2. `SecurityHeadersMiddleware`
3. `CSRFMiddleware`
4. `RateLimitHeaderMiddleware`
5. `LoggingMiddleware`

Order matters — e.g. `SecurityHeadersMiddleware` needs to see (and be able to override)
headers on the way out for both docs and non-docs paths, and `LoggingMiddleware` wraps
closest to the actual handler so its timing measurement is accurate. Don't reorder
without understanding what each middleware assumes about what ran before it — see
[auth-and-security.md](auth-and-security.md) for what each one actually does.

## Version deprecation lifecycle

- Deprecation decisions are approved by the owner of the affected API surface, case by
  case — there's no automatic sunset policy.
- Every deprecation MUST document: impacted routes, migration path, client notice plan,
  target sunset date.
- Prefer backward-compatible changes over a new major version when feasible.

## Pagination standard

| Pattern | Use when | Strengths | Trade-offs |
|---|---|---|---|
| Offset (`limit`, `offset`) | Small/mostly-static datasets, admin panels | Simple for humans and SQL tooling | Drift/duplicate risk under frequent writes |
| Cursor (`limit`, `cursor`) | Large or rapidly-changing datasets | Stable paging, scales better | More complex client implementation |

Rules: every endpoint must document which mode it uses, enforce an explicit max `limit`,
and cursor pagination should sort on stable indexed keys (`created_at`, `id`).

## Filtering / sorting conventions

- Explicit filter parameter names (`status`, `created_before`, `created_after`) —
  not a generic `filter` blob.
- Sorting via `sort_by` + `sort_order` (`asc`/`desc`) with a documented default.
- Invalid filters/sorts return `400` with a deterministic validation message.

## Error envelope (recommended machine-consumable shape)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [{"field": "email", "issue": "Invalid format"}]
  },
  "requestId": "req_123"
}
```

Keep the [canonical exception-contract matrix](layering-and-flow.md) as the single
source of truth, and make sure every endpoint's `responses={}` documents the errors it
can actually produce (including any Deps-layer translation).

## Idempotency and concurrency for writes

- Write endpoints SHOULD accept an `Idempotency-Key` header for retry safety.
- Services SHOULD apply optimistic concurrency (`version` column or ETag) on conflicting
  updates — see the locking decision matrix in
  [layering-and-flow.md](layering-and-flow.md).
- If idempotency is implemented in Deps or the service, the endpoint's docs MUST
  describe the contract and replay behavior explicitly — don't leave it as undocumented
  behavior a client has to discover.

## Authorization model — owner checks first

This repo starts with owner-based authorization, not RBAC/ABAC, and evolves only when
needed:

```python
OWNER_POLICY_MAP: dict[str, str] = {
    "user_profile": "user_id",
    "session": "user_id",
    "organization_membership": "tenant_id",
}
```

- Ownership rules are explicit per resource type — no hidden assumptions.
- Authorization checks run **before** mutation operations.
- Return `403` for authorization failures, not `404`, unless concealment is an explicit,
  deliberate security policy for that resource.
- Move to RBAC/ABAC only when: shared resources need role-based collaboration,
  cross-tenant admin actions appear, or policy depends on attributes beyond ownership
  (region, tier, environment). Don't build RBAC speculatively — this repo currently has
  no roles table; `User` is the only concrete model.
