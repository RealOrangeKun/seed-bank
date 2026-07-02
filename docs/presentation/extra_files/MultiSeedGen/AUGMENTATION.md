# Segmentation, Augmentation & Data-Quality Guide

This guide maps the known dataset problems to the MultiSeedGen options that solve
them, compares the segmentation backends, and documents the SAM integration. A
fully-commented config that exercises every option lives at
[`configs/example.yaml`](../configs/example.yaml).

## Problem → solution map

| Problem | Option(s) | Notes |
|---|---|---|
| Invalid / out-of-bounds bboxes | `min_visibility`, `min_visible_occluded`, `min_box_px` | boxes are clipped to the canvas and degenerate/empty masks are dropped at export. |
| Dataset imbalance (classes) | `sampling.class_balanced`, `sampling.class_probs` | sample a class first (uniform or weighted), then a seed within it — counters uneven source counts. |
| Overfitting / poor generalization | `augmentation.rotation`, `scale_min/max`, `flip`, `augmentation.jitter_*`, `augmentation.shear`, `augmentation.gamma`, `blur_max_sigma`, `motion_blur_max`, `noise_sigma`, `poisson_noise` | per-seed geometric + photometric variety plus camera degradation. |
| Small/large seed-scale variability | `scale_min`, `scale_max` | per-seed random scale before placement. |
| Overlapping seeds / clutter | `overlap_mode: limit`, `max_iou` | rejects placements whose box IoU exceeds the threshold (8 tries/seed). |
| Light / background shift | `backgrounds`, `textures`, `bg_from_sources`, `augmentation.gamma`, `vignette` | solid/gradient/noise/texture/real backgrounds + random gamma + vignette. |
| Mixed-seed false positives | `class_balanced` + many classes per scene; `neg_frac` | scenes mix all classes; background-only negatives suppress texture false positives. |
| **Data leakage (train↔val)** | `split.val_seed_holdout`, `split.val_seeds` | **a source seed reserved for val never appears in any train image** (per-class stratified, deterministic). |
| Binary-classification limitation | `export.multilabel_csv` | per-image multi-label CSV (per-class counts) for downstream classifier training. |
| Provenance / traceability | `export.extra_annotations`, `provenance` | COCO annotations carry source file, scale, rotation, shear, perspective and seg method. |

> Geometric augmentations that would move a label box at the scene level (scene-wide
> shear / perspective) are intentionally avoided to keep annotations exact. The per-seed
> equivalents — shear (`augmentation.shear`) and perspective (`augmentation.perspective` /
> `--perspective`) — are instead applied to the cut-out *before* placement, so the box is
> recomputed from the warped alpha and stays correct. `--perspective` takes the max corner
> jitter as a fraction of the cut-out, **range `0`–`0.3`** (it is a fraction, not degrees/pixels
> — an out-of-range value is rejected to avoid a runaway warp buffer); `0.1` is a sane value.
> Leave it at `0` to disable.

## Segmentation methods

All methods are selected with `segmentation.method` (or `--segment`) and share the
same cut-out → polygon/COCO export path. Per-method parameters live under
`segmentation.<method>` (see [`configs/example.yaml`](../configs/example.yaml)).

| Method | Backend | Best for | Key params | Deps |
|---|---|---|---|---|
| `auto` (default) | colour/brightness cascade + confidence gate + rembg fallback | most single-seed photos | `bg_tolerance`, `conf_thresh`, `strip_shadow` | none |
| `threshold` | border-colour distance | clean, uniform backgrounds | `bg_tolerance`, `morph_kernel` | none |
| `otsu` | grayscale Otsu | high-contrast seed/background | `otsu.blur_kernel`, `otsu.threshold_adjustment` | none |
| `grabcut` | OpenCV GrabCut (rect init) | textured backgrounds | `grabcut.iterations`, `grabcut.rect_margin`, `grabcut.min_object_area` | none |
| `rembg` | U²-Net (ONNX, GPU-capable) | hard/feathered edges | `u2net.device`, `rembg_fallback` | `rembg`, `onnxruntime` |
| `sam` | Segment Anything | prompt-driven / difficult cases | `sam.*` (below) | `torch`, `segment-anything` + checkpoint |

A per-source override manifest (`--segment-map`, JSON/CSV of glob → method) lets you
mix methods within one job.

The confidence skip-gate (`seg_conf_thresh`) drops cut-outs whose mask scores below the
threshold. It always runs for `auto` (default `0.55`) and is **opt-in for the explicit
methods**: there it defaults to `0` (off), so an un-tuned `threshold`/`otsu`/`grabcut`/`rembg`/`sam`
run keeps every mask — set `seg_conf_thresh > 0` (per-method in the tuner, or in config/CLI) to
also gate those. The automatic **rembg fallback stays `auto`-only** (it would silently swap the
method you explicitly chose).

**Device-adaptive rembg.** With `rembg_provider: auto` (the default) the U²-Net session probes the
host at load time — it runs on CUDA when a GPU + `onnxruntime-gpu` are present, else CPU — and if a
worker hits a CUDA out-of-memory mid-run it retries that cut-out on CPU instead of crashing the job.
Pin `rembg_provider: cuda`/`cpu` for a deterministic device (GPU and CPU masks can differ by ~0.01%,
so the resolved device is folded into the segmentation cache key).

## SAM (Segment Anything) integration

SAM is **import-guarded**: nothing is required to install or download unless you
opt in. With no checkpoint/deps, `--segment sam` cleanly skips/falls back and every
other method keeps working.

### Sizes — decide before downloading

| Component | Download | VRAM (approx) | Note |
|---|---|---|---|
| `sam_vit_h_4b8939.pth` (`vit_h`) | **~2.4 GB** | ~7–8 GB | best quality; won't fit a 6 GB GPU alongside rembg |
| `sam_vit_l_0b3195.pth` (`vit_l`) | **~1.2 GB** | ~5–6 GB | middle ground |
| `sam_vit_b_01ec64.pth` (`vit_b`) | **~358 MB** | ~4 GB | **recommended** — fits a 6 GB GPU, runs on CPU |
| `segment-anything` (pip) | tiny | — | pure Python |
| `torch` + `torchvision` | ~2.3–3 GB (CUDA) / ~190 MB (CPU) | — | the real install cost |

The seed crops segmented here are small, so `vit_b` is the recommended default.

### Enabling SAM

```bash
pip install segment-anything torch torchvision          # torch is the large dep
# download ONE checkpoint (vit_b shown; ~358 MB):
mkdir -p models && curl -L -o models/sam_vit_b_01ec64.pth \
  https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth

python seedgen.py --config configs/example.yaml \
  --segment sam --sam-checkpoint models/sam_vit_b_01ec64.pth --sam-model-type vit_b
```

### Running SAM in Docker (opt-in)

To avoid forcing torch on everyone, SAM has its own image
([`docker/Dockerfile.sam`](../docker/Dockerfile.sam), `python:3.12-slim`) behind a
compose **profile** — the default image stays light. After downloading a checkpoint
to `models/`:

```bash
docker compose -f docker/compose.gpu.yaml --profile sam run --rm multiseedgen-sam \
  python -m multiseedgen --sources /data/seeds --out /data/out --num-images 2000 \
  --segment sam --sam-checkpoint models/sam_vit_b_01ec64.pth --sam-model-type vit_b
```

The repo `models/` is mounted at `/app/models`, so the relative `--sam-checkpoint`
path resolves inside the container. torch is CPU-only by default (works with no
NVIDIA toolkit). For **GPU SAM**, use the `sam-gpu` profile instead
(`--profile sam-gpu … multiseedgen-sam-gpu`, CUDA torch, port 8002) — it requires
the NVIDIA Container Toolkit. See [`docker/GPU_SETUP.md`](../docker/GPU_SETUP.md)
"Path 3" for both.

### Prompt modes (`sam.prompt_type`)
- `automatic` (default): `SamAutomaticMaskGenerator`; the central, large, non-frame-filling
  mask is selected for the single-seed crop. Tune `points_per_side`, `pred_iou_thresh`,
  `stability_score_thresh`.
- `box`: a near-full-frame box prompt (like GrabCut's init rect) — fast and deterministic.
- `points`: a single foreground click at the crop centre.

SAM holds a full model per worker process, so segmentation is capped to `--gpu-seg-jobs`
workers to bound memory (default `0` = auto-scale the count to free VRAM; set a positive
value to cap manually). Cut-outs are content-hash cached, so a dataset stays reproducible
even though GPU inference itself is not bit-exact run-to-run.
