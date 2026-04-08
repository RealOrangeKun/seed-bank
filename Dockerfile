# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────────────────
# Multi-stage build.
#
#   builder         — uv-based wheel build of all CPU dependencies.
#   runtime-cpu     — slim Python; api + worker-cpu run from this image.
#   builder-gpu     — adds the `inference` extra (torch / torchvision / yolo).
#   runtime-gpu     — CUDA runtime image; only worker-inference uses this.
#
# The `api` image must NEVER carry torch — it just orchestrates. Verified by
# `make check-image-bloat` (added in a later phase).
# ──────────────────────────────────────────────────────────────────────────────

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.4

# ── builder (CPU) ────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev libmagic1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml ./
RUN uv venv /opt/venv \
 && . /opt/venv/bin/activate \
 && uv pip install --no-cache-dir -e .

# ── runtime (CPU) ─ used by api + worker-cpu ────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime-cpu
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 libmagic1 curl tini \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash --uid 10001 seedbank
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=seedbank:seedbank src ./src
COPY --chown=seedbank:seedbank alembic ./alembic
COPY --chown=seedbank:seedbank alembic.ini ./alembic.ini
USER seedbank
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["seedbank"]

# ── builder (GPU) ────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder-gpu
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev libmagic1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml ./
RUN uv venv /opt/venv \
 && . /opt/venv/bin/activate \
 && uv pip install --no-cache-dir -e ".[inference]"

# ── runtime (GPU) ─ used by worker-inference only ───────────────────────────
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS runtime-gpu
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3.12 python3.12-venv libpython3.12 \
      libpq5 libmagic1 libgl1 libglib2.0-0 curl tini \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash --uid 10001 seedbank
COPY --from=builder-gpu /opt/venv /opt/venv
WORKDIR /app
COPY --chown=seedbank:seedbank src ./src
COPY --chown=seedbank:seedbank alembic ./alembic
COPY --chown=seedbank:seedbank alembic.ini ./alembic.ini
USER seedbank
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["celery", "-A", "seedbank.workers.celery_app", "worker", "--loglevel=info", "-Q", "inference"]
