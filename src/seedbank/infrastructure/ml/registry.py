"""Builder registry — the indirection that lets AI engineers add a new model
architecture without touching ``services/`` or ``api/``.

A *builder* is a zero-arg callable that returns a fresh, weight-uninitialized
``torch.nn.Module``. It is registered under a unique kebab-case key
(typically ``<arch>-<seed-type>-v<n>``). The ``ModelManager`` then looks up
the key recorded on a ``model_artifacts`` row, calls the builder, and loads
weights from MinIO into the resulting module.

Design notes
------------
* The registry is **process-wide** (a module-level dict). Writes happen at
  import time (when a builder file is first imported); reads are concurrent
  but require no lock because dict reads of a steady-state dict are safe.
* Autodiscovery scans ``infrastructure.ml.builders`` exactly once on first
  ``get_builder``/``list_builders``. Files whose name starts with ``_``
  (e.g. ``_cbam.py``) are skipped — they are private helpers, not builders.
* Builders may import torch. The registry itself does **not** import torch,
  so the API process can safely import this module to inspect known keys
  without pulling in the heavy ML stack.
"""

from __future__ import annotations

import importlib
import pkgutil
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — torch is in the [inference] extra
    from torch import nn

    Builder = Callable[[], nn.Module]
else:
    Builder = Callable[[], object]


_REGISTRY: dict[str, Builder] = {}
_DISCOVERED = False
_DISCOVERY_LOCK = threading.Lock()


class BuilderAlreadyRegisteredError(RuntimeError):
    """Raised when two builder files declare the same key."""


class BuilderNotFoundError(KeyError):
    """Raised when a model_artifacts row references a key that nobody registered."""


def register_builder(key: str) -> Callable[[Builder], Builder]:
    """Decorator: bind ``func`` to ``key`` in the process-wide registry.

    Re-registering the same key is rejected — silent shadowing of a builder
    is the kind of bug that produces "wrong model in production" incidents.
    """

    if not key or not isinstance(key, str):
        raise ValueError("Builder key must be a non-empty string.")

    def _decorator(func: Builder) -> Builder:
        existing = _REGISTRY.get(key)
        if existing is not None and existing is not func:
            raise BuilderAlreadyRegisteredError(
                f"Builder key '{key}' is already registered by "
                f"{existing.__module__}.{existing.__qualname__}."
            )
        _REGISTRY[key] = func
        return func

    return _decorator


def _autodiscover() -> None:
    """Import every module under ``infrastructure.ml.builders`` exactly once
    so that decorators run and populate the registry."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    with _DISCOVERY_LOCK:
        if _DISCOVERED:
            return
        # Import the package by name to avoid a circular import at module load.
        pkg = importlib.import_module("seedbank.infrastructure.ml.builders")
        for module_info in pkgutil.iter_modules(pkg.__path__):
            name = module_info.name
            # Convention: a leading underscore marks a private helper module
            # (e.g. _cbam.py) — not a builder, don't import to avoid surprise
            # side effects in tests.
            if name.startswith("_"):
                continue
            importlib.import_module(f"{pkg.__name__}.{name}")
        _DISCOVERED = True


def get_builder(key: str) -> Builder:
    """Look up a builder by key, triggering autodiscovery on first call."""
    _autodiscover()
    try:
        return _REGISTRY[key]
    except KeyError as exc:
        raise BuilderNotFoundError(
            f"No builder registered for key '{key}'. Known: {sorted(_REGISTRY)}"
        ) from exc


def list_builders() -> list[str]:
    """Return all registered builder keys, sorted for determinism."""
    _autodiscover()
    return sorted(_REGISTRY)


def _reset_for_tests() -> None:
    """Wipe the registry — only for unit tests that need a clean slate."""
    global _DISCOVERED
    _REGISTRY.clear()
    _DISCOVERED = False


__all__ = [
    "BuilderAlreadyRegisteredError",
    "BuilderNotFoundError",
    "get_builder",
    "list_builders",
    "register_builder",
]
