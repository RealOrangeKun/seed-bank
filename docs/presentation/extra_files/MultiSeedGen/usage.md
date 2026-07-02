# Usage

Two interchangeable front-ends drive the same pipeline: a CLI and a web UI. Both accept
the same configuration — the CLI flags, YAML/JSON config files, and the web form are all
backed by one validated `Config` (see [architecture.md](architecture.md)).

## CLI

```bash
# From a config file (recommended — reproducible and self-documenting)
seedgen --config configs/soybean_healthy.yaml

# Or fully from flags
seedgen --sources seeds/Test/images --out datasets/demo \
        --num-images 500 --segment auto --fmt both

# Flags override file values; --config sets the baseline.
seedgen --config configs/root.yaml --num-images 2000
```

Outputs land in the config's `out:` directory: `train/` and `val/` (images + labels),
`annotations_*.json` (COCO), `data.yaml`, `provenance_*.jsonl`, optional `multilabel.csv`,
and a `qa/` report. The exact resolved config is written to `run_config.yaml`, which is
itself a valid `--config` input — rerun it to reproduce a dataset byte-for-byte.

Run `seedgen --help` for the complete flag list. The shipped recipes in `configs/`
(`root`, `wheat`, `test`, `soybean_healthy`) are the best starting points; tuning
guidance is in [RECOMMENDED_SETTINGS.md](RECOMMENDED_SETTINGS.md).

## Web UI

```bash
multiseedgen-web                 # serves on the printed URL (default 127.0.0.1:8000)
multiseedgen-web --host 0.0.0.0 --port 9000   # override the bind address (or set HOST / PORT)
```

The UI is a React + TypeScript single-page app (built with Vite, styled with Tailwind +
Radix UI) served by FastAPI. It exposes the full config as a grouped, validated form (with
presets and a sandboxed path picker), streams the run log live over a websocket, keeps a
run-history list, and includes a **segmentation tuner** and a **dataset browser**. The tuner
runs a no-dataset segmentation check with per-method settings, a stop button, and live progress,
then shows kept/skipped counts and a per-seed, confidence-coded gallery — so you can dial in a
method before a full run. For seed sources you can either **upload images** (drag-and-drop,
validated as an all-or-nothing batch) or **browse an existing server folder** with the path
picker and set `sources` directly; a generated dataset **downloads as a `.zip`** (whole dataset
or a single split) straight from the browser. A dark/light theme toggle is persisted locally. It is a
**single-user, local tool** — there is intentionally no auth, CORS, or rate-limiting; do
not expose it to an untrusted network. Filesystem access (browse, upload, download) is
sandboxed to the project root, the configured data root, and the temp dir.

Set `MULTISEEDGEN_DATA_ROOT` to point the dataset browser / path picker at your data
directory; set `MULTISEEDGEN_LOG_LEVEL` (e.g. `DEBUG`) to adjust verbosity.

The compiled UI ships inside the package (`multiseedgen/web/static/`), so `multiseedgen-web`
works from a plain `pip install` with no Node toolchain. The HTTP/WS endpoints behind the UI
are documented in [api.md](api.md); to change the UI, see the frontend dev loop in
[contributing.md](contributing.md).

## Configuration files

Config files accept either flat keys or the grouped/nested layout (`segmentation:`,
`split:`, `sampling:`, `augmentation:`, `export:`). [`../configs/example.yaml`](../configs/example.yaml)
is a fully-commented reference exercising every option. Unknown keys are rejected with a
clear error, and ranges/orderings (`min_seeds ≤ max_seeds`, `0 ≤ val_split ≤ 1`, …) are
validated up front.

## Helper scripts

```bash
python scripts/validate_dataset.py datasets/demo --seg   # invariants + seg sanity checks
python scripts/make_synthetic_seeds.py --out /tmp/seeds  # tiny deterministic seed corpus
```
