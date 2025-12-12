import logging
import os
import tomllib
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

from app.schemas import ApplePayStoreCredentials, FirebaseServiceAccount

PROJECT_DIR = Path(__file__).parent.parent.parent
PROJECT_TOML_PATH = PROJECT_DIR / "pyproject.toml"

with open(PROJECT_TOML_PATH, "rb") as f:
    PYPROJECT_CONTENT = tomllib.load(f)["project"]


class Environment(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    STG = "stg"
    PRD = "prd"


def convert_app_name(s: str) -> str:
    return " ".join(word.capitalize() for word in s.split("-"))


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=False,
        extra="ignore",
    )

    # App variables
    app_name: str = PYPROJECT_CONTENT["name"]
    app_title: str = os.getenv("APP_TITLE", convert_app_name(app_name))
    app_version: str = PYPROJECT_CONTENT["version"]
    app_description: str = PYPROJECT_CONTENT["description"]

    backend_host: str
    backend_port: int

    cors_origins: str
    allowed_hosts: str

    # Number of workers for uvicorn
    workers_count: int

    # Enable uvicorn reloading
    reload_uvicorn: bool = False

    # Current working environment
    current_environment: Environment
    log_level: int = logging.INFO
    debug: bool

    # Variables for the database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_db_schema: str

    # firebase
    firebase_project_id: str
    firebase_private_key_id: str
    firebase_private_key: str
    firebase_private_key_path: Path | None = None
    firebase_client_email: str
    firebase_client_id: str

    # Variables for Redis
    redis_host: str
    redis_port: int
    redis_user: str | None = None
    redis_pass: str
    redis_base: int | None = None
    redis_max_pool_connections: int  # Maximum number of connections in the Redis pool
    redis_socket_connect_timeout: int  # Socket connect timeout in seconds
    redis_socket_timeout: int  # Socket timeout in seconds

    # Cache settings
    cache_enabled: bool
    cache_ttl_default: int  # Default cache TTL in seconds
    cache_ttl_short: int  # Short cache TTL in seconds
    cache_ttl_long: int  # Long cache TTL in seconds
    cache_ttl_very_long: int  # Very long cache TTL in seconds

    # Rate limiting settings (requests per window)
    rate_limit_enabled: bool
    rate_limit_default: int = 100  # Default limit for general API endpoints
    rate_limit_window: int = 60  # Default window in seconds (1 minute)
    rate_limit_strict: int = 10  # Strict limit for authentication endpoints
    rate_limit_lenient: int = 1000  # Lenient limit for public endpoints
    rate_limit_user: int = 300  # Limit for authenticated user endpoints

    # Token security settings
    secret_key: str
    access_token_expire_seconds: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", timedelta(hours=1).seconds)
    )
    refresh_token_expire_seconds: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_SECONDS", timedelta(hours=24).seconds)
    )
    security_bcrypt_rounds: int = 12
    jwt_algorithm: str = "HS256"

    # OpenObserve
    log_to_openobserve: bool = True
    openobserve_url: str
    openobserve_org_id: str
    openobserve_stream_name: str
    openobserve_access_key: str
    openobserve_batch_size: int = 10
    openobserve_flush_interval: float = 5.0

    # App Store Connect API credentials
    apple_pay_store_private_key_id: str
    apple_pay_store_private_key: str
    apple_pay_store_private_key_path: Path | None = None
    apple_pay_store_issuer_id: str
    apple_pay_store_bundle_id: str
    apple_pay_store_root_certificate_path: Path

    # Celery settings
    enable_data_seeding: bool
    seeding_user_count: int
    celery_broker_url: URL | None = None
    celery_result_backend: URL | None = None
    celery_broker_db: int = 1  # Database index for the Celery broker
    celery_result_db: int = 2  # Database index for the Celery result backend
    celery_timezone: str = "UTC"
    celery_task_time_limit: int = 300  # Maximum time limit (default is 5 minutes)

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """
        Parse CORS origins from a comma-separated string.
        """
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @computed_field
    @property
    def allowed_hosts_list(self) -> list[str]:
        """
        Parse allowed hosts from a comma-separated string.
        """
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @computed_field
    @property
    def server_host(self) -> str:
        """
        Get the server host URL based on environment.
        """
        if self.current_environment == "dev":
            return f"http://{self.backend_host}:{self.backend_port}"

        return f"https://{self.backend_host}"

    @computed_field
    @property
    def db_url(self) -> URL:
        """
        Assemble database URL from settings.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.postgres_host,
            port=self.postgres_port,
            user=self.postgres_user,
            password=self.postgres_password,
            path=f"/{self.postgres_db}",
        )

    @computed_field
    @property
    def db_url_sync(self) -> URL:
        """
        Assemble database URL from settings (sync - for Celery).
        """
        return URL.build(
            scheme="postgresql+psycopg",
            host=self.postgres_host,
            port=self.postgres_port,
            user=self.postgres_user,
            password=self.postgres_password,
            path=f"/{self.postgres_db}",
        )

    @computed_field
    @property
    def db_test_url(self) -> URL:
        """
        Assemble test database URL from settings.
        """
        return URL.build(
            scheme="postgresql+asyncpg",
            host=self.postgres_host,
            port=self.postgres_port,
            user=self.postgres_user,
            password=self.postgres_password,
            path=f"/{self.postgres_db}_test",
        )

    @computed_field
    @property
    def firebase_credentials(self) -> FirebaseServiceAccount:
        """
        Assemble Firebase credentials from settings.
        """
        # Check if the private key path is provided and exists
        # If it does, read the private key from the file
        if self.firebase_private_key_path is not None:
            if self.firebase_private_key_path.is_file():
                self.firebase_private_key = self.firebase_private_key_path.read_text()

        return FirebaseServiceAccount(
            project_id=self.firebase_project_id,
            private_key_id=self.firebase_private_key_id,
            private_key=self.firebase_private_key.replace("\\", "\\\\"),
            client_email=self.firebase_client_email,
            client_id=self.firebase_client_id,
        )

    @computed_field
    @property
    def redis_url(self) -> URL:
        """
        Assemble REDIS URL from settings.
        """
        path = ""

        if self.redis_base is not None:
            path = f"/{self.redis_base}"

        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            user=self.redis_user,
            password=self.redis_pass,
            path=path,
        )

    @computed_field
    @property
    def apple_pay_store_credentials(self) -> ApplePayStoreCredentials:
        """
        Assemble App Store Connect API credentials from settings.
        """
        # Check if the private key path is provided and exists
        # If it does, read the private key from the file
        if self.apple_pay_store_private_key_path is not None:
            if self.apple_pay_store_private_key_path.is_file():
                self.apple_pay_store_private_key = self.apple_pay_store_private_key_path.read_text()

        return ApplePayStoreCredentials(
            private_key=self.apple_pay_store_private_key.replace("\\", "\\\\"),
            key_id=self.apple_pay_store_private_key_id,
            issuer_id=self.apple_pay_store_issuer_id,
            bundle_id=self.apple_pay_store_bundle_id,
        )

    @computed_field
    @property
    def celery_broker(self) -> URL:
        """Celery broker URL (Redis DB 1)"""
        if self.celery_broker_url is not None:
            return self.celery_broker_url

        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_pass if self.redis_pass else None,
            path=f"/{self.celery_broker_db}",
        )

    @computed_field
    @property
    def celery_backend(self) -> URL:
        """Celery result backend URL (Redis DB 2)"""
        if self.celery_result_backend is not None:
            return self.celery_result_backend

        return URL.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_pass if self.redis_pass else None,
            path=f"/{self.celery_result_db}",
        )


settings = Settings()  # type: ignore
