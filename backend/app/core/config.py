"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlparse, urlunparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

FORBIDDEN_PRODUCTION_DB_NAMES = frozenset({"postgres", "template0", "template1"})
PersistenceProvider = Literal["memory", "postgres"]


def redact_database_url(url: str) -> str:
    """Return a database URL with the password replaced by ***.

    Uses urllib.parse so passwords with special characters are handled safely.
    """
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.password is None:
        return url
    username = parsed.username or ""
    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{username}:***@{hostname}{port}"
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


def _validate_postgres_url(url: str, field_name: str) -> str:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError(
            f"{field_name} must use postgresql+psycopg:// (or postgresql://) scheme"
        )
    if not parsed.hostname:
        raise ValueError(f"{field_name} must include a hostname")
    if not parsed.path or parsed.path == "/":
        raise ValueError(f"{field_name} must include a database name")
    return url


class Settings(BaseSettings):
    """Runtime configuration for CasaLista Voice API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="CasaLista Voice API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    smmlv: float = Field(default=0, alias="SMMLV")
    raw_data_path: str = Field(default="./data/raw", alias="RAW_DATA_PATH")
    processed_data_path: str = Field(
        default="./data/processed",
        alias="PROCESSED_DATA_PATH",
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="CORS_ORIGINS",
    )
    projects_catalog_path: str = Field(
        default="./data/processed/projects_catalog.json",
        alias="PROJECTS_CATALOG_PATH",
    )
    project_profiles_path: str = Field(
        default="./data/processed/project_profiles.json",
        alias="PROJECT_PROFILES_PATH",
    )
    project_aliases_path: str = Field(
        default="./data/processed/project_aliases.json",
        alias="PROJECT_ALIASES_PATH",
    )
    projects_canonical_path: str = Field(
        default="./data/processed/projects_canonical.json",
        alias="PROJECTS_CANONICAL_PATH",
    )
    mock_affiliates_path: str = Field(
        default="./data/mock/mock_affiliates.json",
        alias="MOCK_AFFILIATES_PATH",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_realtime_model: str = Field(
        default="gpt-realtime-2.1",
        alias="OPENAI_REALTIME_MODEL",
    )
    openai_realtime_voice: str = Field(
        default="marin",
        alias="OPENAI_REALTIME_VOICE",
    )
    openai_realtime_transcription_model: str = Field(
        default="gpt-4o-mini-transcribe",
        alias="OPENAI_REALTIME_TRANSCRIPTION_MODEL",
    )
    openai_realtime_enabled: bool = Field(
        default=True,
        alias="OPENAI_REALTIME_ENABLED",
    )
    openai_request_timeout_seconds: float = Field(
        default=20,
        alias="OPENAI_REQUEST_TIMEOUT_SECONDS",
    )
    openai_recommender_enabled: bool = Field(
        default=True,
        alias="OPENAI_RECOMMENDER_ENABLED",
    )
    openai_recommender_model: str = Field(
        default="gpt-4.1-mini",
        alias="OPENAI_RECOMMENDER_MODEL",
    )
    lead_profiles_path: str = Field(
        default="./data/profiles",
        alias="LEAD_PROFILES_PATH",
    )
    prefer_openai_recommendations: bool = Field(
        default=True,
        alias="PREFER_OPENAI_RECOMMENDATIONS",
    )

    database_enabled: bool = Field(default=False, alias="DATABASE_ENABLED")
    database_url: SecretStr | None = Field(default=None, alias="DATABASE_URL")
    database_admin_url: SecretStr | None = Field(default=None, alias="DATABASE_ADMIN_URL")
    database_name: str = Field(default="home_30x", alias="DATABASE_NAME")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout_seconds: int = Field(
        default=30,
        alias="DATABASE_POOL_TIMEOUT_SECONDS",
    )
    database_pool_recycle_seconds: int = Field(
        default=1800,
        alias="DATABASE_POOL_RECYCLE_SECONDS",
    )
    database_command_timeout_seconds: int = Field(
        default=30,
        alias="DATABASE_COMMAND_TIMEOUT_SECONDS",
    )
    database_migration_lock_id: int = Field(
        default=741852963,
        alias="DATABASE_MIGRATION_LOCK_ID",
    )
    persistence_provider: PersistenceProvider = Field(
        default="memory",
        alias="PERSISTENCE_PROVIDER",
    )
    identity_hash_pepper: str = Field(
        default="casalista-dev-pepper",
        alias="IDENTITY_HASH_PEPPER",
    )
    test_database_url: SecretStr | None = Field(default=None, alias="TEST_DATABASE_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        """Parse comma-separated CORS origins from environment."""
        if value is None or value == "":
            return ["http://localhost:5173"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        raise TypeError("CORS_ORIGINS must be a string or list of strings")

    @field_validator("database_url", "database_admin_url", "test_database_url", mode="before")
    @classmethod
    def empty_url_as_none(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return value

    @field_validator("database_url", "database_admin_url", "test_database_url", mode="after")
    @classmethod
    def validate_postgres_urls(cls, value: SecretStr | None, info: Any) -> SecretStr | None:
        if value is None:
            return None
        _validate_postgres_url(value.get_secret_value(), info.field_name or "database_url")
        return value

    @model_validator(mode="after")
    def validate_production_database_name(self) -> "Settings":
        if self.app_env.lower() == "production":
            name = self.database_name.strip().lower()
            if name in FORBIDDEN_PRODUCTION_DB_NAMES:
                raise ValueError(
                    f"DATABASE_NAME '{self.database_name}' is forbidden in production"
                )
            if self.database_url is not None:
                path = urlparse(self.database_url.get_secret_value()).path.lstrip("/")
                db_from_url = path.split("/")[0].lower() if path else ""
                if db_from_url in FORBIDDEN_PRODUCTION_DB_NAMES:
                    raise ValueError(
                        f"DATABASE_URL targets forbidden production database '{db_from_url}'"
                    )
        return self

    @property
    def is_smmlv_configured(self) -> bool:
        """Return True when SMMLV can be used for salary category calculations."""
        return self.smmlv > 0

    @property
    def is_openai_realtime_ready(self) -> bool:
        """Return True when Realtime voice can be started."""
        return bool(self.openai_realtime_enabled and self.openai_api_key)

    @property
    def is_database_configured(self) -> bool:
        """Return True when PostgreSQL is enabled and a URL is present."""
        return bool(self.database_enabled and self.database_url is not None)

    def get_database_url(self) -> str | None:
        """Return the raw DATABASE_URL value when configured."""
        if self.database_url is None:
            return None
        return self.database_url.get_secret_value()

    def get_database_admin_url(self) -> str | None:
        """Return the raw DATABASE_ADMIN_URL value when configured."""
        if self.database_admin_url is None:
            return None
        return self.database_admin_url.get_secret_value()

    def get_test_database_url(self) -> str | None:
        """Return the raw TEST_DATABASE_URL value when configured."""
        if self.test_database_url is None:
            return None
        return self.test_database_url.get_secret_value()

    def get_redacted_database_url(self) -> str | None:
        """Return DATABASE_URL with password redacted."""
        url = self.get_database_url()
        if url is None:
            return None
        return redact_database_url(url)

    def __repr__(self) -> str:
        redacted = self.get_redacted_database_url() or ""
        return (
            f"Settings(app_env={self.app_env!r}, "
            f"database_enabled={self.database_enabled}, "
            f"database_url={redacted!r}, "
            f"persistence_provider={self.persistence_provider!r})"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
