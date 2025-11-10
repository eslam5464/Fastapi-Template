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
├── main.py                 # Application entry point
├── api/                    # API layer
│   ├── routes.py           # Main API router
│   └── v1/                 # API version 1
│       ├── router.py       # Version router
│       ├── deps/           # Dependencies
│       │   └── auth.py     # Authentication dependencies
│       └── endpoints/      # Endpoint modules
│           ├── auth.py     # Authentication endpoints
│           └── user.py     # User endpoints
├── core/                   # Core business logic
│   ├── config.py           # Configuration management
│   ├── db.py               # Database connection
│   ├── auth.py             # Authentication utilities
│   ├── exceptions.py       # Custom exceptions
│   ├── logger.py           # Logging configuration
│   ├── responses.py        # Standard responses
│   └── field_sizes.py      # Database field constraints
├── models/                 # Data models (SQLAlchemy)
│   ├── base.py             # Base model class
│   └── user.py             # User model
├── schemas/                # Data schemas (Pydantic)
│   ├── base.py             # Base schema classes
│   ├── user.py             # User schemas
│   ├── token.py            # Token schemas
│   └── back_blaze_bucket.py # BackBlaze B2 schemas
├── repos/                  # Repository layer
│   ├── base.py             # Base repository class
│   └── user.py             # User repository
├── services/               # Business logic and external services
│   └── back_blaze_b2.py    # BackBlaze B2 cloud storage service
├── middleware/             # Custom middleware
│   └── logging.py          # Request logging middleware
└── alembic/                # Database migrations
    ├── env.py              # Alembic environment
    ├── script.py.mako      # Migration template
    └── versions/           # Migration files
```

## Layer Architecture

### 1. API Layer (`app/api/`)

**Responsibility**: Handle HTTP requests and responses

- **Routes**: Define API endpoints and their grouping
- **Dependencies**: Provide authentication, database sessions, etc.
- **Endpoints**: Implement specific API operations
- **Validation**: Input validation using Pydantic schemas

```python
# Example endpoint structure
@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repository)
):
    return await user_repo.create(session, user_data)
```

### 2. Core Layer (`app/core/`)

**Responsibility**: Business logic and utilities

- **Configuration**: Environment-based settings management
- **Authentication**: JWT token handling, password hashing
- **Database**: Connection management and session handling
- **Logging**: Structured logging with Loguru
- **Exceptions**: Custom exception classes

### 3. Models Layer (`app/models/`)

**Responsibility**: Data structure definitions

- **SQLAlchemy Models**: Database table representations
- **Base Model**: Common functionality (timestamps, UUID)
- **Relationships**: Define model associations

```python
# Base model with common fields
class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
```

### 4. Schemas Layer (`app/schemas/`)

**Responsibility**: Data validation and serialization

- **Pydantic Models**: API input/output validation
- **Base Schemas**: Common schema patterns
- **Type Safety**: Ensure data integrity

```python
# Example schema structure
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
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
class UserRepository(BaseRepository[User]):
    async def get_by_email(
        self,
        session: AsyncSession,
        email: str
    ) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
```

### 6. Services Layer (`app/services/`)

**Responsibility**: External integrations and business services

- **External Service Integration**: Third-party API clients
- **Business Logic Services**: Complex operations spanning multiple repositories
- **Cloud Services**: Cloud storage, messaging, etc.

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

**Available Services**:

#### BackBlaze B2 Cloud Storage

Cloud storage integration for file management:

- **Bucket Management**: Create, delete, update, list, and select buckets
- **File Operations**: Upload, download, and delete files
- **URL Generation**: Public, private, and temporary authenticated download links
- **File Metadata**: Retrieve file details and information
- **Method Chaining**: Fluent interface for bucket operations
- **Error Handling**: Comprehensive exception handling with logging
- **Type Safety**: Full type hints and Pydantic schema validation

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

#### Firestore Database

NoSQL document database integration:

- **Document Operations**: Add, update, get, and remove documents
- **Collection Queries**: Fetch all documents from collections
- **Error Handling**: Custom exceptions for document-not-found scenarios
- **Type Safety**: Fully typed responses with dictionary return types
- **Automatic Initialization**: Singleton pattern with service account credentials
- **Logging**: Comprehensive debug and error logging for all operations

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
    database_url: str

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Environment
    current_environment: Environment = Environment.LOCAL
```

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

#### Remote Log Aggregation (Optional)

```bash
# Environment variables for centralized logging
OPENOBSERVE_URL=https://observe.example.com
OPENOBSERVE_TOKEN=base64_encoded_credentials
OPENOBSERVE_ORG=default
OPENOBSERVE_STREAM=default
OPENOBSERVE_BATCH_SIZE=10
OPENOBSERVE_FLUSH_INTERVAL=5.0
```

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
- **Authentication Tests**: Token-based auth flow

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

- **Query Caching**: Frequently accessed data
- **Session Caching**: User session information
- **Configuration Caching**: Static configuration data

### Database Optimization

- **Indexes**: Optimized query performance
- **Connection Pooling**: Efficient connection reuse
- **Query Optimization**: Efficient SQL generation

## Security Architecture

### Authentication Security

- **Password Hashing**: Bcrypt with salt
- **JWT Tokens**: Signed with secret key
- **Token Expiration**: Automatic token invalidation

### Authorization Levels

- **Public Routes**: No authentication required
- **Protected Routes**: Valid token required
- **Admin Routes**: Special permissions required

### Data Security

- **Input Validation**: Pydantic schema validation
- **SQL Injection**: SQLAlchemy ORM protection
- **CORS Policy**: Configured origin restrictions

## Deployment Architecture

### Container Strategy

```dockerfile
# Multi-stage build
FROM python:3.13-slim as builder
# Install dependencies
FROM python:3.13-slim as runtime
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
