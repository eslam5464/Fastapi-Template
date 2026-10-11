# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Verbatim copy of Dockerfile from eslam5464/Fastapi-Template, taken 2026-10-11.
# The real repo is the source of truth; this is a fallback/reference copy
# for offline scaffolding and Extend/Audit-mode pattern-matching. It can drift
# from the live repo over time - prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---

# Multi-stage build for optimal size and speed
FROM python:3.14-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    libffi-dev

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set uv configuration for production
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Create virtual environment at /app/.venv and install dependencies
# The `cache` extra provides the `redis` package, which app/services/cache/*
# imports unconditionally at startup (it is not in the main dependencies).
RUN uv sync --frozen --no-dev --extra cache

# Production stage
FROM python:3.14-alpine AS production

# Install runtime dependencies only
# binutils (ld/objdump) + the libpq.so symlink let ctypes.util.find_library("pq")
# locate libpq on musl, which psycopg's pure-Python wrapper requires at import
# time (postgresql-dev would pull ~500 MB of toolchain instead of ~25 MB).
RUN apk add --no-cache \
    postgresql-libs \
    binutils \
    wget \
    && ln -sf libpq.so.5 /usr/lib/libpq.so

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    WORKERS_COUNT=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Create a non-privileged user and group for running the application
RUN addgroup -g 1001 -S uvicorn \
    && adduser -u 1001 -S uvicorn -G uvicorn \
    && mkdir -p /home/uvicorn \
    && chown -R uvicorn:uvicorn /home/uvicorn \
    && chown -R uvicorn:uvicorn /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=uvicorn:uvicorn /app/.venv /app/.venv

# Copy application code as the `app` package (uvicorn app.main:app imports it by name)
COPY --chown=uvicorn:uvicorn ./app ./app

# Alembic config/migrations entry point (CMD runs `alembic upgrade head`) and
# pyproject.toml (app/core/config.py reads it for app name/version/description)
COPY --chown=uvicorn:uvicorn alembic.ini pyproject.toml ./

# Copy uv from builder stage (after changing ownership for efficiency)
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Switch to non-privileged user
USER uvicorn

EXPOSE 8799

# Healthcheck to monitor application status
HEALTHCHECK \
    --interval=10s \
    --timeout=10s \
    --start-period=5s \
    --retries=3 \
    CMD wget --quiet --output-document=/dev/null --timeout=8 http://127.0.0.1:8799/health || exit 1

# Use exec form for better signal handling
CMD ["/bin/sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8799 --forwarded-allow-ips '*' --proxy-headers --workers ${WORKERS_COUNT}"]
