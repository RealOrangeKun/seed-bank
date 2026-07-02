# Seed Bank — Presentation Content Guide (Final)

> **Format**: Content guide for PowerPoint, Canva, or any slide tool
> **Slides**: 34 (skip as needed to manage time — all content preserved)
> **All visual assets are real** — no mockups needed
> **Core narrative**: The AI development journey drives the story

---

## Design System (Apply Globally)

| Element | Specification |
|---|---|
| **Primary color** | Deep leaf green `#2D5016` |
| **Accent color** | Warm amber `#F59E0B` |
| **Light background** | Warm off-white `#FEFDF8` |
| **Dark background** | Soil-night `#1A1A1A` — use for technical/architecture/heatmap slides |
| **Heading font** | Inter Bold (700) or Montserrat Bold |
| **Body font** | Inter Regular (400) |
| **Icon style** | Consistent line icons throughout (Lucide, Phosphor, or Flaticon line pack) |
| **Chart palette** | Green/amber only. Never default software colors |
| **Logo** | Seed Bank watermark bottom-left on every slide |
| **Slide numbers** | Bottom-right on every slide |
| **Transitions** | Subtle fade or rise only |

### Visual Rules
- Every slide has **at least one visual element** (diagram, chart, image, screenshot, icon grid, heatmap)
- Maximum **25–30 words** body text per slide (headlines and labels excluded)
- No bullet lists longer than **4 items** — prefer icon+caption pairs
- **No paragraphs — ever**. Convert to visuals
- Metrics as **large highlighted numbers**, not dense tables
- Architecture diagrams: **conceptual flow**, not implementation detail

---

## Available Visual Assets

| # | Asset | Location | What It Shows |
|---|---|---|---|
| 1 | Dashboard | `screenshots/Dashboard.png` | Web dashboard: KPI strip, quick actions, recent scans |
| 2 | Mobile View | `screenshots/MobileView.png` | Mobile app home: "Check seeds in seconds" CTA, stats, history |
| 3 | Batch Detail | `screenshots/web-batch-detail.png` | AI Insights: 100% good rate donut, 72 seeds, confidence histogram, bounding boxes |
| 4 | YOLO Real-time | `screenshots/YOLO-realtime.png` | 876 seeds detected live via YOLO video, green bounding boxes |
| 5 | MultiSeedGen Output | `screenshots/MultiseedGen-seeds_annotatedWithBB.jpg` | Synthetic composite: 15+ species auto-annotated with red bounding boxes on real tray |
| 6 | Segmentation Tuner | `screenshots/seg-tuner.png` | Seg tuner web UI: kept/skipped gallery, confidence scores, method labels |
| 7 | Models Management | `screenshots/Models_managment.png` | ML platform models page |
| 8 | Heatmap: Damage | `heatmaps/damage.png` | Input seed + 7 Grad-CAM maps — Damage=1.00, focus on dark lesion |
| 9 | Heatmap: Healthy | `heatmaps/healthy.png` | Input seed + 7 Grad-CAM maps — Healthy=1.00, uniform activation |
| 10 | Heatmap: Shriveled | `heatmaps/shriveled.png` | Input seed + 7 Grad-CAM maps — Shriveled=1.00, focus on wrinkled area |
| 11 | Heatmap: Weeveled | `heatmaps/weeveled.png` | Input seed + 7 Grad-CAM maps — Weeveled=1.00, hotspot on bore-hole |

---

## Narrative Flow Overview

```
ACT I   — THE HOOK & PROBLEM (Slides 1–8)
           "What is this?" → "Who needs it?" → "What's broken?" → "Why is it hard?"

ACT II  — THE AI JOURNEY: FROM ML TO CV (Slides 9–11)
           "Can ML solve this?" → "Seeds are too complex → pivot to CV" → "The two-stage design"

ACT III — PHASE 1: FIRST PIPELINE (Slides 12–15)
           Detection (Faster R-CNN) → Classification (ResNet-18 + 4 mods) → Results → "We hit a wall — data"

ACT IV  — PHASE 2: DEEPER MODELS + MULTISEEDGEN (Slides 16–22)
           "Need 100K images" → EfficientNet-B2 replaces ResNet-18 → Heatmap proof → Detection still overfits →
           MultiSeedGen built to solve it → Segmentation → Augmentation & domain bridging

ACT V   — FINAL RESULTS & EVIDENCE (Slides 23–26)
           Detection experiments journey → Final metrics → Speed vs Precision → Competitor landscape

ACT VI  — THE PLATFORM & ENGINEERING (Slides 27–31)
           App showcase → Architecture → Traceability + ML platform → Tech stack → E2E pipeline

ACT VII — CLOSING (Slides 32–34)
           Takeaways → Future roadmap → Team + Q&A
```

---

## Slide-by-Slide Content Guide

---

### ═══ ACT I: THE HOOK & PROBLEM (8 slides) ═══

---

#### SLIDE 1 — Title Slide

**Layout**: Centered, professional

**Content**:
- Title: **"Seed Bank"** (large, stylized)
- Subtitle: **"AI-Powered Seed Quality Intelligence"**
- Institution: Faculty of Computers and Artificial Intelligence, Cairo University
- Supervisors: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- Team in two labeled columns:
  - **AI**: Omar Ez-Eldin Abdullah, Yussuf Ahmed Awad
  - **IS**: Ali Abdelrahman, Mohamed Amr, Youssef Tarek Ali

**Visual**: Agricultural/tech fusion — leaf textures blending into neural-network nodes. Deep green tones.

---

#### SLIDE 2 — "A Seed Bank in Computer Science?"

**Layout**: Full-width split

**Content**:
- Headline: **"A Seed Bank… in Computer Science?"**
- LEFT: Image of a traditional seed vault / agricultural seed storage
- RIGHT: AI/neural network visualization
- Large **"?"** connecting both halves

**Visual**: No explanatory text. Let the visual create curiosity.

---

#### SLIDE 3 — The 30-Second Pitch

**Layout**: Icon flow + product screenshots

**Content**:
- Flow: 📷 **"Photograph seeds"** → 🤖 **"AI analyzes"** → 📊 **"Quality report"**
- Below: embed **Dashboard.png** (small) and **MobileView.png** (small)
- One sentence: *"A platform for farmers and QA labs to instantly grade seed quality using computer vision"*

---

#### SLIDE 4 — Who Is This For?

**Layout**: Two persona cards

**Content**:
- **LEFT — "The Farmer"**: ⏱️ Slow counting · 🎭 Subjective results · 📵 No digital tools
- **RIGHT — "The QA Laboratory"**: 📊 Needs throughput · 🎯 Needs objectivity · 💰 Industrial machines too expensive

---

#### SLIDE 5 — The Problem: Manual Grading

**Layout**: Central image + floating badges

**Content**:
- Image: Manual seed sorting on a tray
- Badges: ⏱️ **"Slow"** · 🎭 **"Subjective"** · ❌ **"Inconsistent"** · 💰 **"Can't scale"**

---

#### SLIDE 6 — The Technology Gap

**Layout**: Horizontal spectrum

**Content**:
- LEFT: **"Industrial Optical Sorters"** — $$$$$ tag
- CENTER: **"Nothing affordable here"** → **"Seed Bank fills this gap"**
- RIGHT: **"Manual Counting"** — hand icon

---

#### SLIDE 7 — Why Seeds Are Hard for AI

**Layout**: 2×2 image grid

**Content**:
- **"Overlap & Clutter"** · **"Lighting Variation"** · **"Subtle Defects"** · **"Natural ≈ Damaged"**
- Title: *"Seeds aren't manufactured parts — they're organic and irregular"*

---

#### SLIDE 8 — The Data Problem

**Layout**: Three problem cards

**Content**:
1. 📊 **"Volume Gap"** — Need ~100K images; best public sets have <20K
2. 🏷️ **"Annotation Mismatch"** — Detection sets have boxes but no quality. Classification sets have labels but no boxes. No dataset has both.
3. 🔬 **"Lab ≠ Real World"** — Lab-trained models fail on real-world phone photos

*This slide sets up the entire AI journey that follows.*

---

### ═══ ACT II: THE AI JOURNEY — FROM ML TO COMPUTER VISION (3 slides) ═══

> This act tells the story of how the AI team approached the problem, discovered its complexity, and designed the solution architecture. This is the intellectual spine of the project.

---

#### SLIDE 9 — "Can Machine Learning Solve This?"

**Layout**: Left = exploration visual. Right = discovery

**Content**:
- **Starting point**: *"We began by asking: can we extract features (size, shape, color, texture ratios) to classify seed quality with traditional ML?"*
- Visual: Feature extraction diagram — seed image → measure size ratio, color histogram, texture patterns → ML classifier
- **The discovery**: Seeds are **morphologically complex** — subtle variations in shape, aspect ratio, and surface texture interact with lighting and pose. Traditional hand-crafted features can't capture these fine-grained differences reliably.
- Visual callout with ⚠️: *"Feature engineering alone can't generalize across species, defects, and environments"*

**Visual direction**: Show the progression from "simple feature extraction" to "this is harder than expected." The slide should feel like a turning point.

---

#### SLIDE 10 — "Pivoting to Computer Vision"

**Layout**: Decision diagram

**Content**:
- **The pivot**: *"Deep learning models can extract generalized features automatically — we reframed this as a Computer Vision problem"*
- Visual: Traditional ML (hand-crafted features → classifier) crossed out → Deep Learning (raw image → CNN → learned features → classifier) highlighted
- **Key insight**: *"Seeds need two separate tasks solved:"*
  - **Task 1**: "Where is each seed in the photo?" → **Object Detection**
  - **Task 2**: "What's wrong with this specific seed?" → **Quality Classification**
- Arrow pointing to slide 11: *"This led us to the two-stage pipeline design"*

**Visual direction**: This should feel like a "eureka" moment. The visual transition from ML → CV should be clean and dramatic.

---

#### SLIDE 11 — The Two-Stage Pipeline Design

**Layout**: Horizontal pipeline diagram

**Content**:
- Pipeline flow:
  📷 **Input Image** → [**STAGE 1: Object Detection** — *"Find every seed, identify its type"*] → **Bounding boxes + seed type** → [**STAGE 2: Quality Classification** — *"Grade each seed for defects"*] → 📊 **Quality Report**
- Stage 1 color: blue tones
- Stage 2 color: green tones
- Below: *"One detector for all seeds. One classifier per crop type. Each stage versioned and optimized independently."*
- Data fan-out: **1 image → N detections → N quality labels**

**Visual direction**: This is the foundational architecture slide. It should be clear, memorable, and referenced back to throughout the presentation.

---

### ═══ ACT III: PHASE 1 — FIRST PIPELINE ITERATION (4 slides) ═══

> This act covers the first implementation cycle: what was built, what worked, and where it hit a wall.

---

#### SLIDE 12 — Phase 1 Detection: Faster R-CNN

**Layout**: Left = architecture diagram. Right = results

**Content**:
- **Architecture**: Faster R-CNN with ResNet-50 backbone + FPN (Feature Pyramid Network)
  - Simplified flow: Image → ResNet-50 → FPN (multi-scale) → Region Proposals → 3 classes [background, coffee, maize]
- **Also tested**: YOLOv8 — performed comparably to Faster R-CNN at this stage
- **Results** (large metric badges):
  - Faster R-CNN: **mAP@50: 0.98** (best config, but overfitted)
  - YOLOv8: **mAP@50: 0.975** (~30ms inference)
- **The problem** (amber callout): *"High test metrics, but the model overfitted — it learned the training images, not the concept of 'seed'"*

---

#### SLIDE 13 — Phase 1 Classification: ResNet-18 + 4 Custom Modifications

**Layout**: Architecture diagram with 4 callout annotations

**Content**:
- **Base**: ResNet-18 (chosen for being lightweight)
- **4 crucial modifications** (each with a visual callout on the architecture diagram):
  1. 🔍 **Stride Reduction to (1,1)** — prevents over-downsampling so the model can see tiny defects (hairline cracks, small discolorations)
  2. 👁️ **CBAM (Attention Mechanism)** — Convolutional Block Attention Module forces the model to look at defect-relevant regions (discoloration, irregularities), not just background patterns
  3. 🔀 **Hybrid Pooling (GMP + GAP)** — combines Max Pooling and Average Pooling to capture both general patterns AND sharp anomalies (like black lines, bore holes)
  4. 📏 **Binary classification head** — good vs. bad with BCEWithLogitsLoss
- **Results** (metric badges):
  - Maize: **Accuracy 83.18%, F1: 0.769, Recall: 0.889**
  - Coffee (V3 Hybrid): **F1: 0.910, Recall: 0.934**

**Visual direction**: The 4 modifications should be visually prominent — they are the core AI contribution of Phase 1. Number them clearly.

---

#### SLIDE 14 — Phase 1 Results: What Worked, What Didn't

**Layout**: Two-column — ✅ Wins vs. ⚠️ Problems

**Content**:
- **✅ What worked**:
  - Detection localized seeds accurately in controlled conditions
  - ResNet-18 modifications improved classification meaningfully
  - Two-stage decoupling proved correct — each stage could be diagnosed independently
  - Maize performed best because it had the highest quality dataset
- **⚠️ What didn't**:
  - Detection overfitted — high test scores but poor generalization to new images
  - YOLO performed comparably to Faster R-CNN (same data limitation)
  - Classification accuracy was decent but not enough for production-grade quality assessment
  - The dataset was the bottleneck, not the architecture

**Visual direction**: Clean split. Green checkmarks left, amber warnings right. This sets up the Phase 2 pivot.

---

#### SLIDE 15 — "We Hit a Wall — The Data Insight"

**Layout**: Insight/turning-point slide

**Content**:
- **The study**: *"We studied the dataset landscape and the research literature on seed analysis more deeply"*
- **The finding** (large, bold): *"To make these models generalize and not overfit, we need at least ~100,000 images per seed type"*
- **The reality**: Best available public datasets have <20,000 images
- **The dual problem**:
  - Detection datasets have bounding boxes but no quality labels
  - Classification datasets have quality labels but no spatial annotations
  - No dataset provides both
- **The decision** (arrow pointing forward):
  - *"Upgrade the classifier to catch real defects better"* → EfficientNet-B2
  - *"Build our own data generation tool"* → MultiSeedGen

**Visual direction**: This should feel like a narrative turning point — the moment the team understood the real challenge. Use a large stat or visual metaphor for the "100K gap."

---

### ═══ ACT IV: PHASE 2 — DEEPER MODELS + MULTISEEDGEN (7 slides) ═══

> This act covers the second iteration: upgrading the classifier, proving it works with heatmaps, and building MultiSeedGen to solve the detection data problem.

---

#### SLIDE 16 — Phase 2: Upgrading to EfficientNet-B2

**Layout**: Left = architecture comparison. Right = why the switch

**Content**:
- **The change**: Kept the same Faster R-CNN detection backbone, replaced **ResNet-18 → EfficientNet-B2** for classification
- **What's different** (architecture diagram with callouts):
  - EfficientNet-B2: compound scaling (depth × width × resolution) — more efficient feature extraction
  - **CBAM** retained (channel + spatial attention)
  - **Hybrid Pooling** retained (GAP + GMP → 1024 features)
  - Now supports **7-class multi-label** defect categorization (not just binary good/bad):
    Broken · Damage · Fungus · Healthy · Immature · Shriveled · Weeveled
- **Why it's better**: *"EfficientNet-B2 catches real physical characteristics and defects dramatically better than ResNet-18"*
- **Metric improvement** (comparison badges):
  - ResNet-18 Maize: F1 0.769 → **EfficientNet-B2 Maize: Macro-F1 0.974**

**Visual direction**: Show the upgrade as an evolution. Side-by-side architecture comparison. The metric jump (0.769 → 0.974) should be visually dramatic.

---

#### SLIDE 17 — Proof: The Model Sees What Matters (Grad-CAM Heatmaps)

**Layout**: Full-width, dark background. **SHOW-STOPPER SLIDE.**

**Content**:
- Title: *"EfficientNet-B2 + CBAM learns different attention patterns for each defect class"*
- Display all **4 heatmap images** (2×2 grid or horizontal strip):
  - **Damage** (`damage.png`): Model focuses on dark lesion → Damage=1.00
  - **Healthy** (`healthy.png`): Uniform activation across clean surface → Healthy=1.00
  - **Shriveled** (`shriveled.png`): Focus on wrinkled deformation → Shriveled=1.00
  - **Weeveled** (`weeveled.png`): Concentrated hotspot on bore-hole → Weeveled=1.00
- Each heatmap shows: **Input Image** + **7 class activation maps** (Broken, Damage, Fungus, Healthy, Immature, Shriveled, Weeveled) — correct class highlighted at 1.00, others at 0.00
- Legend: Red/yellow = high activation, Blue/purple = low activation
- Callout: *"This is the visual proof that the attention mechanism works — the model isn't guessing, it's looking at the right features"*

**Visual direction**: Dark background (#1A1A1A) makes colors pop. Maximum visual real estate. This is the most compelling visual evidence in the entire presentation. Minimal text.

---

#### SLIDE 18 — "Detection Still Overfits — We Need Our Own Data"

**Layout**: Problem → Solution bridge slide

**Content**:
- **The remaining problem**: *"EfficientNet-B2 solved classification. But object detection still overfitted — the models memorized training images instead of learning 'what a seed looks like.'"*
- **Why more data can't be collected manually**:
  - Need ~100K annotated images per type
  - Manual bounding-box annotation is prohibitively slow and error-prone
  - Public datasets are lab-only — don't match real-world conditions
- **The solution** (large, bold): *"We built MultiSeedGen — a synthetic data factory that generates unlimited, perfectly-labeled detection training data"*
- Arrow/transition: leads into the MultiSeedGen deep dive

**Visual direction**: This is the bridge between "the classifier works" and "the detector needs help." The MultiSeedGen reveal should feel like a breakthrough.

---

#### SLIDE 19 — MultiSeedGen: Building Our Own Training Data

**Layout**: Pipeline diagram + output screenshot

**Content**:
- Pipeline flow:
  **Single-seed photos** → [**SEGMENT**: cut out the seed] → **Cut-out pool** → [**COMPOSITE**: place on backgrounds with collision physics] → **Dense multi-seed scenes** → [**DEGRADE**: camera simulation] → [**EXPORT**: YOLO/COCO with auto-labels]
- Embed **MultiseedGen-seeds_annotatedWithBB.jpg** — shows actual output: 15+ species auto-labeled with bounding boxes on realistic tray
- Key callout: *"Labels come for free — the engine placed each seed, so it knows exactly where every one is"*
- Stats: *"6 segmentation backends · 15+ augmentation parameters · byte-reproducible output · ~20 seed species supported"*

**Visual direction**: Clean left-to-right pipeline with arrows. The screenshot proves the output is realistic and properly labeled.

---

#### SLIDE 20 — Segmentation: 6 Ways to Cut a Seed

**Layout**: Left = method cards. Right = seg-tuner screenshot

**Content**:
- **"6 Segmentation Backends"** (ordered by complexity):
  1. **auto** (default) — classical cascade + confidence gate + rembg fallback
  2. **threshold** — border-colour distance (clean backgrounds)
  3. **otsu** — grayscale Otsu (high-contrast)
  4. **grabcut** — OpenCV GrabCut (textured backgrounds)
  5. **rembg (U²-Net)** — learned ONNX model, GPU-capable. Removes cast shadows and watermarks
  6. **SAM (Segment Anything)** — prompt-driven: automatic, box, or point modes
- Embed **seg-tuner.png** — web UI with kept/skipped gallery, confidence scores
- Details: *"Content-hash cached — first pass is the only cost. Per-source override via segment-map."*

---

#### SLIDE 21 — Augmentation & Domain Bridging

**Layout**: Three columns + before/after

**Content**:
- Title: *"Bridging the gap between synthetic and real"*
- **Column 1 — "Geometric Transforms"**:
  - 🔄 Scale jittering (per-seed)
  - ↻ Rotation + flip
  - ◇ Shear deformation
  - 📐 Perspective warping (box recomputed from warped alpha)
  - 💥 Collision-aware placement (IoU rejection, 8 retries/seed)
- **Column 2 — "Photometric Degradation"** (camera simulation):
  - 📷 Sensor noise (Gaussian + Poisson)
  - 🖼️ JPEG compression artifacts
  - 🌫️ Motion blur + defocus
  - 🔆 Gamma variation
  - 🌗 Directional drop shadows with natural fade
- **Column 3 — "Domain Matching"** (critical):
  - 🏞️ **bg_from_sources** — composites onto REAL inpainted tray backgrounds. *Single most impactful quality lever*
  - ⬛ **neg_frac** — 10% background-only negatives to suppress false positives
  - 🔒 **val_seed_holdout** — source seed in val NEVER appears in training. Prevents data leakage
  - ♻️ **Determinism** — fixed (config, seed) → byte-identical output regardless of workers
- **Bottom**: Before/after — sterile synthetic vs. domain-matched scene with real tray + degradation

**Visual direction**: Three equal columns. Domain-matching column visually emphasized (amber border). Before/after at bottom is the visual proof.

---

#### SLIDE 22 — MultiSeedGen Web UI + Data Loop

**Layout**: Screenshots + feedback loop diagram

**Content**:
- **The tool has its own Web UI**: React + TypeScript + Tailwind + Radix, served by FastAPI
  - Run tab: config form, live WebSocket log streaming, run history
  - Seg tuner tab: per-method segmentation preview with quality scoring
  - Dataset browser: browse and download generated datasets
  - Config management: presets, save/load YAML
- **The data feedback loop** (circular diagram):
  MultiSeedGen generates training data → Models train on it → Real-world inference finds edge cases (low confidence, user corrections) → Edge case characteristics fed back into MultiSeedGen's augmentation → Better training data → Better models → …
- Callout: *"Each turn of this loop targets the generator at the system's measured weaknesses"*

**Visual direction**: The circular feedback loop is the key visual here. It shows this isn't just a one-shot generator — it's a self-improving data strategy.

---

### ═══ ACT V: FINAL RESULTS & EVIDENCE (4 slides) ═══

---

#### SLIDE 23 — Detection Experiments: The Full Journey

**Layout**: Timeline/progression chart

**Content**:
- 5 experiments as a visual journey:
  1. **Swin Transformer + FPN** → mAP@50: 0.949 — ⚠️ Overfitted (too powerful for small dataset)
  2. **+ CIoU loss** → mAP@50: 0.981 — Better box regression, still overfitting
  3. **ResNet-50 + Faster R-CNN** → mAP@50: 0.870 — ✅ Lower metrics but better real-world generalization
  4. **+ PANet** → mAP@50: 0.852 — Improved localization at stricter IoU
  5. **YOLOv8** → mAP@50: 0.975 — ⭐ Fast + accurate, best all-round
- Insight: *"Lower test metrics ≠ worse model. ResNet-50 generalized better on real photos."*
- Note: *"After MultiSeedGen, detection trained on 40 total seed types with great performance, especially on highest quality datasets"*

---

#### SLIDE 24 — Classification: Data Quality > Model Architecture

**Layout**: Two-column comparison + convergence chart

**Content**:
- **LEFT — "Soybean (Lab Data)"**: Sterile backgrounds → **0.9936 F1** ❌ Overfitted, fails on real images
- **RIGHT — "Maize (Real-World Data)"**: Natural sunlight, phone captures → **0.974 F1** ✅ Generalizes
- Training progression: Epoch 1: 0.808 → Epoch 3: 0.925 → Epoch 5: 0.964 → **Epoch 7: 0.974**
- Callout: *"The model that scored lower on the test set performed better in the real world"*

---

#### SLIDE 25 — Speed vs. Precision: Two Deployment Modes

**Layout**: Two comparison cards + YOLO screenshot

**Content**:
- **LEFT — "Precision Mode"**: Faster R-CNN + EfficientNet-B2 · ~230ms · ~4.3 FPS · 7-class multi-label · Best for QA labs
- **RIGHT — "Speed Mode"**: YOLOv8 · ~80ms · ~12.5 FPS · Real-time · Best for conveyor belts
- Embed **YOLO-realtime.png**: 876 seeds detected in real-time
- Note: *"Both run on commodity hardware (RTX 3060)"*

---

#### SLIDE 26 — Competitor Landscape

**Layout**: Feature comparison matrix

**Content**:

| Feature | Seed Bank | LemnaTec | PCS Agri Track | Seedy | GerminationPrediction |
|---|---|---|---|---|---|
| Cost | ✅ Low | ❌ Very high | ⚠️ Medium | ⚠️ Subscription | ✅ Free |
| Accessibility | ✅ Web + Mobile | ❌ Custom HW | ⚠️ Needs internet | ⚠️ iOS only | ❌ CLI only |
| Multi-crop | ✅ ~20 species | ✅ Many | ⚠️ Limited | ✅ Good DB | ❌ Germination only |
| Defect granularity | ✅ 7-class multi-label | ✅ Industrial | ⚠️ Basic | ❌ Visual ID | ❌ No quality |
| Mobile | ✅ Native app | ❌ No | ⚠️ Web | ✅ iOS | ❌ No |
| Open/extensible | ✅ Pluggable | ❌ Proprietary | ❌ Proprietary | ❌ Proprietary | ✅ OSS |

---

### ═══ ACT VI: THE PLATFORM & ENGINEERING (5 slides) ═══

---

#### SLIDE 27 — Live App Showcase

**Layout**: Screenshot gallery

**Content**:
- Embed **Dashboard.png** — KPI strip, quick actions
- Embed **web-batch-detail.png** — AI Insights, bounding boxes, confidence histogram
- Embed **YOLO-realtime.png** — 876 seeds real-time video
- Embed **MobileView.png** — Mobile app
- Embed **Models_managment.png** — ML platform
- Callout: *"Full EN/AR localization with RTL layout mirroring — web and mobile"*

---

#### SLIDE 28 — System Architecture

**Layout**: Architecture diagram

**Content**:
- **Clients**: Web App (React 18 + TypeScript + Vite) + Mobile App (Expo SDK 52 / RN) — AR/EN flags
- **Backend**: FastAPI (async, layered: routers → services → repositories) — JWT Auth, RBAC, Rate Limiting
- **Services**: PostgreSQL (16 tables, UUIDv7) · Redis (cache + Celery broker) · MinIO (images, weights) · ClickHouse (analytics, star schema)
- **Workers**: worker-inference (torch, detect→classify) · worker-cpu (DWH, experiments, no torch)
- Label: *"11 containerized services · Docker Compose · 1 command"*

---

#### SLIDE 29 — Full Model Traceability + ML Platform

**Layout**: Chain diagram + 3-step flow

**Content**:
- **Traceability Chain**: Seed Detection → (FK) → Inference → (FK) → Model Artifact
  - *"Every verdict traces to the exact model version"*
- **ML Platform** (3 cards):
  1. 📦 **Register** — upload weights, assign builder, set config
  2. 🧪 **Evaluate** — offline experiments against labelled datasets
  3. 🚀 **Promote** — registered → staging → production. ModelResolver picks production model per segment

---

#### SLIDE 30 — Tech Stack at a Glance

**Layout**: Grouped icon grid

**Content** (icons + names only):
- 🤖 **AI/ML**: PyTorch · EfficientNet-B2 · Faster R-CNN · YOLOv8 · OpenCV · U²-Net · SAM
- 🖥️ **Web**: React 18 · TypeScript · Vite · Tailwind · shadcn/ui · TanStack Query · Recharts
- 📱 **Mobile**: Expo SDK 52 · React Native · expo-camera · React Navigation
- ⚙️ **Backend**: FastAPI · Python 3.12 · Celery · SQLAlchemy 2 · Pydantic v2 · Alembic
- 💾 **Data**: PostgreSQL 16 · ClickHouse · Redis 7 · MinIO
- 🐳 **Infra**: Docker · Multi-stage Dockerfile (CPU/GPU) · nginx · Prometheus · Grafana
- 📊 **Observability**: structlog · OpenTelemetry · Sentry · Prometheus metrics
- 🔒 **Security**: JWT + refresh rotation · OAuth (Google) · RBAC · rate limiting · gitleaks

---

#### SLIDE 31 — End-to-End Pipeline Flow

**Layout**: Vertical/horizontal flowchart

**Content**:
1. `POST /analyze` (multipart images + metadata)
2. Validate every file (count ≤16, size, MIME, real image)
3. Upload → MinIO (before DB commit)
4. Create batch (pending) + images + audit log → COMMIT
5. Dispatch one Celery task per image (after commit)
6. Per image:
   - DETECT (resolve model → forward pass → boxes/scores/labels → persist)
   - CROP each seed from source image
   - GROUP detections by seed type
   - CLASSIFY each group with crop-specific classifier → update quality
7. CAS transition: running → succeeded | partial | failed
8. Client polls until terminal status
- Callout: *"Concurrency-safe state machine · per-seed-type routing · partial degradation"*

---

### ═══ ACT VII: CLOSING (3 slides) ═══

---

#### SLIDE 32 — Key Takeaways

**Layout**: 3 large insight cards

**Content**:
1. 📊 **"Data quality matters more than model architecture"** — *The maize model outperformed because its training data matched the real world*
2. 🔀 **"Decouple detection from classification"** — *Independent stages let us diagnose and swap each without disturbing the other*
3. 🏭 **"Synthetic data narrows the gap — but always test on real photos"** — *MultiSeedGen eliminated the annotation bottleneck; real evaluation is the only fair test*

---

#### SLIDE 33 — Future Roadmap

**Layout**: Visual timeline with 4 milestones

**Content**:
- 🌿 **"More Crops"** — expand real-world datasets for all 20+ species
- 📱 **"Edge AI"** — on-device quantized inference, no internet needed
- 🔄 **"Active Learning"** — low-confidence scans feed back into MultiSeedGen
- 🏭 **"Real-Time Conveyor"** — live camera feeds, instance segmentation for overlapping seeds

---

#### SLIDE 34 — Team + Thank You + Questions

**Layout**: Warm, centered

**Content**:
- Team photos/avatars in two groups (AI + IS)
- *"Special thanks to"*: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- **"Seed Bank"** logo
- **"Thank You · Questions?"**
- University logo

---

## The AI Development Story (Speaker Notes Summary)

For the presenter, here is the chronological AI story that threads through Acts II–V:

> **"We started by exploring if traditional ML could solve seed quality classification — extracting features like size ratios, color histograms, and texture patterns. But seeds are morphologically complex, and hand-crafted features couldn't generalize across species and conditions. So we pivoted to Computer Vision and deep learning.**
>
> **We designed a two-stage pipeline: detect each seed first, then classify its quality. In Phase 1, we used Faster R-CNN for detection and ResNet-18 with 4 custom modifications (stride reduction, CBAM attention, hybrid pooling, binary head). We also tried YOLO — it performed comparably. Maize worked best because it had the highest quality dataset, but even it overfitted.**
>
> **We studied the problem more deeply and realized we need ~100K images per seed type. So we made two moves: we upgraded classification to EfficientNet-B2 (which went from binary to 7-class multi-label and caught real defects dramatically better — the heatmaps prove it), and we built MultiSeedGen to generate unlimited, perfectly-labeled detection training data.**
>
> **MultiSeedGen segments seeds from single-seed photos using 6 different backends (from simple thresholding to Segment Anything), composites them into dense realistic scenes with collision physics and domain-matched augmentations, and exports them with automatic bounding-box labels. The single most impactful setting was compositing onto real tray backgrounds extracted from source photos.**
>
> **The end result: we trained on 40 total seed types and achieved strong performance — especially on the highest quality datasets like maize (0.974 Macro-F1 for classification). The system now runs as a full platform with web and mobile apps, model traceability, and production-grade engineering."**
