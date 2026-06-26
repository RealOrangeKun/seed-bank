"""Worker task modules — imported here so Celery registers them.

``celery_app.autodiscover_tasks(["seedbank.workers.tasks"])`` looks for a
``tasks`` submodule under each named package. We don't have a single
``tasks.py``; the tasks live in sibling modules (``analyze``, ``dwh``,
``experiment``). Importing them here means the worker process picks up
every ``@celery_app.task(...)`` decorator at startup.

Without these imports the worker reports
``Received unregistered task of type 'seedbank.analyze_image'`` and
discards messages.
"""

from __future__ import annotations

from seedbank.workers.tasks import analyze, dwh, experiment

__all__ = ["analyze", "dwh", "experiment"]
