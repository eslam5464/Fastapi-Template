# API Reference

This document provides comprehensive information about the FastAPI Template API endpoints and usage examples.

## Base URL

- **Local Development**: `http://localhost:8799`
- **API Base Path**: `/v1` (each API version is mounted at its own path)

## Interactive Documentation

When running in development mode, you can access:

- **Swagger UI**: `http://localhost:8799/v1/docs`
- **ReDoc**: `http://localhost:8799/v1/redoc`
- **OpenAPI Schema**: `http://localhost:8799/v1/openapi.json`

## Available Services

This API template includes the following services:

### Core Services

- **Health check** - `GET /health` reports the status of the service
<!-- --- FEATURE[auth] START --- -->
- **Authentication** - JWT-based user authentication
<!-- --- FEATURE[redis_token_blacklist] START --- -->
- **Token revocation** - logout puts the token on a Redis blacklist
<!-- --- FEATURE[redis_token_blacklist] END --- -->
- **User Management** - User registration and profile management
<!-- --- FEATURE[auth] END --- -->
<!-- --- FEATURE[redis_rate_limit] START --- -->
- **Rate Limiting** - Redis-based sliding window rate limiting with microsecond precision
<!-- --- FEATURE[redis_rate_limit] END --- -->
<!-- --- FEATURE[redis_cache] START --- -->
- **Caching** - High-performance Redis caching with shared connection pooling
<!-- --- FEATURE[redis_cache] END --- -->

<!-- --- FEATURE[backblaze|gcs|firebase|apple_pay|resend|brevo] START --- -->
### Integrated Services

<!-- --- FEATURE[backblaze|gcs|firebase|apple_pay|resend|brevo] END --- -->
<!-- --- FEATURE[backblaze] START --- -->
- **BackBlaze B2 Cloud Storage** - File storage and management service (available as a service layer, can be integrated into custom endpoints)
<!-- --- FEATURE[backblaze] END --- -->
<!-- --- FEATURE[gcs] START --- -->
- **Google Cloud Storage (GCS)** - GCS bucket integration for file management (available as a service layer)
<!-- --- FEATURE[gcs] END --- -->
<!-- --- FEATURE[firebase] START --- -->
- **Firebase Authentication** - User authentication and management via Firebase (available as a service layer)
- **Firebase Cloud Messaging** - Push notification service for mobile and web applications (available as a service layer)
<!-- --- FEATURE[firebase] END --- -->
<!-- --- FEATURE[firestore] START --- -->
- **Firestore Database** - NoSQL document database for flexible data storage (available as a service layer)
<!-- --- FEATURE[firestore] END --- -->
<!-- --- FEATURE[apple_pay] START --- -->
- **Apple Pay** - App Store Server API integration for in-app purchase verification (available as a service layer)
<!-- --- FEATURE[apple_pay] END --- -->
<!-- --- FEATURE[resend|brevo] START --- -->
- **Email Delivery** - Provider-based email service layer with Pydantic-validated payloads and template support (available as a service layer)
<!-- --- FEATURE[resend|brevo] END --- -->

<!-- --- FEATURE[backblaze|gcs|firebase|apple_pay] START --- -->
For integration examples:

<!-- --- FEATURE[backblaze|gcs|firebase|apple_pay] END --- -->
<!-- --- FEATURE[backblaze] START --- -->
- [BackBlaze B2 Integration](./integrations/backblaze.md)
<!-- --- FEATURE[backblaze] END --- -->
<!-- --- FEATURE[gcs] START --- -->
- [Google Cloud Storage Integration](./integrations/gcs.md)
<!-- --- FEATURE[gcs] END --- -->
<!-- --- FEATURE[firebase] START --- -->
- [Firebase Integration](./integrations/firebase.md)
<!-- --- FEATURE[firebase] END --- -->
<!-- --- FEATURE[firestore] START --- -->
- [Firestore Integration](./integrations/firestore.md)
<!-- --- FEATURE[firestore] END --- -->
<!-- --- FEATURE[apple_pay] START --- -->
- [Apple Pay Integration](./integrations/apple-pay.md)
<!-- --- FEATURE[apple_pay] END --- -->

<!-- --- FEATURE[auth] START --- -->
## Authentication

The API uses JWT (JSON Web Token) authentication with the following flow:

### Authentication Flow

1. **Register/Login** → Get access token and refresh token
2. **Include token** in subsequent requests via `Authorization: Bearer <token>`
3. **Refresh token** when access token expires

### Token Types

- **Access Token**: Short-lived (1 hour by default), used for API requests
- **Refresh Token**: Long-lived (24 hours by default), used to get new access tokens

<!-- --- FEATURE[auth] END --- -->

## API Endpoints

<!-- --- FEATURE[auth] START --- -->
### Authentication Endpoints

#### POST /v1/auth/login

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
curl -X POST "http://localhost:8799/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=secretpassword"
```

#### POST /v1/auth/signup

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
curl -X POST "http://localhost:8799/v1/auth/signup" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&email=john@example.com&password=secretpassword&first_name=John&last_name=Doe"
```

#### POST /v1/auth/refresh-token

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

#### POST /v1/auth/logout

Log out. When token revocation is enabled, the access token is revoked and cannot be used again; otherwise it stays valid until it expires.

**Headers**:

```text
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "message": "Successfully logged out",
  "revoked": true
}
```

**Error Responses**:

- `401 Unauthorized`: Invalid or missing token

**Example Request**:

```bash
curl -X POST "http://localhost:8799/v1/auth/logout" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

**Note**: `revoked` is `false` when the project has no token revocation.
<!-- --- FEATURE[redis_token_blacklist] START --- -->
Revoked tokens are kept on a Redis blacklist until their natural expiration time ([integrations/token-revocation.md](integrations/token-revocation.md)).
<!-- --- FEATURE[redis_token_blacklist] END --- -->

<!-- --- FEATURE[auth] END --- -->

<!-- --- FEATURE[example_items] START --- -->
### Item Endpoints (example domain)

| Method | Path | Result |
| ------ | ---- | ------ |
| GET | `/v1/items?skip=0&limit=50` | 200 with a page of items, oldest first |
| POST | `/v1/items` | 201 with the new item; 409 if the name is taken |
| GET | `/v1/items/{item_id}` | 200 with the item; 404 if it does not exist |
| PATCH | `/v1/items/{item_id}` | 200 with the changed item; 404 or 409 |
| DELETE | `/v1/items/{item_id}` | 204; 404 if it does not exist |

**Request Body** (POST; PATCH takes the same fields, all optional):

```json
{
  "name": "Blue widget",
  "description": "Optional text",
  "is_active": true
}
```

**Response** (item):

```json
{
  "id": 1,
  "name": "Blue widget",
  "description": "Optional text",
  "is_active": true,
  "created_at": "2025-01-19T10:30:00Z",
  "updated_at": "2025-01-19T10:30:00Z"
}
```

<!-- --- FEATURE[auth] START --- -->
Every item route needs an `Authorization: Bearer <access_token>` header.

<!-- --- FEATURE[auth] END --- -->
<!-- --- FEATURE[example_items] END --- -->

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

<!-- --- FEATURE[auth] START --- -->
### User Endpoints

#### GET /v1/users/me

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
curl -X GET "http://localhost:8799/v1/users/me" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

<!-- --- FEATURE[auth] END --- -->

## Data Models

<!-- --- FEATURE[auth] START --- -->
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

<!-- --- FEATURE[auth] END --- -->

### Error Model

```json
{
  "detail": "string (error description)",
  "error_code": "string (error type identifier)",
  "timestamp": "datetime (ISO 8601)"
}
```

<!-- --- FEATURE[auth] START --- -->
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

<!-- --- FEATURE[auth] END --- -->

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

<!-- --- FEATURE[redis_rate_limit] START --- -->
## Rate Limiting

Limits, response headers, the 429 response and configuration: see [integrations/rate-limiting.md](integrations/rate-limiting.md).

<!-- --- FEATURE[redis_rate_limit] END --- -->

## API Versioning

The API uses URL path versioning:

- Current version: `v1`
- Base path: `/v1`
- Future versions: each one gets its own base path and its own docs

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

<!-- --- FEATURE[auth] START --- -->
### Complete Authentication Flow

1. **Register a new user**:

    ```bash
    curl -X POST "http://localhost:8799/v1/auth/signup" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=testuser&email=test@example.com&password=testpass123&first_name=Test&last_name=User"
    ```

2. **Login with credentials**:

    ```bash
    curl -X POST "http://localhost:8799/v1/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=testuser&password=testpass123"
    ```

3. **Use access token**:

    ```bash
    curl -X GET "http://localhost:8799/v1/users/me" \
      -H "Authorization: Bearer <access_token_from_login>"
    ```

<!-- --- FEATURE[auth] END --- -->

### Error Handling Examples

<!-- --- FEATURE[auth] START --- -->
**Invalid credentials**:

```json
{
  "detail": "Incorrect username or password",
  "error_code": "UNAUTHORIZED",
  "timestamp": "2025-01-19T10:30:00Z"
}
```

<!-- --- FEATURE[auth] END --- -->

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
# Test the health endpoint
curl -X GET "http://localhost:8799/health"
```

<!-- --- FEATURE[auth] START --- -->
Test authentication:

```bash
curl -X POST "http://localhost:8799/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```
<!-- --- FEATURE[auth] END --- -->

<!-- --- FEATURE[auth] START --- -->
### Using Python requests

```python
import requests

# Base URL
base_url = "http://localhost:8799/v1"

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
const loginResponse = await fetch("/v1/auth/login", {
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
const userResponse = await fetch("/v1/users/me", {
  headers: {
    Authorization: `Bearer ${tokens.access_token}`,
  },
});

const userData = await userResponse.json();
```

<!-- --- FEATURE[auth] END --- -->

## Production Considerations

### Security

- Use HTTPS in production
- Configure CORS origins properly
- Implement rate limiting
- Add request validation
<!-- --- FEATURE[auth] START --- -->
- Use secure secret keys
- Implement token blacklisting
<!-- --- FEATURE[auth] END --- -->

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
