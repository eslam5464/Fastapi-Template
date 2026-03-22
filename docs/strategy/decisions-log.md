# Decisions Log

| Date | Decision | Rationale | Impact |
|---|---|---|---|
| 2026-03-22 | Use mounted apps for /v1 and /v2 | Isolate OpenAPI/docs per version and simplify evolution | Root docs disabled, version docs enabled |
| 2026-03-22 | Keep /health unversioned on root app | Stable operational endpoint independent of API version rollout | Monitoring integrations remain simple |
| 2026-03-22 | Use route-aware CSP for docs endpoints | Keep strict CSP by default while allowing Swagger/ReDoc assets | Secure-by-default with functional docs UI |
