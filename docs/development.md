# Development Guide

This guide covers everything you need to know for developing with the FastAPI Template, including setup, testing, database management, and contribution guidelines.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.14+**: The project requires Python 3.14 or higher
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

# Optional integrations (install only what you use)
uv sync --all-extras

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
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-postgres-password
POSTGRES_DB=postgres
POSTGRES_DB_SCHEMA=fastapi_template

# Security Settings
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_SECONDS=3600
REFRESH_TOKEN_EXPIRE_SECONDS=2592000

# Server Configuration
BACKEND_HOST=localhost
BACKEND_PORT=8799
CURRENT_ENVIRONMENT=local

# CORS Settings (for development)
CORS_ORIGINS=localhost,0.0.0.0

# Logging
LOG_LEVEL=DEBUG

# Email Providers
RESEND_API_KEY=your_resend_api_key_here
BREVO_API_KEY=your_brevo_api_key_here
```

### 4. Database Setup

#### Create Database

```bash
# Using PostgreSQL command line
createdb fastapi_template

# Or using SQL
psql -c "CREATE DATABASE fastapi_template;"
```

#### Install Redis (Required for Celery)

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
# Or use Docker:
docker run -d -p 6379:6379 redis:alpine
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
uv sync --group test

# Create test database
createdb fastapi_template_test

# Set base database env vars (test DB is derived as <POSTGRES_DB>_test)
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your-postgres-password
export POSTGRES_DB=fastapi_template
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
    engine = create_async_engine(settings.db_test_url)
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

<!-- --- FEATURE[openobserve] START --- -->
#### Centralized Log Aggregation (Optional)

Logs can be shipped to OpenObserve without blocking requests; see [integrations/openobserve.md](integrations/openobserve.md).

<!-- --- FEATURE[openobserve] END --- -->

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

<!-- --- FEATURE[redis_rate_limit] START --- -->
### Rate Limiting

See [integrations/rate-limiting.md](integrations/rate-limiting.md).

<!-- --- FEATURE[redis_rate_limit] END --- -->

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

# Verify database env vars
echo $POSTGRES_HOST
echo $POSTGRES_DB
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

<!-- --- FEATURE[backblaze] START --- -->
### BackBlaze B2 Cloud Storage Integration

See [integrations/backblaze.md](integrations/backblaze.md) for setup, usage and an endpoint example.

<!-- --- FEATURE[backblaze] END --- -->

<!-- --- FEATURE[firebase] START --- -->
### Firebase Authentication & Messaging Integration

See [integrations/firebase.md](integrations/firebase.md) for setup, usage and an endpoint example.

<!-- --- FEATURE[firebase] END --- -->

<!-- --- FEATURE[firestore] START --- -->
### Firestore NoSQL Database Integration

See [integrations/firestore.md](integrations/firestore.md) for usage, an endpoint example and when to use Firestore alongside PostgreSQL.

<!-- --- FEATURE[firestore] END --- -->

<!-- --- FEATURE[gcs] START --- -->
### Google Cloud Storage (GCS) Integration

See [integrations/gcs.md](integrations/gcs.md) for setup, usage and an endpoint example.

<!-- --- FEATURE[gcs] END --- -->

### Apple Pay (App Store Server API) Integration

The template includes Apple Pay integration for verifying in-app purchases and subscriptions via the App Store Server API.

#### Apple Pay Setup

1. **App Store Connect Configuration**

   - Log in to [App Store Connect](https://appstoreconnect.apple.com)
   - Navigate to Users and Access → Keys → App Store Connect API
   - Generate a new API key and download the `.p8` private key file

2. **Download Apple Root Certificate**

   - Download `AppleRootCA-G3.cer` from [Apple PKI](https://www.apple.com/certificateauthority/)
   - Store it securely in your project or server

3. **Configure Credentials**

Add to your `.env` file:

```env
APPLE_PAY_STORE_PRIVATE_KEY_ID=YOUR_KEY_ID
APPLE_PAY_STORE_PRIVATE_KEY=-----KEY-----
APPLE_PAY_STORE_ISSUER_ID=YOUR_ISSUER_ID
APPLE_PAY_STORE_BUNDLE_ID=com.yourcompany.yourapp
APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH=/path/to/AppleRootCA-G3.cer
```

#### Apple Pay Usage Example

```python
from app.services.payments.apple_pay import ApplePay
from app.schemas.apple_pay import ApplePayStoreCredentials

# Initialize Apple Pay client
credentials = ApplePayStoreCredentials(
    private_key_id=settings.apple_pay_store_private_key_id,
    private_key=settings.apple_pay_store_private_key,
    issuer_id=settings.apple_pay_store_issuer_id,
    bundle_id=settings.apple_pay_store_bundle_id,
    root_certificate_path=settings.apple_pay_store_root_certificate_path
)
apple_pay = ApplePay(credentials)

# Verify a transaction
transaction_id = "1000000123456789"
try:
    transaction_info = apple_pay.get_transaction_info(transaction_id)
    print(f"Product ID: {transaction_info.product_id}")
    print(f"Purchase Date: {transaction_info.purchase_date}")
    print(f"Status: {transaction_info.status}")
except ApplePayVerificationError as e:
    print(f"Verification failed: {e}")

# Get subscription status
original_transaction_id = "1000000123456789"
subscription_status = apple_pay.get_subscription_status(original_transaction_id)
for subscription in subscription_status.data:
    print(f"Subscription Group: {subscription.subscription_group_identifier}")
    print(f"Status: {subscription.status}")

# Get transaction history
history = apple_pay.get_transaction_history(original_transaction_id)
for transaction in history.signed_transactions:
    print(f"Transaction: {transaction.transaction_id}")
```

#### Apple Pay Integration in Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.payments.apple_pay import ApplePay
from app.core.config import settings
from app.core.exceptions.apple_pay import ApplePayVerificationError

router = APIRouter()

def get_apple_pay_client() -> ApplePay:
    """Dependency to get Apple Pay client"""
    return ApplePay(settings.apple_pay_credentials)

@router.post("/verify-purchase")
async def verify_purchase(
    transaction_id: str,
    apple_pay: ApplePay = Depends(get_apple_pay_client)
):
    try:
        transaction = apple_pay.get_transaction_info(transaction_id)
        return {
            "valid": True,
            "product_id": transaction.product_id,
            "purchase_date": transaction.purchase_date,
            "expires_date": transaction.expires_date
        }
    except ApplePayVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscription-status/{original_transaction_id}")
async def check_subscription(
    original_transaction_id: str,
    apple_pay: ApplePay = Depends(get_apple_pay_client)
):
    try:
        status = apple_pay.get_subscription_status(original_transaction_id)
        return {
            "active": any(s.status == "ACTIVE" for s in status.data),
            "subscriptions": [
                {
                    "group_id": s.subscription_group_identifier,
                    "status": s.status
                }
                for s in status.data
            ]
        }
    except ApplePayVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

#### Apple Pay Use Cases

- **In-App Purchase Verification**: Verify one-time purchases from iOS apps
- **Subscription Management**: Check subscription status and renewal info
- **Transaction History**: Retrieve complete purchase history for a user
- **Refund Detection**: Identify refunded transactions
- **Server-to-Server Notifications**: Handle App Store Server Notifications (webhooks)

### Security Middleware

The template includes several security middleware components that are automatically applied to all requests.

#### CSRF Protection

CSRF (Cross-Site Request Forgery) protection is implemented via middleware for state-changing requests.

**How it works:**

- Validates CSRF tokens for POST, PUT, DELETE, PATCH requests
- Tokens are validated against the session or a secure cookie
- Safe methods (GET, HEAD, OPTIONS) are exempt

**Frontend Integration:**

```javascript
// Include CSRF token in requests
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/v1/users/me', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  body: JSON.stringify(userData)
});
```

#### Security Headers Middleware

Automatically adds security headers to all responses:

- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-XSS-Protection: 1; mode=block` - XSS filter (legacy browsers)
- `Strict-Transport-Security` - HSTS for HTTPS enforcement (production only)

<!-- --- FEATURE[redis_rate_limit] START --- -->
#### Rate Limit Headers Middleware

Adds rate limiting information to responses (see [integrations/rate-limiting.md](integrations/rate-limiting.md)).

<!-- --- FEATURE[redis_rate_limit] END --- -->

<!-- --- FEATURE[redis_token_blacklist] START --- -->
### Token Blacklisting (Logout)

See [integrations/token-revocation.md](integrations/token-revocation.md).

<!-- --- FEATURE[redis_token_blacklist] END --- -->

### Cache Decorators

The template includes caching decorators for easy function-level caching.

```python
from app.services.cache.decorators import cached, cache_invalidate

# Cache function result for 5 minutes
@cached(ttl=300, key_prefix="user")
async def get_user_profile(user_id: int) -> dict:
    # Expensive database query
    return await fetch_user_from_db(user_id)

# Invalidate cache when data changes
@cache_invalidate(key_pattern="user:*")
async def update_user_profile(user_id: int, data: dict):
    await save_user_to_db(user_id, data)
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
