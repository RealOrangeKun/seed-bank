# Installation

MultiSeedGen is a regular Python package (`pyproject.toml`, setuptools). It needs
**Python ≥ 3.10**. Only `numpy` and `opencv-python-headless` are hard imports of the
core pipeline; everything else is an optional extra.

> In a hurry? The `Makefile` wraps all of this: `make install` (lean core), `make run`
> (web + CPU rembg), `make install-dev`, `make install-gpu`, … See
> [deployment.md](deployment.md) for the full set of run paths (local + Docker, GPU
> optional). This page documents the underlying `pip` commands.

## Core install (CLI + classical segmentation)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

This pulls the core runtime (`numpy`, `opencv-python-headless`, `joblib`, `pyyaml`,
`tqdm`, `pydantic`) and installs two console scripts:

| Script | Equivalent | Purpose |
|--------|------------|---------|
| `seedgen` | `python -m multiseedgen` | run a generation |
| `multiseedgen-web` | `python -m multiseedgen.web` | launch the web UI |

> `python seedgen.py …` still works — it is a backward-compatible shim that re-exports
> the package API.

## Optional extras

Install only what you need (extras are additive, e.g. `pip install -e ".[web,rembg]"`):

| Extra | `pip install -e ".[…]"` | Adds |
|-------|--------------------------|------|
| `web` | `web` | FastAPI + uvicorn + websockets (the web UI) |
| `rembg` | `rembg` | CPU `rembg` (U²-Net) for the learned-mask fallback |
| `gpu` | `gpu` | GPU `rembg` via `onnxruntime-gpu==1.26.0` + CUDA 12 runtime wheels |
| `sam` | `sam` | Segment Anything backend (`torch`, `torchvision`, `segment-anything`) |
| `dev` | `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy` |

GPU notes (CUDA pins, the `onnxruntime-gpu` 1.26 vs 1.27 choice, SAM checkpoints) live in
[`../docker/GPU_SETUP.md`](../docker/GPU_SETUP.md). The SAM backend additionally needs a
downloaded checkpoint — see [AUGMENTATION.md](AUGMENTATION.md).

## Verify

```bash
pip install -e ".[dev]"
pytest -m "not gpu and not golden"   # fast + integration suite (skips GPU + host-pinned golden tests)
```

A green run confirms the package imports, the deterministic pipeline passes its invariants
(backend/worker determinism, config/schema/seg-cache contracts), and the web layer responds. The
host-pinned `golden` byte tests are skipped here — run them on your own host too; see
[contributing.md](contributing.md) for the full developer workflow.
