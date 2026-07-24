"""Verify migrations, schemas, extensions, tables and views."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import app.db.models  # noqa: E402, F401
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.schemas import APPLICATION_SCHEMAS, REQUIRED_EXTENSIONS  # noqa: E402


def main() -> int:
    settings = get_settings()
    url = settings.get_database_url()
    if not url:
        print("DATABASE_URL is not configured.")
        return 1

    sync_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    engine = create_engine(sync_url)
    errors: list[str] = []

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Database connection: OK")

            current = connection.execute(
                text("SELECT version_num FROM core.alembic_version LIMIT 1")
            ).scalar()
            print(f"Current revision: {current}")

            cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
            script = ScriptDirectory.from_config(cfg)
            heads = list(script.get_heads())
            print(f"Expected heads: {', '.join(heads)}")
            if len(heads) != 1:
                errors.append("Unexpected number of Alembic heads")
            if current in heads:
                print("Migration status: up to date")
            else:
                print("Migration status: pending or unknown")
                errors.append("Database revision is not at head")

            schema_rows = connection.execute(
                text(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name = ANY(:schemas)
                    """
                ),
                {"schemas": list(APPLICATION_SCHEMAS)},
            )
            schemas = {row[0] for row in schema_rows}
            print(f"Schemas: {len(schemas)}/{len(APPLICATION_SCHEMAS)}")
            missing_schemas = set(APPLICATION_SCHEMAS) - schemas
            if missing_schemas:
                errors.append(f"Missing schemas: {sorted(missing_schemas)}")

            extension_rows = connection.execute(
                text(
                    """
                    SELECT extname
                    FROM pg_extension
                    WHERE extname = ANY(:extensions)
                    """
                ),
                {"extensions": list(REQUIRED_EXTENSIONS)},
            )
            extensions = {row[0] for row in extension_rows}
            print(f"Extensions: {len(extensions)}/{len(REQUIRED_EXTENSIONS)}")
            missing_ext = set(REQUIRED_EXTENSIONS) - extensions
            if missing_ext:
                errors.append(f"Missing extensions: {sorted(missing_ext)}")

            expected_tables = {
                (table.schema, table.name)
                for table in Base.metadata.tables.values()
                if table.schema in APPLICATION_SCHEMAS
            }
            table_rows = connection.execute(
                text(
                    """
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema = ANY(:schemas)
                    """
                ),
                {"schemas": list(APPLICATION_SCHEMAS)},
            )
            actual_tables = {(row[0], row[1]) for row in table_rows}
            print(f"Tables: {len(actual_tables)}")
            missing_tables = expected_tables - actual_tables
            if missing_tables:
                errors.append(f"Missing tables: {sorted(missing_tables)[:10]}")

            view_rows = connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'analytics'
                    """
                )
            )
            views = [row[0] for row in view_rows]
            print(f"Views: {len(views)}")
            for required in ("lead_funnel", "project_interest", "conversation_performance"):
                if required not in views:
                    errors.append(f"Missing analytics view: {required}")
    except Exception as exc:  # noqa: BLE001
        print(f"Database connection: FAILED ({type(exc).__name__})")
        print(str(exc))
        return 1
    finally:
        engine.dispose()

    if errors:
        print("Verification FAILED:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("Verification PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
