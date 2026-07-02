# Seed Bank — Final Presentation Content Guide (v3)

> **Format**: Content guide for building slides in PowerPoint, Canva, or any presentation tool
> **Slides**: 32 (presenter can skip slides to manage time — all content preserved)
> **All visual assets are real** — no mockups needed

---

## Design System (Apply Globally)

| Element | Specification |
|---|---|
| **Primary color** | Deep leaf green `#2D5016` |
| **Accent color** | Warm amber `#F59E0B` |
| **Light background** | Warm off-white `#FEFDF8` |
| **Dark background** | Soil-night `#1A1A1A` — use for technical and architecture slides |
| **Heading font** | Inter Bold (700) or Montserrat Bold |
| **Body font** | Inter Regular (400) |
| **Icon style** | Consistent line icons throughout (Lucide, Phosphor, or Flaticon line pack) |
| **Chart palette** | Green/amber only. Never default software colors |
| **Logo** | Seed Bank watermark bottom-left on every slide |
| **Slide numbers** | Bottom-right on every slide |
| **Transitions** | Subtle fade or rise only. No spinning, bouncing, or flashy effects |

### Visual Rules
- Every slide must have **at least one visual element** (diagram, chart, image, screenshot, icon grid, or heatmap)
- Maximum **25–30 words** of body text per slide. Headlines and labels are excluded from this count
- No bullet lists longer than **4 items**. Prefer icon+caption pairs over plain bullets
- **No paragraphs — ever**. If something needs more than 2 short lines, convert it to a visual
- Metrics should be shown as **large highlighted numbers**, not dense table rows
- Architecture diagrams should be **conceptual**, not implementation-level

---

## Available Visual Assets

| # | Asset | File | What It Shows |
|---|---|---|---|
| 1 | Dashboard | `screenshots/Dashboard.png` | Web dashboard: KPI strip (3 scans, 31 images, 100% success), quick actions, recent scans |
| 2 | Mobile View | `screenshots/MobileView.png` | Mobile app home: "Check seeds in seconds" CTA, stats strip, scan history cards |
| 3 | Batch Detail | `screenshots/web-batch-detail.png` | AI Insights panel: 100% good rate donut, 72 seeds detected, confidence histogram, bounding-box image |
| 4 | YOLO Real-time | `screenshots/YOLO-realtime.png` | 876 seeds detected live via YOLO real-time video with green bounding boxes on conveyor-like scene |
| 5 | MultiSeedGen Output | `screenshots/MultiseedGen-seeds_annotatedWithBB.jpg` | Synthetic composite: 15+ species (pumpkin, cumin, soybean, maize, chia, rice…) auto-annotated with red bounding boxes and class labels on realistic tray background |
| 6 | Segmentation Tuner | `screenshots/seg-tuner.png` | Web UI: kept/skipped seed gallery with confidence scores, method labels (rembg), checkerboard transparency |
| 7 | Models Management | `screenshots/Models_managment.png` | ML platform models page |
| 8 | Heatmap: Damage | `heatmaps/damage.png` | Input maize seed (dark lesion) + 7 Grad-CAM maps — Damage class = 1.00, hot focus on lesion area |
| 9 | Heatmap: Healthy | `heatmaps/healthy.png` | Input maize seed (clean) + 7 Grad-CAM maps — Healthy class = 1.00, uniform activation across surface |
| 10 | Heatmap: Shriveled | `heatmaps/shriveled.png` | Input maize seed (deformed) + 7 Grad-CAM maps — Shriveled class = 1.00, focus on wrinkled region |
| 11 | Heatmap: Weeveled | `heatmaps/weeveled.png` | Input maize seed (bore-hole) + 7 Grad-CAM maps — Weeveled class = 1.00, concentrated hotspot on hole |

---

## Slide-by-Slide Content Guide

---

### ═══ ACT I: THE HOOK & PROBLEM (8 slides) ═══

---

#### SLIDE 1 — Title Slide

**Layout**: Centered, clean, professional

**Content**:
- Title: **"Seed Bank"** (large, stylized)
- Subtitle: **"AI-Powered Seed Quality Intelligence"**
- Institution: Faculty of Computers and Artificial Intelligence, Cairo University
- Supervisors row: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- Team in two labeled columns:
  - **AI**: Omar Ez-Eldin Abdullah, Yussuf Ahmed Awad
  - **IS**: Ali Abdelrahman, Mohamed Amr, Youssef Tarek Ali

**Visual direction**: Agricultural/tech fusion background — leaf textures blending into neural-network node patterns. Deep green tones. Premium, modern feel.

---

#### SLIDE 2 — "A Seed Bank in Computer Science?"

**Layout**: Full-width split visual

**Content**:
- Headline: **"A Seed Bank… in Computer Science?"**
- LEFT half: Image of a traditional seed vault or agricultural seed storage
- RIGHT half: AI/code visualization — neural network diagram, code snippets, or data flow
- Large **"?"** connecting both halves in the center

**Visual direction**: Zero explanatory text beyond the headline. The visual split creates curiosity. Let the audience sit with the question for a moment.

---

#### SLIDE 3 — The 30-Second Pitch

**Layout**: Horizontal flow + screenshots below

**Content**:
- Icon flow across the top:
  - 📷 **"Photograph seeds"** → 🤖 **"AI analyzes"** → 📊 **"Quality report"**
- Below the flow: embed **Dashboard.png** (small, left) and **MobileView.png** (small, right) showing the actual product
- Single sentence at bottom: *"A platform for farmers and QA labs to instantly grade seed quality using computer vision"*

**Visual direction**: The flow should be clean with connecting arrows. The screenshots give concrete proof this is a real, working product.

---

#### SLIDE 4 — Who Is This For?

**Layout**: Two cards side-by-side

**Content**:
- **LEFT CARD — "The Farmer"**
  - Farmer icon/illustration
  - ⏱️ Slow manual counting
  - 🎭 Subjective, inconsistent results
  - 📵 No affordable digital tools
- **RIGHT CARD — "The QA Laboratory"**
  - Lab technician icon/illustration
  - 📊 Needs high throughput
  - 🎯 Needs objective, repeatable results
  - 💰 Industrial machines cost too much

**Visual direction**: Card-based layout with subtle shadows. Each pain point is an icon + short caption pair, not a sentence.

---

#### SLIDE 5 — The Problem: Manual Grading

**Layout**: Large central image with floating badges

**Content**:
- Central image: photo or illustration of someone manually sorting seeds on a tray
- 4 floating problem badges arranged around the image:
  - ⏱️ **"Slow"** — fatigue after a few hundred seeds
  - 🎭 **"Subjective"** — two graders disagree on the same tray
  - ❌ **"Inconsistent"** — same grader drifts over a long shift
  - 💰 **"Can't scale"** — not viable for high-throughput demands

**Visual direction**: The image is the anchor. Badges float around it like callouts. No paragraph text.

---

#### SLIDE 6 — The Technology Gap

**Layout**: Horizontal spectrum/scale diagram

**Content**:
- LEFT end: **"Industrial Optical Sorters"** — large machine image or icon, price tag **"$$$$$"**, "Custom hardware, specialist maintenance"
- CENTER: Big empty gap with a glowing indicator: **"Nothing affordable here"** → **"Seed Bank fills this gap"**
- RIGHT end: **"Manual Counting"** — hand icon, "Subjective, slow, small samples"

**Visual direction**: This is a positioning diagram. The gap in the middle IS the argument. No paragraphs — the visual scale tells the story.

---

#### SLIDE 7 — Why Seeds Are Hard for AI

**Layout**: 2×2 image grid

**Content**:
- Top-left: **"Overlap & Clutter"** — image of densely packed, touching seeds
- Top-right: **"Lighting Variation"** — same seeds looking different under different light
- Bottom-left: **"Subtle Defects"** — hairline crack or tiny discoloration barely visible
- Bottom-right: **"Natural ≈ Damaged"** — healthy seed next to defective one that looks nearly identical
- Title: *"Seeds aren't manufactured parts — they're organic and irregular"*

**Visual direction**: Real seed photos if available. Each quadrant has a short 2–3 word caption. The grid IS the explanation.

---

#### SLIDE 8 — The Data Problem

**Layout**: Three problem cards in a horizontal row

**Content**:
1. 📊 **"Volume Gap"** — *Need ~100K images per seed type; best public datasets have <20K*
2. 🏷️ **"Annotation Mismatch"** — *Detection sets have boxes but no quality labels. Classification sets have labels but no boxes. No dataset has both.*
3. 🔬 **"Lab ≠ Real World"** — *Models trained on sterile lab images fail when deployed against phone photos in sunlight*

**Visual direction**: Three equal-width cards with icons at top. Each card is one problem. This slide sets up the MultiSeedGen solution that follows immediately.

---

### ═══ ACT II: MULTISEEDGEN — OUR DATA FACTORY (3 slides) ═══

> These slides come right after the Data Problem because MultiSeedGen is the direct answer to it. The narrative: "Here's the data problem → Here's how we solved it → Now let's see the AI pipeline that uses this data."

---

#### SLIDE 9 — MultiSeedGen: Building Our Own Training Data

**Layout**: Horizontal pipeline diagram + output screenshot

**Content**:
- Pipeline flow (left to right):
  **Single-seed photos** → [**SEGMENT**: cut out the seed] → **Cut-out pool** → [**COMPOSITE**: place on backgrounds with collision physics] → **Dense multi-seed scenes** → [**DEGRADE**: camera simulation] → [**EXPORT**: YOLO/COCO format with auto-labels]
- Below or right side: embed **MultiseedGen-seeds_annotatedWithBB.jpg** — shows the actual output with 15+ species auto-labeled with bounding boxes on a realistic tray background
- Key callout: *"Labels come for free — the engine placed each seed, so it knows exactly where every one is"*
- Subtitle stats: *"6 segmentation backends · 15+ augmentation parameters · byte-reproducible output · supports ~20 seed species"*

**Visual direction**: The pipeline should flow cleanly left-to-right with arrows. The screenshot is proof that the output looks realistic and is properly labeled.

---

#### SLIDE 10 — Segmentation: 6 Ways to Cut a Seed

**Layout**: Left = tiered method diagram or card grid. Right = seg-tuner screenshot

**Content**:
- **Left half — "6 Segmentation Backends"** (ordered by complexity):
  1. **auto** (default) — classical cascade + confidence gate + rembg fallback. Best general-purpose.
  2. **threshold** — border-colour distance. Best for clean, uniform backgrounds.
  3. **otsu** — grayscale Otsu thresholding. Best for high-contrast seed/background.
  4. **grabcut** — OpenCV GrabCut (rectangle init). Best for textured backgrounds.
  5. **rembg (U²-Net)** — learned ONNX model, GPU-capable. Best for hard edges, removes cast shadows and watermarks.
  6. **SAM (Segment Anything)** — prompt-driven: automatic, box, or point modes. Best for difficult cases. Optional (import-guarded).
- **Right half**: embed **seg-tuner.png** — shows the web UI with kept/skipped gallery, confidence scores, method labels
- Key detail: *"Content-hash cached — first segmentation pass is the only cost; every later run is near-instant"*
- Small note: *"Per-source override via segment-map: different methods for different seed types in one run"*

**Visual direction**: The 6 methods should feel like a progression from simple → advanced. The seg-tuner screenshot proves this is a real, usable tool with quality controls.

---

#### SLIDE 11 — Augmentation & Domain Bridging

**Layout**: Three columns + before/after at bottom

**Content**:
- **Title**: *"Bridging the gap between synthetic and real"*
- **Column 1 — "Geometric Transforms"**:
  - 🔄 Scale jittering (per-seed random scale)
  - ↻ Rotation + flip
  - ◇ Shear deformation
  - 📐 Perspective warping (per-seed; bounding box recomputed from warped alpha)
  - 💥 Collision-aware placement (IoU rejection threshold, 8 retries per seed)
- **Column 2 — "Photometric Degradation"** (camera simulation):
  - 📷 Sensor noise (Gaussian + Poisson)
  - 🖼️ JPEG compression artifacts
  - 🌫️ Motion blur + defocus blur
  - 🔆 Gamma variation
  - 🔲 Vignette effect
  - 🌗 Directional drop shadows with natural fade
- **Column 3 — "Domain Matching"** (the critical difference):
  - 🏞️ **bg_from_sources** — composites seeds onto REAL inpainted tray backgrounds extracted from source photos. *This is the single most impactful quality lever.*
  - ⬛ **neg_frac** — 10% background-only negative images to suppress false positives on tray textures
  - 🔒 **val_seed_holdout** — a source seed reserved for validation NEVER appears in any training image. Prevents data leakage.
  - ♻️ **Determinism** — fixed (config, seed) → byte-identical dataset regardless of worker count or parallel backend
- **Bottom**: Before/after comparison — sterile synthetic scene (solid background, no noise) vs. domain-matched scene (real tray background + degradation applied + shadows)

**Visual direction**: Three equal columns with icons. The domain-matching column should be visually emphasized (amber accent border?) because it's the most important. The before/after at bottom is the visual proof.

---

### ═══ ACT III: THE AI PIPELINE (4 slides) ═══

---

#### SLIDE 12 — Two-Stage Pipeline: Divide & Conquer

**Layout**: Horizontal pipeline diagram

**Content**:
- Pipeline flow:
  📷 **Input Image** → [**STAGE 1: Detection** — *"Where are the seeds?"*] → **Bounding boxes + class** → [**STAGE 2: Classification** — *"What defects does each seed have?"*] → 📊 **Quality Report**
- Stage 1 color: blue tones
- Stage 2 color: green tones
- Below the pipeline: *"Decoupling lets us optimize, version, and swap each stage independently"*
- Small data fan-out diagram: **1 image → N detections → N quality labels**

**Visual direction**: This is the conceptual overview before diving into each stage. Clean, simple, color-coded.

---

#### SLIDE 13 — Stage 1: Detection (Finding Every Seed)

**Layout**: Left = before/after image. Right = architecture diagram

**Content**:
- **Left half**: Before/after — raw seed photo → same photo with bounding boxes drawn around every seed (crop from **web-batch-detail.png** or **YOLO-realtime.png**)
- **Right half**: Simplified Faster R-CNN diagram:
  Image → **ResNet-50 Backbone** → **FPN** (multi-scale feature pyramid) → **Region Proposal Network** → 3 output classes: `[background, coffee, maize]`
- **Metric badges** (large, prominent):
  - Best Faster R-CNN: **mAP@50: 0.98**
  - YOLOv8 real-time: **mAP@50: 0.975, ~30ms**
- Small note: *"Also tested: Swin Transformer (overfitted), PANet variants — see results slides"*

**Visual direction**: The before/after is visually compelling. The architecture diagram should be a clean flow, not a research-paper-style dense diagram.

---

#### SLIDE 14 — Stage 2: Classification (7-Class Defect Grading)

**Layout**: Left = input flow. Center = architecture. Right = output

**Content**:
- **Left**: Visual of a cropped individual seed being fed into the classifier (arrow from detection stage)
- **Center**: EfficientNet-B2 architecture diagram with two key callouts:
  - **CBAM** (Convolutional Block Attention Module) — channel + spatial attention. *"Forces the model to focus on defect regions, not background"*
  - **Hybrid Pooling** (GAP + GMP → 1024 features) — *"Captures both general texture patterns AND sharp anomalies like cracks"*
- **Right**: Multi-label output shown as 7 colored badges:
  ✅ Broken · ✅ Damage · ✅ Fungus · ✅ Healthy · ✅ Immature · ✅ Shriveled · ✅ Weeveled
- **Metric badge**: **Maize: 0.974 Macro-F1**
- Note: *"One classifier per crop type — detections are grouped by seed type before classification"*

**Visual direction**: This should feel like a pipeline within a pipeline. The CBAM and hybrid pooling callouts are the "secret sauce" — make them visually prominent.

---

#### SLIDE 15 — The Model Sees What Matters (Grad-CAM Heatmaps)

**Layout**: Full-width, dark background. THIS IS A SHOW-STOPPER SLIDE.

**Content**:
- Title: *"The model learns different attention patterns for each defect class"*
- Display all **4 heatmap images** in a 2×2 grid or horizontal strip:
  - **Damage** (damage.png): Model focuses on dark lesion area → Damage class scores 1.00
  - **Healthy** (healthy.png): Uniform activation across clean seed surface → Healthy class scores 1.00
  - **Shriveled** (shriveled.png): Focus on wrinkled deformation area → Shriveled class scores 1.00
  - **Weeveled** (weeveled.png): Concentrated hotspot on bore-hole → Weeveled class scores 1.00
- Each heatmap image shows: **Input Image** + **7 class activation maps** side by side (Broken, Damage, Fungus, Healthy, Immature, Shriveled, Weeveled) with the correct class highlighted at 1.00
- Small legend: Red/yellow = high activation, Blue/purple = low activation

**Visual direction**: Dark background (`#1A1A1A`) makes the heatmap colors pop. Give this slide maximum visual real estate — it is the most visually compelling proof that the AI attention mechanism works. Minimal text; the heatmaps ARE the evidence.

---

### ═══ ACT IV: RESULTS & EVIDENCE (7 slides) ═══

---

#### SLIDE 16 — Detection Experiments: The Journey

**Layout**: Timeline or progression chart

**Content**:
- 5 experiments shown as a visual journey/timeline:
  1. **Swin + FPN** → mAP@50: 0.9487 — ⚠️ "Overfitted — too powerful for small dataset"
  2. **+ CIoU loss** → mAP@50: 0.9805 — "Better box regression, still overfitting"
  3. **ResNet-50 + Faster R-CNN** → mAP@50: 0.8697 — ✅ "Lower metrics but better on real data"
  4. **+ PANet** → mAP@50: 0.8524 — "Improved localization precision at stricter IoU"
  5. **YOLOv8** → mAP@50: 0.975 — ⭐ "Fast + accurate, best all-round"
- Key insight callout: *"Lower test metrics ≠ worse model. ResNet-50 generalized better on real photos."*

**Visual direction**: A stepping-stone or timeline visual. Each experiment is a card or node. Color-code: red/amber for overfitting warnings, green for generalizing well.

---

#### SLIDE 17 — Classification: Why Data Quality > Model Architecture

**Layout**: Two-column comparison + training chart

**Content**:
- **LEFT column — "Soybean (Lab Data)"**:
  - Sterile lab backgrounds, pre-segmented bounding boxes
  - 0.9936 Macro-F1 — ❌ *"Artificially high — severe overfitting"*
  - *"Memorized clean pixel distributions, fails on real-world backgrounds"*
- **RIGHT column — "Maize (Real-World Data)"**:
  - Natural sunlight, phone captures, environmental noise
  - 0.9740 Macro-F1 — ✅ *"Generalizes to real-world deployment"*
  - *"Organic noise in training data forced the model to learn robust features"*
- Below: Training convergence chart for maize showing epoch progression:
  - Epoch 1: F1 0.808 → Epoch 3: 0.925 → Epoch 5: 0.964 → **Epoch 7: 0.974**
- Bottom callout: *"The model that scored lower on the test set performed better in the real world"*

**Visual direction**: Make the contrast stark. Red/danger styling on the soybean side, green/success on the maize side.

---

#### SLIDE 18 — Speed vs. Precision: Two Deployment Modes

**Layout**: Two large comparison cards + screenshot

**Content**:
- **LEFT card — "Precision Mode"**
  - Architecture: Faster R-CNN + EfficientNet-B2
  - Latency: **~230ms** total
  - Throughput: **~4.3 FPS**
  - Output: 7-class multi-label defect analysis
  - Best for: QA labs, detailed inspection reports
- **RIGHT card — "Speed Mode"**
  - Architecture: YOLOv8 single-stage
  - Latency: **~80ms** total
  - Throughput: **~12.5 FPS**
  - Output: Detection + classification in one pass
  - Best for: Conveyor belts, real-time sorting lines
- Below/side: embed **YOLO-realtime.png** showing 876 seeds detected in real-time video with "Both run on commodity hardware (RTX 3060)"

**Visual direction**: Card-based. Speed values should be large, bold numbers. The screenshot proves this works at scale.

---

#### SLIDE 19 — Competitor Landscape

**Layout**: Feature comparison matrix or radar chart

**Content**:
- Compare across 6 dimensions:

| Feature | Seed Bank | LemnaTec SeedAIxpert | PCS Agri Track | Seedy | GerminationPrediction |
|---|---|---|---|---|---|
| **Cost** | ✅ Low (commodity HW) | ❌ Very high | ⚠️ Medium | ⚠️ Subscription | ✅ Free (OSS) |
| **Accessibility** | ✅ Web + Mobile | ❌ Custom hardware | ⚠️ Needs internet | ⚠️ iOS only | ❌ CLI only |
| **Multi-crop** | ✅ ~20 species | ✅ Many | ⚠️ Limited | ✅ Good DB | ❌ Germination only |
| **Defect granularity** | ✅ 7-class multi-label | ✅ Industrial grade | ⚠️ Basic | ❌ Visual ID only | ❌ No quality |
| **Mobile support** | ✅ Native app | ❌ No | ⚠️ Mobile web | ✅ iOS app | ❌ No |
| **Open/extensible** | ✅ Pluggable backends | ❌ Proprietary | ❌ Proprietary | ❌ Proprietary | ✅ Open source |

**Visual direction**: Clean matrix with checkmarks/crosses or a radar chart. Seed Bank should clearly lead on accessibility + cost + extensibility. LemnaTec leads on industrial throughput but at extreme cost.

---

#### SLIDE 20 — Live App Showcase (Web)

**Layout**: Full-width screenshot showcase

**Content**:
- Embed **Dashboard.png** — KPI strip, quick actions, recent scans
- Embed **web-batch-detail.png** — AI Insights panel with donut chart, confidence histogram, 72 seeds detected, bounding-box overlay on seed image
- Minimal text: *"Dashboard → Upload photos → AI Insights with interactive bounding-box overlay"*

**Visual direction**: Let the screenshots do the talking. Arrange them to suggest a user flow (left to right or top to bottom).

---

#### SLIDE 21 — Live App Showcase (Real-Time + Mobile)

**Layout**: Split — video screenshot left, mobile right

**Content**:
- **Left**: Embed **YOLO-realtime.png** — 876 seeds detected in real-time video, green bounding boxes, AI insights panel showing 100% good rate, 78.1% mean confidence
- **Right**: Embed **MobileView.png** — Mobile app with scan history and "Check seeds in seconds" CTA
- Bottom text: *"Real-time video analysis · Native mobile app with camera capture · Full AR/EN localization with RTL"*

**Visual direction**: This proves the system works at two different scales — massive batch processing AND mobile point-and-shoot.

---

#### SLIDE 22 — The Bilingual Experience

**Layout**: Side-by-side comparison

**Content**:
- LEFT: English version of a page (LTR layout)
- RIGHT: Arabic version of the same page (RTL layout — mirrored sidebar, right-aligned text, correct Arabic typography)
- Show the language switcher UI element
- Callout: *"Full EN/AR localization with RTL layout mirroring — web and mobile"*
- Technical detail: *"Dependency-free, fully-typed i18n system — missing Arabic key = compile error"*

**Visual direction**: The visual mirror effect between LTR and RTL is inherently compelling. If you have Arabic screenshots, use them. If not, show the concept with mirrored wireframes.

---

### ═══ ACT V: ENGINEERING & PLATFORM (5 slides) ═══

---

#### SLIDE 23 — System Architecture

**Layout**: Architecture diagram (full slide)

**Content**:
- Clean, layered diagram:
  - **Top layer**: Web App (React 18 + TypeScript + Vite) + Mobile App (Expo SDK 52 / React Native) — show AR/EN flags
  - **Middle layer**: FastAPI Backend (async, layered: routers → services → repositories → ORM) — badges: JWT Auth, RBAC, Rate Limiting, RFC 9457 Errors
  - **Bottom layer** (services row with icons):
    - PostgreSQL (16 tables, UUIDv7 PKs)
    - Redis (cache + Celery broker)
    - MinIO (images, weights, datasets)
    - ClickHouse (analytics warehouse, star schema)
  - **Side**: Two Celery Worker containers:
    - worker-inference: detect → classify pipeline (torch)
    - worker-cpu: DWH dual-write, experiments (no torch — keeps image small)
- Label: *"11 containerized services · Docker Compose · 1 command to run the entire stack"*

**Visual direction**: Use icons for each service. Connection lines show data flow. Color-code: green for clients, dark for backend, blue for data stores, amber for workers.

---

#### SLIDE 24 — Full Model Traceability + ML Platform

**Layout**: Top = chain diagram. Bottom = 3-step flow

**Content**:
- **Top half — Traceability Chain**:
  Visual foreign-key chain: **Seed Detection** → (FK) → **Inference** → (FK) → **Model Artifact**
  - *"Every single quality verdict traces back to the exact model version that produced it"*
- **Bottom half — ML Platform Workflow** (3 cards):
  1. 📦 **Register** — upload model weights to MinIO, assign builder key, set per-model config (confidence threshold, IoU, image size)
  2. 🧪 **Evaluate** — run offline experiments against labelled datasets, compute confusion matrices, F1 scores
  3. 🚀 **Promote** — lifecycle: `registered → staging → production`. ModelResolver automatically picks the promoted production model per (kind, seed_type) segment

**Visual direction**: The chain at the top should look like connected links. The 3-step flow below should be left-to-right cards with arrows.

---

#### SLIDE 25 — Tech Stack at a Glance

**Layout**: Grouped icon grid (full slide)

**Content** (icons + names only, no sentences):
- 🤖 **AI/ML**: PyTorch · EfficientNet-B2 · Faster R-CNN · YOLOv8 · OpenCV · U²-Net · SAM · NumPy
- 🖥️ **Web Frontend**: React 18 · TypeScript · Vite · Tailwind CSS · shadcn/ui · Radix · TanStack Query · React Router · Recharts
- 📱 **Mobile**: Expo SDK 52 · React Native 0.76 · expo-camera · React Navigation · expo-secure-store
- ⚙️ **Backend**: FastAPI · Python 3.12 · Celery · SQLAlchemy 2 (async) · Pydantic v2 · Alembic · authlib
- 💾 **Data**: PostgreSQL 16 · ClickHouse · Redis 7 · MinIO
- 🐳 **Infrastructure**: Docker · Docker Compose · Multi-stage Dockerfile (CPU/GPU variants) · nginx · uv
- 📊 **Observability**: Prometheus · Grafana · OpenTelemetry · Sentry · structlog
- 🔒 **Security**: JWT + refresh-token rotation · OAuth (Google) · RBAC (3 roles) · rate limiting · gitleaks

**Visual direction**: Clean icon grid. Group headers in the accent color. This is a "wall of tech" slide that impresses through breadth.

---

#### SLIDE 26 — Production Readiness & Observability

**Layout**: 2×2 feature grid + optional Grafana screenshot

**Content**:
- **Top-left**: 📊 **Metrics** — Prometheus scrapes 9 custom metrics (HTTP rate/latency, inference count/duration, DWH dispatch, auth logins). Grafana auto-provisioned dashboard.
- **Top-right**: 📝 **Structured Logging** — structlog: JSON in production, colored console in dev. Every log line carries a request_id for correlation.
- **Bottom-left**: 🔍 **Distributed Tracing** — OpenTelemetry instruments FastAPI → SQLAlchemy → Redis → Celery. A trace follows a request from API through the queue into worker DB calls.
- **Bottom-right**: 🚨 **Error Monitoring** — Sentry integration with FastAPI + Celery. No PII shipped. Request_id flows through for cross-system correlation.
- Optional: embed a Grafana dashboard screenshot if available
- Bottom: *"Health probes: /healthz (liveness) · /readyz (probes all 4 datastores) · /metrics (Prometheus)"*

**Visual direction**: 2×2 grid with icons. Each quadrant is one observability pillar. Dark background works well here.

---

#### SLIDE 27 — The End-to-End Data Pipeline

**Layout**: Vertical or horizontal flowchart

**Content**:
- Complete analyze flow:
  1. `POST /analyze` (multipart: images + optional metadata)
  2. **Validate** every file (count ≤16, size, MIME, real image via PIL)
  3. **Upload** images → MinIO (before DB commit — committed rows always reference reachable objects)
  4. **Create** scan_batch (pending) + scan_images + audit log → **COMMIT**
  5. **Dispatch** one Celery task per image (queue=inference) — AFTER commit
  6. Per image in parallel:
     - **DETECT** — resolve detection model → Faster R-CNN forward pass → boxes/scores/labels → persist inference + N seed_detections
     - **CROP** each seed from source image using normalized bounding box
     - **GROUP** detections by seed_type
     - **CLASSIFY** each group with its crop-specific classifier → good/bad + confidence → update detection quality
  7. When all images processed: **CAS transition** running → succeeded | partial | failed
  8. Client polls `GET /batches/{id}` every ~2s until terminal status
- Callout: *"Concurrency-safe state machine · per-seed-type routing · partial degradation — never throws away good detection data"*

**Visual direction**: Color-coded steps with icons at each stage. The detect → crop → group → classify inner loop should be visually distinct (boxed or highlighted). This shows engineering rigor.

---

### ═══ ACT VI: CLOSING (5 slides) ═══

---

#### SLIDE 28 — Key Takeaways

**Layout**: 3 large insight cards

**Content**:
1. 📊 **"Data quality matters more than model architecture"** — *The maize model outperformed because its training data matched the real world, not because of a better network*
2. 🔀 **"Decouple detection from classification"** — *Independent stages let us diagnose, retrain, and swap each one without disturbing the other*
3. 🏭 **"Synthetic data narrows the gap, but always test on real photos"** — *MultiSeedGen eliminated the annotation bottleneck, but the only fair evaluation is against real, labeled images*

**Visual direction**: Three large cards with icons. Each card has a bold heading and one supporting line. These are the three things you want the audience to remember.

---

#### SLIDE 29 — Future Roadmap

**Layout**: Visual timeline or roadmap with 4 milestones

**Content**:
- 🌿 **"More Crops"** — expand real-world datasets for all 20+ supported species. Collect mobile-captured field images that mirror the target environment. Feed characteristics back into MultiSeedGen.
- 📱 **"Edge AI"** — on-device inference with quantized YOLO models. No internet required. Serve farmers in areas with poor connectivity.
- 🔄 **"Active Learning"** — low-confidence scans and user-corrected results automatically feed back into MultiSeedGen's training data generation, targeting the system's measured weaknesses.
- 🏭 **"Real-Time Conveyor"** — live camera feeds for industrial sorting. Instance segmentation for overlapping/occluded seeds on moving belts.

**Visual direction**: Horizontal timeline with milestone nodes. Each milestone has an icon and a short description. Feels forward-looking and ambitious.

---

#### SLIDE 30 — What This Validates

**Layout**: Bold statement on clean background

**Content**:
- Large text: *"Automated seed-quality grading on commodity hardware is feasible."*
- Second line: *"Intelligent synthetic data generation can overcome the agricultural annotation bottleneck."*
- Background: subtle seed pattern, agricultural field, or abstract green gradient
- University branding at bottom

**Visual direction**: This is a confidence slide. Large, bold typography on a clean or lightly textured background. Let the statement breathe.

---

#### SLIDE 31 — The Team

**Layout**: Team photo/avatars + supervisors

**Content**:
- Team member photos or avatar placeholders in two groups:
  - **AI Team**: Omar Ez-Eldin Abdullah, Yussuf Ahmed Awad
  - **IS Team**: Ali Abdelrahman, Mohamed Amr, Youssef Tarek Ali
- *"Special thanks to our supervisors"*: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- Faculty of Computers and Artificial Intelligence, Cairo University

**Visual direction**: Warm, personal slide. Earthy tones. This is a human moment in the presentation.

---

#### SLIDE 32 — Thank You / Questions

**Layout**: Centered, minimal

**Content**:
- **"Seed Bank"** logo, large and centered
- **"Thank You"**
- **"Questions?"**
- Contact info or GitHub link (optional)
- University logo

**Visual direction**: The simplest slide in the deck. Clean, memorable, inviting questions. Deep green background with white text, or the reverse.

---

## Narrative Flow Summary

```
ACT I: THE HOOK & PROBLEM (Slides 1–8)
  "What is this?" → "Who needs it?" → "What's broken today?" → "Why is it hard?"

ACT II: MULTISEEDGEN (Slides 9–11)
  "We built our own data factory" → "6 ways to segment" → "Augmentation that bridges the domain gap"

ACT III: THE AI PIPELINE (Slides 12–15)
  "Two-stage approach" → "Detection" → "Classification" → "PROOF: heatmaps show it works"

ACT IV: RESULTS & EVIDENCE (Slides 16–22)
  "Experiment journey" → "Data > Architecture" → "Speed vs Precision" → "vs Competitors" → "App showcase" → "Bilingual"

ACT V: ENGINEERING (Slides 23–27)
  "Architecture" → "Traceability" → "Tech stack" → "Observability" → "Full pipeline flow"

ACT VI: CLOSING (Slides 28–32)
  "Takeaways" → "Future" → "Validation statement" → "Team" → "Questions"
```
