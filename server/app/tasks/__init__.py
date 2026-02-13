"""Celery task definitions.

These are registered but not yet wired to the API routes.
When ready, replace synchronous service calls in the API routes
with .delay() calls to these tasks.
"""

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
)
