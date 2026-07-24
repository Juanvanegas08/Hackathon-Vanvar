"""
Configuración de Gunicorn para producción (FastAPI / ASGI).

Importante: NO usar gevent aquí. FastAPI es ASGI → worker Uvicorn.
Patrón alineado con airport-ops-back / vanvar-plane-api.
"""
from __future__ import annotations

import multiprocessing
import os

basedir = os.path.abspath(os.path.dirname(__file__))

log_dir = os.path.join(basedir, "logs")
os.makedirs(log_dir, exist_ok=True)

# =========================
# WORKERS (ASGI)
# =========================
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
worker_class = "uvicorn.workers.UvicornWorker"

# =========================
# TIMEOUTS
# =========================
# OpenAI / Twilio pueden superar 30s; override con GUNICORN_TIMEOUT.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

# =========================
# BIND
# En host bare-metal / VPS detrás de Nginx: 127.0.0.1:8100
# En contenedor expuesto: GUNICORN_BIND=0.0.0.0:8100
# =========================
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8100")

# =========================
# LOGGING
# =========================
accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(D)s'
)

# =========================
# PROCESS CONTROL
# =========================
preload_app = False
daemon = False

# =========================
# SECURITY LIMITS
# =========================
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# =========================
# WORKER RECYCLING
# =========================
max_requests = 2000
max_requests_jitter = 200


def on_starting(server):
    os.makedirs(log_dir, exist_ok=True)
    server.log.info("Gunicorn iniciando (UvicornWorker / CasaLista Voice)")


def when_ready(server):
    server.log.info("Gunicorn listo en %s", bind)


def on_exit(server):
    server.log.info("Gunicorn deteniéndose")
