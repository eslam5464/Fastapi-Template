# The example Items domain

Items is a small, complete CRUD slice. It exists to show how one domain passes through
every layer of this architecture. Copy it to start your own domain, then delete it.

It is included when the project is generated with
`--data services=custom --data include_example_items=true` (or by answering "yes" to the
example domain question).

## What it contains

| Layer | File | What it does |
| ----- | ---- | ------------ |
| Model | `app/models/item.py` | `Item`: `name` (unique), `description`, `is_active`, plus `id` and timestamps from `Base` |
| Schemas | `app/schemas/item.py` | `ItemCreate`, `ItemUpdate` (all fields optional), `ItemResponse` |
| Repository | `app/repos/item.py` | `ItemRepo`: `get_by_name`, `get_page`, plus the `BaseRepository` operations |
| Service | `app/services/item_service.py` | `ItemService`: the rules (unique names, missing items) |
| Dependency | `app/api/v1/deps/items.py` | `get_item_service`: builds the service with its repository |
| Endpoints | `app/api/v1/endpoints/items.py` | list, read, create, update and delete under `/v1/items` |
| Migration | `app/alembic/versions/` | the first revision creates the `item` table |
| Tests | `tests/services/item_service_test.py`, `tests/api/v1/endpoints/items_test.py` | service rules and HTTP behaviour |

## How a request flows

1. The endpoint receives validated data (`ItemCreate`) and the service from
   `Depends(get_item_service)`.
2. The service applies the rules and calls the repository. It never sees the database
   session or anything from FastAPI.
3. When a rule fails, the service raises a service exception (`ResourceNotFoundError`,
   `DuplicateResourceError` from `app/services/exceptions/base.py`).
4. The endpoint translates it to an HTTP exception (404, 409) and returns
   `ItemResponse` otherwise.

Keep that split in your own domains: rules in the service, queries in the repository,
HTTP details in the endpoint.

## Turning it into your own domain

Take "orders" as the example.

1. Copy the six files and rename them: `app/models/order.py`, `app/schemas/order.py`,
   `app/repos/order.py`, `app/services/order_service.py`, `app/api/v1/deps/orders.py`,
   `app/api/v1/endpoints/orders.py`. Rename the classes to match.
2. Change the columns in the model and the fields in the schemas.
3. Export the model from `app/models/__init__.py`. Alembic finds models through that
   module, so a model that is not imported there gets no migration.
4. Include the router in `app/api/v1/router.py`:

   ```python
   from app.api.v1.endpoints.orders import router as orders_router

   api_v1_router.include_router(orders_router, prefix="/orders", tags=["Orders"])
   ```

5. Create the migration and apply it:

   ```bash
   alembic revision --autogenerate -m "add order table"
   alembic upgrade head
   ```

   Read the generated file before you apply it. `alembic check` then reports whether the
   models and the migrations agree.
6. Copy the two test files and adapt them.

<!-- --- FEATURE[auth] START --- -->
## Access control

The Items router requires a logged-in user for every route:

```python
router = APIRouter(dependencies=[Depends(get_current_user)])
```

To record who owns a row, take the user in the endpoint instead and pass its ID to the
service:

```python
async def create_order(
    data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> OrderResponse:
    order = await service.create_order(data, owner_id=current_user.id)
    return OrderResponse.model_validate(order)
```

Add an `owner_id` column with a foreign key to the `user` table, and make the service
check it before it returns, changes or deletes a row. The endpoint tests skip the login
check with a dependency override (see `items_client` in
`tests/api/v1/endpoints/items_test.py`); `items_auth_test.py` tests the check itself.

<!-- --- FEATURE[auth] END --- -->
<!-- --- FEATURE[!auth] START --- -->
## Access control

This project has no authentication, so the `/v1/items` routes are public. Add your own
access check (for example a router-level dependency that validates an API key) before
you expose data that is not public.

<!-- --- FEATURE[!auth] END --- -->
<!-- --- FEATURE[csrf] START --- -->
## CSRF

The CSRF middleware checks every POST, PUT, PATCH and DELETE outside its exempt paths.
Clients of `/v1/items` must send the `csrf_token` cookie value back in the
`X-CSRF-Token` header; the tests do that in the `items_client` fixture.

<!-- --- FEATURE[csrf] END --- -->
## Removing it

Delete the six `item` files and the two test files, remove the `Item`, `ItemRepo` and
schema exports from the three `__init__.py` files, and remove the `items_router` lines
from `app/api/v1/router.py`. Then drop the table with a new migration
(`alembic revision --autogenerate -m "drop item table"`); do not edit the first revision
once a database has run it.
