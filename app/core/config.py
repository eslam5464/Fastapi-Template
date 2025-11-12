import logging
import os
import tomllib
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

from app.schemas import FirebaseServiceAccount

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
    debug: bool = False

    # Variables for the database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_db_schema: str
    db_echo: bool = False

    # firebase
    firebase_project_id: str
    firebase_private_key_id: str
    firebase_private_key: str
    firebase_private_key_path: Path | None = None
    firebase_client_email: str
    firebase_client_id: str

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


settings = Settings()  # type: ignore
