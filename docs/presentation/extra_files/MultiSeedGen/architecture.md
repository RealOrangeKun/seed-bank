# Architecture

A map of the package, the data flow, and the invariants that make generated datasets
reproducible. Read this before changing the pipeline, the config model, or the
segmentation/compositing draw order.

## Package layout

```
multiseedgen/
  config.py          Validated Pydantic v2 Config — the single source of truth
  models.py          Seed / SegResult / _QAStats dataclasses (+ re-exports Config)
  errors.py          MultiSeedGenError → ConfigError / SplitError / SegmentationError
  logging_setup.py   configure_logging() — CLI/web entry points only
  cliconfig.py       argparse parser + --config loading + nested-section flattening
  constants.py       version, SEG_VERSION (cache key), shared literals
  optdeps.py         import guards for optional deps (joblib/yaml/rembg/torch/…)
  segmentation/      cut a seed out of a source photo
    masks.py         classical mask methods (otsu/grabcut/border-colour) + quality scoring
    session.py       rembg/SAM session singletons (module-level, lazy, per-process)
    segment.py       segment_seed() cascade + extract_background()
    cache.py         content-hash + SEG_VERSION + params disk cache
    loader.py        load_seeds(): discover sources, segment, build the Seed pool
  sam_segment.py     optional Segment Anything backend (import-guarded; used by segmentation/session.py)
  compositing/       paint seeds onto a canvas
    transforms.py    per-seed scale/flip/rotate/shear/jitter
    backgrounds.py   solid/gradient/noise/seedbed/texture backgrounds
    blend.py         place_seed() compositing + shadow + IoU
    scene.py         generate_scene(): assemble one image + labels + polys + provenance
  degrade.py         camera-matched photometric degradation (blur/noise/jpeg/vignette)
  export.py          YOLO / YOLO-seg / COCO writers, data.yaml, run manifest
  qa.py              QA charts, montages, annotated previews, seed checker
  pipeline.py        run(): load → stage → per-scene workers → export → summary
  web/               FastAPI backend + built SPA
    app.py           routes (thin): schema, runs (+WS), seg/check, datasets, fs, upload, download
    schemas.py       typed request/response models
    services.py      form-schema builder + preset loader
    static/          compiled web UI (generated from frontend/; committed, served by FastAPI)
frontend/            React + TS + Tailwind v4 + Radix UI source for the web UI (Vite)
  src/api/           typed client + endpoints + TanStack Query hooks
  src/store/         Zustand stores (working config, picker, toasts)
  src/components/    UI primitives (ui/) + SchemaForm, PathPicker, DatasetViewer, …
  src/features/      the four tabs (Run, Seg tuner, Browser, Config)
```

The web UI is a single-page app: the FastAPI layer is a thin, sandboxed wrapper over the
same CLI/pipeline (it launches `python -m multiseedgen` as a subprocess and streams its
log over a websocket); see [api.md](api.md) for the full route reference. The frontend builds into `web/static/` (committed) so the package
runs without a Node toolchain; see [contributing.md](contributing.md) for the dev loop.

`seedgen.py` (repo root) is a backward-compat shim re-exporting the package API so
`python seedgen.py …` and `from seedgen import Config` keep working.

## Data flow

```
Config ──▶ load_seeds ──▶ Seed pool ──▶ stage assets ──▶ per-scene workers ──▶ writers ──▶ QA
            (segment +      (split-      (mmap / pickle)   generate_scene()      YOLO/COCO   report
             cache)          filtered)                     + degrade             + provenance
```

`run()` (in `pipeline.py`) is decomposed into load → build split pools → generate →
write annotations → summary. Per-scene work fans out over a `joblib`/`loky` (process) or
threading backend; results are gathered and written serially.

## The single source of truth: `Config`

`config.py` defines one **flat** Pydantic v2 `Config` (~90 fields). It is the only place
that knows the field set, types, choices (`Literal[...]`), and defaults. Every consumer
derives from it: the CLI parser, the YAML/JSON loader, the web form schema, and
`run_config.yaml`. `Literal` types double as CLI `choices` and form choices.

Two design rules are load-bearing and **must not change** without understanding why:

- **`Config` is mutable and flat (`validate_assignment=False`).** The parent process
  rewrites `cfg.rembg_provider` to a concrete device (`cuda`/`cpu`) *before* staging work
  into loky workers; freezing it or re-validating on assignment would break that.
- **Validators may only `raise`, never mutate.** The pipeline gates RNG draws on
  "is this knob enabled?" predicates (`aug_shear > 0`, `shadow_dir_mode == "scene"`,
  `blur_max_sigma > 0`, …). Silently coercing `0`→`None` or filling a default would shift
  the random stream and change generated pixels. The only sanctioned post-merge
  derivations are `class_probs → class_balanced=True` and `fmt == "yolo-seg" → masks=True`.

## Determinism contract

For a fixed `(config, seed)` the generated dataset is **byte-identical** regardless of
parallel backend or worker count. This is guarded by `tests/test_determinism.py`
(backend/worker invariance) and `tests/test_golden.py` (committed byte manifests). The
invariants:

- **Per-(split, scene-index) `SeedSequence`** — a scene's pixels never depend on worker
  count or scheduling.
- **Content-hashed segmentation cache** — keyed by content hash + `SEG_VERSION` + a
  frozen `_seg_params_signature` (exact fields, `round()` digits, `int()` casts). The
  wire format is pinned by `tests/test_seg_cache_contract.py`; do not bump `SEG_VERSION`
  incidentally.
- **`cv2.setNumThreads(1)`** is the first line of every worker entry on every backend —
  OpenCV reductions are not bit-identical across thread counts.
- **The worker pool split-filter** (`s.split in ("train", "both")`) is byte-identical
  between the parent and the worker.

Because draw *order* is the contract, any change to `transforms.py` / `backgrounds.py` /
`scene.py` / `degrade.py` must preserve the exact sequence of `rng` calls. The unit tests
in `tests/unit/test_compositing.py` assert same-seed → same-pixels for these functions.

## Fork-safety

`rembg`/SAM/onnxruntime sessions are unpicklable. They live as **module-level, lazily
initialised, per-process singletons** in `segmentation/session.py`. Each loky worker
rebuilds its own session on first use from the (already device-resolved) pickled config —
a live session is never pickled into a worker. Keep session init lazy and per-process.

## Errors & logging

Library code raises typed `MultiSeedGenError` subclasses (`errors.py`) — never
`sys.exit()`. The CLI entry point (`__main__.main`) catches them and re-raises
`SystemExit(msg)` for a clean exit code; the web layer maps them to `HTTPException`.
Library modules only ever `logging.getLogger(__name__)`; the handler is configured once,
to **stdout**, at the entry point (`logging_setup.configure_logging`) — never in a
library module, so loky workers don't double-configure.

## Testing strategy

- `tests/` — integration & contract tests (determinism, golden manifests, config/schema
  snapshots, seg-cache wire format, web `TestClient`).
- `tests/unit/` — fast, isolated unit tests (config validation, export writers,
  compositing/transform determinism, classical segmentation, QA renderers, entry points).

See [contributing.md](contributing.md) for how to run them and regenerate goldens.
