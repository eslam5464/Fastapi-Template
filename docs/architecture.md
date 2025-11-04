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

**Key Features**:

- **BackBlaze B2 Integration**: Cloud storage service client
  - Bucket management (create, delete, update, list, select)
  - File operations (upload, download, delete)
  - URL generation (public, private, temporary auth links)
  - File metadata and details retrieval
- **Method Chaining**: Fluent interface for bucket operations
- **Error Handling**: Comprehensive exception handling with logging
- **Type Safety**: Full type hints and Pydantic schema validation

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

```
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
