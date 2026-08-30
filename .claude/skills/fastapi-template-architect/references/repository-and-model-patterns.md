# Repository & Model Patterns

Source: `docs/backend-architecture.md` ("Repository Layer", "Model Layer" and its
relationship deep-dive sections) cross-checked against the real
`app/repos/base.py` and `app/models/base.py` (both snapshotted in `../assets/`).

## `BaseRepository` — the generic CRUD base

`app/repos/base.py` defines `BaseRepository[Model, CreateSchema, UpdateSchema]` — a
`Generic` bound to `Base` (models), and `BaseModel` (Pydantic, for create/update
schemas). **Read `../assets/app/repos/base.py` for the authoritative signatures** — it's
richer than the architecture doc's illustrative example:

- `create_one(schema, exclude_none=True, auto_commit=True)` / `create_bulk(...)`
- `get_by_id(obj_id, id_column_name="id")` / `get_multi_by_ids(...)`
- `update_by_id(...)` / `update_bulk(updates, ..., allow_multiple=False)`
- `delete_by_id(...)` / `delete_by_ids(...)`
- `custom_query(query, params)` — parameterized raw SQL escape hatch, never string-build
  the query with user input (OWASP SQL-injection cheat sheet referenced in the docstring)

Two real behaviors worth knowing that the simplified doc example omits:

- `update_bulk`/`delete_by_id` default to **single-row-match enforcement**: if
  `id_column_name` isn't actually unique and a call matches more than one row, the
  in-flight transaction is rolled back and `MultipleResultsFound` is raised, *regardless*
  of `auto_commit`. Pass `allow_multiple=True` to explicitly opt into multi-row behavior.
  This is a deliberate guard against silent multi-row mutations from an
  accidentally-non-unique `id_column_name` — don't remove it when extending the base
  class.
- `_validate_column_exists()` runs before every dynamic-column operation and raises
  `ValueError` for a typo'd column name instead of a confusing SQLAlchemy `AttributeError`
  three frames deeper.

Domain-specific repositories extend the base and add custom query methods:

```python
class ResourceRepository(BaseRepository[ResourceModel, CreateResourceSchema, UpdateResourceSchema]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ResourceModel)

    async def get_by_category(self, category: str, skip: int = 0, limit: int = 100) -> list[ResourceModel]:
        stmt = (
            select(self.model)
            .where(self.model.category == category)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### `auto_commit` and transaction ownership

- Default `True` — safe for single-operation calls made directly by Deps.
- Pass `auto_commit=False` when Deps needs to coordinate multiple repo calls inside one
  transaction; Deps is then responsible for the final `session.commit()`. **Forgetting
  that commit is silent data loss** — the operation appears to succeed (no exception) but
  nothing is persisted. See the anti-patterns catalog, #9.
- Services never see `auto_commit` decisions directly — that's a Deps-layer concern
  passed through, since services never hold a session.

## `Base` model — the real one, not the doc's illustrative version

`app/models/base.py` (`../assets/app/models/base.py`) is the actual base every model
inherits:

- `__abstract__ = True`, `metadata = meta` (the schema-qualified `MetaData` from
  `app/core/db.py` — see `../assets/app/core/db.py`).
- Auto columns on every model: `id` (`BigInteger`, PK, indexed), `created_at`
  (`server_default=func.now()`), `updated_at` (`server_default`/`onupdate=func.now()`).
  Never redeclare these on a concrete model.
- `__tablename__` auto-derived via `@declared_attr.directive` and a CamelCase→snake_case
  regex — a model named `OrderLineItem` gets table `order_line_item` for free.
- `to_dict(exclude_keys=None, exclude_none=False)`, `get_schema()`, `get_table_name()`,
  `dict_keys()`, and a real `__repr__` (`<ClassName(id=...)>` — much shorter than the
  architecture doc's illustrative full-attribute version).

## SQLAlchemy ORM standards (2.1-aligned)

- **MUST** use Declarative typed mapping only: `DeclarativeBase`, `Mapped[...]`,
  `mapped_column`, `relationship`. No legacy `Column(...)` style, no untyped mappings.
- **MUST** keep nullability aligned across three layers at once: Python typing
  (`Mapped[int | None]`), the column constraint (`nullable=True`), and the DB schema.
  Mismatches between typing and `nullable=` are a documented anti-pattern (#12).
- **MUST** pair bidirectional relationships with matching `back_populates` names on both
  sides.
- **MUST** model many-to-many with an **Association Object** class — see below. Never mix
  a writable `secondary=` path and a writable Association Object path for the same join.
- **SHOULD** keep the loader strategy explicit (`selectinload`/`joinedload`/default lazy)
  rather than leaving it implicit, especially on high-traffic list endpoints.
- **SHOULD** align ORM cascade behavior with DB-level `ON DELETE` (`passive_deletes=True`
  when the DB is expected to drive the delete).

## Relationship configuration matrix

| Pattern | FK location | Python cardinality | Canonical mapping | Notes |
|---|---|---|---|---|
| One-to-many | Child table | `Parent.children: list[Child]` | Bidirectional `back_populates` | Parent side usually owns cascade |
| Many-to-one | Parent table | `Child.parent: Parent` | Bidirectional with reverse collection | Keep FK nullability/typing aligned |
| One-to-one | Child table, unique FK | Scalar both sides | `uselist=False` + `UniqueConstraint` | Add real DB uniqueness, not just ORM convention |
| Many-to-many (canonical here) | Association table | `Parent.links: list[Association]` | Association Object mapped class | Required for write paths in this template |
| Self-referential | Same table | Parent scalar + child list | `remote_side` + explicit `back_populates` | Declare delete/null semantics explicitly |
| Composite FK | Child table | Depends on parent shape | `ForeignKeyConstraint([...], [...])` | Only when domain identity is genuinely multi-column |

### One-to-many / many-to-one (bidirectional)

```python
class ParentModel(Base):
    children: Mapped[list["ChildModel"]] = relationship(
        "ChildModel", back_populates="parent", cascade="all, delete-orphan", lazy="selectin",
    )

class ChildModel(Base):
    parent_id: Mapped[int] = mapped_column(ForeignKey("parent_model.id", ondelete="CASCADE"), nullable=False, index=True)
    parent: Mapped["ParentModel"] = relationship("ParentModel", back_populates="children")
```

### Many-to-many — Association Object (canonical, mandatory)

```python
class UserGroupAssociation(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group_model.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(nullable=False, default="member")
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="group_links")
    group: Mapped["GroupModel"] = relationship("GroupModel", back_populates="user_links")

class UserModel(Base):
    group_links: Mapped[list["UserGroupAssociation"]] = relationship(
        "UserGroupAssociation", back_populates="user", cascade="all, delete-orphan", lazy="selectin",
    )

class GroupModel(Base):
    user_links: Mapped[list["UserGroupAssociation"]] = relationship(
        "UserGroupAssociation", back_populates="group", cascade="all, delete-orphan", lazy="selectin",
    )
```

Why not plain `secondary=`? Plain `secondary=` is common SQLAlchemy, but this template
standardizes on the Association Object for every many-to-many **write path** because the
link is a first-class entity (it can carry its own columns like `role`/`assigned_at`,
and its lifecycle is explicit). A read-only `viewonly=True` convenience path via
`secondary=` alongside the Association Object is allowed:

```python
class UserModel(Base):
    group_links: Mapped[list["UserGroupAssociation"]] = relationship("UserGroupAssociation", back_populates="user")
    groups: Mapped[list["GroupModel"]] = relationship("GroupModel", secondary="user_group_association", viewonly=True)
```

Deletion semantics: Association Object rows are deleted via cascade rules on the link
collection (`cascade="all, delete-orphan"`), not auto-managed the way `secondary=`
auto-manages INSERT/DELETE on membership change. Don't configure broad bidirectional
delete cascades across both sides of a many-to-many graph unless full-graph deletion is
genuinely intended — see anti-pattern #12.

### Self-referential

```python
class NodeModel(Base):
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("node_model.id", ondelete="SET NULL"), nullable=True, index=True)
    parent: Mapped["NodeModel | None"] = relationship("NodeModel", back_populates="children", remote_side="NodeModel.id")
    children: Mapped[list["NodeModel"]] = relationship("NodeModel", back_populates="parent", cascade="all")
```

### Composite foreign keys (only when domain identity is genuinely multi-column)

```python
class ChildVersionModel(Base):
    parent_id: Mapped[int] = mapped_column(nullable=False)
    parent_version: Mapped[int] = mapped_column(nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_id", "parent_version"],
            ["parent_versioned_model.id", "parent_versioned_model.version"],
            ondelete="CASCADE",
        ),
    )
```

### Polymorphic inheritance (only when subtype behavior/lifecycle materially differs)

```python
class AssetModel(Base):
    type: Mapped[str] = mapped_column(nullable=False)
    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "asset"}

class ImageAssetModel(AssetModel):
    __tablename__ = "image_asset_model"
    id: Mapped[int] = mapped_column(ForeignKey("asset_model.id", ondelete="CASCADE"), primary_key=True)
    resolution: Mapped[str] = mapped_column(nullable=False)
    __mapper_args__ = {"polymorphic_identity": "image"}
```

## Loader strategy and N+1 prevention

| Strategy | Best for | Trade-off | Common failure mode |
|---|---|---|---|
| `selectinload(...)` | Collections, nested graphs | More statements, avoids row explosion | Forgetting it in list endpoints → N+1 |
| `joinedload(...)` | Small, always-needed scalar/child data | Joined rows can duplicate parent rows on large collections | Over-joining large collections |
| Default lazy (`select`) | Optional relationships rarely accessed | Deferred IO can hide perf costs | Implicit lazy loads inside hot loops |

Mandatory rules for async code:

1. High-traffic list endpoints **must** explicitly preload required relationship graphs.
2. Services **should not** trigger lazy relationship access inside loops.
3. Repositories **should** provide query helpers with explicit loading options for common
   read shapes.

Anti-pattern → fix:

```python
# ❌ WRONG — implicit lazy loads inside a loop
for order in orders:
    for line in order.lines:
        total += line.price

# ✅ CORRECT — preload the graph once
stmt = select(OrderModel).options(selectinload(OrderModel.lines))
orders = (await session.scalars(stmt)).all()
for order in orders:
    for line in order.lines:
        total += line.price
```

## Cascade / `ON DELETE` alignment

| Intent | Relationship cascade | FK `ondelete` | `passive_deletes` | Notes |
|---|---|---|---|---|
| Child owned by parent | `all, delete-orphan` | `CASCADE` | usually `True` for large graphs | canonical ownership model |
| Child survives parent deletion | omit `delete` | `SET NULL` | `True` when DB enforces | ensure nullable FK + optional typing |
| Hard-block parent deletion | omit `delete` | `RESTRICT`/default | `False`/omitted | DB raises integrity error |
| Association object cleanup | `all, delete-orphan` on link collection | `CASCADE` on link FKs | usually not required | keep writes through the association object |

## PR-review checklist for relationship changes

- Did every bidirectional relationship declare matching `back_populates` names?
- Does `Mapped[T | None]` always match `nullable=True` (and non-optional match
  `nullable=False`)?
- Are delete cascades limited to the true ownership side (no unbounded bidirectional
  delete)?
- Is every many-to-many write path using an Association Object, not writable
  `secondary=`?
- Do high-traffic list queries explicitly load the relationship graphs they use?
