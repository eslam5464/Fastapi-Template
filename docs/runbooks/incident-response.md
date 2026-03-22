# Incident Response Runbook

## Severity Levels

- Sev-1: Full outage or data integrity risk
- Sev-2: Major feature degradation
- Sev-3: Partial degradation with workaround

## Immediate Checklist

1. Acknowledge incident and assign incident commander.
2. Confirm service status via /health and recent logs.
3. Identify blast radius (v1, v2, auth, database, redis).
4. Stabilize first: rollback, scale, or disable risky paths.
5. Communicate status updates every 15 minutes for Sev-1/Sev-2.

## Common Failures

| Failure | Signal | First Action |
|---|---|---|
| Database unavailable | /health failure, DB connection errors | Check DB connectivity and failover state |
| Redis unavailable | Rate-limit/token-blacklist/cache errors | Verify Redis availability, degrade gracefully if possible |
| Auth failures spike | Elevated 401/403 on v1 auth routes | Validate secret key, token expiry, and blacklist behavior |
| App startup failure | Process crash on boot | Inspect dependency health checks in app/main.py |

## Escalation

- Escalate Sev-1 to on-call lead immediately.
- Escalate to platform/DB owner when infrastructure failures are confirmed.

## Closure

1. Confirm recovery metrics and endpoint health.
2. Publish incident summary with timeline.
3. Create follow-up action items and owners.
