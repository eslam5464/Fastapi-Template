# Multi-stage build for optimal size and speed
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    postgresql-dev \
    libffi-dev \
    && pip install --no-cache-dir poetry==2.1.3

# Set Poetry configuration for production
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_HOME="/opt/poetry"

WORKDIR /build

# Copy Poetry files for dependency resolution
COPY pyproject.toml poetry.lock ./

# Install dependencies to a virtual environment
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-root && \
    rm -rf /tmp/poetry_cache

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
