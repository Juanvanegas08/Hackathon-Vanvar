"""Tests for database configuration validation."""

from __future__ import annotations

import pytest
from app.core.config import Settings, redact_database_url
from app.db.engine import create_engine, reset_engine
from pydantic import ValidationError


def test_rejects_non_postgres_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_ENABLED=True,
            DATABASE_URL="mysql://user:pass@localhost:3306/db",
        )


def test_redacts_password_in_url() -> None:
    url = "postgresql+psycopg://user:s3cret@host:5432/home_30x"
    redacted = redact_database_url(url)
    assert "s3cret" not in redacted
    assert "***" in redacted
    assert "user" in redacted


def test_settings_repr_hides_password() -> None:
    settings = Settings(
        DATABASE_ENABLED=True,
        DATABASE_URL="postgresql+psycopg://user:s3cret@host:5432/home_30x",
        PERSISTENCE_PROVIDER="memory",
    )
    rendered = repr(settings)
    assert "s3cret" not in rendered
    assert "***" in rendered


def test_database_disabled_does_not_create_engine() -> None:
    reset_engine()
    settings = Settings(DATABASE_ENABLED=False, DATABASE_URL=None)
    assert create_engine(settings) is None


def test_production_forbids_postgres_database_name() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DATABASE_ENABLED=True,
            DATABASE_NAME="postgres",
            DATABASE_URL="postgresql+psycopg://user:pass@host:5432/postgres",
        )
