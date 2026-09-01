# Repository custom instructions

This repo (and any project generated from it via its Copier template) follows a strict
layered architecture. For the full detail — SQLAlchemy patterns, auth/security
conventions, testing gotchas, CI config, Copier generation mechanics — see
`docs/backend-architecture.md` and, if you have access to it, the
`fastapi-template-architect` skill at `.claude/skills/fastapi-template-architect/` (same
content, organized for an AI agent to consult on demand). What follows is the condensed
version for everyday work in this repo.

## Layers and import direction

`Client -> API -> Deps -> Service -> Repository -> Model -> DB`, with `Core` and
`Schema` shared underneath everyone. Enforced by `tach.toml`, not just documented —
a violation fails `tach check` (pre-commit hook and CI).

| Layer | Location | Job | Can import |
|---|---|---|---|
| API | `app/api/` | Routing, domain→HTTP exception translation, final `except Exception` + `logger.exception(...)` | Deps, Schemas, Core |
| Deps | `app/api/*/deps/` | Session ownership, repo/service wiring, atomic-transaction orchestration | Services, Repos, Schemas, Core |
| Service | `app/services/` | Business logic, domain exceptions, `TypedDict` I/O contracts | Repos, `app/services/types`, Cache |
| Repository | `app/repos/` | CRUD, query building, `auto_commit` support | Models, Schemas |
| Schema | `app/schemas/` | Pydantic v2 validation/serialization | Core (enums only) |
| Model | `app/models/` | SQLAlchemy ORM mapping | Core (`Base` only) |
| Core | `app/core/` | Config, HTTP exceptions, DB setup | Nothing |

Lower layers never import from higher ones. If two layers need a shared type, move it
down into `app/schemas/`, don't reach up.

## Non-negotiable rules

- DB session ownership stays in Deps. Services receive repository instances via
  constructor, never a session.
- Services raise domain exceptions only (`ResourceNotFoundError`, `ValidationError`,
  ...), never `HTTPException`. API's `try/except` maps each one to the matching HTTP
  exception: `ValidationError`→400, `ResourceNotFoundError`→404, unexpected
  `Exception`→re-raise after `logger.exception(...)`→500.
- ORM models use SQLAlchemy 2.0 typed Declarative mapping only (`Mapped[...]`,
  `mapped_column`, `relationship` with `back_populates`).
- Many-to-many relationships use an Association Object class — never a writable
  `secondary=`.
- Service constructors stay at or under 5 injected repositories; split by concern past
  that.
- Every `auto_commit=False` repo call is paired with an explicit `session.commit()`/
  `rollback()` in the same Deps function — an unpaired one is silent data loss (no
  exception, endpoint returns success, nothing persists).
- Endpoints stay thin (1–5 lines of real logic): validate via Pydantic, delegate to a
  service, translate exceptions. No business logic, no direct DB queries in a route
  function.
- Tests use the `*_test.py` suffix (not `test_*.py`) and `anyio`, not
  `pytest-asyncio`.

## Before proposing a change

Check it against the rules above and the full anti-patterns catalog in
`.claude/skills/fastapi-template-architect/references/anti-patterns-catalog.md` (or
`docs/backend-architecture.md`'s "Anti-patterns Catalog" section if that's not
available). When something in this repo's actual code conflicts with what's documented,
follow the real code — it wins.
