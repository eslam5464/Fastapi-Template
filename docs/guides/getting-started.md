# Getting Started

## Prerequisites

- Python 3.13+
- PostgreSQL 12+
- Redis
- uv

## Clone

```bash
git clone <repo-url>
cd Fastapi-Template
```

## Environment Setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
uv sync --all-groups
```

## Configure Environment

```bash
copy .env.example .env
```

Update .env values for database, redis, and secrets.

## Database

```bash
alembic upgrade head
```

## Run the App

```bash
python main.py
```

## Verify

- Health check: <http://localhost:8799/health>
- v1 docs: <http://localhost:8799/v1/docs>
- v2 docs: <http://localhost:8799/v2/docs>

## First Test Run

```bash
uv run pytest
```
