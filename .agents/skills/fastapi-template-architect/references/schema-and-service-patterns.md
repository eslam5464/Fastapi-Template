# Schema & Service Patterns

Source: `docs/backend-architecture.md` ("Schema Layer", "Service Layer" sections) plus
the real `app/schemas/base.py` (snapshotted in `../assets/`).

## Schema layer (`app/schemas/`)

### Real base schemas

`app/schemas/base.py` (the real one — smaller than the architecture doc's illustrative
three-base-class example):

```python
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True, extra="forbid")

class BaseTimestampSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True, extra="forbid")
    created_at: datetime
    updated_at: datetime | None = None
```

Key points from `model_config`: `from_attributes=True` enables ORM-object → schema
construction (`Schema.model_validate(orm_instance)`), `extra="forbid"` rejects unknown
fields on input (fail loud on typos/unexpected payloads), `arbitrary_types_allowed=True`
permits non-Pydantic types where genuinely needed.

The architecture doc's fuller illustrative pattern (`BaseCreateSchema`/`BaseUpdateSchema`
with `validate_assignment=True`, `use_enum_values=True`) is a reasonable pattern to reach
for when a new project needs create/update-specific config — it isn't wrong to add, it's
just not what ships by default in this repo's `base.py` today.

### What belongs in schemas vs. what doesn't

✅ Request/response model definitions, field validation/constraints, `@field_validator`/
`@model_validator`, discriminated unions, enum definitions, serialization config.

❌ Business logic, database queries, external API calls, any side effects.

### Naming convention

| Suffix | Purpose | Example |
|---|---|---|
| `*Create` | Input schema for create operations | `UserCreate` |
| `*Update` | Input schema for partial/full updates | `UserUpdate` |
| `*Read` / `*Response` | Output schema returned by the API | `UserRead`, `UserResponse` |
| Action-specific (`*Signup`, `*Login`) | Explicit workflow payloads | `UserSignup`, `UserLogin` |

Validation split: **Pydantic schemas validate structure, type, and field format. Services
enforce business rules and cross-entity invariants.** Don't put a business rule (e.g. "a
user can only have 3 active orders") into a `@model_validator` — that belongs in the
service layer where it can query other entities.

### Discriminated unions (Pydantic v2)

```python
class FilterTypeA(BaseSchema):
    type: Literal["exact"] = "exact"
    value: str = Field(..., min_length=1)

class FilterTypeB(BaseSchema):
    type: Literal["range"] = "range"
    min_value: float | None = None
    max_value: float | None = None

FilterType = Annotated[Union[FilterTypeA, FilterTypeB], Field(discriminator="type")]
```

`Field(discriminator="type")` is required for Pydantic v2 to resolve the union correctly
— a plain `Union` without the discriminator will fall back to slower, ambiguous
left-to-right validation.

## Service layer (`app/services/`)

### What belongs vs. what doesn't

✅ Business logic and domain rules, orchestrating multiple repo calls, `TypedDict`
contracts in `app/services/types/`, cache integration, complex calculations, raising
domain exceptions.

❌ HTTP concerns, creating sessions, creating repository instances (receive them via
constructor), direct SQL, returning framework-coupled objects, holding session
references, broad unnecessary SDK dependencies.

### Constructor injection — the whole point

```python
class ResourceService:
    def __init__(self, resource_repo: ResourceRepository, audit_repo: AuditRepository):
        self.resource_repo = resource_repo
        self.audit_repo = audit_repo

    async def process(self, item: ResourceInput, option: ProcessingOption) -> ResourceOutput:
        self._validate_item(item)
        processed = self._apply_rules(item, option)
        created = await self.resource_repo.create_one(CreateResourceSchema(**processed))
        await self.audit_repo.log_action(action="PROCESS", resource_id=created.id, details={"option": option.value})
        return ResourceOutput(id=created.id, name=created.name, value=created.value, status=created.status)
```

Why constructor injection instead of the service creating its own repos: testing becomes
trivial (mock repos, inject, no internal patching needed — see
[testing-conventions.md](testing-conventions.md)), and dependencies are explicit instead
of hidden inside `__init__`.

### The >5-repos threshold

If a service constructor takes more than 5 repositories, it's doing too much — split it
into smaller, focused services. A 6th/7th repo in a constructor (e.g.
`OrderService(order_repo, product_repo, user_repo, payment_repo, shipping_repo,
notification_repo, audit_repo)`) is a concrete signal to split by concern (`OrderService`,
`PaymentService`, `ShippingService`, each taking only the repos it actually needs).

### Standalone vs. abstract base services

Use **standalone services by default** — single implementation, direct constructor
injection, no inheritance. Introduce an **abstract base** only when multiple
implementations must satisfy one interface (e.g. an email-provider strategy with
Resend/Brevo adapters — see [optional-integrations.md](optional-integrations.md)). Don't
add an ABC "for future flexibility" when there's only one implementation today.

### Infrastructure services are the exception to repo-injection

Not every service follows the repo-injection pattern. SDK wrappers like `firebase.py`,
`gcs.py`, `back_blaze_b2.py`, `firestore.py` live in `app/services/` too but wrap
external SDKs directly and don't take repositories — they're typically used by Deps or
other services directly, and MAY be module-level singletons if stateless. Stateful/
request-scoped integrations should still go through a Deps factory.

### `TypedDict`-first contracts

Define service inputs/outputs in `app/services/types/` as `TypedDict`s, not ad-hoc dicts
or leaked ORM models:

```python
# app/services/types/resource.py
class ResourceInput(TypedDict):
    name: str
    value: float
    category: str

class ResourceOutput(TypedDict):
    id: int
    name: str
    value: float
    status: str
```

Pydantic MAY be used internally within a service for complex payload normalization, but
the boundary contract returned to Deps/API should be the `TypedDict`. This keeps services
easy to migrate across Python/runtime changes and keeps the API layer as the one place
that converts to/from framework-coupled Pydantic response models.

### Cache key naming

Deterministic structure: `{service}:{entity}:{identifier}` — e.g. `cache:user:123`,
`ratelimit:auth:192.168.1.1`, `blacklist:token:abc123`. Don't invent a different key
shape per service; consistency here makes Redis key inspection/debugging tractable.

## Auto_commit and multi-step transactions (Deps-layer responsibility)

Services never decide commit timing themselves — a Deps function coordinating multiple
service/repo calls in one transaction passes `auto_commit=False` down and commits once at
the end:

```python
async def get_resource_atomic(
    service: ResourceService = Depends(get_resource_service),
    session: AsyncSession = Depends(get_session),
) -> ResourceResponse:
    try:
        result = await service.process_batch(request, auto_commit=False)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise
```

See [layering-and-flow.md](layering-and-flow.md) for the full transaction/concurrency
guide (isolation levels, optimistic vs. pessimistic locking, retry policy).
