"""Quick connectivity check against DATABASE_URL."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    url = settings.get_database_url()
    if not url:
        print("DATABASE_URL is not configured.")
        return 1

    print(f"Connecting to: {settings.get_redacted_database_url()}")
    # Keep the psycopg3 driver URL (postgresql+psycopg://...).
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            value = connection.execute(text("SELECT 1")).scalar()
            version = connection.execute(text("SHOW server_version")).scalar()
        print(f"SELECT 1 => {value}")
        print(f"PostgreSQL version: {version}")
        print("Database connection: OK")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Database connection: FAILED ({type(exc).__name__})")
        print(str(exc))
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
