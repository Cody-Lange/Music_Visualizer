"""Celery task definitions.

These are registered but not yet wired to the API routes.
When ready, replace synchronous service calls in the API routes
with .delay() calls to these tasks.
"""

import platform

from celery import Celery

from app.config import settings

celery_app = Celery(
    "music_visualizer",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry broker connection on startup so the worker doesn't crash
    # if Redis is briefly unavailable or still spinning up.
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_connection_timeout=30,
    # Redis-specific: keepalive and socket timeouts to detect stale
    # connections before the OS does (prevents silent hangs).
    broker_transport_options={
        "socket_keepalive": True,
        "socket_keepalive_options": {},
        "socket_connect_timeout": 30,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    },
)

# On Windows, billiard's prefork pool has known issues with shutdown
# (PermissionError / [WinError 5]). Use the solo pool instead.
if platform.system() == "Windows":
    celery_app.conf.update(
        worker_pool="solo",
        worker_concurrency=1,
    )
