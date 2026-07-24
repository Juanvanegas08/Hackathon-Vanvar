"""Optional bootstrap script to create the application database.

Does not create roles, drop databases, or run migrations unless requested.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings, redact_database_url  # noqa: E402

SAFE_DB_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FORBIDDEN_NAMES = frozenset({"postgres", "template0", "template1"})


def validate_database_name(name: str) -> str:
    if not SAFE_DB_NAME.fullmatch(name):
        raise ValueError(
            "DATABASE_NAME must contain only letters, numbers and underscore, "
            "and must start with a letter or underscore."
        )
    if name.lower() in FORBIDDEN_NAMES:
        raise ValueError(f"DATABASE_NAME '{name}' is not allowed.")
    return name


def database_exists(admin_url: str, database_name: str) -> bool:
    sync_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            )
            return result.scalar() is not None
    finally:
        engine.dispose()


def create_database(admin_url: str, database_name: str) -> None:
    sync_url = admin_url.replace("postgresql+psycopg://", "postgresql://", 1)
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            # Identifier already validated; quote safely.
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        engine.dispose()


def run_migrations() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        check=False,
    )
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap CasaLista PostgreSQL database")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run-migrations", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    database_name = validate_database_name(settings.database_name)
    admin_url = settings.get_database_admin_url()

    if not admin_url:
        print(
            "DATABASE_ADMIN_URL is not set. Create the database manually, then run:\n"
            "  alembic upgrade head\n"
            f"Target database name: {database_name}"
        )
        if settings.get_database_url():
            print(f"App URL (redacted): {settings.get_redacted_database_url()}")
        return 1

    print(f"Admin URL (redacted): {redact_database_url(admin_url)}")
    print(f"Target database: {database_name}")

    exists = database_exists(admin_url, database_name)
    if args.check_only:
        print(f"Database exists: {exists}")
        return 0 if exists else 2

    if exists:
        print("Database already exists. No changes made.")
    else:
        create_database(admin_url, database_name)
        print(f"Database '{database_name}' created.")

    if args.run_migrations:
        code = run_migrations()
        if code != 0:
            print("Migrations failed.", file=sys.stderr)
            return code
        print("Migrations applied successfully.")

    # Avoid unused import warning for urlparse when validating admin URL shape
    parsed = urlparse(admin_url)
    if not parsed.scheme.startswith("postgresql"):
        print("Warning: admin URL scheme is unexpected.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
