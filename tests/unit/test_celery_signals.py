"""Unit tests for the per-worker observability signal in
``workers/celery_app.py``.

Both tracing and Sentry need to be installed **after** Celery prefork —
installing pre-fork either shares a gRPC channel across children (OTel)
or breaks Sentry's event loop assumptions. The module hooks both into
``worker_process_init``; this test pins that wiring without spinning up
a real worker.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from celery.signals import worker_process_init

from seedbank.workers import celery_app as celery_app_module

pytestmark = pytest.mark.unit


def test_init_obs_per_worker_is_connected_to_worker_process_init() -> None:
    """The handler must live on Celery's ``worker_process_init`` signal —
    otherwise Sentry/OTel never bootstrap inside a forked worker."""
    receivers = [
        ref() for _, ref in worker_process_init.receivers if ref() is not None
    ]
    assert celery_app_module._init_obs_per_worker in receivers


def test_worker_process_init_invokes_sentry_and_tracing() -> None:
    """Sending the signal in-process (no real worker fork) must fan out to
    both ``init_sentry`` and ``init_tracing_for_celery``. Both initialisers
    are patched so test runs don't actually try to dial an OTLP collector
    or a Sentry DSN."""
    with (
        patch.object(celery_app_module, "init_sentry") as sentry_init,
        patch.object(celery_app_module, "init_tracing_for_celery") as tracing_init,
    ):
        worker_process_init.send(sender=None)

    sentry_init.assert_called_once()
    tracing_init.assert_called_once()
