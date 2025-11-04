# Development Guide

This guide covers everything you need to know for developing with the FastAPI Template, including setup, testing, database management, and contribution guidelines.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+**: The project requires Python 3.13 or higher
- **PostgreSQL**: Database server (version 12+)
- **Git**: Version control system
- **uv** (recommended): Fast Python package manager, or pip as alternative

### Optional Tools

- **Docker**: For containerized development
- **PostgreSQL client**: For database management (psql, pgAdmin, etc.)
- **VS Code**: Recommended IDE with Python extensions

## Environment Setup

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd FastApi-Template
```

### 2. Python Environment

#### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment with dependencies
uv sync

# Activate the environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Using pip and venv

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/fastapi_template

# Security Settings
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CURRENT_ENVIRONMENT=local

# CORS Settings (for development)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Logging
LOG_LEVEL=DEBUG
```

### 4. Database Setup

#### Create Database

```bash
# Using PostgreSQL command line
createdb fastapi_template

# Or using SQL
psql -c "CREATE DATABASE fastapi_template;"
```

#### Run Migrations

```bash
# Initialize Alembic (only if starting fresh)
alembic init alembic

# Run existing migrations
alembic upgrade head
```

### 5. Verify Installation

```bash
# Run the application
python main.py

# Check if it's working
curl http://localhost:8000/docs
```

## Development Workflow

### Running the Application

#### Development Server

```bash
# Using the main script (with auto-reload)
python main.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Mode

```bash
# Using gunicorn (production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
```

### Code Quality Tools

The project includes several tools for maintaining code quality:

#### Black (Code Formatting)

```bash
# Format all code
black .

# Check formatting without changes
black --check .

# Format specific files
black app/main.py
```

#### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

## Database Management

### Alembic Migrations

#### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration
alembic revision -m "Description of changes"
```

#### Applying Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade revision_id

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade revision_id
```

#### Migration Management

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

### Database Operations

#### Reset Database

```bash
# Drop all tables and recreate
alembic downgrade base
alembic upgrade head
```

#### Seed Data

```bash
# Run custom seeder (if implemented)
python -m app.core.seeders
```

## Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_auth.py             # Authentication tests
├── test_users.py            # User endpoint tests
├── test_models.py           # Model tests
├── test_repositories.py     # Repository tests
└── integration/             # Integration tests
    ├── test_api.py          # Full API tests
    └── test_database.py     # Database integration tests
```

### Running Tests

#### Setup Test Environment

```bash
# Install test dependencies
uv add pytest pytest-asyncio pytest-cov httpx

# Create test database
createdb fastapi_template_test

# Set test environment variable
export DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/fastapi_template_test
```

#### Execute Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test function
pytest tests/test_auth.py::test_login

# Run with verbose output
pytest -v

# Run in parallel (with pytest-xdist)
pytest -n auto
```

### Writing Tests

#### Test Example

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/signup",
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
                "first_name": "Test",
                "last_name": "User"
            }
        )
    assert response.status_code == 201
    assert "access_token" in response.json()
```

#### Test Fixtures

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.config import settings
from app.core.db import get_session, Base

@pytest.fixture
async def async_session():
    engine = create_async_engine(settings.database_url_test)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## Debugging

### Logging

The application uses Loguru for structured logging:

```python
from loguru import logger

# Different log levels
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")

# Structured logging
logger.info("User created", user_id=user.id, username=user.username)
```

### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "program": "main.py",
      "console": "integratedTerminal",
      "env": {
        "CURRENT_ENVIRONMENT": "local"
      }
    }
  ]
}
```

### Database Debugging

```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or in settings
echo=True  # In database engine creation
```

## Performance Optimization

### Database Optimization

```python
# Use select with joinedload for relationships
from sqlalchemy.orm import selectinload

users = await session.execute(
    select(User).options(selectinload(User.posts))
)

# Use pagination for large datasets
async def get_users_paginated(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100
):
    result = await session.execute(
        select(User).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### Caching

```python
# Example with Redis (if implemented)
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_by_id(user_id: str):
    # Cached function
    pass
```

### Async Best Practices

```python
# Use async/await consistently
async def async_operation():
    result = await some_async_function()
    return result

# Use async context managers
async with AsyncSession(engine) as session:
    # Database operations
    pass
```

## Adding New Features

### Creating New Endpoints

1. **Create schema** in `app/schemas/`
2. **Create model** in `app/models/` (if needed)
3. **Create repository** in `app/repos/`
4. **Create endpoint** in `app/api/v1/endpoints/`
5. **Add to router** in `app/api/v1/router.py`
6. **Write tests**

#### Example: Adding a Posts Feature

**Schema** (`app/schemas/post.py`):

```python
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class PostBase(BaseModel):
    title: str
    content: str

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime
```

**Model** (`app/models/post.py`):

```python
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Post(Base):
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Relationship
    author: Mapped["User"] = relationship("User", back_populates="posts")
```

**Repository** (`app/repos/post.py`):

```python
from app.repos.base import BaseRepository
from app.models.post import Post

class PostRepository(BaseRepository[Post]):
    async def get_by_author(
        self,
        session: AsyncSession,
        author_id: UUID
    ) -> List[Post]:
        result = await session.execute(
            select(Post).where(Post.author_id == author_id)
        )
        return result.scalars().all()
```

**Endpoint** (`app/api/v1/endpoints/post.py`):

```python
from fastapi import APIRouter, Depends
from app.schemas.post import PostCreate, PostResponse
from app.repos.post import PostRepository

router = APIRouter()

@router.post("/", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    post_repo: PostRepository = Depends(get_post_repository)
):
    return await post_repo.create(session, post_data, author_id=current_user.id)
```

### Database Migration for New Feature

```bash
alembic revision --autogenerate -m "Add posts table"
alembic upgrade head
```

## Security Best Practices

### Password Security

```python
# Always hash passwords
from app.core.auth import get_password_hash, verify_password

hashed = get_password_hash("plain_password")
is_valid = verify_password("plain_password", hashed)
```

### Input Validation

```python
# Use Pydantic for validation
from pydantic import validator, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr

    @validator('username')
    def username_must_be_alphanumeric(cls, v):
        assert v.isalnum(), 'Username must be alphanumeric'
        return v
```

### SQL Injection Prevention

```python
# Use SQLAlchemy ORM (automatic protection)
# Avoid raw SQL queries
# If needed, use parameterized queries

# Good
result = await session.execute(
    select(User).where(User.username == username)
)

# Avoid
# result = await session.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

## Contribution Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Add type hints to all functions
- Write descriptive docstrings
- Keep functions small and focused

### Commit Messages

Use conventional commit format:

```
feat: add user authentication
fix: resolve database connection issue
docs: update API documentation
test: add user repository tests
refactor: improve error handling
```

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Write** tests for new functionality
4. **Ensure** all tests pass
5. **Format** code with Black
6. **Write** clear commit messages
7. **Submit** pull request with description

### Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance implications considered
- [ ] Security implications reviewed

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_ctl status

# Check database exists
psql -l | grep fastapi_template

# Verify connection string
echo $DATABASE_URL
```

#### Migration Issues

```bash
# Check current migration state
alembic current

# Reset migrations (development only)
alembic downgrade base
alembic upgrade head

# Fix migration conflicts
alembic merge -m "merge migrations" head1 head2
```

#### Import Errors

```bash
# Check Python path
echo $PYTHONPATH

# Verify virtual environment
which python
pip list

# Reinstall dependencies
uv sync --reinstall
```

### Performance Issues

- Enable SQL query logging to identify slow queries
- Use database indexes for frequently queried fields
- Implement connection pooling
- Add caching for expensive operations
- Profile code with tools like `py-spy`

### Memory Issues

- Monitor memory usage with `memory_profiler`
- Use generators for large datasets
- Implement pagination for API endpoints
- Close database connections properly

## Advanced Development

### BackBlaze B2 Cloud Storage Integration

The template includes integration with BackBlaze B2 cloud storage service for file management.

#### Setup

1. **Create BackBlaze Account**

   - Sign up at [backblaze.com](https://www.backblaze.com/b2/cloud-storage.html)
   - Create an application key in account settings

2. **Configure Credentials**

Add to your `.env` file (optional - can be provided at runtime):

```env
# BackBlaze B2 Configuration (Optional)
B2_APPLICATION_KEY_ID=your_key_id_here
B2_APPLICATION_KEY=your_application_key_here
B2_BUCKET_NAME=your_bucket_name
```

#### Usage Example

```python
from app.services.back_blaze_b2 import BackBlaze, B2BucketTypeEnum
from app.schemas import ApplicationData, UploadedFileInfo

# Initialize BackBlaze client
app_data = ApplicationData(
    app_id="your_application_key_id",
    app_key="your_application_key"
)
b2_client = BackBlaze(app_data)

# List available buckets
buckets = b2_client.list_buckets()

# Create a new bucket
b2_client.create_bucket("my-new-bucket", B2BucketTypeEnum.ALL_PRIVATE)

# Select a bucket for operations
b2_client.select_bucket("my-bucket-name")

# Upload a file
file_version = b2_client.upload_file(
    local_file_path="/path/to/local/file.pdf",
    b2_file_name="documents/file.pdf",
    file_info=UploadedFileInfo(scanned=True)
)

# Get download URL
download_link = b2_client.get_download_url_by_name("documents/file.pdf")
print(download_link.download_url)

# Get temporary download link (with auth token)
from pydantic import AnyUrl
temp_link = b2_client.get_temporary_download_link(
    url=AnyUrl(download_link.download_url),
    valid_duration_in_seconds=3600  # 1 hour
)

# Delete a file
b2_client.delete_file(
    file_id=file_version.id_,
    file_name="documents/file.pdf"
)

# Update bucket settings
b2_client.update_selected_bucket(
    bucket_type=B2BucketTypeEnum.ALL_PUBLIC
)

# Delete bucket
b2_client.delete_selected_bucket()
```

#### BackBlaze B2 Features

- **Bucket Management**: Create, delete, update, list, and select buckets
- **File Operations**: Upload, download, and delete files
- **URL Generation**:
  - Public download URLs for public buckets
  - File ID-based URLs
  - Temporary authenticated URLs for private files
- **Method Chaining**: Fluent interface for bucket selection
- **Metadata**: Custom file information with `UploadedFileInfo`
- **Error Handling**: Comprehensive exception handling with detailed logging

#### Bucket Types

- `ALL_PUBLIC`: Files are publicly accessible
- `ALL_PRIVATE`: Files require authentication
- `SNAPSHOT`: Snapshot storage
- `SHARE`: Shared access
- `RESTRICTED`: Restricted access with authorization rules

#### Integration in Endpoints

```python
from fastapi import APIRouter, Depends, UploadFile, File
from app.services.back_blaze_b2 import BackBlaze
from app.schemas import ApplicationData

router = APIRouter()

def get_b2_client() -> BackBlaze:
    """Dependency to get BackBlaze client"""
    app_data = ApplicationData(
        app_id=settings.b2_app_id,
        app_key=settings.b2_app_key
    )
    return BackBlaze(app_data).select_bucket(settings.b2_bucket_name)

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    b2_client: BackBlaze = Depends(get_b2_client)
):
    # Save uploaded file temporarily
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Upload to BackBlaze
    result = b2_client.upload_file(
        local_file_path=temp_path,
        b2_file_name=f"uploads/{file.filename}"
    )

    # Get download URL
    download_link = b2_client.get_download_url_by_file_id(result.id_)

    return {
        "file_id": result.id_,
        "file_name": result.file_name,
        "download_url": download_link.download_url
    }
```

### Custom Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Pre-processing
        start_time = time.time()

        response = await call_next(request)

        # Post-processing
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        return response
```

### Background Tasks

```python
from fastapi import BackgroundTasks

def send_email(email: str, message: str):
    # Email sending logic
    pass

@router.post("/send-notification/")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_email, email, "Welcome!")
    return {"message": "Email sent in background"}
```

### WebSocket Support

```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message: {data}")
```

This development guide provides a comprehensive foundation for working with the FastAPI template. For specific questions or advanced use cases, refer to the FastAPI documentation or create an issue in the project repository.
