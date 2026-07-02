# Deployment

MultiSeedGen runs as a local Python app **or** in Docker. **GPU is always optional** —
every path works on a plain CPU machine; GPU only ever makes segmentation faster. The
committed frontend bundle (`multiseedgen/web/static/`) means **no Node is needed to run
the app** — only to develop the UI.

The `Makefile` at the repo root is the easiest entry point; `make help` lists every
target. The pip extras behind these (`web` / `rembg` / `gpu` / `sam` / `dev`) are
documented in [installation.md](installation.md).

## Without Docker (local Python)

Needs **Python ≥ 3.10**. The GPU rows additionally need an NVIDIA **driver** on the host
(no Container Toolkit — that is Docker-only). Everything installs into `./.venv` (created
on demand) unless a venv/conda env is already active.

| Goal | Command | Adds on top of core | Segmentation |
|------|---------|---------------------|--------------|
| Lean CLI only | `make install` → `seedgen --config …` | nothing | classical |
| Lean web UI | `make install-web` → `multiseedgen-web` | FastAPI | classical |
| **Web app (recommended)** | `make run` | FastAPI + CPU rembg | rembg (CPU) |
| Generate headless | `make generate CONFIG=…` | FastAPI + CPU rembg | rembg (CPU) |
| **GPU — rembg** | `make run-gpu` | `onnxruntime-gpu` + CUDA 12 wheels | rembg (GPU) |
| **GPU — SAM** | `make install-sam-gpu` + `make download-sam` | CUDA torch + SAM | SAM (GPU) |
| SAM on CPU | `make install-sam` + `make download-sam` | CPU torch + SAM | SAM (CPU) |

"Lean" = smallest footprint, no learned-mask model download. `make install` is CLI-only;
`make install-web` adds the web UI but still uses the classical methods
(otsu/grabcut/threshold) — no model is downloaded until you opt into rembg or SAM.

## With Docker (no local Python needed)

All images serve the prebuilt SPA — no Node in any image. Datasets and the rembg model
cache persist on the host via mounted volumes, so models download once.

| Goal | Command | Needs |
|------|---------|-------|
| **CPU — runs anywhere** | `make docker-up` | Docker only |
| **GPU — rembg** | `make docker-gpu` | Docker + NVIDIA Container Toolkit |
| **GPU — SAM** | `make docker-sam-gpu` | Docker + NVIDIA Container Toolkit |
| SAM on CPU | `make docker-sam` | Docker only |

`make docker-up` builds `docker/Dockerfile.cpu` (no torch, no CUDA wheels) and serves the
UI on `http://localhost:8000` with **no NVIDIA driver or toolkit**. The GPU rows reserve
an NVIDIA device, so they require the [NVIDIA Container Toolkit](../docker/GPU_SETUP.md);
without it the run fails with "could not select device driver" — which is exactly why the
CPU image exists. The CPU and GPU rembg stacks both publish `:8000` (run one at a time);
SAM uses `:8001` (CPU) / `:8002` (GPU).

## GPU: two independent backends — pick one

"Running on the GPU" can mean **two different things** here. They are unrelated stacks;
choose by which segmentation backend you want, not by "do I have a GPU":

| | **rembg-gpu** | **SAM** |
|---|---------------|---------|
| What | U²-Net background removal | Segment Anything (Meta) |
| GPU via | `onnxruntime-gpu` (CUDA 12 pip wheels) | CUDA `torch` (cu126 wheels) |
| pip extra | `gpu` | `sam` |
| Local install | `make install-gpu` / `make run-gpu` | `make install-sam-gpu` + `make download-sam` |
| Docker | `make docker-gpu` (toolkit) | `make docker-sam-gpu` (toolkit) |
| Footprint | light (~hundreds of MB CUDA wheels) | heavy (torch ~2.5 GB) + checkpoint |
| Best for | fast, clean cut-outs on most seeds; the everyday GPU path | hard cases where rembg masks bleed; needs a checkpoint + more VRAM |
| Checkpoint | none (U²-Net auto-downloads, cached) | required — `make download-sam` (vit_b ~358 MB) |

You do **not** install both for one GPU run — `--segment rembg` uses rembg-gpu,
`--segment sam` uses SAM. The two never share an `onnxruntime` install (the rembg-gpu
targets purge the CPU `onnxruntime` first, since both ship the same import name and
keeping both makes the CUDA execution provider silently disappear). CUDA-pin details
(`onnxruntime-gpu` 1.26 vs 1.27, torch cu126 vs cu130) live in
[../docker/GPU_SETUP.md](../docker/GPU_SETUP.md).

## Path details

### Local — run the web app (`make run`)
Creates `./.venv` (if no venv/conda env is active), installs `web` + CPU `rembg`, and
launches the UI on `http://127.0.0.1:8000`. Override the bind address with
`make run HOST=0.0.0.0 PORT=9000`. On first segmentation, rembg downloads the U²-Net model
(~180 MB) into `U2NET_HOME` (default `~/.u2net`); cached afterward.

### Local — lean (`make install` / `make install-web`)
`make install` installs just the core (`numpy`, `opencv-python-headless`, `joblib`,
`pyyaml`, `tqdm`, `pydantic`) — no web UI, no model downloads; segmentation uses the
classical methods. Add the UI without a model via `make install-web`. Note that `make run`
installs `.[web,rembg]` (it adds CPU rembg), so to keep the web app lean launch it directly
with `multiseedgen-web` after `make install-web`, or use `seedgen --segment otsu …` for the CLI.

### Local — GPU rembg (`make run-gpu`)
`make run-gpu` (or `make install-gpu`) installs the `gpu` extra and prints the available
ONNX Runtime providers so you can confirm `CUDAExecutionProvider` is visible. Switching
between `make install-rembg` (CPU) and `make install-gpu` purges the other `onnxruntime*`
package first.

### Local — SAM, CPU or GPU (`make install-sam[-gpu]`)
`make install-sam` installs CPU torch (lean); `make install-sam-gpu` installs CUDA torch
(cu126) for GPU. Then `make download-sam` fetches the `vit_b` checkpoint (~358 MB) into
`models/` if absent. Run it via the CLI or point the web UI at the checkpoint:

```bash
seedgen --config configs/example.yaml \
  --segment sam --sam-checkpoint models/sam_vit_b_01ec64.pth --sam-model-type vit_b
```

SAM auto-uses CUDA when CUDA torch + a GPU are present, else CPU. Model sizes and prompt
modes are in [AUGMENTATION.md](AUGMENTATION.md).

### Local — develop (`make dev`)
Installs dev tooling + frontend node deps, then runs the FastAPI backend (`:8000`,
`--reload`) and the Vite dev server (`:5173`) together; Vite proxies `/api` and `/ws` to
the backend. Ctrl-C stops both. `make dev-backend` / `make dev-frontend` run one side
alone. After any UI change, `make frontend-build` regenerates the committed
`multiseedgen/web/static/` bundle (commit it alongside your source change).

### Docker — CPU (`make docker-up`)
For a one-off batch run instead of the web UI:
```bash
docker compose -f docker/compose.yaml run --rm multiseedgen \
  python -m multiseedgen --sources /data/seeds --out /data/out --num-images 2000
```

### Docker — GPU rembg / SAM
`make docker-gpu` (rembg, `:8000`), `make docker-sam` (CPU SAM, `:8001`),
`make docker-sam-gpu` (GPU SAM, `:8002`). The GPU services need the NVIDIA Container
Toolkit; the SAM services mount the repo `models/` so a downloaded checkpoint is visible
in the container. See [../docker/GPU_SETUP.md](../docker/GPU_SETUP.md).

## Volumes, caches & ports

- **`docker/_out` → `/data/out`** — generated datasets persist on the host.
- **`docker/_models` → `/models`** — `U2NET_HOME=/models/u2net`, so the rembg model
  survives container rebuilds.
- **`seeds/` → `/data/seeds` (read-only)** — your source single-seed images.
- **`MULTISEEDGEN_DATA_ROOT=/data`** — the web UI's dataset browser is sandboxed here.
- **Ports:** CPU and GPU rembg both publish `:8000`; SAM uses `:8001` / `:8002`. Run one
  `:8000` stack at a time.
