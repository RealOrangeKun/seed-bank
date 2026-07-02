# MultiSeedGen documentation

Start at the [project README](../README.md) for the one-paragraph overview and quick
start. This folder holds the full documentation set.

## Guides

| Doc | What it covers |
|-----|----------------|
| [installation.md](installation.md) | Install, the optional extras (`web`/`rembg`/`gpu`/`sam`/`dev`), and how to verify. |
| [deployment.md](deployment.md) | `make` targets, the lean CPU Docker image/compose, and the GPU/SAM run paths. |
| [usage.md](usage.md) | Running the CLI and the web UI, config files, and the helper scripts. |
| [configuration tuning](RECOMMENDED_SETTINGS.md) | Recommended settings and per-dataset tuning guidance. |
| [augmentation & segmentation](AUGMENTATION.md) | Mapping data-quality problems to options; segmentation backends; the optional SAM integration. |
| [architecture.md](architecture.md) | Package layout, data flow, the determinism contract, fork-safety, error/logging model. |
| [api.md](api.md) | The web UI's HTTP/WS API — routes, request/response shapes, and the path sandbox. |
| [contributing.md](contributing.md) | Dev setup, the regression gate, test conventions, regenerating goldens. |
| [../docker/GPU_SETUP.md](../docker/GPU_SETUP.md) | GPU / Docker setup (CUDA pins, `onnxruntime-gpu`, GPU SAM). |

## Where things live

- **Configuration model & validation** → [architecture.md](architecture.md#the-single-source-of-truth-config)
- **Why output is byte-reproducible** → [architecture.md](architecture.md#determinism-contract)
- **Adding a config option / writing tests** → [contributing.md](contributing.md)
