# Observability & Performance

Source: `docs/backend-architecture.md` ("Observability Baseline", "Performance Budget
Guide") plus the real `app/core/logger.py` and `app/middleware/logging.py`
(snapshotted in `../assets/`).

## Logging — Loguru, not stdlib, with a real interception layer

This repo does **not** use Python's stdlib `logging` module directly for application
logs — it uses **Loguru**, and redirects stdlib logging (including Uvicorn's own
loggers) into Loguru so log formatting stays consistent everywhere:

- `InterceptHandler` (a `logging.Handler` subclass) forwards stdlib log records into
  `logger.opt(...).log(...)`.
- `configure_uvicorn_logging()` walks `logging.root.manager.loggerDict`, finds anything
  starting with `"uvicorn"`, and repoints its handlers at `InterceptHandler` with
  `propagate = False`. Call this **after** `setup_logger()` in the lifespan, or Uvicorn's
  own default handlers win.

### Three sinks, each with a purpose

1. **Console** — colorized, `DEBUG` in `DEV`, `INFO` otherwise, `enqueue=True`
   (thread-safe queue-based logging, doesn't block the event loop on write).
2. **File** (`logs/app.log`) — `10 MB` rotation, `3 months` retention, gzip compression
   of rotated files, `enqueue=True` (also process-safe — matters with multiple Uvicorn
   workers all logging to the same file), `backtrace=True` + `diagnose=True` (full
   traceback + variable values on exceptions — don't turn `diagnose` off without
   realizing it removes variable-value context from crash logs, which is genuinely
   useful in this repo's failure-triage workflow, though it's also more verbose and can
   leak values into logs — that trade-off is already made deliberately here).
3. **OpenObserve** (optional, `settings.log_to_openobserve`) — a **hand-rolled**,
   thread-based, batching async HTTP log shipper (`OpenObserveHandler`): a daemon
   background thread reads off a bounded `queue.Queue(maxsize=1000)`, batches by size or
   a flush interval, retries with exponential backoff, and registers `atexit.register
   (self.shutdown)` for a graceful flush on process exit. `shutdown_logger()` (called
   from `main.py`'s lifespan shutdown) also explicitly stops it. If you ever need a
   similar "ship logs/events to an external HTTP sink without blocking the request path"
   requirement elsewhere in the app, this is the reference implementation to copy the
   shape of (bounded queue + background thread + batching + backoff + `atexit` +
   explicit shutdown hook), not `httpx.AsyncClient` called inline from a Loguru sink.

### Correlation IDs

- `request_id_var: ContextVar[str | None]` holds the current request's ID.
- `correlation_filter()` (a Loguru filter, applied to every sink) injects
  `extra["request_id"]` (falling back to a fresh short UUID if unset) and
  `extra["process_id"]` (`os.getpid()`, so multi-worker logs can be told apart) into
  every log record.
- `LoggingMiddleware` (`../assets/app/middleware/logging.py`) generates an 8-char request
  ID per request, stores it on `request.state.request_id`, and adds it as the
  `X-Request-ID` response header — so a client-visible header and the server-side log
  correlation ID are the same value for any given request.
- On an unhandled exception, `LoggingMiddleware` also captures and logs the (sanitized)
  request body, query params, and path params alongside the error — see
  `sanitize_body()`, which recursively redacts any key matching a `SENSITIVE_FIELDS` set
  (`password`, `token`, `secret`, `api_key`, `authorization`, `refresh_token`,
  `access_token`, `credit_card`, `card_number`, `cvv`, `ssn`, `private_key`) before it
  ever reaches a log line. **Extend this set** when adding a new field that could carry a
  credential or PII — don't assume it's covered by a substring match that doesn't
  actually match your new field's name.

### Mandatory logging contract

- Every request-lifecycle log includes: `timestamp`, `level`, `message`, `request_id`,
  `path`, `method`, `status_code`, `latency_ms`.
- Sensitive values are redacted before emission (see `sanitize_body` above).
- API's final `except Exception` handler calls `logger.exception(...)` — never a plain
  `logger.error(...)` there, since `.exception()` captures the traceback.
- Middleware and endpoint logs share `request_id` so one request is reconstructable
  end-to-end from logs alone.

## Metrics contract (mandatory baseline)

| Metric | Type | Why |
|---|---|---|
| `http_requests_total` | Counter | Throughput/traffic shape |
| `http_request_duration_ms` | Histogram | Latency SLI/SLO tracking |
| `http_errors_total` (4xx/5xx) | Counter | Error-budget monitoring |
| `db_query_duration_ms` | Histogram | DB bottleneck visibility |
| `cache_hit_ratio` | Gauge | Cache effectiveness |

Tracing is optional by default — enable it only when incident analysis genuinely needs
cross-service timing; if enabled, propagate `traceparent` through outgoing HTTP calls.

## Performance budgets

| Budget | Target | Alert threshold | Ownership |
|---|---|---|---|
| Endpoint latency p95 (standard reads) | ≤ 250 ms | ≥ 400 ms sustained | API + Repo owners |
| Endpoint latency p95 (critical writes) | ≤ 400 ms | ≥ 600 ms sustained | API + Service owners |
| DB queries per list endpoint | explicit per-endpoint budget (e.g. 3–8) | > budget by 20% | Repo owner |
| Error rate (5xx) | < 1% | ≥ 2% sustained | API owner |

Every public endpoint should have an explicit budget card, not just a vague "should be
fast":

```text
Endpoint: GET /v1/orders
Target p95: 220 ms
Query budget: <= 5 queries at page_size=20
Guardrails: selectinload(order_lines), indexed sort on created_at
Fallback: reduce optional expansions when page_size > 50
```

Profiling workflow when a budget is at risk: capture trace + query logs for
representative load → compare observed query count and p95 against the budget → identify
the top offender (N+1, missing index, over-joined query, oversized payload) → apply a
targeted fix and re-measure before merging. High-traffic endpoint PRs should include
query-count assertions; regressions beyond the agreed budget block merge unless
explicitly waived. If p95 exceeds threshold for two consecutive measurement windows, open
a performance incident with an assigned owner in the same sprint.

## Lifespan hooks — startup/shutdown discipline

`app/main.py`'s `lifespan()` runs `_check_dependencies()` at startup (health-checks
`cache_manager`, `rate_limiter`, and — outside `LOCAL` only — `token_blacklist`; raises
`RuntimeError` and refuses to start if a required dependency is unhealthy) and
`_shutdown_dependencies()` on shutdown (closes each of their Redis connections). **When
adding a new shared infrastructure client** (another Redis-backed service, a new SDK
client held as a module singleton, etc.), add both a startup health check and an explicit
shutdown close/dispose step — don't let a new client leak connections on shutdown just
because nothing currently calls its `.close()`.
