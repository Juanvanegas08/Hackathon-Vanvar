"""PostgreSQL schema name constants for CasaLista Voice."""

CORE_SCHEMA = "core"
IDENTITY_SCHEMA = "identity"
AFFILIATION_SCHEMA = "affiliation"
LEADS_SCHEMA = "leads"
HOUSING_SCHEMA = "housing"
QUALIFICATION_SCHEMA = "qualification"
RECOMMENDATIONS_SCHEMA = "recommendations"
CONVERSATIONS_SCHEMA = "conversations"
COMMERCIAL_SCHEMA = "commercial"
INGESTION_SCHEMA = "ingestion"
AUDIT_SCHEMA = "audit"
ANALYTICS_SCHEMA = "analytics"

APPLICATION_SCHEMAS: tuple[str, ...] = (
    CORE_SCHEMA,
    IDENTITY_SCHEMA,
    AFFILIATION_SCHEMA,
    LEADS_SCHEMA,
    HOUSING_SCHEMA,
    QUALIFICATION_SCHEMA,
    RECOMMENDATIONS_SCHEMA,
    CONVERSATIONS_SCHEMA,
    COMMERCIAL_SCHEMA,
    INGESTION_SCHEMA,
    AUDIT_SCHEMA,
    ANALYTICS_SCHEMA,
)

SYSTEM_SCHEMAS: frozenset[str] = frozenset(
    {
        "public",
        "information_schema",
        "pg_catalog",
        "pg_toast",
        "pg_temp",
        "pg_toast_temp",
    }
)

REQUIRED_EXTENSIONS: tuple[str, ...] = (
    "pgcrypto",
    "citext",
    "unaccent",
    "pg_trgm",
)
