# Authentication (JWT and the User model)

JWT authentication with a `User` model: signup, login, token refresh, logout and a
"current user" dependency for protected routes.

It is included when the project is generated with
`--data services=custom --data include_auth=true` (or by answering "yes" to the
authentication question). It adds `python-jose`, `pwdlib[argon2]` and `python-multipart`
to the dependencies, the `user` table to the first Alembic revision, and the
`SECRET_KEY` and token lifetime settings.

## Files

- `app/models/user.py`: the `User` model (`username`, `email`, `hashed_password`,
  `first_name`, `last_name`)
- `app/repos/user.py`: `UserRepo` (`get_by_username`, `get_by_email`, plus the
  `BaseRepository` operations)
- `app/schemas/user.py` and `app/schemas/token.py`: request and response schemas
- `app/services/auth_service.py`: `AuthService`, which hashes passwords, signs and
  validates tokens, and registers and authenticates users
- `app/api/v1/deps/auth.py`: the dependencies (`get_current_user`, `get_auth_service`
  and the login, signup and refresh flows)
- `app/api/v1/endpoints/auth.py` and `app/api/v1/endpoints/user.py`: the routes

## Configuration

```env
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secret-key-here-make-it-very-long-and-random
ACCESS_TOKEN_EXPIRE_SECONDS=3600
REFRESH_TOKEN_EXPIRE_SECONDS=2592000
```

- `SECRET_KEY` is required and must be at least 32 characters. It signs every token
  (HS256), so changing it logs every user out.
- The lifetimes default to 1 hour (access) and 24 hours (refresh) when the variables are
  not set.

## Endpoints

| Method | Path | Body | Result |
| ------ | ---- | ---- | ------ |
| POST | `/v1/auth/signup` | form: `username`, `email`, `password` | 201 with an access and a refresh token |
| POST | `/v1/auth/login` | form: `username`, `password` | 200 with an access and a refresh token |
| POST | `/v1/auth/refresh-token` | JSON: `refresh_token` | 200 with a new token pair |
| POST | `/v1/auth/logout` | none (bearer token) | 200 with `message` and `revoked` |
| GET | `/v1/users/me` | none (bearer token) | 200 with the current user |

Signup rules: the username has 3 to 50 letters, digits or underscores with at least one
digit; the password has at least 8 characters with an uppercase letter, a lowercase
letter, a digit and one of `@$!%*?&`.

```bash
curl -X POST "http://localhost:8799/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=Str0ng@Pass"

curl "http://localhost:8799/v1/users/me" \
  -H "Authorization: Bearer <access_token>"
```

## Protecting a route

Add the `get_current_user` dependency. It reads the bearer token, validates it and
returns the `User`, or answers `401`.

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import get_current_user
from app.models import User

router = APIRouter()


@router.get("/protected")
async def protected_route(current_user: Annotated[User, Depends(get_current_user)]):
    return {"message": f"Hello {current_user.username}!"}
```

To protect every route of a router at once, pass it to the router:
`APIRouter(dependencies=[Depends(get_current_user)])`.

## Logout and token revocation

<!-- --- FEATURE[redis_token_blacklist] START --- -->
Logout puts the access token on a Redis blacklist until it expires, so it cannot be used
again. See [token-revocation.md](token-revocation.md).
<!-- --- FEATURE[redis_token_blacklist] END --- -->
<!-- --- FEATURE[!redis_token_blacklist] START --- -->
This project has no token blacklist: logout answers `revoked: false` and **the access
token stays valid until it expires**. Clients must drop their tokens themselves; keep
`ACCESS_TOKEN_EXPIRE_SECONDS` short.
<!-- --- FEATURE[!redis_token_blacklist] END --- -->

## Passwords

`AuthService` hashes passwords with Argon2 (`pwdlib`). Store only the hash
(`User.hashed_password`), and compare with `AuthService.verify_password`, never with
`==`. A failed login takes the same time whether or not the username exists, so response
times do not reveal which usernames are registered.

## Production

1. Generate `SECRET_KEY` per environment and keep it in your secret manager.
2. Serve the API over HTTPS only: bearer tokens are credentials.
3. Keep the access token lifetime short, and prefer the token blacklist if a logged-out
   or stolen token must stop working immediately.
4. Put a request limit on `/v1/auth/*` (the rate limiting service, or your reverse proxy)
   to slow down password guessing.
