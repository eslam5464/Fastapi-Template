# Layering & Data Flow

Source: `docs/backend-architecture.md` ("Overview", "Data Flow", "Dependency Direction
Rules" sections) plus `app/main.py`, `tach.toml` (both snapshotted in `../assets/`).

## The six layers

```
Client → API → Deps → Service → Repository → Model → DB
                  ↘                ↗
                    (Deps creates repos & injects into services)
Core and Schema are low-level, shared by everyone above them.
```

| Layer | Location | Responsibility | Depends on |
|---|---|---|---|
| API | `app/api/` | HTTP routing, domain→HTTP exception translation, final `except Exception` + `logger.exception(...)` | Deps, Schemas, Core |
| Deps | `app/api/*/deps/`, factories in `deps/services.py` | Session ownership, repo/service wiring, atomic-transaction orchestration | Services, Repos, Schemas, Core |
| Service | `app/services/` | Business logic, domain rules, domain exceptions, `TypedDict` contracts | Repos, `app/services/types`, Cache |
| Repository | `app/repos/` | CRUD, query building, `auto_commit` support | Models, Schemas |
| Schema | `app/schemas/` | Validation, serialization (Pydantic v2) | Core (enums/shared primitives only) |
| Model | `app/models/` | SQLAlchemy ORM table mapping | Core (`Base` only) |
| Core | `app/core/` | Config, HTTP exceptions, DB setup — no business logic | Nothing |

`app.main`, `app.web`, and `app.alembic` are the composition root and are deliberately
**not** covered by `tach.toml`'s module graph (see `../assets/tach.toml`) — they're
allowed to touch every layer because wiring the app together is their job.

## Import rules (enforced by `tach.toml`, not just documented)

| Layer | Can import | Cannot import |
|---|---|---|
| API | Deps, Schemas, Core | Services, Repos, Models |
| Deps | Services, Repos, Schemas, Core | API, Models |
| Service | Repos, Schemas, Core, Cache | API, Deps, Models |
| Repository | Models, Schemas | API, Deps, Services |
| Schema | Core (enums only) | everything else |
| Model | Core (`Base` only) | everything else |
| Core | nothing | everything else |

If two layers need to share a type and the natural import would go the wrong direction,
move the shared type down into `app/schemas/` (low-level shared contracts), not up.

Real `tach.toml` in this repo runs `tach check` as a pre-commit hook (`language: system`,
needs the project's own venv) and again in CI's `lint` job via `pre-commit run --all-files`
— it's an enforced gate, not just a diagram, so a violation genuinely fails CI.

## Normative rules (MUST / SHOULD / MAY)

- **MUST**: DB session ownership stays in Deps during request handling. Services receive
  repository instances via constructor, never a session.
- **MUST**: Services raise domain exceptions only, never HTTP exceptions.
- **MUST**: Service input/output contracts are `TypedDict`s in `app/services/types/`.
- **MUST**: Multi-step atomic operations are coordinated in Deps (`auto_commit=False` +
  explicit `session.commit()`/`rollback()`).
- **MUST**: API is the canonical owner of domain→HTTP exception translation. If Deps
  performs reusable pre-validation translation (e.g. the shared auth dependency), the
  resulting HTTP contract must still be documented in the endpoint's `responses={}`.
- **MUST**: API has the final `except Exception` with `logger.exception(...)` for
  traceback visibility — this is what turns a genuinely unexpected failure into a
  debuggable 500 instead of a silent one.
- **MUST**: ORM models use SQLAlchemy Declarative typed mapping only (`DeclarativeBase`,
  `Mapped[...]`, `mapped_column`, `relationship`) — see
  [repository-and-model-patterns.md](repository-and-model-patterns.md).
- **MUST**: Many-to-many relationships use an Association Object class, not a writable
  `secondary=`.
- **SHOULD**: Endpoints stay thin (target 1–5 lines of actual logic).
- **SHOULD**: Repository mutation methods expose `auto_commit` (default `True`).
- **SHOULD**: Write endpoints support idempotency keys and optimistic concurrency.
- **MAY**: Services use Pydantic internally for complex validation, then return
  `TypedDict` contracts at the boundary.

## The canonical exception-contract matrix

Every endpoint's `responses={}` block and every `try/except` in the API layer should
trace back to this table. Keep it synchronized wherever it's referenced.

| Domain exception | HTTP exception | Status | Response model |
|---|---|---|---|
| `ValidationError` | `BadRequestException` | 400 | `BadRequestResponse` |
| `ResourceNotFoundError` | `NotFoundException` | 404 | `NotFoundResponse` |
| `AppException` | `BadRequestException` | 400 | `BadRequestResponse` |
| Unexpected `Exception` | re-raise after `logger.exception(...)` | 500 | `InternalServerErrorResponse` |

`AppException` (in `app/core/exceptions/base.py`, snapshotted in `../assets/`) is a
**documented compatibility shim** in this repo, not the strict-profile ideal — the
strict profile keeps domain exceptions entirely out of `app/core/`. New projects
generated from this template inherit the shim; don't "fix" it away in Extend/Audit mode
without the user asking for that migration.

## The canonical API-layer example

```python
router = APIRouter(tags=["Resources"], prefix="/resources")


@router.post(
    "/process",
    response_model=ResourceResponse,
    summary="Process a resource",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": responses.BadRequestResponse},
        status.HTTP_404_NOT_FOUND: {"model": responses.NotFoundResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": responses.InternalServerErrorResponse},
    },
)
async def process_resource(
    request: ResourceRequest,
    service=Depends(get_resource_service),
) -> ResourceResponse:
    try:
        return await service.process(request)
    except ResourceNotFoundError as e:
        raise exceptions.NotFoundException(detail=str(e))
    except ValidationError as ex:
        raise exceptions.BadRequestException(detail=str(ex))
    except AppException as e:
        raise exceptions.BadRequestException(detail=e.message)
    except Exception:
        logger.exception("Unhandled error in process_resource")
        raise
```

No function docstring on the endpoint — its documentation lives in `summary`,
`description`, and `responses`, per the Google-docstring standard's one exception.

## Deps: file organization and version isolation

```
app/api/v1/deps/
├── services.py      # all get_*_service() factories — service wiring only
├── auth.py          # oauth2_scheme, get_current_user
├── rate_limit.py     # rate_limit_auth, rate_limit_api, ...
└── __init__.py       # re-exports for stable import paths
```

- Each API version owns its own `deps/` package **even when the implementation starts
  identical** — this avoids hidden cross-version coupling later.
- `deps/__init__.py` re-exports common dependencies so callers don't depend on internal
  file layout: `from app.api.v1.deps import get_current_user, get_auth_service` instead
  of reaching into `deps.auth` / `deps.services` directly.
- Use `SessionLocal()` directly (not `Depends(get_session)`) only where FastAPI's DI
  genuinely isn't available: lifespan/startup, Celery tasks, CLI scripts.

## Request lifecycle (sequence)

```
Client → API: HTTP request
API → API: validate auth (JWT)
API → Deps: Depends(get_*_service)
Deps: receive session via Depends(get_session), create repo instances
Deps → Service: Service(repo_a, repo_b, ...)
Deps → API: wired service instance
API → Service: service.process(...)
Service: validate business rules
Service → Repo: repo.create_one(...)
Repo → DB: INSERT/SELECT/UPDATE
DB → Repo → Service: Model instance
Service → API: TypedDict contract (or raises a domain exception)
API: try/except maps domain exception → HTTP exception
API → Client: JSON response
```

## Type contracts between layers

| From | To | Type |
|---|---|---|
| Client → API | request body | Pydantic schema |
| API → Deps | `Depends` result | wired service instance |
| Deps → Service | constructor | injected repository instances |
| Service → Repo | CRUD calls | Create/Update schemas |
| Repo → Service | query results | SQLAlchemy models |
| Service → API | return value | `TypedDict` (`app/services/types`) |
| Service → API | error path | domain exception (`app/services/exceptions/...`) |
| API → Client | response body | Pydantic response schema |

## Scale profile (side note only — don't lead with this)

This architecture targets 1–15 developers and roughly 10–150 endpoints; past that it's
meant to evolve into domain-driven modules (`app/domains/<name>/`) rather than stay
layer-first. **Don't bring this up unprompted** — it's not relevant to scaffolding or
extending a normal-sized project, and leading with "is this architecture right for your
team size" reads as unsolicited hedging. Only mention it as a brief side note if it's
genuinely relevant to something already in play (e.g. the user describes a much larger
org/endpoint count, or asks whether they're outgrowing this structure), or if they ask
about it directly.

## Decision trees

**Where does this code belong?**
HTTP-related (routing/auth/headers) → API. Creates service instances → Deps. Business
logic → Service. Database access → Repository. Validation → Schema. ORM mapping →
Model. None of the above → Core.

**When to create a new service?** Crosses multiple repos, has business rules, needs
caching logic, or needs complex orchestration → new service. Otherwise, add to an
existing service or use the repository directly.

**Repository method vs. `custom_query`?** Standard CRUD → `BaseRepository` methods.
Domain-specific filter → add a method to the concrete repository. Very complex SQL that
doesn't fit the ORM cleanly → `custom_query()` escape hatch (still parameterized —
never string-concatenate user input into it).
