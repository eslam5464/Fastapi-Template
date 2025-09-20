# FastAPI Template

A production-ready FastAPI project template with modern best practices, async support, JWT authentication, and PostgreSQL integration.

## ✨ Features

- **🚀 FastAPI** - Modern, fast web framework for building APIs
- **🔐 JWT Authentication** - Secure token-based authentication system
- **📊 PostgreSQL** - Async database integration with SQLAlchemy 2.0
- **🗄️ Database Migrations** - Alembic for schema management
- **🏗️ Clean Architecture** - Repository pattern and dependency injection
- **📝 Automatic API Documentation** - Interactive Swagger UI and ReDoc
- **🔒 Security** - Password hashing, CORS, and security middleware
- **📊 Logging** - Structured logging with Loguru
- **⚡ Environment Management** - Multi-environment configuration
- **🧪 Development Tools** - Pre-commit hooks, code formatting with Black

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

   ```bash
   # Create a virtual environment
   uv venv .venv

   # Activate the virtual environment

   # On Linux / macOS
   source .venv/bin/activate
   # On Windows (PowerShell)
   .venv\Scripts\Activate.ps1

   # Install dependencies
   uv sync --all-groups

   # Install pre-commit hooks
   pre-commit install
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

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## 📖 Documentation

Detailed documentation is available in the `docs/` folder:

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
- Password hashing with bcrypt
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

### Security Analysis

Run security analysis using Bandit:

```bash
bandit -x VIRTUAL_ENV_PATH -f json -o bandit_results.json -r PROJECT_PATH
```

### Running Tests

```bash
# Install test dependencies
uv add pytest pytest-asyncio

# Run tests
pytest
```

### Database Migrations

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
- **staging** - Pre-production testing
- **prod** - Production deployment

Configure via environment variables or `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
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
