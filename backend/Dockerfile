# Imagen de producción — CasaLista Voice API (FastAPI + Gunicorn/UvicornWorker)
# Build:  docker build -t casalista-voice-api:latest -f Dockerfile .
#         podman build -t casalista-voice-api:latest -f Dockerfile .
# Run:    ver deploy/compose.yml

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GUNICORN_BIND=0.0.0.0:8100 \
    APP_ENV=production \
    ENVIRONMENT=production

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=app:app . .

RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && mkdir -p /app/logs /app/data/raw /app/data/processed /app/data/profiles /app/data/mock \
    && chown -R app:app /app/logs /app/data

USER app

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:8100/api/v1/health" || exit 1

ENTRYPOINT ["sh", "./docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "gunicorn_config.py", "app.main:app"]
