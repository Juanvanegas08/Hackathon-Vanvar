#!/bin/sh
# Entrypoint del contenedor: migraciones opcionales + comando (gunicorn).
set -eu

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"

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
  alembic upgrade head
fi

echo "[entrypoint] exec: $*"
exec "$@"
