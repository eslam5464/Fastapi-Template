# OpenObserve log shipping

`app/core/openobserve.py` ships the application's Loguru records to
[OpenObserve](https://openobserve.ai/) without blocking requests: records go into a
bounded in-memory queue, a background thread sends them in batches over HTTP (`httpx`),
retries with exponential backoff, and flushes what is left on shutdown. Local console and
file logging keep working if OpenObserve is unreachable.

The integration is included when the project is generated with
`--data services=custom --data include_openobserve=true` (or by answering "yes" to the
OpenObserve question). It adds `httpx` to the runtime dependencies and the
`LOG_TO_OPENOBSERVE` / `OPENOBSERVE_*` settings to `app/core/config.py`, `.env.example`
and the backend service in `docker-compose.yml`.

## Setup

1. **Run OpenObserve** (or use a hosted instance). For a quick self-hosted one:

   ```bash
   docker run -d --name openobserve -p 5080:5080 \
     -v /data/openobserve:/data \
     public.ecr.aws/zinclabs/openobserve:latest
   ```

2. **Create the access key**: the Basic-auth token is base64 of `user:password`
   (`echo -n "admin:ComplexPassword123" | base64`).
3. **Configure `.env`**. Shipping is off until `LOG_TO_OPENOBSERVE` is true:

   ```env
   LOG_TO_OPENOBSERVE=True
   OPENOBSERVE_URL=https://observe.example.com
   OPENOBSERVE_ACCESS_KEY=your-base64-encoded-access-key
   OPENOBSERVE_ORG_ID=default
   OPENOBSERVE_STREAM_NAME=fastapi_logs
   OPENOBSERVE_BATCH_SIZE=10        # records per HTTP request
   OPENOBSERVE_FLUSH_INTERVAL=5.0   # seconds between flushes
   ```

## How it plugs into the logger

`app/core/logger.py` calls `add_openobserve_sink()` from `setup_logger()` and
`shutdown_openobserve()` from `shutdown_logger()`; its record filter drops the HTTP
client's own log lines about requests to OpenObserve, so shipping a batch does not
produce more records to ship. Each shipped record carries the timestamp, level,
message, module/function/line, process ID, request ID, environment and any exception.

## Production

- Use a larger batch size (for example 50) for busy services
- Give each environment its own stream (or organization)
- Keep the access key in your secret manager, not in the image or repository
- Watch stderr for "OpenObserve queue full" or send failures: records are dropped
  rather than blocking the app when the queue (1000 records) is full
