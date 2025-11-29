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
BACKEND_PORT=8799
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
curl http://localhost:8799/docs
```

## Development Workflow

### Running the Application

#### Development Server

```bash
# Using the main script (with auto-reload)
python main.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8799
```

#### Production Mode

```bash
# Using gunicorn (production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8799
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

```text
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

### Logging System

The application uses a production-grade logging system built with Loguru, providing structured, traceable logs across all environments.

#### Basic Usage

```python
from loguru import logger

# Different log levels
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")

# Structured logging with context
logger.info("User created", user_id=user.id, username=user.username)

# Exception logging with full traceback
try:
    risky_operation()
except Exception as e:
    logger.exception("Operation failed")  # Automatically includes traceback
```

#### Log Output Locations

**Console Output (Development)**:

- Colored output for quick visual scanning
- Shows timestamp, log level, process ID, request ID, and message
- Simplified format for rapid debugging

**File Output (Always Active)**:

- Located in `logs/app.log`
- Includes full context: module, function, line number
- UTC timestamps for consistency across time zones
- Automatically rotates at 10MB, compresses with gzip
- Retains logs for 3 months

#### Request Tracing

Every HTTP request automatically gets a unique request ID that appears in all related logs:

```python
# All logs within a request context automatically include the request ID
logger.info("Processing user registration")
# Output: ... | ReqID:abc123 | Processing user registration

logger.info("Database query executed")
# Output: ... | ReqID:abc123 | Database query executed
```

To find all logs for a specific request:

```bash
# Search logs for specific request ID
grep "ReqID:abc123" logs/app.log

# Or use log viewer tools to filter by request_id field
```

#### Log Levels by Environment

- **Local/Development**: DEBUG and above
- **Staging/Production**: INFO and above

Configure via `.env`:

```bash
LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR, CRITICAL
```

#### Centralized Log Aggregation (Optional)

For production deployments, configure remote log shipping:

```bash
# Add to .env for centralized logging
OPENOBSERVE_URL=https://observe.example.com
OPENOBSERVE_TOKEN=your_base64_token
OPENOBSERVE_ORG=your_organization
OPENOBSERVE_STREAM=fastapi_logs
OPENOBSERVE_BATCH_SIZE=10
OPENOBSERVE_FLUSH_INTERVAL=5.0
```

Benefits:

- Non-blocking: doesn't slow down your application
- Batched: reduces network overhead
- Resilient: continues local logging if remote service unavailable
- Searchable: query logs across all application instances

#### Multi-Worker Considerations

When running with multiple workers (`--workers 4`):

- Each log entry includes process ID (PID) to identify which worker generated it
- Thread-safe queue-based writing prevents log corruption
- All workers write to same unified log file safely

```bash
# Run with multiple workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8799

# Logs will show:
# ... | PID:12345 | ReqID:abc123 | Message from worker 1
# ... | PID:12346 | ReqID:def456 | Message from worker 2
```

#### Viewing Logs

```bash
# Tail logs in real-time
tail -f logs/app.log

# Search for errors
grep "ERROR" logs/app.log

# View logs with timestamps in specific range
grep "2025-01-19" logs/app.log

# Decompress old logs
gunzip logs/app.2025-01-01.log.gz
cat logs/app.2025-01-01.log
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
# Using the CacheManager service
from app.services.cache import cache_manager

async def get_user_profile(user_id: str):
    # Try to get from cache first
    cache_key = f"user:profile:{user_id}"
    cached_data = await cache_manager.get(cache_key)

    if cached_data:
        return cached_data

    # Fetch from database if not cached
    user_data = await fetch_user_from_db(user_id)

    # Store in cache with TTL
    await cache_manager.set(cache_key, user_data, expire=300)

    return user_data
```

### Rate Limiting

The template includes a production-ready rate limiting system using Redis and sliding window algorithm.

#### Quick Start

Apply pre-configured rate limiters to endpoints using FastAPI dependencies:

```python
from fastapi import APIRouter, Depends
from app.api.v1.deps.rate_limit import (
    rate_limit_auth,    # Strict: 10 req/min (for login, signup)
    rate_limit_api,     # Default: 100 req/min (for general API)
    rate_limit_public,  # Lenient: 1000 req/min (for public data)
    rate_limit_user,    # User-based: 300 req/min (for authenticated)
)

router = APIRouter()

# IP-based rate limiting for authentication
@router.post("/login", dependencies=[Depends(rate_limit_auth)])
async def login(credentials: LoginForm):
    # Limited to 10 requests per minute per IP
    pass

# IP-based rate limiting for public API
@router.get("/posts", dependencies=[Depends(rate_limit_api)])
async def list_posts():
    # Limited to 100 requests per minute per IP
    pass

# User-based rate limiting for authenticated endpoints
@router.get("/profile", dependencies=[Depends(rate_limit_user)])
async def get_profile(current_user: User = Depends(get_current_user)):
    # Limited to 300 requests per minute per user
    # Multiple users on same IP each get their own quota
    pass
```

#### Custom Rate Limits

Create custom rate limiters for specific endpoints:

```python
from app.api.v1.deps.rate_limit import create_rate_limit

# Custom limit for heavy operations (5 requests per 5 minutes)
heavy_limit = create_rate_limit(limit=5, window=300, prefix="heavy")

@router.post("/export", dependencies=[Depends(heavy_limit)])
async def export_large_file():
    pass

# Custom user-based limit (20 uploads per minute per user)
upload_limit = create_rate_limit(
    limit=20,
    window=60,
    prefix="upload",
    use_user_id=True
)

@router.post("/upload", dependencies=[Depends(upload_limit)])
async def upload_file(current_user: User = Depends(get_current_user)):
    pass
```

#### Rate Limit Response Headers

All rate-limited endpoints automatically include headers in responses:

```http
X-RateLimit-Limit: 100          # Maximum requests allowed
X-RateLimit-Remaining: 73       # Requests remaining in window
X-RateLimit-Reset: 1701234567   # Unix timestamp when limit resets
```

When limit is exceeded, clients receive HTTP 429:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701234567

{
  "detail": "Rate limit exceeded. Please slow down your requests."
}
```

#### Environment Variables

Configure rate limits in `.env`:

```env
# Rate limiting settings (requests per window)
RATE_LIMIT_DEFAULT=100      # General API endpoints
RATE_LIMIT_WINDOW=60        # Time window in seconds
RATE_LIMIT_STRICT=10        # Authentication endpoints
RATE_LIMIT_LENIENT=1000     # Public endpoints
RATE_LIMIT_USER=300         # Authenticated user endpoints
```

#### Rate Limiting Strategies

**IP-Based** (for unauthenticated endpoints):

- Login, signup, password reset: 10 req/min per IP
- Public API endpoints: 100 req/min per IP
- Health checks, documentation: 1000 req/min per IP

**User-Based** (for authenticated endpoints):

- User profile, settings: 300 req/min per user
- Solves shared IP problem (office/cafe networks)
- Each user gets independent quota regardless of IP

#### Available Prefixes

Rate limit keys use prefixes to separate quotas by endpoint group:

```python
from app.core.constants import RateLimitPrefix

# Pre-defined prefixes
RateLimitPrefix.AUTH      # "ratelimit:auth:"    - Authentication
RateLimitPrefix.USER      # "ratelimit:user:"    - User endpoints
RateLimitPrefix.API       # "ratelimit:api:"     - General API
RateLimitPrefix.PUBLIC    # "ratelimit:public:"  - Public endpoints
RateLimitPrefix.EXPORT    # "ratelimit:export:"  - File exports
RateLimitPrefix.UPLOAD    # "ratelimit:upload:"  - File uploads
RateLimitPrefix.SEARCH    # "ratelimit:search:"  - Search queries
RateLimitPrefix.ADMIN     # "ratelimit:admin:"   - Admin operations
```

Add custom prefixes to `app/core/constants.py` to avoid collisions.

#### Local Development

Rate limiting is automatically disabled in LOCAL environment:

- No Redis connection required
- All requests allowed (no limits enforced)
- Useful for development and testing

To test rate limiting locally, change environment in `.env`:

```env
CURRENT_ENVIRONMENT=dev  # Enable rate limiting
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

```text
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

### Using Logs for Debugging

The logging system is your first line of defense when troubleshooting issues:

```bash
# Check recent errors
grep "ERROR" logs/app.log | tail -20

# Find all logs for a specific request (if you have the request ID)
grep "ReqID:abc123" logs/app.log

# Monitor logs in real-time
tail -f logs/app.log

# Check logs from specific worker process
grep "PID:12345" logs/app.log

# View logs with full exception details
grep -A 10 "ERROR" logs/app.log  # Shows 10 lines after each error
```

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

### Firebase Authentication & Messaging Integration

The template includes Firebase integration for user authentication, user management, and push notifications.

#### Firebase Setup

1. **Create Firebase Project**

   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or use existing one
   - Navigate to Project Settings → Service Accounts
   - Generate new private key (downloads JSON file)

2. **Configure Credentials**

Add to your `.env` file or provide at runtime from `.env.example`

#### Firebase Authentication Usage

```python
from app.services.firebase import Firebase
from app.schemas.firebase import FirebaseServiceAccount

# Initialize Firebase (uses singleton pattern)
firebase_service = Firebase()

# Get user by ID
user = firebase_service.get_user_by_id("user_uid_123")
print(f"User: {user.email}, Display Name: {user.display_name}")

# Get user by email
user = firebase_service.get_user_by_email("user@example.com")

# Get user by phone number
user = firebase_service.get_user_by_phone_number("+1234567890")

# List all users with pagination
users_page = firebase_service.get_all_users(max_results=1000)
for user in users_page.iterate_all():
    print(f"UID: {user.uid}, Email: {user.email}")

# Create custom token for user
custom_token = firebase_service.create_custom_id_token(
    uid="user_uid_123",
    additional_claims={"role": "admin", "premium": True}
)

# Verify ID token from client
try:
    decoded_token = firebase_service.verify_id_token(id_token="client_token_here")
    uid = decoded_token['uid']
    print(f"Token verified for user: {uid}")
except ConnectionAbortedError as e:
    print(f"Token invalid or expired: {e}")
```

#### Firebase Push Notifications

```python
from app.services.firebase import Firebase

firebase_service = Firebase()

# Validate FCM token
device_token = "fcm_device_token_here"
is_valid = firebase_service.validate_fcm_token(device_token)

# Send notification to single device
success = firebase_service.notify_a_device(
    device_token=device_token,
    title="Welcome!",
    content="Thank you for signing up"
)

# Send notification to multiple devices (automatically batches in chunks of 500)
device_tokens = ["token1", "token2", "token3", ...]  # Can be thousands
success_count = firebase_service.notify_multiple_devices(
    device_tokens=device_tokens,
    title="New Update Available",
    content="Version 2.0 is now available"
)
print(f"Successfully sent to {success_count} devices")
```

#### Firebase Integration in Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.firebase import Firebase

router = APIRouter()

def get_firebase_service() -> Firebase:
    """Dependency to get Firebase service"""
    return Firebase()

@router.post("/auth/verify-token")
async def verify_user_token(
    token: str,
    firebase: Firebase = Depends(get_firebase_service)
):
    try:
        decoded_token = firebase.verify_id_token(token)
        return {
            "uid": decoded_token['uid'],
            "email": decoded_token.get('email'),
            "verified": True
        }
    except ConnectionAbortedError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/notifications/send")
async def send_push_notification(
    user_id: str,
    title: str,
    message: str,
    firebase: Firebase = Depends(get_firebase_service)
):
    # Get user's device tokens from your database
    device_tokens = await get_user_device_tokens(user_id)

    success_count = firebase.notify_multiple_devices(
        device_tokens=device_tokens,
        title=title,
        content=message
    )

    return {
        "sent": success_count,
        "total": len(device_tokens)
    }
```

### Firestore NoSQL Database Integration

Firestore integration for document-based data storage alongside your PostgreSQL database.

#### Firestore Setup

Uses the same Firebase service account credentials as Firebase Authentication.

#### Firestore Usage

```python
from app.services.firestore import Firestore
from app.schemas.firebase import FirebaseServiceAccount

# Initialize Firestore (uses singleton pattern)
service_account = FirebaseServiceAccount(
    type="service_account",
    project_id="your-project-id",
    # ... other credentials
)
firestore_service = Firestore(service_account)

# Add a document
firestore_service.add_document(
    collection_name="users",
    document_id="user123",
    data={
        "name": "John Doe",
        "email": "john@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    }
)

# Get a document
user_data = firestore_service.get_document(
    collection_name="users",
    document_id="user123"
)
if user_data:
    print(f"User: {user_data['name']}")

# Update a document
firestore_service.update_document(
    collection_name="users",
    document_id="user123",
    data={
        "preferences.theme": "light",  # Nested field update
        "last_login": "2025-01-19T10:30:00Z"
    }
)

# Fetch all documents from collection
all_users = firestore_service.fetch_all_documents("users")
for user in all_users:
    print(f"User: {user['name']}")

# Remove a document
firestore_service.remove_document(
    collection_name="users",
    document_id="user123"
)
```

#### Error Handling

```python
from app.core.exceptions.firebase_exceptions import FirebaseDocumentNotFoundError

try:
    firestore_service.update_document(
        collection_name="users",
        document_id="nonexistent",
        data={"status": "active"}
    )
except FirebaseDocumentNotFoundError as e:
    print(f"Document not found: {e}")
```

#### Firestore Integration in Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.firestore import Firestore
from app.core.exceptions.firebase_exceptions import FirebaseDocumentNotFoundError

router = APIRouter()

def get_firestore_service() -> Firestore:
    """Dependency to get Firestore service"""
    from app.core.config import settings
    return Firestore(settings.firebase_credentials)

@router.post("/user-preferences")
async def save_user_preferences(
    user_id: str,
    preferences: dict,
    firestore: Firestore = Depends(get_firestore_service)
):
    firestore.add_document(
        collection_name="user_preferences",
        document_id=user_id,
        data=preferences
    )
    return {"status": "saved"}

@router.get("/user-preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    firestore: Firestore = Depends(get_firestore_service)
):
    prefs = firestore.get_document(
        collection_name="user_preferences",
        document_id=user_id
    )
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs

@router.put("/user-preferences/{user_id}")
async def update_user_preferences(
    user_id: str,
    preferences: dict,
    firestore: Firestore = Depends(get_firestore_service)
):
    try:
        firestore.update_document(
            collection_name="user_preferences",
            document_id=user_id,
            data=preferences
        )
        return {"status": "updated"}
    except FirebaseDocumentNotFoundError:
        raise HTTPException(status_code=404, detail="User preferences not found")
```

#### Use Cases for Firestore

**When to use Firestore alongside PostgreSQL:**

- **User Preferences**: Store user settings, UI state, personalization
- **Real-time Data**: Chat messages, notifications, activity feeds
- **Session Data**: Temporary data that doesn't need relational integrity
- **Device Tokens**: FCM tokens for push notifications
- **Analytics Events**: User behavior tracking, event logging
- **Cache Layer**: Frequently accessed data to reduce database load

**When to use PostgreSQL:**

- **Transactional Data**: Orders, payments, critical business data
- **Relational Data**: Data with complex relationships and foreign keys
- **Data Integrity**: When ACID compliance is required
- **Complex Queries**: JOINs, aggregations, full-text search

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
