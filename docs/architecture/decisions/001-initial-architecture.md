# ADR-001: Adopt Layered FastAPI with Mounted API Versioning

- **Date**: 2026-03-22
- **Status**: Accepted
- **Deciders**: Backend maintainers

## Context

The project needed a maintainable backend structure with clear boundaries for HTTP handling, business logic, and persistence. At the same time, API evolution required isolated version contracts and separate documentation per version without exposing global docs routes.

## Options Considered

| Option | Pros | Cons |
|---|---|---|
| Single app with shared /docs and path-prefixed routers | Simpler startup wiring | Shared OpenAPI surface, harder per-version contract isolation |
| Mounted FastAPI sub-apps per version (/v1, /v2) with root operational app | Isolated OpenAPI docs per version, cleaner rollout path | Slightly more composition complexity |
| Full microservices split by version | Strong isolation | Operational overhead too high for current team size |

## Decision

Use a layered modular-monolith architecture and mount separate FastAPI sub-apps per API version.

- Root app hosts operational endpoints (for example /health) and shared middleware.
- v1 and v2 are mounted at /v1 and /v2.
- Each mounted app has independent /docs, /redoc, and /openapi.json paths.
- Services remain framework-agnostic and repositories own persistence details.

## Consequences

- **Easier**: Versioned docs management, gradual endpoint migration, bounded contract changes.
- **Harder**: Dependency override/test setup must account for mounted sub-apps.
- **Risks**: Middleware or security policy drift between root and mounted surfaces; mitigated by shared middleware strategy and tests.
