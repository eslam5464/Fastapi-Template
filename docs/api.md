# API Reference

This document provides comprehensive information about the FastAPI Template API endpoints, authentication, and usage examples.

## Base URL

- **Local Development**: `http://localhost:8799`
- **API Base Path**: `/api/v1`

## Interactive Documentation

When running in development mode, you can access:

- **Swagger UI**: `http://localhost:8799/docs`
- **ReDoc**: `http://localhost:8799/redoc`
- **OpenAPI Schema**: `http://localhost:8799/openapi.json`

## Available Services

This API template includes the following services:

### Core Services

- **Authentication** - JWT-based user authentication with token blacklisting
- **User Management** - User registration and profile management
- **Rate Limiting** - Redis-based sliding window rate limiting with microsecond precision
- **Caching** - High-performance Redis caching with shared connection pooling

### Integrated Services

- **BackBlaze B2 Cloud Storage** - File storage and management service (available as a service layer, can be integrated into custom endpoints)
- **Google Cloud Storage (GCS)** - GCS bucket integration for file management (available as a service layer)
- **Firebase Authentication** - User authentication and management via Firebase (available as a service layer)
- **Firebase Cloud Messaging** - Push notification service for mobile and web applications (available as a service layer)
- **Firestore Database** - NoSQL document database for flexible data storage (available as a service layer)
- **Apple Pay** - App Store Server API integration for in-app purchase verification (available as a service layer)

For integration examples:

- [BackBlaze B2 Integration](./development.md#backblaze-b2-cloud-storage-integration)
- [Google Cloud Storage Integration](./development.md#google-cloud-storage-gcs-integration)
- [Firebase Integration](./development.md#firebase-authentication--messaging-integration)
- [Firestore Integration](./development.md#firestore-nosql-database-integration)
- [Apple Pay Integration](./development.md#apple-pay-app-store-server-api-integration)

## Authentication

The API uses JWT (JSON Web Token) authentication with the following flow:

### Authentication Flow

1. **Register/Login** → Get access token and refresh token
2. **Include token** in subsequent requests via `Authorization: Bearer <token>`
3. **Refresh token** when access token expires

### Token Types

- **Access Token**: Short-lived (1 hour by default), used for API requests
- **Refresh Token**: Long-lived (24 hours by default), used to get new access tokens

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/login

Authenticate user and receive access tokens.

**Request Body** (Form Data):

```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: Invalid request format

**Example Request**:

```bash
curl -X POST "http://localhost:8799/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=secretpassword"
```

#### POST /api/v1/auth/signup

Register a new user and receive access tokens.

**Request Body** (Form Data):

```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string",
  "first_name": "string",
  "last_name": "string"
}
```

**Response** (201 Created):

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:

- `400 Bad Request`: User already exists or invalid data
- `422 Unprocessable Entity`: Validation errors

**Example Request**:

```bash
curl -X POST "http://localhost:8799/api/v1/auth/signup" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&email=john@example.com&password=secretpassword&first_name=John&last_name=Doe"
```

#### POST /api/v1/auth/refresh

Get a new access token using a refresh token.

**Request Body**:

```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or expired refresh token

#### POST /api/v1/auth/logout

Revoke the current access token. After logout, the token cannot be used again.

**Headers**:

```text
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "message": "Successfully logged out",
  "revoked_at": "2025-01-19T10:30:00Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or missing token

**Example Request**:

```bash
curl -X POST "http://localhost:8799/api/v1/auth/logout" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

**Note**: This endpoint uses token blacklisting via Redis. Revoked tokens are stored until their natural expiration time, after which they are automatically cleaned up.

### Health Endpoints

#### GET /health

Check the health status of the API and its dependencies.

**Response** (200 OK):

```json
{
  "status": "healthy",
  "timestamp": "2025-01-19T10:30:00Z",
  "version": "0.1.0"
}
```

**Response** (503 Service Unavailable):

```json
{
  "status": "unhealthy",
  "error": "Database connection failed",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

**Example Request**:

```bash
curl -X GET "http://localhost:8799/health"
```

### User Endpoints

#### GET /api/v1/users/me

Get current authenticated user information.

**Headers**:

```text
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2025-01-19T10:30:00Z",
  "updated_at": "2025-01-19T10:30:00Z"
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or missing token
- `404 Not Found`: User not found

**Example Request**:

```bash
curl -X GET "http://localhost:8799/api/v1/users/me" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## Data Models

### User Model

```json
{
  "id": "integer (auto-increment)",
  "username": "string (unique, 3-50 characters)",
  "email": "string (valid email, unique)",
  "first_name": "string (1-50 characters)",
  "last_name": "string (1-50 characters)",
  "created_at": "datetime (ISO 8601)",
  "updated_at": "datetime (ISO 8601)"
}
```

### Token Model

```json
{
  "access_token": "string (JWT token)",
  "refresh_token": "string (JWT token, optional)",
  "token_type": "string (always 'bearer')"
}
```

### Error Model

```json
{
  "detail": "string (error description)",
  "error_code": "string (error type identifier)",
  "timestamp": "datetime (ISO 8601)"
}
```

## Authentication Implementation

### Using Access Tokens

Include the access token in the Authorization header for protected endpoints:

```http
Authorization: Bearer <access_token>
```

### Token Validation

The API validates tokens by:

1. Checking token signature
2. Verifying token expiration
3. Extracting user information
4. Validating user exists in database

### Security Headers

The API includes security headers:

- `WWW-Authenticate: Bearer` (for 401 responses)
- CORS headers (configurable origins)
- Security middleware headers

## Error Handling

### Standard Error Codes

| Status Code | Description           | Example                  |
| ----------- | --------------------- | ------------------------ |
| 400         | Bad Request           | Invalid input data       |
| 401         | Unauthorized          | Invalid or missing token |
| 403         | Forbidden             | Insufficient permissions |
| 404         | Not Found             | Resource not found       |
| 422         | Unprocessable Entity  | Validation errors        |
| 500         | Internal Server Error | Server-side error        |

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Detailed error message",
  "error_code": "ERROR_TYPE_IDENTIFIER",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

### Validation Errors

For 422 status codes, the response includes field-specific errors:

```json
{
  "detail": [
    {
      "loc": ["field_name"],
      "msg": "Error message",
      "type": "validation_error_type"
    }
  ]
}
```

## Rate Limiting

The API implements production-ready rate limiting using Redis with a sliding window algorithm and microsecond precision.

### Rate Limit Tiers

| Endpoint Type                        | Limit    | Window | Description          |
| ------------------------------------ | -------- | ------ | -------------------- |
| Authentication (`/login`, `/signup`) | 10 req   | 1 min  | Strict limit per IP  |
| General API                          | 100 req  | 1 min  | Default limit per IP |
| Public endpoints                     | 1000 req | 1 min  | Lenient limit per IP |
| Authenticated user endpoints         | 300 req  | 1 min  | Per user ID          |

### Rate Limit Response Headers

All rate-limited endpoints include these headers:

```http
X-RateLimit-Limit: 100          # Maximum requests allowed
X-RateLimit-Remaining: 73       # Requests remaining in window
X-RateLimit-Reset: 1701234567   # Unix timestamp when limit resets
```

### Rate Limit Exceeded Response

When the limit is exceeded, clients receive HTTP 429:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701234567
```

```json
{
  "detail": "Rate limit exceeded. Please slow down your requests."
}
```

### Configuration

Rate limiting can be configured via environment variables:

```env
RATE_LIMIT_ENABLED=true     # Enable/disable rate limiting
RATE_LIMIT_DEFAULT=100      # General API endpoints
RATE_LIMIT_WINDOW=60        # Time window in seconds
RATE_LIMIT_STRICT=10        # Authentication endpoints
RATE_LIMIT_LENIENT=1000     # Public endpoints
RATE_LIMIT_USER=300         # Authenticated user endpoints
```

**Note**: Rate limiting requires Redis. If Redis is unavailable, the system fails open (allows requests) to prevent service disruption

## API Versioning

The API uses URL path versioning:

- Current version: `v1`
- Base path: `/api/v1`
- Future versions: `/api/v2`, etc.

### Version Support

- Each version is maintained separately
- Deprecation notices provided 6 months before removal
- Migration guides provided for version changes

## CORS Configuration

The API supports Cross-Origin Resource Sharing (CORS) with configurable settings:

```python
# Default CORS settings
allow_origins: List[str] = ["*"]  # Configure for production
allow_credentials: bool = True
allow_methods: List[str] = ["*"]
allow_headers: List[str] = ["*"]
```

## Request/Response Examples

### Complete Authentication Flow

1. **Register a new user**:

    ```bash
    curl -X POST "http://localhost:8799/api/v1/auth/signup" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=testuser&email=test@example.com&password=testpass123&first_name=Test&last_name=User"
    ```

2. **Login with credentials**:

    ```bash
    curl -X POST "http://localhost:8799/api/v1/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=testuser&password=testpass123"
    ```

3. **Use access token**:

    ```bash
    curl -X GET "http://localhost:8799/api/v1/users/me" \
      -H "Authorization: Bearer <access_token_from_login>"
    ```

### Error Handling Examples

**Invalid credentials**:

```json
{
  "detail": "Incorrect username or password",
  "error_code": "UNAUTHORIZED",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

**Validation error**:

```json
{
  "detail": [
    {
      "loc": ["email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Testing the API

### Using curl

```bash
# Test health endpoint (if available)
curl -X GET "http://localhost:8799/health"

# Test authentication
curl -X POST "http://localhost:8799/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```

### Using Python requests

```python
import requests

# Base URL
base_url = "http://localhost:8799/api/v1"

# Login
response = requests.post(
    f"{base_url}/auth/login",
    data={
        "username": "testuser",
        "password": "testpass"
    }
)
tokens = response.json()

# Use access token
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
user_response = requests.get(f"{base_url}/users/me", headers=headers)
user_data = user_response.json()
```

### Using JavaScript/fetch

```javascript
// Login
const loginResponse = await fetch("/api/v1/auth/login", {
  method: "POST",
  headers: {
    "Content-Type": "application/x-www-form-urlencoded",
  },
  body: new URLSearchParams({
    username: "testuser",
    password: "testpass",
  }),
});

const tokens = await loginResponse.json();

// Use access token
const userResponse = await fetch("/api/v1/users/me", {
  headers: {
    Authorization: `Bearer ${tokens.access_token}`,
  },
});

const userData = await userResponse.json();
```

## Production Considerations

### Security

- Use HTTPS in production
- Configure CORS origins properly
- Implement rate limiting
- Add request validation
- Use secure secret keys
- Implement token blacklisting

### Monitoring

- Add request/response logging
- Implement health checks
- Monitor API performance
- Track error rates
- Set up alerting

### Documentation

- Keep API documentation updated
- Provide SDK/client libraries
- Include code examples
- Document breaking changes
- Maintain changelog
