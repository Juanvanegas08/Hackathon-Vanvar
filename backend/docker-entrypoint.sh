#!/bin/sh
# Entrypoint del contenedor: migraciones opcionales + comando (gunicorn).
set -eu

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"

echo "[entrypoint] APP_ENV=${APP_ENV:-} GUNICORN_BIND=${GUNICORN_BIND:-} RUN_MIGRATIONS=${RUN_MIGRATIONS}"

if [ -z "${DATABASE_URL:-}" ]; then
  # pydantic también lee /app/.env; este check evita fallar tarde en alembic
  # si el .env no se copió al build (.dockerignore / sin archivo).
  if [ ! -f /app/.env ]; then
    echo "[entrypoint] ERROR: no hay DATABASE_URL ni /app/.env (backend/.env del build)." >&2
    exit 1
  fi
fi

if [ -n "${DATABASE_URL:-}" ]; then
  _db_safe="$(printf '%s' "$DATABASE_URL" | sed -E 's#://([^:/@]+):([^@]+)@#://\1:***@#')"
  echo "[entrypoint] DATABASE_URL (env)=${_db_safe}"
elif [ -f /app/.env ]; then
  echo "[entrypoint] DATABASE_URL se tomará de /app/.env"
fi

if [ "${RUN_MIGRATIONS}" = "1" ]; then
  echo "[entrypoint] alembic upgrade head…"
  if ! alembic upgrade head; then
    echo "[entrypoint] ERROR: falló alembic upgrade head." >&2
    echo "[entrypoint] Revisa DATABASE_URL en /app/.env (host, user, password, db)." >&2
    echo "[entrypoint] Para arrancar sin migrar (solo debug): -e RUN_MIGRATIONS=0" >&2
    exit 1
  fi
else
  echo "[entrypoint] migraciones omitidas (RUN_MIGRATIONS=${RUN_MIGRATIONS})"
fi

echo "[entrypoint] exec: $*"
exec "$@"
