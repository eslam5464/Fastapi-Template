# Deployment Guide

This guide covers production deployment strategies, environment configuration, containerization, and monitoring for the FastAPI Template.

## Deployment Overview

The FastAPI Template supports multiple deployment strategies:

- **Traditional Server Deployment**: Direct deployment on VPS/dedicated servers
- **Container Deployment**: Docker-based deployment with orchestration
- **Cloud Platform Deployment**: AWS, GCP, Azure, and other cloud providers
- **Serverless Deployment**: Function-as-a-Service platforms

## Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ cores recommended for production)
- **RAM**: 2GB minimum (4GB+ recommended)
- **Storage**: 10GB minimum (SSD recommended)
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, or similar)

### Required Software

- **Python 3.13+**
- **PostgreSQL 12+**
- **Nginx** (for reverse proxy)
- **Supervisor** or **systemd** (for process management)
- **SSL Certificate** (Let's Encrypt recommended)

## Environment Configuration

### Production Environment Variables

Create a production `.env` file:

```env
# Application Settings
CURRENT_ENVIRONMENT=prod
APP_TITLE=Your FastAPI Application
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/database_name
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Security Settings
SECRET_KEY=your-super-secure-secret-key-with-64-characters-minimum
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Server Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
WORKERS_COUNT=4
RELOAD_UVICORN=false

# CORS Settings
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/fastapi-app/app.log

# External Services (if applicable)
REDIS_URL=redis://localhost:6379/0
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# BackBlaze B2 Configuration (Optional)
B2_APPLICATION_KEY_ID=your_backblaze_key_id
B2_APPLICATION_KEY=your_backblaze_application_key
B2_BUCKET_NAME=your_bucket_name
```

### BackBlaze B2 Setup for Production

If your application uses BackBlaze B2 cloud storage:

1. **Create Application Keys**

   - Log in to BackBlaze account
   - Navigate to App Keys section
   - Create a new application key with appropriate permissions
   - Store `keyID` as `B2_APPLICATION_KEY_ID`
   - Store `applicationKey` as `B2_APPLICATION_KEY`

2. **Bucket Configuration**

   - Create bucket(s) for production use
   - Set appropriate bucket type (allPrivate recommended for sensitive data)
   - Configure bucket lifecycle rules if needed
   - Set up CORS rules if accessing from web browsers

3. **Security Best Practices**

   - Use separate application keys for different environments
   - Limit key capabilities to only what's needed
   - Rotate keys periodically
   - Monitor bucket access logs
   - Implement file scanning for uploaded content

4. **Performance Optimization**
   - Use appropriate bucket regions close to your users
   - Enable CDN if serving public files
   - Implement file size limits
   - Use multipart uploads for large files

### Security Considerations

- **Secret Key**: Generate a cryptographically secure secret key
- **Database Credentials**: Use strong passwords and restricted access
- **CORS Origins**: Specify exact domains, avoid wildcard in production
- **Environment Separation**: Never use development settings in production

## Docker Deployment

### Dockerfile

Create a production-ready `Dockerfile`:

```dockerfile
# Multi-stage build for smaller image size
FROM python:3.13-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv export --no-hashes --format requirements-txt > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.13-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /var/log/fastapi-app && chown appuser:appuser /var/log/fastapi-app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UnicornWorker", "--bind", "0.0.0.0:8000"]
```

### Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/fastapi_app
      - B2_APPLICATION_KEY_ID=${B2_APPLICATION_KEY_ID}
      - B2_APPLICATION_KEY=${B2_APPLICATION_KEY}
      - B2_BUCKET_NAME=${B2_BUCKET_NAME}
    env_file:
      - .env.prod
    volumes:
      - ./logs:/var/log/fastapi-app
      - ./uploads:/app/uploads # Temporary storage for file uploads before B2 sync
    depends_on:
      - db
      - redis
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    container_name: fastapi-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: fastapi_app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    container_name: fastapi-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    container_name: fastapi-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:

networks:
  app-network:
    driver: bridge
```

### Building and Running

```bash
# Build the image
docker build -t fastapi-app .

# Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f app

# Scale the application
docker-compose -f docker-compose.prod.yml up -d --scale app=3
```

## Traditional Server Deployment

### Server Setup

#### 1. System Updates and Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.13 python3.13-venv python3-pip postgresql postgresql-contrib nginx supervisor

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE fastapi_app;
CREATE USER fastapi_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE fastapi_app TO fastapi_user;
ALTER USER fastapi_user CREATEDB;
\q
```

#### 3. Application Deployment

```bash
# Create application user
sudo adduser --system --group --home /opt/fastapi-app fastapi

# Clone repository
sudo -u fastapi git clone <repository-url> /opt/fastapi-app
cd /opt/fastapi-app

# Setup Python environment
sudo -u fastapi python3.13 -m venv .venv
sudo -u fastapi .venv/bin/pip install uv
sudo -u fastapi .venv/bin/uv sync

# Set up environment variables
sudo -u fastapi cp .env.example .env.prod
sudo -u fastapi nano .env.prod  # Configure production settings

# Run database migrations
sudo -u fastapi .venv/bin/alembic upgrade head
```

### Process Management

#### Supervisor Configuration

Create `/etc/supervisor/conf.d/fastapi-app.conf`:

```ini
[program:fastapi-app]
command=/opt/fastapi-app/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
directory=/opt/fastapi-app
user=fastapi
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/fastapi-app/app.log
environment=PATH="/opt/fastapi-app/.venv/bin"
```

#### Systemd Configuration (Alternative)

Create `/etc/systemd/system/fastapi-app.service`:

```ini
[Unit]
Description=FastAPI Application
After=network.target

[Service]
Type=exec
User=fastapi
Group=fastapi
WorkingDirectory=/opt/fastapi-app
Environment=PATH=/opt/fastapi-app/.venv/bin
ExecStart=/opt/fastapi-app/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### Start Services

```bash
# Using Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start fastapi-app

# Using Systemd
sudo systemctl daemon-reload
sudo systemctl enable fastapi-app
sudo systemctl start fastapi-app
```

### Nginx Configuration

Create `/etc/nginx/sites-available/fastapi-app`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

    # Main Application
    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Authentication Endpoints (Stricter Rate Limiting)
    location /api/v1/auth/ {
        limit_req zone=auth_limit burst=5 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static Files (if any)
    location /static/ {
        alias /opt/fastapi-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health Check
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/fastapi-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS Configuration

### Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Set up auto-renewal cron job
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Manual SSL Certificate

If using a purchased SSL certificate:

```bash
# Copy certificate files
sudo cp yourdomain.crt /etc/ssl/certs/
sudo cp yourdomain.key /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/yourdomain.key
```

## Cloud Platform Deployment

### AWS Deployment

#### Using Elastic Beanstalk

1. **Prepare Application**:

```python
# requirements.txt (generated from pyproject.toml)
# Procfile
web: gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
```

2. **Deploy**:

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init

# Create environment
eb create production

# Deploy
eb deploy
```

#### Using EC2 + RDS

1. **Launch EC2 Instance** (t3.medium or larger)
2. **Create RDS PostgreSQL Instance**
3. **Configure Security Groups**
4. **Follow traditional server deployment steps**

### Google Cloud Platform

#### Using Cloud Run

1. **Create Dockerfile** (as shown above)
2. **Build and Push**:

```bash
# Build and tag
docker build -t gcr.io/PROJECT_ID/fastapi-app .

# Push to Container Registry
docker push gcr.io/PROJECT_ID/fastapi-app

# Deploy to Cloud Run
gcloud run deploy fastapi-app \
  --image gcr.io/PROJECT_ID/fastapi-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Deployment

#### Using App Service

1. **Create App Service Plan**
2. **Deploy via GitHub Actions or Azure CLI**
3. **Configure environment variables**
4. **Set up Azure Database for PostgreSQL**

## Performance Optimization

### Application Level

```python
# Optimize database queries
from sqlalchemy.orm import selectinload

# Use connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Implement caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_settings():
    return Settings()
```

### Infrastructure Level

#### Load Balancing

```nginx
upstream fastapi_app {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    location / {
        proxy_pass http://fastapi_app;
    }
}
```

#### Database Optimization

```sql
-- Create indexes for frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Configure PostgreSQL for performance
-- In postgresql.conf:
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Caching Strategy

```python
# Redis configuration
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(cache_key)

            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator
```

## Monitoring and Logging

### Application Monitoring

#### Health Check Endpoint

```python
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        # Check database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": settings.app_version
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
```

#### Logging Configuration

```python
# Enhanced logging setup
from loguru import logger
import sys

def setup_logging():
    logger.remove()

    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # File logging
    logger.add(
        "/var/log/fastapi-app/app.log",
        rotation="10 MB",
        retention="30 days",
        compression="gzip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO"
    )
```

### External Monitoring

#### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="fastapi_app"

# Create backup
pg_dump -h localhost -U fastapi_user -d $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/backup_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://your-backup-bucket/postgresql/

# Or upload to BackBlaze B2
b2 upload-file your-bucket-name $BACKUP_DIR/backup_$DATE.sql.gz backups/postgresql/backup_$DATE.sql.gz
```

### BackBlaze B2 for Backups

Using BackBlaze B2 for application backups:

```bash
# Install B2 CLI
pip install b2

# Authorize account
b2 authorize-account $B2_APPLICATION_KEY_ID $B2_APPLICATION_KEY

# Upload backup to B2
b2 upload-file your-backup-bucket /path/to/backup.sql.gz backups/backup_$DATE.sql.gz

# List backups
b2 ls your-backup-bucket backups/

# Download backup
b2 download-file-by-name your-backup-bucket backups/backup_$DATE.sql.gz /path/to/restore/
```

**Lifecycle Rules for B2 Backups**:

- Keep daily backups for 7 days
- Keep weekly backups for 4 weeks
- Keep monthly backups for 12 months
- Configure via BackBlaze web console

### Automated Backup Cron Job

```bash
# Add to crontab
0 2 * * * /opt/scripts/backup.sh
```

### Recovery Process

```bash
# Restore from backup
gunzip backup_20250119_020000.sql.gz
psql -h localhost -U fastapi_user -d fastapi_app < backup_20250119_020000.sql

# Or create new database and restore
createdb fastapi_app_restored
psql -h localhost -U fastapi_user -d fastapi_app_restored < backup_20250119_020000.sql
```

## Security Best Practices

### Server Security

```bash
# Update system regularly
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Application Security

- Use environment variables for sensitive data
- Implement rate limiting
- Validate all input data
- Use HTTPS everywhere
- Keep dependencies updated
- Regular security audits

## Troubleshooting

### Common Issues

1. **Database Connection Issues**:

   - Check PostgreSQL service status
   - Verify connection string
   - Check firewall rules

2. **High Memory Usage**:

   - Monitor with `htop` or `ps`
   - Check for memory leaks
   - Optimize database queries

3. **Slow Response Times**:

   - Enable query logging
   - Use APM tools
   - Check server resources

4. **SSL Certificate Issues**:
   - Check certificate expiration
   - Verify certificate chain
   - Test with SSL Labs

### Performance Monitoring

```bash
# Monitor system resources
htop
iotop
free -h
df -h

# Monitor application
sudo systemctl status fastapi-app
sudo journalctl -u fastapi-app -f

# Monitor database
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
```

This deployment guide provides a comprehensive foundation for production deployment of the FastAPI template. Always test deployments in staging environments before production releases, and maintain regular backups and monitoring.
