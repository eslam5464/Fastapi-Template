# Multi-stage build for optimal size and speed
FROM python:3.13-alpine AS builder

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
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-alpine AS production

# Install runtime dependencies only
RUN apk add --no-cache \
    postgresql-libs \
    wget

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

# Copy application code
COPY --chown=uvicorn:uvicorn ./app ./

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
    CMD wget --quiet --output-document=/dev/null --timeout=8 http://127.0.0.1:8080/ || exit 1

# Use exec form for better signal handling
CMD ["/bin/sh", "-c", "alembic upgrade head && python main.py"]
