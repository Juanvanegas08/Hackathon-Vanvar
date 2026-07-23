"""Unit tests for ORM metadata conventions."""

from __future__ import annotations

import app.db.models  # noqa: F401
from app.db.base import Base
from app.db.schemas import APPLICATION_SCHEMAS
from sqlalchemy import Float, Numeric
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


def test_all_models_use_application_schemas() -> None:
    for table in Base.metadata.tables.values():
        assert table.schema in APPLICATION_SCHEMAS
        assert table.schema != "public"


def test_all_tables_have_primary_key() -> None:
    for table in Base.metadata.tables.values():
        assert table.primary_key is not None
        assert len(table.primary_key.columns) >= 1


def test_all_constraints_are_named() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            assert constraint.name, f"Anonymous constraint on {table.fullname}"


def test_money_columns_are_numeric_not_float() -> None:
    money_hints = ("price", "salary", "income", "savings", "obligations", "cost", "goal")
    for table in Base.metadata.tables.values():
        for column in table.columns:
            name = column.name.lower()
            if any(hint in name for hint in money_hints):
                assert not isinstance(column.type, Float)
                if isinstance(column.type, Numeric):
                    assert column.type.precision is not None


def test_uuid_primary_keys_use_postgres_uuid() -> None:
    for table in Base.metadata.tables.values():
        for column in table.primary_key.columns:
            if column.name == "id" or column.name.endswith("_id"):
                assert isinstance(column.type, PG_UUID)


def test_timestamps_have_timezone() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name.endswith("_at") or column.name in {"created_at", "updated_at"}:
                col_type = column.type
                assert getattr(col_type, "timezone", None) is True, table.fullname


def test_foreign_keys_are_schema_qualified() -> None:
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            target = fk.target_fullname
            assert "." in target, f"FK {target} is not schema-qualified"


def test_recommendation_items_unique_project_per_run() -> None:
    table = Base.metadata.tables["recommendations.recommendation_items"]
    unique_cols = {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("project_id", "recommendation_run_id") in unique_cols
    assert ("rank", "recommendation_run_id") in unique_cols


def test_project_aliases_unique_normalized_alias() -> None:
    table = Base.metadata.tables["housing.project_aliases"]
    unique_cols = {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("normalized_alias",) in unique_cols


def test_lead_profiles_one_row_per_lead() -> None:
    table = Base.metadata.tables["leads.lead_profiles"]
    pk_cols = [c.name for c in table.primary_key.columns]
    assert pk_cols == ["lead_id"]


def test_models_import_without_cycles() -> None:
    from app.db import models

    assert len(models.__all__) > 40
