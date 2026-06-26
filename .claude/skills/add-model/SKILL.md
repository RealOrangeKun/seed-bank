---
name: add-model
description: Register a new ML model (architecture + weights + metadata) in the seed-bank platform without editing services or routers. Use this when an AI engineer wants to add a new detection or quality-classification model variant.
---

# Add an ML model

## Purpose

Add a new model variant to the platform as a self-contained change: a builder
file, a script invocation, and a status promotion. The platform is layered so
that the registry and traffic router pick up new models by data, not by code —
if you find yourself editing a service, a router, or `manager.py` to add a
model, the change is in the wrong place; the design exists to prevent that.

## When to use

- An AI engineer trained a new detection or quality-classification model and
  wants it registered, evaluated, and (eventually) promoted to production.
- You are setting up a model fixture for local or CI inference runs.

## Steps

### 0. Gather prereqs

- A `.pth` weights file produced offline.
- Whether it is a **detection** model (multi-class object detection) or a
  **classification** model (per-crop quality good/bad). This is the `kind`.
- For classification: the seed type code (e.g. `coffee`, `maize`, `lentil`).
- An MLflow run id if you tracked the training (optional, but it makes the
  artifact reproducible later).

### 1. Add the architecture builder

Create `src/seedbank/infrastructure/ml/builders/<key>.py`. The key is the
unique identifier you reference in the database — kebab-case, lowercase, with
seed type and version baked in.

```python
# src/seedbank/infrastructure/ml/builders/resnet50_lentil_v1.py
import torch.nn as nn
from torchvision.models import resnet50

from seedbank.infrastructure.ml.registry import register_builder


@register_builder("resnet50-lentil-v1")
def build() -> nn.Module:
    backbone = resnet50(weights=None)
    backbone.fc = nn.Linear(backbone.fc.in_features, 1)
    return backbone
```

The decorator registers the builder by key; autodiscovery imports every module
under `builders/` at app start (it skips `_*.py`), so dropping the file in is
all the wiring needed — no manual registration call.

Conventions for builders:

- **Builder takes no arguments.** Anything tunable belongs in the
  `model_artifacts.config` JSON so it travels with the artifact, not the code.
- **Return the bare architecture; the manager loads weights afterwards.** The
  builder describes the shape; `manager.py` fetches the `.pth` from MinIO and
  calls `load_state_dict`.
- **Don't import from `services/` or `api/`.** A builder depends only on
  `infrastructure/ml/` internals — that keeps the dependency arrows pointing
  the right way and lets the worker import builders without pulling in the API.
- **Never edit a builder referenced by a `production` model.** Clone it to a
  new key and version instead, so an in-flight production model keeps loading
  against the exact architecture it was registered with (PILLAR 5: every
  detection stays traceable to a reproducible model).

### 2. Upload weights to MinIO + register

```bash
python scripts/register_model.py upload \
    --weights /path/to/ResNet50_lentil_v1.pth \
    --key resnet50-lentil-v1 \
    --kind classification \
    --seed-type lentil \
    --name "ResNet50 Lentil Quality" \
    --version v1 \
    --threshold 0.5 \
    --image-size 224 \
    --mlflow-run-id <optional> \
    --metadata '{"dataset":"lentil-2026-q1","val_f1":0.91}'
```

The `upload` subcommand:

1. Verifies the builder key is registered, rejecting unknown keys early so a
   typo fails fast instead of at first inference.
2. Uploads the file into the `seedbank-models` MinIO bucket.
3. POSTs to `/api/v1/models` using an `ai_developer` API key from env.
4. Creates a `model_artifacts` row with `status='registered'`.
5. Prints the new `model_id` (UUID).

### 3. Promote to staging and evaluate

```bash
# Move registered -> staging so the manager can load it for evaluation.
python scripts/register_model.py promote --model-id <id> --to staging

# Evaluate against a frozen test set (see the run-experiment skill).
python scripts/run_experiment.py \
    --model-id <id> \
    --dataset-id <small-test-set-id> \
    --name "smoke: resnet50-lentil-v1"
```

Read the metrics once the experiment succeeds:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/models/<id>/performance
```

### 4. Promote to production

When offline metrics hold up (and any staging canary has run long enough):

```bash
python scripts/register_model.py promote --model-id <id> --to production
```

Promotion is atomic and enforces the `model_artifacts` state machine
(`registered → staging → production → archived`). It:

1. Sets the new model's `status='production'`.
2. Auto-archives the previously-active production model for the same
   `(kind, seed_type_id)` — there is at most one production model per segment,
   so the traffic router never has to break a tie.
3. Updates `traffic_splits` so the new model takes the segment (unless you set
   up a canary first; see below).
4. Mirrors the stage to the MLflow Model Registry.

### Optional — canary with a traffic split

Send a small fraction first instead of cutting over to 100%:

```bash
curl -X POST http://localhost:8000/api/v1/traffic-splits \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '[
    {"kind": "classification", "seed_type": "lentil", "model_id": "<old-id>", "weight": 90},
    {"kind": "classification", "seed_type": "lentil", "model_id": "<new-id>", "weight": 10}
  ]'
```

Weights are 0–100 and the rows for a segment must sum to 100. Watch
`fact_inference` in ClickHouse for both models, compare bad-rate / confidence /
latency, then dial up to 50/50 and finally 0/100.

## Conventions

- One builder file per architecture; the decorator key is the contract between
  code and the `model_artifacts` row.
- Weights live in the `seedbank-models` bucket, never in the repo. The only
  `.pth` files tracked in-tree are the preserved originals under `models/`,
  uploaded at bootstrap.
- `Inference.model_id` is NOT NULL and flows to `SeedDetection`, so every
  detection is traceable to the model that produced it. A model with no
  reproducible builder breaks that guarantee.

## Gotchas

- **Local or CI inference needs a promoted detection model**, or analyze raises
  `ModelNotReadyError`. Provision the tiny fixture instead of real weights with
  `make provision-smoke-model` — see [analyze needs a model](../../memory/known-issues.md#analyze-needs-a-promoted-detection-model) for what it
  registers/promotes and its caveats (CI/dev only, runs in `worker-inference`).
- **"unknown builder key" on upload** → the `@register_builder("...")` string
  has a typo, or the API/worker images weren't rebuilt to include the new file.
- **Weights fail to load on the worker** → the builder architecture doesn't
  match the saved state dict. Diff the keys: `torch.load(path).keys()`.
- **Inference throws for a specific seed type** → you registered the wrong
  `--seed-type`. Archive it, fix, register a new version.
- **`/models/{id}/performance` is empty** → no inferences served by this
  `model_id` yet, or the DWH dual-write task isn't shipping rows to ClickHouse.
  Check `docker compose logs worker-cpu` for `dwh`-task errors.
- **torch is only in the inference worker image** (see [lean Compose](../../memory/decisions.md#lean-compose-without-degrading-quality)).
  The API image is torch-free by design (the build guard enforces it), so
  builder-loading and the provision script must run in `worker-inference`, not `api`.

## Checklist

- [ ] Builder file added under `builders/` with a unique `@register_builder` key
- [ ] No edits to `services/`, `api/`, or `manager.py`
- [ ] No `if seed_type == "...":` branch anywhere
- [ ] Weights uploaded to MinIO; no `.pth` committed to the repo
- [ ] `model_artifacts` row created (status `registered`)
- [ ] At least one successful experiment before reaching `production`
- [ ] Production promotion verified to archive the prior model for the segment
