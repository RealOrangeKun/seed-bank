# MultiSeedGen — Recommended Settings

Practical, opinionated settings for generating **multi-seed detection** training data
from your single-seed sources. Defaults are sane; this doc says *what to change and why*
for the datasets in `seeds/` and for the GPU on this box.

> **Golden rule:** quality of the **cut-outs** and **domain match of the backgrounds**
> matter far more than how many images you generate. Always verify segmentation before a
> big run, and always keep a small **real, hand-labelled multi-seed** set for evaluation —
> synthetic training accuracy is not the real metric.

---

## 0. The workflow (do this every time)

```bash
# 1) VERIFY segmentation first (no dataset yet) — look at out/seed_check/*.png
python seedgen.py --sources seeds/Root --out /tmp/chk --check-seeds 40 --num-images 0
#    inspect out/seg_report.txt: kept-by-method, skipped reasons, confidence histogram

# 2) GENERATE (see per-dataset recipes below)
python seedgen.py --config configs/root.yaml --out datasets/root

# 3) INSPECT the exported labels (drawn back from disk) + QA charts
#    open datasets/root/preview/*.jpg and datasets/root/qa/report.md
python tests/validate_dataset.py datasets/root          # box==ann parity, schema, in-frame
```

Or do all of it in the browser: `python -m multiseedgen.web` → http://localhost:8000
(Run + live log, Segmentation tuner, Dataset browser, Config save/load).

---

## 1. Global recommendations (apply to most runs)

| Setting | Recommend | Why |
|---|---|---|
| `--rembg-provider auto` | **default** | Uses the RTX 3060 when present (~11× faster cut-outs), CPU otherwise. |
| `--gpu-seg-jobs 0` | **default** (auto) | `0` = auto-scales concurrent GPU rembg sessions to free VRAM (~0.9 GB each; falls back to 4 if `nvidia-smi` is absent). A per-image OOM→CPU fallback also prevents a hard crash. Set a positive number only to cap manually. |
| `--workers 0` | **default** (auto) | Parallel scene generation. Use `--workers 1` only when you want the deterministic reference. |
| `--seed 7` | **set it** | Reproducible runs; output is byte-identical for a given seed regardless of `--workers`. |
| `--bg-from-sources` | **on** | Composites onto your **real tray** (inpainted from sources) → closes the domain gap. Best single quality lever. |
| `--neg-frac 0.1` | **on** | ~10% background-only images → suppresses false positives on the tray/texture. |
| `--shadow-dir-mode scene` | **default** | One light direction per scene → soft, directional shadows that fade into the tray. |
| `--shadow-opacity 0.25` | **default** | Subtle grounding shadow. Raise toward 0.4 for harder light; lower to ~0.15 for flat/diffuse. |
| `--edge-feather 0.5` | **default** | Anti-aliases the paste edge only; never moves boxes. |
| `--degrade` (mild) | **on** | Adds sensor noise + JPEG + slight defocus so composites look photographed, not pasted. |
| `--qa-report --visualize-count 12` | **on** | Always eyeball the result before training. |
| `--format` | `yolo-seg` or `both` | `yolo-seg` matches your real `Test/annotations/*.txt` polygons; `both` = YOLO boxes + COCO. |

**Recommended realism preset** (photometric only — never moves boxes):

```
--degrade --noise-sigma 3 --jpeg-quality-min 80 --jpeg-quality-max 95 --blur-max-sigma 0.5 --shadow-dir-mode scene
```

Leave `--vignette 0` when using `--bg-from-sources` (the real tray already carries its
vignette — don't double it). Keep `--blend alpha` (default); `seamless` is slower and only
occasionally better. `--perspective` applies a per-seed perspective warp before placement
(box recomputed from the warped alpha); a small value like `0.05`–`0.1` adds viewpoint
variety, `0` disables it.

> **Drop shadows fade into the background** (v3.0.1). The shadow is rendered on a padded
> canvas so its blur tapers to zero instead of being clipped to each seed's bounding box — the
> old hard rectangular "halo box" around every seed is gone. Box/polygon labels are now keyed to
> the seed's true silhouette (independent of `--edge-feather`), so softening the edge never
> shifts a label. Turn shadows off entirely with `--no-shadow`.

---

## 2. Per-dataset recipes

Source folders (confirmed): `seeds/Root` (5118, 27 species, dark seed on near-white vignetted
tray — clean), `seeds/Varietal purity of wheat seeds dataset/...` (1124, tiny pale seed on
gray, 256 px), `seeds/Test/images` (272, pale soybean + cast shadow + burned-in watermark —
hardest; real labels are YOLO-seg polygons). `seeds/Test/images/Healthy` (133) is the
single-condition healthy-soybean subset — same hard photometric case, one class.

### Root — clean, large, 27 species

```bash
python seedgen.py \
  --sources seeds/Root --out datasets/root \
  --class-mode subfolders \
  --num-images 6000 --img-size 640 \
  --min-seeds 8 --max-seeds 30 --scale-min 0.05 --scale-max 0.16 \
  --bg-from-sources --neg-frac 0.10 \
  --segment auto --rembg-provider auto \
  --format both --masks \
  --degrade --noise-sigma 3 --jpeg-quality-min 80 --jpeg-quality-max 95 --blur-max-sigma 0.5 \
  --shadow-dir-mode scene --qa-report --visualize-count 12 --seed 7
```

- `--class-mode subfolders` → one class per species (detection *and* species ID). Drop it
  (`single`) if you only need "seed vs background".
- Classical segmentation nails dark-on-white; the GPU rembg fallback auto-handles the few
  low-contrast species (e.g. *Caraway*). No `--segment-map` needed.

### Wheat — tiny, low-contrast, 256 px sources

```bash
python seedgen.py \
  --sources "seeds/Varietal purity of wheat seeds dataset" --out datasets/wheat \
  --class-mode subfolders \
  --num-images 4000 --img-size 512 \
  --min-seeds 12 --max-seeds 45 --scale-min 0.03 --scale-max 0.09 \
  --bg-from-sources --neg-frac 0.10 \
  --segment auto --seg-conf-thresh 0.48 --rembg-provider auto \
  --format both --masks \
  --degrade --noise-sigma 3 --jpeg-quality-min 80 --jpeg-quality-max 95 \
  --shadow-dir-mode scene --qa-report --seed 7
```

- Seeds are tiny → **smaller scale, more per scene** (`--scale-min 0.03 --max-seeds 45`).
- Pale-on-gray is low-contrast → lower the gate slightly (`--seg-conf-thresh 0.48`) so good
  faint seeds aren't skipped; the rembg fallback covers the rest. Check `seg_report.txt`.
- `--min-box-px 6` if many seeds render below the 8 px default and get filtered.

### Test — hardest (cast shadow + watermark); matches real polygon labels

```bash
python seedgen.py \
  --sources seeds/Test/images --out datasets/test \
  --num-images 3000 --img-size 640 \
  --min-seeds 6 --max-seeds 22 --scale-min 0.06 --scale-max 0.18 \
  --bg-from-sources --neg-frac 0.12 \
  --segment rembg --rembg-provider auto \
  --format yolo-seg \
  --degrade --noise-sigma 3 --jpeg-quality-min 75 --jpeg-quality-max 95 --blur-max-sigma 0.6 \
  --shadow-dir-mode scene --qa-report --visualize-count 12 --seed 7
```

- Force `--segment rembg`: the learned mask cleanly drops the **cast shadow** and avoids the
  **burned-in watermark** text that classical thresholding can latch onto.
- `--format yolo-seg` so synthetic labels are **schema-identical** to `Test/annotations/*.txt`.
- On the GPU this stays fast even though every source goes through rembg (capped to 4 sessions).

### Soybean (Healthy) — single class, narrow subset of Test

```bash
python seedgen.py \
  --sources seeds/Test/images/Healthy --out datasets/soybean_healthy \
  --class-mode single \
  --num-images 2500 --img-size 640 \
  --min-seeds 6 --max-seeds 22 --scale-min 0.06 --scale-max 0.18 \
  --bg-from-sources --neg-frac 0.12 \
  --segment rembg --rembg-provider auto \
  --format yolo-seg \
  --degrade --noise-sigma 3 --jpeg-quality-min 75 --jpeg-quality-max 95 --blur-max-sigma 0.6 \
  --shadow-dir-mode scene --qa-report --visualize-count 12 --seed 7
```

- Same hard photometric case as the full Test set, narrowed to the **133 Healthy sources** as a
  single class (`--class-mode single`). Synthetic labels carry class id `0`; the real
  `Test/annotations/Healthy/*.txt` use id `4` inside the 5-class condition scheme — fine for
  seed-vs-background detection, just not id-compatible with the real multi-condition labels.
- Cold first pass on a fresh `out` runs every source through rembg live. Session count now
  **auto-scales to free VRAM** and a `bfc_arena` VRAM OOM mid-run **falls back to CPU for that
  worker** instead of crashing, so the old `--gpu-seg-jobs 2` workaround is rarely needed; set
  a positive `--gpu-seg-jobs` only to cap manually (or `--rembg-provider cpu` to force CPU).
  With only 133 sources either is quick. Shipped as `configs/soybean_healthy.yaml`.
- **Use `rembg`, not `auto`, for this domain.** The warm cast shadow is far in colour from the
  cream tray, so the classical `auto` cascade grabs it (and sometimes the burned-in watermark)
  into the cut-out — and because a shadow+seed blob scores *high* confidence, the rembg fallback
  never fires, so the shadow is silently baked into the labels. `rembg` segments only the seed
  body. The **Segmentation tuner** now inherits the loaded preset's method, so loading
  "Soybean — Healthy (single class)" makes the tuner check `rembg` (it no longer always tests
  `auto`).
- The confidence skip-gate (`seg_conf_thresh`) used to run only in `auto`; it now applies to any
  method, but is **opt-in for explicit methods** — it defaults to `0` (off) for non-`auto`, so
  existing `rembg`/`grabcut`/… runs skip nothing unless you raise it. Set it (e.g. `0.6`) to also
  drop low-confidence cut-outs in an explicit-method run. The **rembg fallback stays auto-only**.

---

## 3. Reusable `--config` templates

Save as `configs/<name>.yaml` and run `python seedgen.py --config configs/<name>.yaml`.
CLI flags still override the file, and any run writes a `run_config.yaml` you can re-feed.

**`configs/root.yaml`**
```yaml
config:
  sources: seeds/Root
  out: datasets/root
  class_mode: subfolders
  num_images: 6000
  img_size: 640
  min_seeds: 8
  max_seeds: 30
  scale_min: 0.05
  scale_max: 0.16
  bg_from_sources: true
  neg_frac: 0.10
  segment: auto
  rembg_provider: auto
  fmt: both          # 'format' is also accepted
  masks: true
  degrade: true
  noise_sigma: 3
  jpeg_quality_min: 80
  jpeg_quality_max: 95
  blur_max_sigma: 0.5
  shadow_dir_mode: scene
  qa_report: true
  visualize_count: 12
  seed: 7
```

**`configs/test.yaml`** (hard set, polygon labels)
```yaml
config:
  sources: seeds/Test/images
  out: datasets/test
  num_images: 3000
  bg_from_sources: true
  neg_frac: 0.12
  segment: rembg
  rembg_provider: auto
  # gpu_seg_jobs omitted -> auto-scales to free VRAM (set a number to cap manually)
  fmt: yolo-seg
  degrade: true
  noise_sigma: 3
  jpeg_quality_min: 75
  jpeg_quality_max: 95
  blur_max_sigma: 0.6
  shadow_dir_mode: scene
  qa_report: true
  seed: 7
```

**`configs/soybean_healthy.yaml`** (Healthy soybean only, single class)
```yaml
config:
  sources: seeds/Test/images/Healthy
  out: datasets/soybean_healthy
  class_mode: single
  num_images: 2500
  img_size: 640
  min_seeds: 6
  max_seeds: 22
  scale_min: 0.06
  scale_max: 0.18
  bg_from_sources: true
  neg_frac: 0.12
  segment: rembg
  rembg_provider: auto
  # gpu_seg_jobs omitted -> auto-scales to free VRAM; OOM falls back to CPU (set to cap)
  fmt: yolo-seg
  degrade: true
  noise_sigma: 3
  jpeg_quality_min: 75
  jpeg_quality_max: 95
  blur_max_sigma: 0.6
  shadow_dir_mode: scene
  qa_report: true
  visualize_count: 12
  seed: 7
```

---

## 4. Speed & scale (6500+ sources, locally, without taking days)

- **Segmentation is cached** (`<out>/.seg_cache`, content-hashed). The first pass over a
  source library is the cost; every later run is near-instant. Share one cache across runs
  with `--cache-dir /path/to/shared_cache`.
- **GPU rembg** is ~11× faster per cut-out than CPU; keep `--rembg-provider auto`.
- **Scene generation** scales with `--workers` (auto = min(cpu, 8) here) and is byte-identical
  regardless of worker count **or backend**.
- **Memory-safe parallelism (`--parallel-backend auto`, default).** The seed + background
  assets are held in RAM for the whole run. The `loky` (process) backend gives each worker its
  own *full copy* — on a big library that multiplies into an out-of-memory kill (e.g. ~7 GB of
  assets × 8 workers ≫ 16 GB). `auto` keeps `loky` only when the copies fit in ~60% of free RAM,
  otherwise it transparently switches to **`threading`** (one shared in-memory copy, still
  multi-core via OpenCV/NumPy — ~3–4× on 8 cores) and prints a one-line `[mem]` notice. Force
  either with `--parallel-backend loky|threading`. On a RAM-constrained box, threading is the
  safe default and produces identical output.
- For a **quick iteration** while tuning, cap sources and images:
  `--max-sources 40 --num-images 200 --no-qa` … then drop the caps for the full run.
- Classical-heavy sets (Root) are fastest with CPU parallelism; if you don't need the learned
  fallback there, `--rembg-provider cpu` keeps all cores busy on segmentation.

---

## 5. Segmentation tuning (when good seeds get skipped)

Read `out/seg_report.txt` (or the **Segmentation-tuner tab**, which shows kept/skipped counts and a
per-seed, confidence-coded gallery so you can see exactly which cut-outs were dropped and why). If
legitimate seeds are skipped:

1. Lower the gate: `--seg-conf-thresh 0.45`.
2. Force a method per source folder with a **segment map** (`--segment-map map.json`):

```json
[
  { "glob": "Test/**",         "method": "rembg" },
  { "glob": "*Caraway*",       "method": "rembg" },
  { "glob": "**",              "method": "auto"  }
]
```

First match wins; it's folded into the cache key so changing it re-segments only what's affected.
3. Watermark fragment surviving on a Test cut-out? `--segment rembg` (or map → rembg) removes it.

Per-method knobs can also be set in config files under nested `segmentation.<method>` sections
(e.g. `segmentation.grabcut.iterations`, `segmentation.otsu.threshold_adjustment`,
`segmentation.u2net.device`) — see [`configs/example.yaml`](../configs/example.yaml); each method's
params are isolated in the cache key, so tuning one never invalidates another's cache.

---

## 6. Honest caveats (carry these into the thesis)

- **Evaluate on real, hand-labelled, multi-seed images.** The `seeds/Test` set is *single*-seed,
  so it validates the classifier/domain but **not** multi-seed detection. Generate train data here;
  keep a small real multi-seed set as val/test.
- **Use the full unique-seed library**, not a handful — a small pool invites memorization.
- GPU cut-outs aren't bit-identical run-to-run on a **cold** cache (cuDNN nondeterminism; CPU vs
  GPU masks differ ~0.01%). Within a run they're cached, so determinism is exact. Use
  `--rembg-provider cpu` if you need strict cross-run reproducibility.
- **OOM→CPU fallback caveat:** if a GPU rembg worker hits a mid-run CUDA OOM it retries that
  image (and the rest of that worker) on CPU rather than crashing. The seg-cache key encodes the
  *resolved* device (`cuda`), so such a CPU-computed mask is cached under the `cuda` key. This is
  a rare degraded path; for a strictly reproducible publishable run use `--rembg-provider cpu`
  (which also sidesteps the cold-cache nondeterminism above).
- Synthetic backgrounds (`solid/gradient/noise`) are a fallback; **prefer `--bg-from-sources`**
  (or `--textures <real photos>`). Avoid `--backgrounds seedbed` (unlabelled seed clutter).
```

## 7. Class / seed-type provenance (multi-type datasets)

Each **top-level source subfolder is one class** when you pass `--class-mode subfolders`
(the torchvision *ImageFolder* convention). The folder name becomes the class name, enumerated
in sorted order to a 0-based `class_id`. Nested subfolders (e.g. `wheat/variety_a/`) are *not*
yet a hierarchy — every file under `wheat/` is class `wheat`.

- **Default `--class-mode single`** merges everything into one class `seed`. If your `--sources`
  has ≥2 image-bearing subfolders, a startup **warning** reminds you to switch to `subfolders`
  (otherwise the per-type distinction is silently lost).

Where the class shows up in the outputs:

| Artifact | Field |
| --- | --- |
| YOLO label line | leading `class_id` (0-based) |
| `data.yaml` | `nc`, `names: [...]` (id→name) |
| COCO `categories` | `{"id", "name", "supercategory": "seed"}` (id is 1-based) |
| COCO annotation `category_id` | `class_id + 1` |
| COCO `extra_annotations`* | `class_id`, `class_name` (+ `source` rel path) |
| `provenance_<split>.jsonl`* | per-box `class_id`, `class_name`, `source` |
| `seg_report.json` | `summary.class_counts` (kept cut-outs per class); class on each skipped entry |
| `.seg_cache/<key>.json` | `report.class_id` / `report.class_name` |

\* `extra_annotations` requires `--extra-annotations`; the JSONL requires `--provenance`.

> **Cache note:** the `.seg_cache` is keyed by image *content* (not folder), so one image reused
> across two class folders shares a single cache entry — its stored `class_*` is the last writer's.
> This is cosmetic: the class for every generated label/annotation is resolved per task at run
> time, so outputs are always correct.
