# syntax=docker/dockerfile:1.7
# ──────────────────────────────────────────────────────────────────────────────
# Multi-stage build. Runtime targets (what compose builds):
#
#   runtime-cpu               — slim Python; api + worker-cpu. NO torch.
#   runtime-inference-cpu     — + slim [inference] (torch CPU, torchvision,
#                               headless cv2). Default worker-inference.
#   runtime-inference-cpu-full— + [inference-full] (ultralytics + Roboflow).
#                               Opt-in: only when a YOLO/Roboflow model ships.
#   runtime-gpu               — CUDA runtime; worker-inference on GPU hosts.
#   mlflow                    — MLflow server + psycopg2 + boto3.
#
# The `api` image must NEVER carry torch — it just orchestrates. Guarded in CI
# by `.github/workflows/build.yml`; `make image-bloat` prints the largest files.
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
# Hatchling reads the readme path from pyproject.toml at metadata time, so
# README.md must be in the context. The package layout (src/seedbank) is
# also required because hatchling resolves it during editable install.
COPY pyproject.toml README.md ./
COPY src ./src
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
COPY --chown=seedbank:seedbank scripts ./scripts
USER seedbank
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["seedbank"]

# ── builder (CPU + inference, SLIM) ──────────────────────────────────────────
# Same as the CPU builder but installs the lean [inference] extra (torch CPU
# wheels, torchvision, numpy, headless OpenCV) — exactly what the torch_local
# backend (the only wired models) loads. ~1.6 GB runtime vs the ~640 MB CPU
# runtime. The optional YOLO/Roboflow backends live in the `*-full` targets
# below; build those only when such a model is actually deployed.
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder-inference-cpu
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_INDEX_URL=https://download.pytorch.org/whl/cpu \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev libmagic1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# UV_INDEX_STRATEGY=unsafe-best-match lets uv reach the pytorch CPU index
# for torch* and the public pypi for everything else.
RUN uv venv /opt/venv \
 && . /opt/venv/bin/activate \
 && UV_INDEX_STRATEGY=unsafe-best-match \
    uv pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        -e ".[inference]"

# ── runtime (CPU + inference, SLIM) ─ default worker-inference image ────────
# No libgl1: headless OpenCV (opencv-python-headless) needs only libglib2.0-0,
# not the GL stack. The `*-full` runtime below re-adds libgl1 because
# ultralytics pulls non-headless cv2.
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime-inference-cpu
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 libmagic1 libglib2.0-0 curl tini \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash --uid 10001 seedbank
COPY --from=builder-inference-cpu /opt/venv /opt/venv
WORKDIR /app
COPY --chown=seedbank:seedbank src ./src
COPY --chown=seedbank:seedbank alembic ./alembic
COPY --chown=seedbank:seedbank alembic.ini ./alembic.ini
COPY --chown=seedbank:seedbank scripts ./scripts
USER seedbank
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["celery", "-A", "seedbank.workers.celery_app", "worker", "--loglevel=info", "-Q", "inference,evaluation"]

# ── builder (CPU + inference, FULL) ──────────────────────────────────────────
# Adds the [inference-full] extra (ultralytics + inference-sdk) on top of the
# slim torch stack. Build + run the `runtime-inference-cpu-full` image only
# when a YOLO or Roboflow model is registered — the torch_local backend never
# needs it. Roughly doubles image size (non-headless cv2, matplotlib, pandas,
# scipy come in via ultralytics).
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder-inference-cpu-full
ARG UV_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_INDEX_URL=https://download.pytorch.org/whl/cpu \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev libmagic1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv==${UV_VERSION}"
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv venv /opt/venv \
 && . /opt/venv/bin/activate \
 && UV_INDEX_STRATEGY=unsafe-best-match \
    uv pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        -e ".[inference-full]"

# ── runtime (CPU + inference, FULL) ─ opt-in worker-inference image ─────────
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime-inference-cpu-full
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 libmagic1 libgl1 libglib2.0-0 curl tini \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash --uid 10001 seedbank
COPY --from=builder-inference-cpu-full /opt/venv /opt/venv
WORKDIR /app
COPY --chown=seedbank:seedbank src ./src
COPY --chown=seedbank:seedbank alembic ./alembic
COPY --chown=seedbank:seedbank alembic.ini ./alembic.ini
COPY --chown=seedbank:seedbank scripts ./scripts
USER seedbank
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["celery", "-A", "seedbank.workers.celery_app", "worker", "--loglevel=info", "-Q", "inference,evaluation"]

# ── builder (GPU) ────────────────────────────────────────────────────────────
# Installs the slim [inference] extra (GPU torch from the default index bundles
# its own CUDA libs). For a YOLO/Roboflow-on-GPU box, change the extra below to
# ".[inference-full]" — there's no separate full-GPU target since GPU hosts are
# bespoke.
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
COPY pyproject.toml README.md ./
COPY src ./src
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
COPY --chown=seedbank:seedbank scripts ./scripts
USER seedbank
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["celery", "-A", "seedbank.workers.celery_app", "worker", "--loglevel=info", "-Q", "inference"]


# ── mlflow ──────────────────────────────────────────────────────────────────
# The official MLflow image ships without `psycopg2` and without `boto3`,
# but our compose configures Postgres as the backend store and MinIO/S3 as
# the artifact destination. Add both here so the image runs as configured.
# Pin versions explicitly so the image is reproducible — bump in lockstep
# with the upstream MLflow tag.
FROM ghcr.io/mlflow/mlflow:v2.18.0 AS mlflow
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 boto3==1.35.36
