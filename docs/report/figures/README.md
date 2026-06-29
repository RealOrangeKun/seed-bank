# Report figures

Everything the LaTeX report pulls in via `\figslot{...}` lives here. The macro
(defined in `../main.tex`) renders the image if the file exists, otherwise a
labelled placeholder box — so `make doc-pdf` always compiles. To finalise a
figure, drop a file with the **exact name** below into this folder and rebuild.

## 1. Diagrams (auto-generated — do not hand-edit)

Produced by `scripts/render_diagrams.sh` from the Mermaid sources in
`docs/diagrams/`. Run it once before the final build:

```bash
bash scripts/render_diagrams.sh        # writes the *.pdf files below
```

| File | Source | Used in |
|---|---|---|
| `01-system-context.pdf` | `diagrams/01-system-context.md` | 4.1 Architecture |
| `02-containers.pdf` | `diagrams/02-containers.md` | 4.1 Architecture |
| `03-api-components.pdf` | `diagrams/03-api-components.md` | 4.1 Architecture |
| `04-worker-components.pdf` | `diagrams/04-worker-components.md` | 4.1 / 5.2 |
| `05-db-erd.pdf` | `diagrams/05-db-erd.md` | 4.4 ERD |
| `06-analyze-sequence.pdf` | `diagrams/06-analyze-sequence.md` | 4.3 Sequence |
| `07-batch-state-machine.pdf` | `diagrams/07-batch-state-machine.md` | 5.2 State machine |
| `08-auth-sequence.pdf` | `diagrams/08-auth-sequence.md` | 4.3 / 4.6 Security |
| `09-ml-platform.pdf` | `diagrams/09-ml-platform.md` | 4.x / 5.2 ML platform |
| `10-deployment.pdf` | `diagrams/10-deployment.md` | 5.1 Deployment |
| `11-gantt.pdf` | `diagrams/11-gantt.mmd` | 1.7 Timeline |
| `12-usecase.pdf` | `diagrams/12-usecase.mmd` | 3.4 Use cases |
| `13-class.pdf` | `diagrams/13-class.mmd` | 4.2 Class diagram |
| `14-multiseedgen-pipeline.pdf` | `diagrams/14-multiseedgen-pipeline.mmd` | 4.x / 5.2 MultiSeedGen |

## 2. Screenshots (TEAM TO PROVIDE)

Capture these from the running apps and save with the exact names. Until then
the report shows a placeholder box naming the missing file.

### Web app
| File | What to capture |
|---|---|
| `web-login.png` | Sign-in screen (with theme + language toggles) |
| `web-dashboard.png` | Dashboard: KPI strip + recent scans |
| `web-analyze.png` | "Check seeds" upload page |
| `web-batch-detail.png` | Batch detail: AI insights + bounding-box overlay |
| `web-analytics.png` | Analytics page (trends / quality by seed type) |
| `web-compare.png` | Compare scans side by side |
| `web-models.png` | ML model registry (admin/developer view) |
| `web-shared-report.png` | Public read-only shared report |

### Mobile app
| File | What to capture |
|---|---|
| `mobile-camera.png` | Realtime camera capture with framing guide |
| `mobile-result.png` | Result screen (good-rate, counts) |
| `mobile-history.png` | Scan history list |

### MultiSeedGen
| File | What to capture |
|---|---|
| `msg-ui.png` | Config + run web UI |
| `msg-seg-tuner.png` | Segmentation tuner (kept/skipped gallery) |
| `msg-sample-scene.png` | One generated multi-seed scene with boxes |
| `msg-output-montage.png` | QA montage of generated annotated images |

### Output samples
| File | What to capture |
|---|---|
| `sample-detection-output.png` | Annotated analyze output (boxes + good/bad labels) |
