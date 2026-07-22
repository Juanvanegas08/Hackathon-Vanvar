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


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
