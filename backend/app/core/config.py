"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    @property
    def is_smmlv_configured(self) -> bool:
        """Return True when SMMLV can be used for salary category calculations."""
        return self.smmlv > 0

    @property
    def is_openai_realtime_ready(self) -> bool:
        """Return True when Realtime voice can be started."""
        return bool(self.openai_realtime_enabled and self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
