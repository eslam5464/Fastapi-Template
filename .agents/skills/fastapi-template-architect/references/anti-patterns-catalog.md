# Anti-Patterns Catalog

Source: `docs/backend-architecture.md` ("Anti-patterns Catalog"). Use this as a literal
review checklist in Extend/Audit Mode, not just background reading — when reviewing a
diff or freshly-written code, check it against each of these explicitly.

## 1. Business logic in endpoints

❌ Validation, calculations, or direct DB queries written inline in the route function.
✅ Endpoint delegates everything to an injected service and only does `try/except`
exception translation. Target: 1–5 lines of actual logic in the endpoint body.

## 2. Database calls from services (skipping the repository)

❌ `class ResourceService: def __init__(self, session: AsyncSession): self.session =
session` — then running `select(...)` directly inside the service.
✅ Service receives repository instances via constructor, never a session, and calls
`self.resource_repo.get_by_id(...)`.

## 3. Mixing exception layers

❌ A service raising `HTTPException` directly (HTTP concern leaking into business logic),
or Deps calling a service and letting a domain exception crash uncaught into a 500.
✅ Service raises a domain exception (`ResourceNotFoundError`, `ValidationError`); API's
`try/except` maps it to the correct HTTP exception per the
[canonical exception-contract matrix](layering-and-flow.md).

## 4. Tight coupling between layers

❌ A service returning a raw SQLAlchemy model up to the API layer, forcing API to know
ORM internals.
✅ Service returns a `TypedDict` contract (`ResourceOutput`); API converts to the
Pydantic response model at the boundary (`ResourceResponse.model_validate(...)`).

## 5. Circular imports

❌ A service importing from `app/api/*/deps/` (or anything in the API layer) — violates
the layering direction and creates a circular import risk.
✅ Service takes what it needs (repositories) as constructor parameters instead of
importing anything from a higher layer.

## 6. Missing input validation

❌ An endpoint accepting a raw `dict` and manually pulling fields with `.get(...)` — no
type checking, no constraints, silent defaults hiding bad input.
✅ A Pydantic request schema does the validation automatically before the endpoint body
even runs.

## 7. Creating repositories inside services

❌ `class ResourceService: def __init__(self, session): self.resource_repo =
ResourceRepository(session)` — repos constructed internally, hiding real dependencies
and making the service hard to test without a real/patched session.
✅ Repos are injected by Deps: `def __init__(self, resource_repo: ResourceRepository,
audit_repo: AuditRepository)`. Explicit, testable with plain mocks.

## 8. Injecting too many repositories

**Threshold: more than 5 repositories in one service constructor is a red flag.**
❌ A single `OrderService` taking `order_repo, product_repo, user_repo, payment_repo,
shipping_repo, notification_repo, audit_repo` (7 repos) — doing too much.
✅ Split by concern: `OrderService(order_repo, product_repo)`,
`PaymentService(payment_repo, order_repo)`, `ShippingService(shipping_repo, order_repo)`.

## 9. Forgetting to commit with `auto_commit=False`

❌ Calling multiple repo methods with `auto_commit=False` and never calling
`session.commit()` afterward — **this is silent data loss**: no exception is raised, the
endpoint returns success, but nothing was actually persisted once the session closes.
✅ Wrap the sequence in `try: ... await session.commit() except Exception: await
session.rollback(); raise`, always in the Deps layer, always explicitly.

## 10. Inconsistent exception-translation strategy

❌ An endpoint that calls a service and doesn't catch its documented domain exceptions at
all — an uncaught `ResourceNotFoundError` crashes as an undifferentiated 500 instead of a
404.
✅ Every endpoint maps every domain exception its service can raise (per that service
method's docstring `Raises` section) to the matching HTTP exception, consistently with
the canonical matrix.

## 11. Missing idempotency/concurrency controls on writes

❌ A `POST` endpoint with no `Idempotency-Key` handling and no optimistic-concurrency
check — a client retry (e.g. after a timeout) can silently create a duplicate resource.
✅ Accept an `Idempotency-Key` header on write endpoints where retries are plausible, and
apply optimistic concurrency (`version` field/ETag) where concurrent conflicting updates
are plausible. See [api-governance.md](api-governance.md).

## 12. Inconsistent SQLAlchemy relationship modeling

Several distinct sub-mistakes, all real:

- Untyped `relationship(...)` (not `Mapped[...]`) with no reverse `back_populates` pair.
- A **writable `secondary=` path mixed with a writable Association Object path** for the
  same many-to-many join — two ways to write the same link is a correctness hazard, not
  a convenience.
- `Mapped[int]` (non-optional) paired with `nullable=True` on the actual column (or the
  reverse) — the type lies about what the database will actually accept/return.
- Bidirectional `cascade="all, delete"` on **both sides** of a relationship — can wipe an
  unexpectedly large connected graph on a single delete.
- Implicit lazy-loading relationship access inside a loop (`for parent in parents: for
  child in parent.children: ...` with default lazy loading) — a classic N+1, invisible
  in code review unless you're specifically looking for it.

✅ See [repository-and-model-patterns.md](repository-and-model-patterns.md) for every
correct counterpart — typed `Mapped[...]` + paired `back_populates`, Association Object
as the sole many-to-many write path, aligned nullability, ownership-scoped cascades, and
explicit `selectinload`/`joinedload` before iterating a relationship collection.

## PR-review quick pass (common failure-mode checklist)

- Did each bidirectional relationship declare matching `back_populates` names?
- Does `Mapped[T | None]` always match `nullable=True` (and vice versa)?
- Are delete cascades limited to the true ownership side?
- Are many-to-many write paths using an Association Object instead of writable
  `secondary=`?
- Are high-traffic list queries explicitly loading the relationship graphs they use?
- Does every service constructor stay at or under 5 injected repositories?
- Is every `auto_commit=False` call paired with an explicit `commit()`/`rollback()` in
  the same Deps function?
- Does every endpoint's exception handling match what its service can actually raise?
