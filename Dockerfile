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

WORKDIR /build

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    uv sync --frozen --no-dev --no-install-project

# Production stage
FROM python:3.13-alpine AS production

# Install runtime dependencies only
RUN apk add --no-cache \
    postgresql-libs

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHON_VERSION=3.13 \
    PATH="/opt/venv/bin:$PATH" \
    WORKERS_COUNT=1

WORKDIR /app

# Create a non-privileged user and group for running the application
RUN addgroup -g 1001 -S uvicorn \
    && adduser -u 1001 -S uvicorn -G uvicorn \
    && mkdir -p /home/uvicorn \
    && chown -R uvicorn:uvicorn /home/uvicorn \
    && chown -R uvicorn:uvicorn /app

# Copy application code
COPY --chown=uvicorn:uvicorn ./ ./

# Switch to non-privileged user
USER uvicorn

EXPOSE 8080

# Use exec form for better signal handling
CMD ["/bin/sh", "-c", "alembic upgrade head && python main.py"]
