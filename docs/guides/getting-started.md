# Getting Started

## Prerequisites

- Python 3.14+
- PostgreSQL 12+
<!-- --- FEATURE[redis] START --- -->
- Redis
<!-- --- FEATURE[redis] END --- -->
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

Update the .env values (database, secrets, and the settings of any optional service this project includes).

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
<!-- --- FEATURE[api_v2] START --- -->
- v2 docs: <http://localhost:8799/v2/docs>
<!-- --- FEATURE[api_v2] END --- -->

## First Test Run

```bash
uv run pytest
```
