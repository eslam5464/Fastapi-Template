# Architecture Documentation

## Overview

This FastAPI template follows clean architecture principles with a focus on maintainability, testability, and scalability. The project is structured using the Repository pattern, dependency injection, and clear separation of concerns.

## Design Principles

### 1. Clean Architecture

- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Single Responsibility**: Each module has one reason to change

### 2. Repository Pattern

- Abstracts data access logic
- Makes testing easier with mock repositories
- Provides consistent interface for data operations

### 3. Dependency Injection

- Loose coupling between components
- Easy testing and mocking
- Configurable dependencies

## Project Structure

```text
app/
├── main.py                 # Application entry point (lifespan, middleware, routers)
├── web.py                  # Gunicorn application runner
├── api/                    # API layer
│   ├── routes.py           # Unversioned routes (/health)
│   └── v1/                 # API version 1
│       ├── router.py       # Version router
│       ├── deps/           # Route dependencies
│       └── endpoints/      # Endpoint modules
├── core/                   # Settings, infrastructure, shared helpers
│   ├── config.py           # Settings (pydantic-settings)
│   ├── db.py               # Async engine and sessions
│   ├── constants.py        # Application constants
│   ├── logger.py           # Logging configuration
│   ├── responses.py        # Standard API responses
│   ├── utils.py            # Utility functions
│   ├── credentials/        # Credential models of the integrations
│   └── exceptions/
│       ├── base.py         # Base exception classes
│       └── http_exceptions.py  # HTTP exceptions
├── models/                 # SQLAlchemy models
│   └── base.py
├── schemas/                # Pydantic schemas
│   ├── base.py
│   └── health_check.py
├── repos/                  # Repository layer
│   └── base.py
├── services/               # Business logic
│   ├── exceptions/         # Service-layer exceptions
│   └── types/              # Service-layer TypedDicts
├── middleware/
│   ├── logging.py          # Request logging middleware
│   └── security_headers.py # Security headers middleware
└── alembic/                # Database migrations
    ├── env.py
    ├── script.py.mako
    └── versions/
```

<!-- --- FEATURE[auth|api_v2|csrf|redis|celery|firebase|gcs|backblaze|resend|brevo|openobserve|apple_pay] START --- -->
Optional files in this project:

<!-- --- FEATURE[auth|api_v2|csrf|redis|celery|firebase|gcs|backblaze|resend|brevo|openobserve|apple_pay] END --- -->
<!-- --- FEATURE[auth] START --- -->
- `app/models/user.py`, `app/repos/user.py`, `app/schemas/user.py`, `app/schemas/token.py`, `app/services/auth_service.py`, `app/api/v1/deps/auth.py`, `app/api/v1/endpoints/auth.py`, `app/api/v1/endpoints/user.py` — authentication and the User model
<!-- --- FEATURE[auth] END --- -->
<!-- --- FEATURE[api_v2] START --- -->
- `app/api/v2/router.py` — the second API version, an empty scaffold mounted at `/v2`
<!-- --- FEATURE[api_v2] END --- -->
<!-- --- FEATURE[csrf] START --- -->
- `app/middleware/csrf.py` — CSRF protection middleware
<!-- --- FEATURE[csrf] END --- -->
<!-- --- FEATURE[redis] START --- -->
- `app/services/cache/base.py` — shared Redis connection pool (`BaseRedisClient`)
<!-- --- FEATURE[redis] END --- -->
<!-- --- FEATURE[redis_cache] START --- -->
- `app/services/cache/manager.py`, `decorators.py` — Redis cache ([guide](integrations/caching.md))
<!-- --- FEATURE[redis_cache] END --- -->
<!-- --- FEATURE[redis_rate_limit] START --- -->
- `app/services/cache/rate_limiter.py`, `app/api/v1/deps/rate_limit.py`, `app/middleware/rate_limit.py`, `app/core/exceptions/rate_limiter.py`, `app/core/types.py` — rate limiting ([guide](integrations/rate-limiting.md))
<!-- --- FEATURE[redis_rate_limit] END --- -->
<!-- --- FEATURE[redis_token_blacklist] START --- -->
- `app/services/cache/token_blacklist.py` — token revocation ([guide](integrations/token-revocation.md))
<!-- --- FEATURE[redis_token_blacklist] END --- -->
<!-- --- FEATURE[celery] START --- -->
- `app/services/task_queue/` (`celery_config.py`, `tasks/`), `app/core/db_sync.py` — Celery background jobs ([guide](integrations/celery.md))
<!-- --- FEATURE[celery] END --- -->
<!-- --- FEATURE[firebase] START --- -->
- `app/services/firebase.py`, `app/schemas/firebase.py`, `app/core/credentials/firebase.py`, `app/core/exceptions/firebase_exceptions.py` — Firebase ([guide](integrations/firebase.md))
<!-- --- FEATURE[firebase] END --- -->
<!-- --- FEATURE[firestore] START --- -->
- `app/services/firestore.py` — Firestore ([guide](integrations/firestore.md))
<!-- --- FEATURE[firestore] END --- -->
<!-- --- FEATURE[gcs] START --- -->
- `app/services/gcs.py`, `app/schemas/google_bucket.py`, `app/core/exceptions/gcs_exceptions.py` — Google Cloud Storage ([guide](integrations/gcs.md))
<!-- --- FEATURE[gcs] END --- -->
<!-- --- FEATURE[backblaze] START --- -->
- `app/services/back_blaze_b2.py`, `app/schemas/back_blaze_bucket.py`, `app/core/exceptions/back_blaze_exceptions.py` — BackBlaze B2 ([guide](integrations/backblaze.md))
<!-- --- FEATURE[backblaze] END --- -->
<!-- --- FEATURE[resend|brevo] START --- -->
- `app/services/email/` (`base.py`, `static/` templates), `app/services/types/email.py`, `app/services/exceptions/email.py` — email ([guide](integrations/email.md))
<!-- --- FEATURE[resend|brevo] END --- -->
<!-- --- FEATURE[resend] START --- -->
  - `app/services/email/resend.py` — Resend provider
<!-- --- FEATURE[resend] END --- -->
<!-- --- FEATURE[brevo] START --- -->
  - `app/services/email/brevo.py` — Brevo provider
<!-- --- FEATURE[brevo] END --- -->
<!-- --- FEATURE[openobserve] START --- -->
- `app/core/openobserve.py` — OpenObserve log shipping ([guide](integrations/openobserve.md))
<!-- --- FEATURE[openobserve] END --- -->
<!-- --- FEATURE[apple_pay] START --- -->
- `app/services/payments/apple_pay.py`, `app/core/credentials/apple_pay.py`, `app/core/exceptions/apple_pay.py` — Apple Pay ([guide](integrations/apple-pay.md))
<!-- --- FEATURE[apple_pay] END --- -->

## Layer Architecture

### 1. API Layer (`app/api/`)

**Responsibility**: Handle HTTP requests and responses

- **Routes**: Define API endpoints and their grouping
- **Dependencies**: Provide database sessions and other shared request dependencies
- **Endpoints**: Implement specific API operations
- **Validation**: Input validation using Pydantic schemas

```python
# Example endpoint structure
@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    product_repo: ProductRepository = Depends(get_product_repository)
):
    return await product_repo.create(session, product_data)
```

### 2. Core Layer (`app/core/`)

**Responsibility**: Business logic and utilities

- **Configuration**: Environment-based settings management
- **Database**: Connection management and session handling
- **Logging**: Structured logging with Loguru
- **Exceptions**: Custom exception classes

### 3. Models Layer (`app/models/`)

**Responsibility**: Data structure definitions

- **SQLAlchemy Models**: Database table representations
- **Base Model**: Common functionality (timestamps, auto-increment ID)
- **Relationships**: Define model associations

```python
# Base model with common fields
class Base(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger(),
        autoincrement=True,
        primary_key=True,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Auto-generates table name from class name (e.g., UserProfile -> user_profile)
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    def to_dict(self, exclude_keys: set[str] | None = None) -> dict[str, Any]:
        """Convert model instance to dictionary with serializable fields."""
        ...
```

### 4. Schemas Layer (`app/schemas/`)

**Responsibility**: Data validation and serialization

- **Pydantic Models**: API input/output validation
- **Base Schemas**: Common schema patterns
- **Type Safety**: Ensure data integrity

```python
# Example schema structure
class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: Decimal

class ProductCreate(ProductBase):
    sku: str

class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
```

### 5. Repository Layer (`app/repos/`)

**Responsibility**: Data access abstraction

- **CRUD Operations**: Create, Read, Update, Delete
- **Query Building**: Complex database queries
- **Transaction Management**: Database transaction handling

```python
# Repository pattern example
class ProductRepository(BaseRepository[Product]):
    async def get_by_sku(
        self,
        session: AsyncSession,
        sku: str
    ) -> Optional[Product]:
        result = await session.execute(
            select(Product).where(Product.sku == sku)
        )
        return result.scalar_one_or_none()
```

### 6. Services Layer (`app/services/`)

**Responsibility**: External integrations and business services

- **External Service Integration**: Third-party API clients
- **Business Logic Services**: Complex operations spanning multiple repositories
- **Cloud Services**: Cloud storage, messaging, etc.

<!-- --- FEATURE[backblaze] START --- -->
```python
# BackBlaze B2 service example
class BackBlaze:
    def __init__(self, app_data: ApplicationData) -> None:
        self._authorize(app_data)

    def select_bucket(self, bucket_name: str) -> Self:
        """Select a bucket for operations"""
        self._bucket = self._b2_api.get_bucket_by_name(bucket_name)
        return self

    def upload_file(
        self,
        local_file_path: str,
        b2_file_name: str,
        file_info: UploadedFileInfo | None = None,
    ) -> FileVersion:
        """Upload file to selected bucket"""
        bucket = self._b2_api.get_bucket_by_name(self._bucket.name)
        return bucket.upload_local_file(
            local_file=local_file_path,
            file_name=b2_file_name,
            file_info=file_info.model_dump(),
        )
```
<!-- --- FEATURE[backblaze] END --- -->

<!-- --- FEATURE[backblaze|firebase|resend|brevo|redis] START --- -->
**Available Services**:

<!-- --- FEATURE[backblaze|firebase|resend|brevo|redis] END --- -->
<!-- --- FEATURE[backblaze] START --- -->
#### BackBlaze B2 Cloud Storage

Cloud storage integration for file management:

- **Bucket Management**: Create, delete, update, list, and select buckets
- **File Operations**: Upload, download, and delete files
- **URL Generation**: Public, private, and temporary authenticated download links
- **File Metadata**: Retrieve file details and information
- **Method Chaining**: Fluent interface for bucket operations
- **Error Handling**: Comprehensive exception handling with logging
- **Type Safety**: Full type hints and Pydantic schema validation

<!-- --- FEATURE[backblaze] END --- -->

<!-- --- FEATURE[firebase] START --- -->
#### Firebase Authentication & Messaging

Firebase integration for user authentication and push notifications:

- **User Management**: Get users by ID, email, or phone number
- **User Listing**: Fetch all users with pagination support
- **Custom Tokens**: Create custom ID tokens with additional claims
- **Token Verification**: Verify and validate ID tokens with expiration/revocation checks
- **Push Notifications**: Send notifications to single or multiple devices
- **FCM Token Validation**: Validate Firebase Cloud Messaging tokens
- **Batch Notifications**: Send up to 500 notifications per batch with automatic chunking
- **Singleton Pattern**: Single Firebase app initialization across application

<!-- --- FEATURE[firebase] END --- -->

<!-- --- FEATURE[firestore] START --- -->
#### Firestore Database

NoSQL document database integration:

- **Document Operations**: Add, update, get, and remove documents
- **Collection Queries**: Fetch all documents from collections
- **Error Handling**: Custom exceptions for document-not-found scenarios
- **Type Safety**: Fully typed responses with dictionary return types
- **Automatic Initialization**: Singleton pattern with service account credentials
- **Logging**: Comprehensive debug and error logging for all operations

<!-- --- FEATURE[firestore] END --- -->

<!-- --- FEATURE[resend|brevo] START --- -->
#### Email Delivery Services

Provider-based email delivery with shared contracts and strict validation:

- **Base Contract**: Abstract base service for consistent provider behavior
<!-- --- FEATURE[resend] START --- -->
- **Provider**: Resend (`app/services/email/resend.py`)
<!-- --- FEATURE[resend] END --- -->
<!-- --- FEATURE[brevo] START --- -->
- **Provider**: Brevo (`app/services/email/brevo.py`)
<!-- --- FEATURE[brevo] END --- -->
- **Validation**: Pydantic request/response models for payload safety
- **Templates**: File-based HTML templates under `app/services/email/static/html`
- **Error Handling**: Domain-specific service exceptions

<!-- --- FEATURE[resend|brevo] END --- -->

<!-- --- FEATURE[redis] START --- -->
#### Redis-backed Services

Redis-based infrastructure shared by the cache, rate limiting and the token blacklist:

<!-- --- FEATURE[redis_cache] START --- -->
**CacheManager** - General-purpose caching service:

- **Data Caching**: Store and retrieve any Python object using pickle serialization
- **TTL Management**: Configurable expiration times (default, short, long, very long)
- **Pattern Operations**: Delete multiple keys matching a pattern
- **Key Management**: Check key existence and delete specific keys
- **Graceful Degradation**: Continues operation even if Redis is unavailable
- **Shared Connection Pool**: Efficient Redis connection management

<!-- --- FEATURE[redis_cache] END --- -->
<!-- --- FEATURE[redis_rate_limit] START --- -->
**RateLimiter** - Sliding window rate limiting:

- **Sliding Window Algorithm**: Accurate request counting using Redis sorted sets with microsecond precision
- **High-Frequency Support**: Handles multiple requests per second with unique timestamp tracking
- **IP-Based Limiting**: Rate limit by client IP for unauthenticated endpoints
<!-- --- FEATURE[auth] START --- -->
- **User-Based Limiting**: Rate limit by user ID for authenticated endpoints
<!-- --- FEATURE[auth] END --- -->
- **Custom Prefixes**: Separate rate limit quotas per endpoint group
- **Configurable Limits**: Pre-configured presets (strict, default, lenient)
- **Custom Rate Limits**: Factory function for endpoint-specific limits
- **Rate Limit Headers**: Automatic `X-RateLimit-*` headers in responses
- **Fail-Open Design**: Allows requests if Redis is unavailable
- **Environment Control**: Toggle rate limiting via `RATE_LIMIT_ENABLED` setting

**Rate Limiting Strategies**:

- **Sensitive Endpoints** (login, signup and similar): 10 req/min per IP (strict)
- **General API Endpoints**: 100 req/min per IP (default)
- **Public Endpoints**: 1000 req/min per IP (lenient)
<!-- --- FEATURE[auth] START --- -->
- **Authenticated User Endpoints**: 300 req/min per user (user-based)
<!-- --- FEATURE[auth] END --- -->
- **Custom Endpoints**: Configurable limits with custom prefixes

<!-- --- FEATURE[redis_rate_limit] END --- -->

**Redis Connection Pooling**:

- **Shared Pool**: All Redis clients share a connection pool
- **Resource Efficiency**: Maximum 50 connections across all clients
- **Automatic Management**: Connection pooling, health checks, and graceful shutdown

<!-- --- FEATURE[redis] END --- -->

## Data Flow

### 1. Request Flow

```text
HTTP Request → API Router → Endpoint → Service/Repository → Database
                    ↓            ↓           ↓
               Dependencies  Validation  Transaction
```

### 2. Response Flow

```text
Database → Repository → Service → Business Logic → Schema → HTTP Response
                          ↓            ↓              ↓
                    External API  Processing    Serialization
```

### 3. Service Integration Flow

```text
Endpoint → Service Client → External API → Process Response → Return Data
              ↓                  ↓              ↓
         Initialize      Authenticate    Error Handling
```

<!-- --- FEATURE[auth] START --- -->
## Authentication Architecture

### JWT Token System

```text
User Login → Verify Credentials → Generate Tokens → Return Response
                    ↓                    ↓
            Password Hash Check    Access + Refresh Tokens
```

### Protected Routes

```text
Request → Extract Token → Validate Token → Get User → Execute Handler
              ↓               ↓              ↓
         Authorization    JWT Decode    Database Query
```

<!-- --- FEATURE[auth] END --- -->

## Database Architecture

### Connection Management

- **Async Sessions**: Using SQLAlchemy async sessions
- **Connection Pooling**: Efficient database connections
- **Transaction Handling**: Automatic rollback on errors

### Migration Strategy

- **Alembic**: Database schema versioning
- **Incremental Changes**: Safe schema modifications
- **Rollback Support**: Ability to revert changes

## Configuration Management

### Environment-Based Config

```python
class Settings(BaseSettings):
    # Database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8799

    # Environment
    current_environment: Environment = Environment.LOCAL
```

<!-- --- FEATURE[auth] START --- -->
With authentication, `Settings` also has `secret_key` (required, at least 32 characters), `access_token_expire_seconds`, `refresh_token_expire_seconds` and `jwt_algorithm`.
<!-- --- FEATURE[auth] END --- -->

### Environment Types

- **Local**: Development with debug features
- **Dev**: Development server deployment
- **Staging**: Pre-production testing
- **Prod**: Production deployment

## Middleware Stack

### Request Processing Pipeline

```text
Request → CORS Middleware → Logging Middleware → Route Handler
                ↓               ↓                    ↓
         Cross-Origin      Request Logging    Business Logic
```

### Custom Middleware

- **Logging Middleware**: Request/response logging
- **Security Middleware**: Additional security headers
- **Error Handling**: Centralized exception handling

## Logging Architecture

### Production-Grade Logging System

The template implements a sophisticated logging infrastructure built with Loguru, designed for production multi-worker environments with distributed request tracing and centralized log aggregation.

### Multi-Worker Safety

- **Thread-Safe Queue-Based Logging**: All log operations use queued writes to prevent race conditions in multi-worker deployments
- **Process Differentiation**: Each log entry includes process ID (PID) to track which worker generated the log
- **Atomic Writes**: Sequential log writing ensures file integrity across concurrent workers
- **No Corruption**: Queue-based approach eliminates log file corruption from simultaneous writes

### Request Tracing & Correlation

- **Correlation IDs**: Each HTTP request receives a unique identifier that persists throughout the request lifecycle
- **Context Variables**: Uses Python's async-safe `ContextVar` for request tracking
- **Distributed Tracing**: Follow a single request through multiple services and layers
- **Request Flow Analysis**: Debug complex operations by filtering all logs for a specific request ID

### Dual Output Strategy

#### Console Output (Development-Friendly)

- **Colored Formatting**: Visual distinction between log levels for quick scanning
- **Simplified Format**: Essential information only (timestamp, level, PID, request ID, message)
- **Environment Adaptive**: Debug level in development, info level in production
- **Real-Time Monitoring**: Immediate feedback during development

#### File Output (Production Analysis)

- **UTC Timestamps**: Critical for distributed systems across time zones
- **Full Context**: Includes module name, function name, and line number
- **Structured Format**: Easy parsing with log analysis tools
- **Enhanced Debugging**: Full stack traces with variable values on exceptions
- **Plain Text Format**: Standard .log files for universal compatibility

### Log Rotation & Retention

- **Automatic Rotation**: Log files rotate when reaching 10MB to maintain manageable sizes
- **Compression**: Rotated files automatically compressed with gzip (reduces storage by ~90%)
- **Retention Policy**: Logs retained for 3 months, then auto-deleted
- **Disk Space Management**: Prevents disk exhaustion with automatic cleanup
- **Compliance Ready**: Retention period meets most audit requirements

### Centralized Log Aggregation

#### Non-Blocking Architecture

- **Background Worker Thread**: HTTP requests for log shipping run in separate OS thread
- **Zero Event Loop Blocking**: FastAPI request handling never waits for log transmission
- **Daemon Thread**: Won't prevent application shutdown
- **Async-Safe**: Completely isolated from async event loop

#### Batching & Efficiency

- **Configurable Batch Size**: Send multiple logs in single HTTP request (default: 10 logs per batch)
- **Time-Based Flushing**: Automatic flush every 5 seconds even if batch not full
- **90% Reduction in HTTP Calls**: Dramatically reduces network overhead
- **Tunable Performance**: Adjust batch size and flush interval based on log volume

#### Resilience & Reliability

- **Retry Logic**: Automatic retry with exponential backoff (1s, 2s, 4s)
- **Graceful Degradation**: Local file logging continues if remote service unavailable
- **No Data Loss**: Local files remain source of truth
- **Connection Pooling**: Reuses TCP connections to reduce latency by 50-200ms per request
- **Graceful Shutdown**: Waits up to 10 seconds to flush pending logs before termination

### Unified Logging Interface

- **Uvicorn Integration**: Intercepts and redirects all standard library logging to Loguru
- **Consistent Formatting**: All logs (FastAPI, Uvicorn, SQLAlchemy, third-party libraries) use same format
- **Single Configuration Point**: One setup function configures entire application logging
- **Depth-Aware**: Preserves correct file/line information from original logging calls

### Configuration

#### File-Based Logging (Always Active)

```python
# Configured via settings
log_level = "DEBUG"  # or "INFO", "WARNING", "ERROR"
log_file = "logs/app.log"
rotation = "10 MB"
retention = "3 months"
compression = "gz"
```

<!-- --- FEATURE[openobserve] START --- -->
#### Remote Log Aggregation (Optional)

```bash
# Environment variables for centralized logging
OPENOBSERVE_URL=https://observe.example.com
OPENOBSERVE_ACCESS_KEY=base64_encoded_credentials
OPENOBSERVE_ORG_ID=default
OPENOBSERVE_STREAM_NAME=default
OPENOBSERVE_BATCH_SIZE=10
OPENOBSERVE_FLUSH_INTERVAL=5.0
```

<!-- --- FEATURE[openobserve] END --- -->

### Performance Characteristics

- **Memory Overhead**: ~600KB per worker (queue + HTTP client)
- **Log Call Latency**: <1ms (non-blocking enqueue operation)
- **File Throughput**: 10,000+ logs/second with queue-based writes
- **Remote Throughput**: 2,000+ logs/second with batching enabled
- **Zero User-Facing Impact**: All I/O happens asynchronously

### Production Benefits

- **Troubleshooting**: Quickly identify issues with request correlation and process tracking
- **Performance Monitoring**: Track request durations and system behavior
- **Audit Trails**: Complete history of system operations for compliance
- **Observability**: Centralized logs enable comprehensive system monitoring
- **Scalability**: Handles thousands of requests per second across multiple workers
- **Reliability**: No single point of failure; local and remote logging work independently

## Error Handling

### Exception Hierarchy

```python
class BaseAPIException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"

class ValidationError(BaseAPIException):
    status_code: int = 422

class NotFoundError(BaseAPIException):
    status_code: int = 404
```

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

## Testing Strategy

### Unit Tests

- **Repository Tests**: Mock database operations
- **Service Tests**: Business logic validation
- **Schema Tests**: Data validation testing

### Integration Tests

- **API Tests**: End-to-end endpoint testing
- **Database Tests**: Real database operations
<!-- --- FEATURE[auth] START --- -->
- **Authentication Tests**: Token-based auth flow
<!-- --- FEATURE[auth] END --- -->

### Test Database

- **Isolated Environment**: Separate test database
- **Transaction Rollback**: Clean state between tests
- **Fixtures**: Reusable test data

## Performance Considerations

### Async Operations

- **Database Queries**: Non-blocking database operations
- **HTTP Requests**: Async HTTP client usage
- **Background Tasks**: Non-blocking task execution

### Caching Strategy

- **Configuration**: settings are read once at import (`app.core.config.settings`)
- **Frequently read data**: cache in the service layer, behind a small interface, when a profile shows it is worth it
<!-- --- FEATURE[redis_cache] START --- -->
- **Redis cache**: `cache_manager` / `@cache_result` ([guide](integrations/caching.md))
<!-- --- FEATURE[redis_cache] END --- -->

### Database Optimization

- **Indexes**: Optimized query performance
- **Connection Pooling**: Efficient connection reuse
- **Query Optimization**: Efficient SQL generation

## Security Architecture

<!-- --- FEATURE[auth] START --- -->
### Authentication Security

- **Password Hashing**: Argon2 via pwdlib (modern, secure alternative to bcrypt)
- **JWT Tokens**: Signed with HS256 algorithm using secret key
- **Token Expiration**: Automatic token invalidation (1 hour access, 24 hours refresh)
<!-- --- FEATURE[redis_token_blacklist] START --- -->
- **Token Blacklisting**: Redis-based token revocation for logout functionality
<!-- --- FEATURE[redis_token_blacklist] END --- -->

### Authorization Levels

- **Public Routes**: No authentication required
- **Protected Routes**: Valid token required
- **Admin Routes**: Special permissions required

<!-- --- FEATURE[auth] END --- -->

### Data Security

- **Input Validation**: Pydantic schema validation
- **SQL Injection**: SQLAlchemy ORM protection
- **CORS Policy**: Configured origin restrictions
<!-- --- FEATURE[csrf] START --- -->
- **CSRF Protection**: Middleware-based CSRF token validation
<!-- --- FEATURE[csrf] END --- -->
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
<!-- --- FEATURE[redis_rate_limit] START --- -->
- **Rate Limiting**: Redis-based sliding window algorithm with microsecond precision
<!-- --- FEATURE[redis_rate_limit] END --- -->

## Deployment Architecture

### Container Strategy

```dockerfile
# Multi-stage build
FROM python:3.14-slim as builder
# Install dependencies
FROM python:3.14-slim as runtime
# Copy application
```

### Environment Variables

- **Database Configuration**: Connection strings
- **Security Settings**: Secret keys and tokens
- **Feature Flags**: Environment-specific features

### Health Checks

- **Database Connectivity**: Connection status
- **External Services**: API availability
- **Application Health**: Memory and CPU usage

This architecture provides a solid foundation for building scalable, maintainable FastAPI applications with proper separation of concerns and modern development practices.
