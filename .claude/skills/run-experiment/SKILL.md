---
name: run-experiment
description: Run an offline evaluation of a model against a frozen dataset, read its metrics, and decide whether to promote. Use this for any model rollout, A/B preparation, or quality regression check.
---

# Run an experiment

## Purpose

An experiment is the evidence behind a promotion. It turns an AI engineer's
claim ("this model is better") into numbers the platform can act on. We require
at least one successful experiment behind every model that reaches
`production`, so that a promotion is a decision backed by data rather than a
hunch.

## When to use

- Before promoting a model from `staging` to `production`.
- Preparing an A/B test or canary — establish the offline baseline first.
- Checking a candidate for a quality regression against a frozen holdout set.

## What an experiment does

1. Pulls a `dataset` (rows in `dataset_items`, files in the
   `seedbank-datasets` MinIO bucket).
2. Iterates each item through the chosen model + backend.
3. Compares predictions against ground truth and computes:
   - Detection: precision, recall, F1, mAP@0.5, mAP@0.5:0.95, latency p50/p95.
   - Classification: accuracy, per-class precision/recall, confusion matrix,
     latency p50/p95.
4. Writes per-item rows to `experiment_results` (Postgres) and
   `fact_experiment_result` (ClickHouse).
5. Logs the run to MLflow with params (model_id, dataset_id, git SHA, library
   versions) and metrics.
6. Renders a Markdown report and uploads it to
   `seedbank-experiments/<experiment_id>/report.md`.

## Steps

### 1. Make sure a dataset exists

```bash
# Create a dataset row.
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer $AI_DEV_TOKEN" \
  -d '{"name": "coffee-2026-q1-holdout", "description": "Held-out 200 images, expert-labeled."}'

# Upload each image to MinIO's seedbank-datasets bucket yourself (presigned
# PUT, or the minio/mc client) and pick the object key — there is no upload
# script for this yet. Then bulk-add items by key:
curl -X POST http://localhost:8000/api/v1/datasets/<id>/items \
  -H "Authorization: Bearer $AI_DEV_TOKEN" \
  -d '{"items": [
    {"image_storage_key": "coffee-2026-q1-holdout/img_0001.jpg",
     "ground_truth": {"kind": "detection", "boxes": [
       {"x": 0.10, "y": 0.20, "w": 0.05, "h": 0.06, "label": "coffee", "quality": "good"}
     ]}}
  ]}'
```

`image_storage_key` and `ground_truth` are `DatasetItemCreateIn`
(`src/seedbank/schemas/dataset.py`) — boxes are normalized 0–1, matching how
detections are stored, so the evaluator never deals in pixel coordinates.
`ground_truth` is `{"kind": "detection", "boxes": [...]}` or
`{"kind": "classification", "label": "good"}`; full narrative in
`docs/system-overview.md` §4.9. The bulk-add endpoint caps at 1000 items per
call, so a large dataset needs several calls.

### 2. Kick the experiment

The model must already exist and be loadable (`staging` or `production`); the
worker resolves its weights from the registry by `model_id`. Two equivalent
entry points, both dispatching the same Celery task on the `experiments` queue:

```bash
# CLI
python scripts/run_experiment.py \
  --model-id <model-uuid> \
  --dataset-id <dataset-uuid> \
  --name "compare resnet18-coffee-v3 vs v4"
# add --wait to block until the run finishes (--timeout / --poll-interval tune it)
```

```bash
# API (ai_developer token required)
curl -X POST http://localhost:8000/api/v1/experiments \
  -H "Authorization: Bearer $AI_DEV_TOKEN" \
  -d '{
    "name": "compare resnet18-coffee-v3 vs v4",
    "model_id": "<uuid>",
    "dataset_id": "<uuid>"
  }'
```

The API returns immediately with `status: pending`; the worker runs it.
Typical runtime is 1–5 min depending on dataset size and GPU availability.

### 3. Watch and read

```bash
# Status + summary metrics
curl -H "Authorization: Bearer $AI_DEV_TOKEN" \
  http://localhost:8000/api/v1/experiments/<id>

# Full per-item results (paginated: ?page=&page_size=)
curl -H "Authorization: Bearer $AI_DEV_TOKEN" \
  "http://localhost:8000/api/v1/experiments/<id>/results?page=1"

# Markdown report (redirects to a signed MinIO URL)
curl -H "Authorization: Bearer $AI_DEV_TOKEN" \
  http://localhost:8000/api/v1/experiments/<id>/report
```

Or via UI: MLflow (`http://localhost:5000`) for run-level params, metrics, and
plots; Adminer (`make up-dev`) for the `experiments` / `experiment_results`
tables; ClickHouse for rich aggregations over `fact_experiment_result`.

### 4. Compare two experiments

```sql
-- ClickHouse
SELECT
  e.name,
  avg(latency_ms)                     AS avg_latency,
  quantileExact(0.95)(latency_ms)     AS p95_latency,
  countIf(prediction_correct)/count() AS accuracy
FROM fact_experiment_result fr
JOIN dim_experiment e ON e.id = fr.experiment_id
WHERE e.id IN ('<exp1>', '<exp2>')
GROUP BY e.name
```

### 5. Decide

Promote only when all of these hold — each guards a different way a model can
look better on paper but worse in production:

- The headline metric (accuracy / F1 / mAP) improved by more than your noise
  floor. Estimate that floor by running the same model + config twice and
  measuring the spread.
- No latency p95 regression you can't tolerate at production traffic.
- No regression on tail classes or known failure modes — read the per-class
  breakdown, not just the average.
- A human spot-checked a sample of disagreements between the new and old model.

If it passes, hand off to the `add-model` skill for the promotion and
traffic-split flow.

## Conventions

- Datasets and ground truth are frozen: an experiment is only comparable if the
  items and labels are identical across runs.
- Reproducibility — every experiment should be re-runnable from its recorded
  params. Confirm MLflow captured: `git_sha`, `model_artifact_uri` (the exact
  MinIO key), `dataset_id`, `library_versions` (torch, torchvision,
  ultralytics), and `random_seed` if any randomness exists. Without these, an
  experiment is a number, not a result.

## Gotchas

- **Local runs have no model to evaluate against** until one is loadable. For a
  smoke-level run with no real weights, provision the tiny fixture detector first
  (`make provision-smoke-model`) — see [analyze needs a model](../../memory/known-issues.md#analyze-needs-a-promoted-detection-model). Numbers
  from it are meaningless; it only exercises the pipeline end to end.
- **Empty results / status stuck `running`** → check the worker
  (`docker compose logs worker-inference`). Common causes: an invalid weights
  URL in MinIO, or a builder-key mismatch.
- **Numbers don't match the engineer's offline notebook** → confirm the dataset
  holds the exact same items and ground truth, and that the backend being
  evaluated (`torch_local` vs `roboflow` vs `ultralytics_yolo`) matches the one
  the notebook used.
- **Latency far higher than production inference** → the run may lack GPU.
  Confirm `worker-inference` is the target, not `worker-cpu`.

## Checklist

- [ ] Dataset created and items uploaded with ground truth
- [ ] Model is loadable (`staging` or `production`)
- [ ] Experiment reached `status: succeeded`
- [ ] Headline metric beats the measured noise floor
- [ ] No intolerable p95 latency regression
- [ ] Per-class / tail-failure breakdown reviewed, not just the average
- [ ] Disagreements spot-checked by a human
- [ ] MLflow params let someone re-run the experiment cold
