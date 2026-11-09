# Token revocation (logout blacklist)

`app/services/cache/token_blacklist.py` keeps revoked JWTs in Redis so that logout and
"log out everywhere" really end a session. It is included when the project is generated
with `--data services=custom --data include_redis_token_blacklist=true` (or by answering
"yes" to the token blacklist question).

## Without it

Logout still validates the token and answers `200` with `{"message": "Successfully logged out", "revoked": false}`,
but nothing is stored: **the access token stays valid until it expires**
(`ACCESS_TOKEN_EXPIRE_SECONDS`, and the refresh token until `REFRESH_TOKEN_EXPIRE_SECONDS`).
Clients must drop their tokens themselves. Keep the expiry times short, or add the
blacklist, if a stolen or logged-out token must stop working immediately.

## How it works

Every access and refresh token carries a unique `jti` claim.

- **Logout** (`POST /v1/auth/logout`): `AuthService.get_logout_revoke_payload()` reads the
  token's `jti` and remaining lifetime, and `token_blacklist.revoke_token(jti, ttl_seconds)`
  stores it with that TTL, so the entry disappears when the token would have expired
  anyway. The response has `"revoked": true`.
- **Every authenticated request and token refresh**: `AuthService` rejects a token whose
  `jti` is revoked (`token_blacklist.is_revoked(jti)`) with `401 Token has been revoked`.
- **Revoke all of a user's tokens** (for example after a password change):
  `await token_blacklist.revoke_all_user_tokens(user_id, ttl_seconds)` records the
  revocation time; tokens issued before it are rejected
  (`token_blacklist.get_user_revocation_time(user_id)`).

```python
from app.core.config import settings
from app.services.cache.token_blacklist import token_blacklist

# e.g. in a "change password" service method, after saving the new hash:
await token_blacklist.revoke_all_user_tokens(
    str(user.id),
    ttl_seconds=settings.refresh_token_expire_seconds,
)
```

Keys: `token:blacklist:<jti>` per revoked token, and `token:revoke_all:<user_id>` holding a
user's revocation timestamp.

## Behaviour when Redis is unavailable

The blacklist shares the project's Redis connection pool. In the `LOCAL` environment it
is a no-op; elsewhere a failed health check at startup only logs a warning (startup
continues), and failed lookups are treated as "not revoked" so authentication keeps
working, at the cost of revocation not being enforced while Redis is down.

## Testing

`tests/api/conftest.py` replaces the blacklist with an in-memory `FakeTokenBlacklist` for
every API test, so revocation is tested without Redis:
`tests/api/v1/endpoints/logout_revocation_test.py` (logout, then the same token gets 401)
and `tests/api/v1/deps/token_revocation_test.py`.
