"""Celery application factory.

Builds the single ``seedbank`` Celery app used by every worker container.

Settings come from :class:`seedbank.core.config.Settings`; nothing reads
``os.environ`` directly. The ``celery_task_always_eager`` flag is a
**test-only** escape hatch — when true, ``send_task`` runs the task body
inline in the calling process. Production keeps it ``False`` so the broker
boundary is the same in dev and prod.

Workers must NOT reuse the API's ``@lru_cache``'d engine. Each task opens
a fresh engine via :mod:`seedbank.workers.session`.
"""

from __future__ import annotations

from celery import Celery

from seedbank.core.config import Settings, get_settings


def _make_celery_app(settings: Settings) -> Celery:
    """Build a configured Celery app. Private so tests can rebuild it
    cleanly via :func:`make_celery_app`."""
    app = Celery(
        "seedbank",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        # CPU-heavy inference: one task per worker process at a time.
        worker_prefetch_multiplier=1,
        # Test-only inline execution.
        task_always_eager=settings.celery_task_always_eager,
        task_eager_propagates=settings.celery_task_always_eager,
        task_routes={
            "seedbank.analyze_image": {"queue": "inference"},
            "seedbank.run_experiment": {"queue": "experiments"},
        },
    )
    app.autodiscover_tasks(["seedbank.workers.tasks"])
    return app


def make_celery_app() -> Celery:
    """Public builder — used by tests to instantiate a fresh app after
    overriding settings (e.g. flipping ``celery_task_always_eager``)."""
    return _make_celery_app(get_settings())


celery_app: Celery = make_celery_app()


__all__ = ["celery_app", "make_celery_app"]
