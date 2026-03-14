# FastAPI Template

A production-ready FastAPI project template with modern best practices, async support, JWT authentication, and PostgreSQL integration.

## ✨ Features

- **🚀 FastAPI** - Modern, fast web framework for building APIs
- **🔐 JWT Authentication** - Secure token-based authentication with token blacklisting
- **📊 PostgreSQL** - Async database integration with SQLAlchemy 2.0
- **🗄️ Database Migrations** - Alembic for schema management
- **🏗️ Clean Architecture** - Repository pattern and dependency injection
- **📝 Automatic API Documentation** - Interactive Swagger UI and ReDoc
- **🔒 Security** - Password hashing with Argon2, CORS, CSRF, and security headers middleware
- **📊 Logging** - Structured logging with Loguru and centralized log aggregation
- **⚡ Environment Management** - Multi-environment configuration
- **🧪 Development Tools** - Pre-commit hooks, code formatting with Black
- **☁️ Cloud Storage Integration** - BackBlaze B2 cloud storage service support
- **🔥 Firebase Integration** - Authentication, push notifications, and Firestore database
- **⚡ Redis Caching** - High-performance caching with shared connection pooling
- **🚦 Rate Limiting** - Sliding window rate limiting with microsecond precision
- **🌩️ Google Cloud Storage** - GCS bucket integration for file management
- **💳 Apple Pay** - App Store Server API integration for in-app purchase verification
- **📧 Email Providers** - Brevo and Resend email service integrations
- **🧪 Comprehensive Testing** - Coverage reporting with unit and integration test suites
- **⚙️ Background Jobs** - Celery with Redis for async task processing and scheduled jobs

## 🚀 Quick Start

### Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [uv](https://docs.astral.sh/uv/)

### Installation

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd FastApi-Template
   ```

2. **Install dependencies**

   Create a virtual environment

   ```bash
   python -m venv .venv
   ```

   Activate the virtual environment

   ```bash
   # On Linux / macOS
   source .venv/bin/activate
   # On Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

   Install dependencies

   ```bash
   # Install dependencies
   uv sync --all-groups

   # Install optional integrations as needed
   uv sync --all-groups --all-extras

   # Install pre-commit hooks
   pre-commit install
   ```

   **Note:** If you are facing SSL issues on Windows, use:

   ```bash
   uv sync --all-groups --native-tls
   uv sync --native-tls --all-extras
   ```

3. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Configure database**

   ```bash
      # Create database
      createdb fastapi_template

      # Run migrations
      alembic upgrade head
   ```

5. **Start the development server**

   ```bash
      python main.py
   ```

The API will be available at `http://localhost:8799` with interactive documentation at `http://localhost:8799/docs`.

## 📖 Documentation

Detailed documentation is available in the [docs/](docs/) folder:

- **[Architecture](docs/architecture.md)** - Project structure and design patterns
- **[API Reference](docs/api.md)** - Endpoint documentation and examples
- **[Development Guide](docs/development.md)** - Setup, testing, and contribution guidelines
- **[Deployment](docs/deployment.md)** - Production deployment strategies

## 🏗️ Project Structure

```text
├── app/
│   ├── api/                 # API routes and endpoints
│   │   └── v1/             # API version 1
│   │       ├── endpoints/  # Individual endpoint modules
│   │       └── deps/       # Dependencies (auth, database)
│   ├── core/               # Core functionality
│   │   ├── auth.py         # Authentication utilities
│   │   ├── config.py       # Configuration management
│   │   ├── db.py           # Database connection
│   │   └── exceptions.py   # Custom exceptions
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── repos/              # Repository pattern implementations
│   ├── services/           # Business logic and external services
│   ├── middleware/         # Custom middleware
│   └── alembic/            # Database migrations
├── docs/                   # Detailed documentation
├── scripts/                # Utility scripts
└── logs/                   # Application logs (Generated at runtime)
```

## 🔐 Authentication

The template includes a complete JWT-based authentication system:

- User registration and login
- Access and refresh tokens
- Password hashing with Argon2 (via pwdlib)
- Token blacklisting for secure logout
- Protected routes with dependency injection

### Example Usage

```python
from app.api.v1.deps.auth import get_current_user

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}!"}
```

## 🛠️ Development

### Code Quality

The project includes several tools for maintaining code quality:

- **Black** - Code formatting
- **Pre-commit hooks** - Automated checks before commits
- **Loguru** - Structured logging
- **Environment validation** - Pydantic settings

### Testing

The project maintains comprehensive test coverage with **~90% code coverage** across all modules:

```bash
# Run all tests with verbose output and detailed reporting
uv run pytest -v

# Run tests with coverage report
uv run pytest tests/ --cov=app --cov-report=term --cov-report=html

# View detailed HTML coverage report
# Open htmlcov/index.html in your browser
```

**Coverage Scope:**

- ✅ Unit, service, and integration tests
- 📊 Terminal and HTML coverage reports
- 🎯 Tests cover API endpoints, authentication, database operations, services, middleware, and utilities

### Security Analysis

Run security analysis using Bandit:

```bash
uv run bandit -r app -f json -o bandit_results.json
```

### Running Tests

```bash
uv run pytest -v
```

### Background Jobs & Task Queue

The project uses Celery for background job processing with Redis as the message broker.

#### Start Celery Worker

```bash
# Linux/macOS
./scripts/celery_worker.sh

# Windows
.\scripts\celery_worker.bat

# Or directly
celery -A app.services.task_queue worker --loglevel=info --pool=solo
```

#### Start Celery Beat (Scheduler)

```bash
# Linux/macOS
./scripts/celery_beat.sh

# Windows
.\scripts\celery_beat.bat

# Or directly
celery -A app.services.task_queue beat --loglevel=info
```

**Available Tasks:**

- `seed_fake_users` - Generates fake users for testing (runs every 10 seconds when `ENABLE_DATA_SEEDING=true`)

### Database Migrations

Use the scripts provided (Recommended):

```bash
# Run database migrations for linux/macOS
./scripts/alembic.sh

# Run database migrations for windows
.\scripts\alembic.bat
```

Or use Alembic commands directly:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## 🌍 Environment Configuration

The application supports multiple environments:

- **local** - Development with debug features
- **dev** - Development server
- **stg** - Pre-production testing (Staging)
- **prd** - Production deployment

Configure via environment variables or `.env` file:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_DB=postgres
POSTGRES_DB_SCHEMA=fastapi_template

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_SECONDS=2582000
REFRESH_TOKEN_EXPIRE_SECONDS=2592000

# Server
BACKEND_HOST=localhost
BACKEND_PORT=8799
CURRENT_ENVIRONMENT=local

# Redis (for caching and rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASS=your-redis-password

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100
RATE_LIMIT_WINDOW=60

# Celery & Background Tasks
ENABLE_DATA_SEEDING=false
SEEDING_USER_COUNT=100

# Email Providers
resend_api_key=your_resend_api_key_here
brevo_api_key=your_brevo_api_key_here
```

## 📦 Dependencies

Key dependencies include:

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM with async support
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **PostgreSQL** - Database driver (asyncpg)
- **JWT** - Token authentication
- **Loguru** - Logging
- **Redis** - Caching and rate limiting backend
- **Celery** - Distributed task queue for background jobs
- **B2SDK** - BackBlaze B2 cloud storage integration
- **Firebase Admin** - Firebase authentication and messaging
- **Google Cloud Storage** - GCS integration
- **Brevo / Resend** - Email delivery providers (optional `email` extra)

### Optional Dependency Extras

Install optional provider groups only when needed:

```bash
uv sync --extra email
uv sync --extra cloud-service
uv sync --extra cache
uv sync --extra task-queue
uv sync --extra apple-services
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - The amazing web framework
- [SQLAlchemy](https://sqlalchemy.org/) - The Python SQL toolkit
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation library
- [Fastapi Template by tiangolo](https://github.com/tiangolo/fastapi-template) - A FastAPI project template
- [Fastapi best practices](https://github.com/zhanymkanov/fastapi-best-practices) - Inspiration for best practices
- [Fastapi Tips](https://github.com/Kludex/fastapi-tips) - Useful tips and tricks from FastAPI Expert
- [Fastapi structure](https://github.com/rannysweis/fast-api-docker-poetry) - Project structure inspiration
