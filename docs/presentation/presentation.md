# Seed Bank — Presentation Content Guide (Final)

> **Format**: Content guide for PowerPoint, Canva, or any slide tool
> **Slides**: 39 *logical* slides (skip as needed to manage time — all content preserved)
> **All visual assets are real** — no mockups needed
> **Core narrative**: The AI development journey drives the story; the engineering
> platform lands it as a real product

### On slide counts (read this first)
Slide numbers below are **logical**, not physical. A few image-heavy slides are meant
to **span 2–3 physical slides** so each screenshot gets room to breathe — these are
flagged inline with **⚠️ Image spread**. Build those as a short sequence and the
running total will end up a little higher than 39; that's expected. Keep the *order*
and the *transitions*; adjust the numbering to your final deck.

---

## Design System (Apply Globally)

The palette below is the **real product's agricultural identity** (pulled from the
app's theme tokens), tuned to stay legible on a projector. Slides look like the
actual product — which is consistent with every screenshot in the deck.

| Element | Specification |
|---|---|
| **Primary — leaf green** | `#1E7A40` (buttons, highlights, brand). For large headings on a light background use the deeper `#14532D` for contrast |
| **Accent — wheat / amber** | `#F59E0B` (calls-to-action, "best" highlights, metric emphasis) |
| **Info hue — sky blue** | `#157AAC` (light) · `#3EA2E9` (dark) — use so technical slides aren't monochrome green |
| **Light background** | Warm off-white field `#FAFBF8`; body text `#16261E`; cards `#FFFFFF` |
| **Dark background ("soil-night")** | Use for technical / architecture / heatmap slides. **4-step elevation ramp** so surfaces read as layered, not flat: canvas `#121615` → surface `#191E1C` → card `#1E2321` → popover `#252B29`. Near-white text `#F3F6F4`. In dark mode the primary green brightens to `#3DCB78` |
| **Heading font** | **Inter** Bold (700) — a heavier display weight is fine for titles |
| **Body font** | **Inter** Regular (400) / Medium (500) |
| **Icon style** | Consistent line icons throughout (Lucide — the app itself uses `lucide-react`) |
| **Chart palette** | Leaf-green + wheat-amber + info-blue only. Never default software colors |
| **Logo** | Seed Bank leaf mark (two-tone green — `frontend/public/seed.svg`), watermark bottom-left on every slide |
| **Slide numbers** | Bottom-right on every slide |
| **Transitions** | Subtle fade or rise only |

### Visual Rules
- Every slide has **at least one visual element** (diagram, chart, image, screenshot, icon grid, heatmap)
- Maximum **25–30 words** body text per slide (headlines and labels excluded)
- No bullet lists longer than **4 items** — prefer icon+caption pairs
- **No paragraphs — ever**. Convert to visuals
- Metrics as **large highlighted numbers**, not dense tables
- Architecture diagrams: **conceptual flow**, not implementation detail
- Agricultural texture direction: subtle leaf / field motifs behind title and section dividers; keep them faint so they never fight the content

---

## Available Visual Assets

Two kinds of assets: **captured screenshots/heatmaps** (photorealistic proof) and a
**large library of conceptual diagrams** already exported to PDF. The diagram library
was almost unused before — it is the single biggest lever for the engineering slides.

### A. Screenshots & heatmaps (photorealistic)

| # | Asset | Path (repo-root-relative) | What It Shows |
|---|---|---|---|
| 1 | Dashboard | `docs/report/figures/screenshots/Dashboard.png` | Web dashboard: KPI strip, quick actions, recent scans |
| 2 | Mobile View | `docs/report/figures/screenshots/MobileView.png` | Mobile home: "Check seeds in seconds" CTA, stats, history |
| 3 | Batch Detail | `docs/report/figures/screenshots/web-batch-detail.png` | AI Insights: good-rate donut, seed count, confidence histogram, bounding boxes |
| 4 | YOLO Real-time (model demo) | `docs/report/figures/screenshots/YOLO-realtime.png` | 876 seeds detected in a single dense frame — a **detection-model demo** |
| 5 | MultiSeedGen Output | `docs/report/figures/screenshots/MultiseedGen-seeds_annotatedWithBB.jpg` | Synthetic composite: 15+ species auto-annotated with bounding boxes on a real tray |
| 6 | Segmentation Tuner | `docs/report/figures/screenshots/seg-tuner.png` | Seg-tuner UI: kept/skipped gallery, confidence scores, method labels |
| 7 | Models Management | `docs/report/figures/screenshots/Models_managment.png` | ML platform models page (registry + lifecycle) |
| 8 | Heatmap: Damage | `docs/presentation/extra_files/heatmaps/damage.png` | Input seed + 7 Grad-CAM maps — Damage=1.00, focus on dark lesion |
| 9 | Heatmap: Healthy | `docs/presentation/extra_files/heatmaps/healthy.png` | Input seed + 7 Grad-CAM maps — Healthy=1.00, uniform activation |
| 10 | Heatmap: Shriveled | `docs/presentation/extra_files/heatmaps/shriveled.png` | Input seed + 7 Grad-CAM maps — Shriveled=1.00, focus on wrinkled area |
| 11 | Heatmap: Weeveled | `docs/presentation/extra_files/heatmaps/weeveled.png` | Input seed + 7 Grad-CAM maps — hotspot on bore-hole |
| 12 | University logos | `docs/report/logos/Cairo_University_new_logo.png` · `docs/report/logos/FCAI.jpg` | Title + closing slides |

### B. Conceptual diagram library (Mermaid → PDF, ready to drop in)

**55 diagrams** live as source in `docs/diagrams/*.{mmd,md}` and as **PDF exports in
`docs/report/figures/*.pdf`**. Use the PDFs directly. The curated presentation-grade
subset (avoid the raw implementation-detail ones):

| Diagram | PDF | Best slide |
|---|---|---|
| System context (C4 L1) | `01-system-context.pdf` | Proposed System Architecture (Slide 12) |
| Containers — app | `02-containers-app.pdf` | System Architecture (Slides 12 & 32) |
| Containers — datastores | `02-containers-datastores.pdf` | System Architecture (Slides 12 & 32) |
| Two-stage pipeline (detect→classify) | `04-worker-components-pipeline.pdf` | Proposed System Architecture (Slide 13) |
| Analyze sequence | `06-analyze-sequence.pdf` | Analyze Pipeline (Slide 33) |
| Batch state machine | `07-batch-state-machine.pdf` | Analyze Pipeline (Slide 33) |
| Auth sequence | `08-auth-sequence.pdf` | Secure by Design (Slide 35, optional) |
| ML platform lifecycle | `09-ml-platform.pdf` | Traceability & Lifecycle (Slide 34) |
| Model resolution | `16-model-resolution.pdf` | Traceability & Lifecycle (Slide 34) |
| Core ERD | `05-db-erd-core.pdf` | Architecture / data model (Slide 32, optional) |
| Faster R-CNN architecture | `17-fasterRCNN-architecture.pdf` | Phase 1 Detection (Slide 14) |
| EfficientNet-B2 architecture | `18-Efficient-net-B2.pdf` | Phase 2 Classification (Slide 18) |
| MultiSeedGen pipeline | `14-multiseedgen-pipeline.pdf` | MultiSeedGen (Slide 21) |
| Farmer / Dev / Admin use-cases | `12a-…`, `12b-…`, `12c-usecase-*.pdf` | Audiences (Slide 31, optional) |

> **Skip** the `*-tooling.*` and `10-deployment-runtime-tooling.*` diagrams — they show
> ops/monitoring detail that's out of scope for this deck.

*A full slide→asset map and a checklist of screenshots still worth capturing are at
the end of this document.*

---

## Narrative Flow Overview

```
ACT I   — THE HOOK & PROBLEM (Slides 1–8)
           "What is this?" → "Who needs it?" → "What's broken?" → "Why is it hard?"

ACT II  — THE AI JOURNEY: FROM ML TO CV (Slides 9–13)
           "Can ML solve this?" → "Our solution: platform + MultiSeedGen" → "Pivot to CV" →
           "Proposed system architecture" (system at a glance → the two-stage design)

ACT III — PHASE 1: FIRST PIPELINE (Slides 14–17)
           Detection (Faster R-CNN) → Classification (ResNet-18 + 4 mods) → Results → "We hit a wall — data"

ACT IV  — PHASE 2: DEEPER MODELS + MULTISEEDGEN (Slides 18–24)
           EfficientNet-B2 → Heatmap proof → Detection still overfits →
           MultiSeedGen → Segmentation → Augmentation & domain bridging → data loop

ACT V   — FINAL RESULTS & EVIDENCE (Slides 25–28)
           Detection journey → Data > architecture → Speed vs Precision → Competitor landscape

ACT VI  — THE PLATFORM & ENGINEERING (Slides 29–36)
           From models to a product → App showcase → Two audiences + EN/AR RTL →
           Architecture → Analyze pipeline → Traceability & lifecycle → Secure by design → Tech stack

ACT VII — CLOSING (Slides 37–39)
           Takeaways → Future roadmap → Team + Q&A
```

The engineering act is intentionally a **smooth arc**, not a feature dump: it starts
by bridging out of the ML results, shows the product, then peels back one layer at a
time (what users see → how it's built → how a request flows → how results stay
traceable → how it's kept safe), and hands the model-lifecycle thread **back** to the
AI story.

---

## Slide-by-Slide Content Guide

---

### ═══ ACT I: THE HOOK & PROBLEM (8 slides) ═══

---

#### SLIDE 1 — Title Slide   ⚠️ Image spread (title can breathe over a full-bleed visual)

**Layout**: Centered, professional

**Content**:
- Title: **"Seed Bank"** (large, stylized)
- Subtitle: **"AI-Powered Seed Quality Intelligence"**
- Institution: Faculty of Computers and Artificial Intelligence, Cairo University
- Supervisors: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- Team in two labeled columns:
  - **AI**: Omar Ez-Eldin Abdullah, Yussuf Ahmed Awad
  - **IS**: Ali Abdelrahman, Mohamed Amr, Youssef Tarek Ali

**Visual**: Agricultural/tech fusion — leaf textures blending into neural-network nodes. Deep green tones. University logos (`docs/report/logos/`) bottom-center.

**Speaker note**: Open warm and confident — one line: *"We built an AI platform that grades seed quality from a single photo — usable by a farmer in a field or a QA lab."* Name the two sub-teams (AI + IS) so the audience knows the project spans research **and** a production system. → Next: the playful hook — why a "seed bank" in computer science?

---

#### SLIDE 2 — "A Seed Bank in Computer Science?"

**Layout**: Full-width split

**Content**:
- Headline: **"A Seed Bank… in Computer Science?"**
- LEFT: Image of a traditional seed vault / agricultural seed storage
- RIGHT: AI/neural network visualization
- Large **"?"** connecting both halves

**Visual**: No explanatory text. Let the visual create curiosity.

**Speaker note**: Let the visual do the work — pause on the "?". Ask the room what "seed bank" evokes, then reveal we mean *seed-quality intelligence*, not a storage vault. → Next: the 30-second version of what it actually does.

---

#### SLIDE 3 — The 30-Second Pitch

**Layout**: Icon flow + product screenshots

**Content**:
- Flow: 📷 **"Photograph seeds"** → 🤖 **"AI analyzes"** → 📊 **"Quality report"**
- Below: embed **Dashboard.png** (small) and **MobileView.png** (small)
- One sentence: *"A platform for farmers and QA labs to instantly grade seed quality using computer vision"*

**Speaker note**: The whole product in one breath — photograph → analyze → report, on web and mobile. Keep it to three beats; details come later. → Next: who actually needs this.

---

#### SLIDE 4 — Who Is This For?

**Layout**: Two persona cards

**Content**:
- **LEFT — "The Farmer"**: ⏱️ Slow counting · 🎭 Subjective results · 📵 No digital tools
- **RIGHT — "The QA Laboratory"**: 📊 Needs throughput · 🎯 Needs objectivity · 💰 Industrial machines too expensive

**Speaker note**: Two audiences, two different pains — the farmer wants speed and objectivity; the lab wants throughput without a six-figure machine. Stress that **one backend serves both** (we'll pay this off in the platform act). → Next: what today's manual grading looks like.

---

#### SLIDE 5 — The Problem: Manual Grading

**Layout**: Central image + floating badges

**Content**:
- Image: Manual seed sorting on a tray
- Badges: ⏱️ **"Slow"** · 🎭 **"Subjective"** · ❌ **"Inconsistent"** · 💰 **"Can't scale"**

**Speaker note**: Manual grading is slow, subjective, inconsistent, and doesn't scale — the core pain in four words. → Next: the market gap between manual and industrial.

---

#### SLIDE 6 — The Technology Gap

**Layout**: Horizontal spectrum

**Content**:
- LEFT: **"Industrial Optical Sorters"** — $$$$$ tag
- CENTER: **"Nothing affordable here"** → **"Seed Bank fills this gap"**
- RIGHT: **"Manual Counting"** — hand icon

**Speaker note**: There's nothing affordable between hand-counting and industrial optical sorters — that empty middle is our wedge. → Next: why this is genuinely hard for AI.

---

#### SLIDE 7 — Why Seeds Are Hard for AI

**Layout**: 2×2 image grid

**Content**:
- **"Overlap & Clutter"** · **"Lighting Variation"** · **"Subtle Defects"** · **"Natural ≈ Damaged"**
- Title: *"Seeds aren't manufactured parts — they're organic and irregular"*

**Speaker note**: Seeds are organic — overlap, lighting, subtle defects, and healthy-looks-damaged ambiguity. Not clean manufactured parts. → Next: and the data behind that difficulty.

---

#### SLIDE 8 — The Data Problem

**Layout**: Three problem cards

**Content**:
1. 📊 **"Volume Gap"** — Need ~100K images; best public sets have <20K
2. 🏷️ **"Annotation Mismatch"** — Detection sets have boxes but no quality. Classification sets have labels but no boxes. No dataset has both.
3. 🔬 **"Lab ≠ Real World"** — Lab-trained models fail on real-world phone photos

*This slide sets up the entire AI journey that follows.*

**Speaker note**: Three data problems — volume, annotation mismatch, lab≠real-world — are the seeds (pun intended) of the whole journey. Plant them now; Acts III–IV pay them off. → Next: could classic machine learning even solve this?

---

### ═══ ACT II: THE AI JOURNEY — FROM ML TO COMPUTER VISION (5 slides) ═══

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

**Speaker note**: We started honestly with hand-crafted features and classic ML — frame it as diligent, not naive. The discovery: those features don't generalize across species and conditions. → Next: the solution we propose.

---

#### SLIDE 10 — The Proposed Solution

**Layout**: Two-column split (platform | data factory) + a one-line thesis

**Content**:
- **Thesis**: *"Grade seed quality from an ordinary photo — and manufacture the training data that makes it possible."*
- **LEFT — 🌱 Seed Bank (the platform)**: photo/video of a seed batch → **find every seed** → **grade each one** → **aggregate report** (good-rate, seed count, per-crop breakdown). Every verdict is **traceable** to the model that produced it; ships with basic **model management + offline evaluation**; delivered as a **web + mobile app a farmer can actually use**.
- **RIGHT — 🧬 MultiSeedGen (the data factory)**: cut real seeds from single-seed photos → **composite** many onto realistic backgrounds with lighting + camera-like noise → **export fully-labelled detection datasets**. *"The tool places every seed itself, so the labels come for free."*
- **Bottom band — answers the two problems from Slide 8**: 💰 **No expensive rig** — useful accuracy from ordinary single-view photos · 📊 **Closes the ~100K-image data gap** — synthetic generation instead of hand-labelling

**Visual direction**: A clean two-part split — one deliverable per column — with the bottom band drawing arrows back to the "Technology Gap" (Slide 6) and "Data Problem" (Slide 8). This is the *proposed-solution* statement: unlike the 30-second pitch (Slide 3), it names **both** deliverables — the product **and** the data tool — as the answer to the stated problem.

**Speaker note**: Before any model details, here's the entire solution on one slide — a platform that grades seeds from a normal photo, and a data factory that generates the labelled images the detector needs. Two problems from earlier — cost and data — one deliverable each. → Next: why this had to be a computer-vision solution.

---

#### SLIDE 11 — "Pivoting to Computer Vision"

**Layout**: Decision diagram

**Content**:
- **The pivot**: *"Deep learning models can extract generalized features automatically — we reframed this as a Computer Vision problem"*
- Visual: Traditional ML (hand-crafted features → classifier) crossed out → Deep Learning (raw image → CNN → learned features → classifier) highlighted
- **Key insight**: *"Seeds need two separate tasks solved:"*
  - **Task 1**: "Where is each seed in the photo?" → **Object Detection**
  - **Task 2**: "What's wrong with this specific seed?" → **Quality Classification**
- Arrow pointing to Slides 12–13: *"This led us to the proposed system architecture"*

**Visual direction**: This should feel like a "eureka" moment. The visual transition from ML → CV should be clean and dramatic.

**Speaker note**: The pivot to deep learning, plus the key reframe: two distinct tasks — *where* is each seed, and *what's wrong* with it. → Next: those two tasks shape our proposed system architecture.

---

#### SLIDE 12 — Proposed System Architecture (1/2): The System at a Glance

**Layout**: One high-level conceptual diagram + a five-piece component list

**Content**:
- **Hero diagram**: `docs/report/figures/01-system-context.pdf` (who uses it + external services) — *alt/complement*: `02-containers-app.pdf` + `02-containers-datastores.pdf` (or the composite `02-containers.pdf`)
- **Five pieces** (keep it conceptual):
  - 📱 **Clients** — a React web app + an Expo mobile app (English / Arabic)
  - ⚙️ **FastAPI backend** — accepts a batch, records it, responds fast; async + cleanly layered
  - 🔧 **Background workers** — the heavy **detect → classify** work runs *off* the request path
  - 💾 **Datastores** — PostgreSQL (results) · ClickHouse (analytics) · MinIO (images + weights) · Redis (queue / cache)
- **Design-principle callout**: *"Inference is heavy, so it never runs inside the request the user is waiting on — the API stays responsive."*

**Visual direction**: High-level and non-expert-friendly — this is the *proposed* architecture, not the deep dive. Use the system-context diagram as the hero so it reads differently from the detailed container view later. **Forward-ref**: the full container topology is at **Slide 32**, and we trace a live request end-to-end at **Slide 33**.

**Speaker note**: The system in one picture — clients talk to a fast API, which hands the heavy model work to background workers, with four datastores behind them. The one idea to land: inference never blocks the user's request. Keep it conceptual; the deep dive is in the platform act. → Next: the two-stage pipeline at the core of it.

---

#### SLIDE 13 — Proposed System Architecture (2/2): The Two-Stage Detect→Classify Pipeline

**Layout**: Horizontal pipeline diagram

**Content**:
- Pipeline flow:
  📷 **Input Image** → [**STAGE 1: Object Detection** — *"Find every seed, identify its type"*] → **Bounding boxes + seed type** → **crop each seed** → **GROUP by seed type** → [**STAGE 2: Quality Classification** — *"Grade each seed for defects"*] → 📊 **Quality Report**
- Stage 1 color: blue tones
- Stage 2 color: green tones
- Below: *"One detector for all seeds. One classifier per crop type. Each stage versioned and optimized independently."*
- Data fan-out: **1 image → N detections → N quality labels**
- *Optional diagram*: `docs/report/figures/04-worker-components-pipeline.pdf` (keep it conceptual)

**Visual direction**: This is the foundational architecture slide — clear, memorable, and referenced back to throughout the presentation. **Forward-ref**: the engineering behind it (concurrency-safe batching, per-seed-type routing, graceful partial results) is at **Slide 33**.

**Speaker note**: This is the architectural spine of the entire project — detect, then classify — and we'll point back to it repeatedly, including in the platform act. → Next: Phase 1, how we first built the detector.

---

### ═══ ACT III: PHASE 1 — FIRST PIPELINE ITERATION (4 slides) ═══

> This act covers the first implementation cycle: what was built, what worked, and where it hit a wall.

---

#### SLIDE 14 — Phase 1 Detection: Faster R-CNN

**Layout**: Left = architecture diagram. Right = results

**Content**:
- **Architecture**: Faster R-CNN with ResNet-50 backbone + FPN (Feature Pyramid Network)
  - Simplified flow: Image → ResNet-50 → FPN (multi-scale) → Region Proposals → 3 classes [background, coffee, maize]
  - *Optional diagram*: embed `docs/report/figures/17-fasterRCNN-architecture.pdf` (keep it conceptual)
- **Also tested**: YOLOv8 — performed comparably to Faster R-CNN at this stage
- **Results** (large metric badges):
  - Faster R-CNN: **mAP@50: 0.98** (best config, but overfitted)
  - YOLOv8: **mAP@50: 0.975** (~30ms inference)
- **The problem** (amber callout): *"High test metrics, but the model overfitted — it learned the training images, not the concept of 'seed'"*

**Speaker note**: Phase 1 detection with Faster R-CNN (YOLOv8 tested alongside). Strong test metrics but overfitting — foreshadow the data problem. Use the architecture diagram to stay conceptual, not layer-by-layer. → Next: the Phase 1 classifier and our four custom modifications.

---

#### SLIDE 15 — Phase 1 Classification: ResNet-18 + 4 Custom Modifications

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

**Speaker note**: The core AI contribution of Phase 1 — four deliberate modifications to ResNet-18 so it can catch tiny defects. Number them clearly and tie each to *why* (see small cracks, focus attention, catch sharp anomalies). → Next: an honest scorecard of what worked and what didn't.

---

#### SLIDE 16 — Phase 1 Results: What Worked, What Didn't

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

**Speaker note**: Honest scorecard — decoupling worked, maize was best (best data), but detection overfit and accuracy wasn't production-grade. The punchline: the bottleneck was **data**, not architecture. → Next: the insight that reframed the whole project.

---

#### SLIDE 17 — "We Hit a Wall — The Data Insight"

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

**Speaker note**: The turning point — we need ~100K images per type, and no public set has *both* boxes and quality labels. Two responses follow: a stronger classifier and our own data factory. → Next: the classifier upgrade.

---

### ═══ ACT IV: PHASE 2 — DEEPER MODELS + MULTISEEDGEN (7 slides) ═══

> This act covers the second iteration: upgrading the classifier, proving it works with heatmaps, and building MultiSeedGen to solve the detection data problem.

---

#### SLIDE 18 — Phase 2: Upgrading to EfficientNet-B2

**Layout**: Left = architecture comparison. Right = why the switch

**Content**:
- **The change**: Kept the same Faster R-CNN detection backbone, replaced **ResNet-18 → EfficientNet-B2** for classification
- **What's different** (architecture diagram with callouts — optional embed `docs/report/figures/18-Efficient-net-B2.pdf`):
  - EfficientNet-B2: compound scaling (depth × width × resolution) — more efficient feature extraction
  - **CBAM** retained (channel + spatial attention)
  - **Hybrid Pooling** retained (GAP + GMP → 1024 features)
  - Now supports **7-class multi-label** defect categorization (not just binary good/bad):
    Broken · Damage · Fungus · Healthy · Immature · Shriveled · Weeveled
- **Why it's better**: *"EfficientNet-B2 catches real physical characteristics and defects dramatically better than ResNet-18"*
- **Metric improvement** (comparison badges):
  - ResNet-18 Maize: F1 0.769 → **EfficientNet-B2 Maize: Macro-F1 0.974**

**Visual direction**: Show the upgrade as an evolution. Side-by-side architecture comparison. The metric jump (0.769 → 0.974) should be visually dramatic.

**Speaker note**: EfficientNet-B2 replaces ResNet-18, keeps CBAM + hybrid pooling, and goes from binary to 7-class multi-label. Land the metric jump (0.769 → 0.974). → Next: proof it's actually looking at the right thing.

---

#### SLIDE 19 — Proof: The Model Sees What Matters (Grad-CAM Heatmaps)   ⚠️ Image spread

**Layout**: Full-width, dark background. **SHOW-STOPPER SLIDE.** (Consider one heatmap per physical slide, then a 2×2 recap.)

**Content**:
- Title: *"EfficientNet-B2 + CBAM learns different attention patterns for each defect class"*
- Display all **4 heatmap images** (2×2 grid or one-per-slide sequence):
  - **Damage** (`docs/presentation/extra_files/heatmaps/damage.png`): focuses on dark lesion → Damage=1.00
  - **Healthy** (`docs/presentation/extra_files/heatmaps/healthy.png`): uniform activation across clean surface → Healthy=1.00
  - **Shriveled** (`docs/presentation/extra_files/heatmaps/shriveled.png`): focus on wrinkled deformation → Shriveled=1.00
  - **Weeveled** (`docs/presentation/extra_files/heatmaps/weeveled.png`): concentrated hotspot on bore-hole → Weeveled=1.00
- Each heatmap shows: **Input Image** + **7 class activation maps** (Broken, Damage, Fungus, Healthy, Immature, Shriveled, Weeveled) — correct class highlighted at 1.00, others at 0.00
- Legend: Red/yellow = high activation, Blue/purple = low activation
- Callout: *"This is the visual proof that the attention mechanism works — the model isn't guessing, it's looking at the right features"*

**Visual direction**: Dark "soil-night" background (`#121615`) makes the heatmap colors pop. Maximum visual real estate. This is the most compelling visual evidence in the entire presentation. Minimal text.

**Speaker note**: The show-stopper — Grad-CAM proves the attention mechanism focuses on the *actual* defect for each class, not the background. Minimal words; let the heatmaps land, maybe one per beat. → Next: but detection still needed help.

---

#### SLIDE 20 — "Detection Still Overfits — We Need Our Own Data"

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

**Speaker note**: Classification is solved; detection still overfits, and manual annotation can't scale. That's exactly why we built MultiSeedGen. → Next: how MultiSeedGen works.

---

#### SLIDE 21 — MultiSeedGen: Building Our Own Training Data

**Layout**: Pipeline diagram + output screenshot

**Content**:
- Pipeline flow (optional embed `docs/report/figures/14-multiseedgen-pipeline.pdf`):
  **Single-seed photos** → [**SEGMENT**: cut out the seed] → **Cut-out pool** → [**COMPOSITE**: place on backgrounds with collision physics] → **Dense multi-seed scenes** → [**DEGRADE**: camera simulation] → [**EXPORT**: YOLO/COCO with auto-labels]
- Embed **MultiseedGen-seeds_annotatedWithBB.jpg** — actual output: 15+ species auto-labeled with bounding boxes on a realistic tray
- Key callout: *"Labels come for free — the engine placed each seed, so it knows exactly where every one is"*
- Stats: *"6 segmentation backends · 15+ augmentation parameters · byte-reproducible output · ~20 seed species supported"*

**Visual direction**: Clean left-to-right pipeline with arrows. The screenshot proves the output is realistic and properly labeled.

**Speaker note**: MultiSeedGen is a synthetic data factory — and the killer property is that labels are **free**, because the engine placed each seed. Show the annotated output as proof. → Next: how we cut seeds out cleanly.

---

#### SLIDE 22 — Segmentation: 6 Ways to Cut a Seed

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

**Speaker note**: Six segmentation backends, from simple thresholding to Segment Anything, chosen per image with a tuner UI. Don't read all six — group as "classical → learned → promptable." → Next: how we make synthetic data look real.

---

#### SLIDE 23 — Augmentation & Domain Bridging

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

**Speaker note**: Augmentation plus domain bridging — and the single biggest lever was compositing onto **real** tray backgrounds. Emphasize the amber column; the before/after is the proof. → Next: the tool itself and the self-improving data loop.

---

#### SLIDE 24 — MultiSeedGen Web UI + Data Loop

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

**Speaker note**: MultiSeedGen is a full tool with its own web UI, and the data feedback loop aims the generator at the system's measured weaknesses — it's a strategy, not a one-shot script. → Next: the detection results after all of this.

---

### ═══ ACT V: FINAL RESULTS & EVIDENCE (4 slides) ═══

---

#### SLIDE 25 — Detection Experiments: The Full Journey

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

**Speaker note**: The full detection experiment journey — and the counter-intuitive lesson: lower test metrics can mean *better* real-world generalization. → Next: the same lesson, seen in classification.

---

#### SLIDE 26 — Classification: Data Quality > Model Architecture

**Layout**: Two-column comparison + convergence chart

**Content**:
- **LEFT — "Soybean (Lab Data)"**: Sterile backgrounds → **0.9936 F1** ❌ Overfitted, fails on real images
- **RIGHT — "Maize (Real-World Data)"**: Natural sunlight, phone captures → **0.974 F1** ✅ Generalizes
- Training progression: Epoch 1: 0.808 → Epoch 3: 0.925 → Epoch 5: 0.964 → **Epoch 7: 0.974**
- Callout: *"The model that scored lower on the test set performed better in the real world"*

**Speaker note**: Data quality beats architecture — the real-world maize model generalizes; the sterile-lab soybean model overfits despite a higher score. → Next: how we deploy for two very different needs.

---

#### SLIDE 27 — Speed vs. Precision: Two Deployment Modes

**Layout**: Two comparison cards + YOLO screenshot

**Content**:
- **LEFT — "Precision Mode"**: Faster R-CNN + EfficientNet-B2 · ~230ms · ~4.3 FPS · 7-class multi-label · Best for QA labs
- **RIGHT — "Speed Mode"**: YOLOv8 · ~80ms · ~12.5 FPS · Real-time · Best for conveyor belts
- Embed **YOLO-realtime.png**: 876 seeds detected in a single dense frame — a **detection-model demo** of speed-mode throughput
- Note: *"Both run on commodity hardware (RTX 3060). The shipped mobile app also has a **realtime mode** that streams camera frames one at a time and shows a running good/bad tally."*

**Visual direction**: Keep the 876-seed image labeled as a *model demo* — it shows raw detection density, not a product screen. The product's realtime experience is the mobile frame-streaming mode (shown in Act VI).

**Speaker note**: Two deployment modes — precision (Faster R-CNN + EfficientNet-B2) vs speed (YOLOv8). Be precise: the 876-seed image is a **model demo** of dense detection; the *product* realtime experience is the mobile frame-streaming mode we'll show shortly. → Next: how we compare to what's already out there.

---

#### SLIDE 28 — Competitor Landscape

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

**Speaker note**: Where we sit — affordable, accessible, multi-crop, fine-grained, and extensible. Highlight the column that's all-green (us). → Next: the models are only half the story — now the platform that makes them a real product.

---

### ═══ ACT VI: THE PLATFORM & ENGINEERING (8 slides) ═══

> The bridge from research to product. A trained model helps no one until real people can
> use it. This act peels the platform back one layer at a time — what users see, how it's
> built, how a request flows, how every result stays traceable, and how it's kept safe —
> and hands the model-lifecycle thread back to the AI story.

---

#### SLIDE 29 — From Trained Models to a Real Product   *(bridge slide)*

**Layout**: Split — "research artifact" → "production product"

**Content**:
- Headline: *"A model in a notebook helps no one."*
- LEFT: a lone `.pth` weights file / notebook icon — *"trained model"*
- Arrow → RIGHT: web + mobile app icons, users — *"a platform two audiences use every day"*
- Three anchor words for what "productizing" took: **Usable · Traceable · Secure**
- Sub-caption: *"The engineering team turned the detect→classify pipeline into a live web + mobile product with a full model platform behind it"*

**Visual direction**: Clean, symbolic. This is the hinge of the talk — pause here.

**Speaker note**: This is the seam. Everything so far was research; now we turn it into something a farmer and a QA lab actually use — the IS/backend team's contribution. The three anchor words (usable, traceable, secure) map to the next few slides. → Next: let's see it running.

---

#### SLIDE 30 — Live App Showcase   ⚠️ Image spread (build as 2–3 physical slides)

**Layout**: Screenshot gallery / walkthrough

**Content** (walk the farmer journey, then a peek at the ML side):
- Embed **MobileView.png** + **Dashboard.png** — *"capture on mobile, review on web"*
- Embed **web-batch-detail.png** — *"AI Insights: good-rate donut, confidence histogram, interactive bounding boxes"*
- Embed **Models_managment.png** — *"and behind it, an ML platform for the developers"*
- One-line captions only; let the product speak

**Visual direction**: Give each screenshot room — this is where you spread across 2–3 slides. Consistent framing/device mockups.

**Speaker note**: Walk the real farmer journey through the screenshots — capture, analyze, review the insights — then reveal there's a whole ML platform behind it. Keep captions to one line each. → Next: who uses which part, and in which language.

---

#### SLIDE 31 — One Platform, Two Audiences — in Two Languages   *(NEW)*

**Layout**: Two role cards on top + an EN/AR side-by-side below

**Content**:
- **Two role-gated surfaces from one backend**:
  - 👩‍🌾 **Farmer (end user)** — capture, analyze, history, share a read-only report
  - 🧑‍🔬 **AI developer / admin** — models, datasets, experiments, user management
- **Fully bilingual**: **English + Arabic** with **complete RTL layout mirroring** — on **web AND mobile**
- Side-by-side: the same screen in English and in Arabic (mirrored) — *use the captured EN + AR screenshots (see capture checklist)*
- Caption: *"Every user-facing string is translated; the whole layout flips for Arabic — not an afterthought"*

**Visual direction**: The EN/AR mirror is the money shot — put them literally side by side so the RTL flip is obvious. Optionally use the `12a/12b/12c-usecase-*.pdf` diagrams to show the role split.

**Speaker note**: One platform, two role-gated audiences, and it's fully bilingual EN/AR with mirrored RTL on **both** web and mobile — a real accessibility win most projects skip entirely. The side-by-side makes the RTL flip undeniable. → Next: what's under the hood.

---

#### SLIDE 32 — System Architecture

**Layout**: Conceptual architecture diagram (use `02-containers-app.pdf` + `02-containers-datastores.pdf`)

**Content**:
- **Clients**: Web App (React 18 + TypeScript + Vite) + Mobile App (Expo SDK 56 / React Native) — EN/AR
- **Backend**: FastAPI — **async end-to-end**, **cleanly layered** (routers → services → repositories) with JWT auth + RBAC
- **Datastores**: PostgreSQL (16 tables, UUIDv7) · Redis (cache + Celery broker) · MinIO (images, weights) · ClickHouse (analytics)
- **Workers**: `worker-inference` (torch: detect→classify) · `worker-cpu` (analytics + experiments, no torch)
- Label: *"7 core services · Docker Compose · one command (`docker compose up`)"*

**Visual direction**: Conceptual flow, not implementation detail. Two clear tiers (clients → backend) feeding four datastores + two worker types. *This is the deep dive on the high-level view from Slide 12.*

**Speaker note**: The payoff of the high-level architecture we teased at Slide 12 — clean layered design, async end-to-end, seven core services that come up with one command. The layering is *why* each piece is swappable and testable; don't go deeper than that. → Next: let's follow one photo all the way through.

---

#### SLIDE 33 — The Analyze Pipeline, End-to-End

**Layout**: Horizontal flow + a small state-machine inset (use `06-analyze-sequence.pdf` + `07-batch-state-machine.pdf`)

**Content**:
- Flow (conceptual):
  1. `POST /analyze` (photos + optional metadata)
  2. Validate every file → upload to MinIO → create batch (`pending`) → commit
  3. Dispatch one background job per image
  4. Per image: **DETECT** (find seeds) → **CROP** each seed → **GROUP** by seed type → **CLASSIFY** each group with its crop-specific model
  5. Batch state machine: `pending → running → succeeded / partial / failed`
  6. Client polls until a terminal status
- Callout: *"Concurrency-safe state machine · per-seed-type routing · graceful partial results"*

**Visual direction**: One clean left-to-right flow. The state machine can be a small inset showing the transitions.

**Speaker note**: Trace a single analyze request end-to-end — this is the two-stage pipeline from Slide 13 in motion: the fan-out (one image → many seeds → many labels), the per-seed-type routing, and the concurrency-safe state machine that lets a mixed batch degrade gracefully to "partial" instead of failing. → Next: how every result stays traceable to a model.

---

#### SLIDE 34 — Model Traceability & Lifecycle   *(the seam back to the ML story)*

**Layout**: Chain diagram + 3-step lifecycle (use `09-ml-platform.pdf` + `16-model-resolution.pdf`)

**Content**:
- **Traceability chain**: Seed Detection → (FK) → Inference → (FK) → Model Artifact
  - *"Every single verdict traces back to the exact model version that produced it"*
- **Model lifecycle** (3 cards):
  1. 📦 **Register** — upload weights, assign builder, set config
  2. 🧪 **Evaluate** — offline experiments against labelled datasets
  3. 🚀 **Promote** — `registered → staging → production → archived`
- **ModelResolver**: picks the `production` model per `(kind, seed_type_id)` segment, with a global fallback — swapping the live model is a **promotion, not a code change**

**Visual direction**: The FK chain is the hero. The lifecycle is a simple three-step ribbon.

**Speaker note**: This is the seam back to the AI story — every detection links by foreign key to the exact model version, and models move register → evaluate → promote, with the resolver always serving the current production model. Swapping models is a promotion, not a redeploy. → Next: how we keep all of this secure.

---

#### SLIDE 35 — Secure by Design   *(NEW — keep it high-level)*

**Layout**: 4 icon+caption pairs (optionally `08-auth-sequence.pdf`)

**Content**:
- 🔑 **JWT + refresh-token rotation** — short-lived access tokens; a reused refresh token invalidates the chain (replay-safe)
- 🔗 **Google OAuth** — social sign-in alongside email/password
- 👥 **Role-based access** — `end_user` · `ai_developer` · `admin`, enforced on every route
- 📜 **Append-only audit log + one stable error shape** — sensitive actions are recorded; all errors return a consistent, typed response (RFC 9457)

**Visual direction**: Four clean tiles. No deep detail — this is a "we did auth properly" slide.

**Speaker note**: Security done properly for a student project — rotating refresh tokens with replay detection, OAuth, real role-based access, an audit trail, and one consistent error contract. Keep it to the four tiles; don't rabbit-hole. → Next: the full toolset at a glance.

---

#### SLIDE 36 — Tech Stack at a Glance

**Layout**: Grouped icon grid

**Content** (icons + names only):
- 🤖 **AI / ML**: PyTorch · torchvision (Faster R-CNN) · EfficientNet-B2 (timm) · Ultralytics YOLOv8 · OpenCV · rembg (U²-Net) · Pillow · NumPy
- 🧬 **MultiSeedGen** *(separate data tool)*: classical-CV + rembg + **SAM** segmentation · React + FastAPI web UI
- 🖥️ **Web**: React 18 · TypeScript · Vite · Tailwind · shadcn/ui (Radix) · TanStack Query · React Hook Form + Zod · openapi-fetch (typed client) · jsPDF (report export) · lucide-react
- 📱 **Mobile**: Expo SDK 56 · React Native 0.85 · expo-camera · React Navigation
- ⚙️ **Backend**: FastAPI · Python 3.12 · Celery · SQLAlchemy 2 (async) · Pydantic v2 · Alembic
- 💾 **Data**: PostgreSQL 16 · ClickHouse · Redis 7 · MinIO
- 🐳 **Infra**: Docker · multi-stage Dockerfile (CPU / GPU) · nginx
- 🔒 **Security**: JWT + refresh rotation · OAuth (Google) · RBAC

**Visual direction**: Grouped tiles, one row per group. Don't crowd — breadth is the message.

**Speaker note**: A quick grouped inventory — don't read every item, let it convey breadth and coherence. Note that SAM lives in MultiSeedGen, our separate data tool, not the runtime backend. → Next: what we learned.

---

### ═══ ACT VII: CLOSING (3 slides) ═══

---

#### SLIDE 37 — Key Takeaways

**Layout**: 3 large insight cards

**Content**:
1. 📊 **"Data quality matters more than model architecture"** — *The maize model outperformed because its training data matched the real world*
2. 🔀 **"Decouple detection from classification"** — *Independent stages let us diagnose and swap each without disturbing the other*
3. 🏭 **"Synthetic data narrows the gap — but always test on real photos"** — *MultiSeedGen eliminated the annotation bottleneck; real evaluation is the only fair test*

**Speaker note**: Three durable lessons — data > architecture, decouple the two stages, and synthetic data narrows the gap but real evaluation is the only fair test. These are the sentences you want the room to remember. → Next: where it goes from here.

---

#### SLIDE 38 — Future Roadmap

**Layout**: Visual timeline with 4 milestones

**Content**:
- 🌿 **"More Crops"** — expand real-world datasets for all 20+ species
- 📱 **"Edge AI"** — on-device quantized inference, no internet needed
- 🔄 **"Active Learning"** — low-confidence scans feed back into MultiSeedGen
- 🏭 **"Hardware-Integrated Conveyor"** — a realtime frame-streaming mode already ships on mobile; next is fixed-camera conveyor integration + instance segmentation for overlapping seeds

**Speaker note**: Future work — more crops, edge AI, active learning; and note honestly that a realtime frame mode *already ships*, so the frontier is hardware-integrated conveyor lines and instance segmentation for overlap, not realtime itself. → Next: thanks and questions.

---

#### SLIDE 39 — Team + Thank You + Questions

**Layout**: Warm, centered

**Content**:
- Team photos/avatars in two groups (AI + IS)
- *"Special thanks to"*: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed
- **"Seed Bank"** logo
- **"Thank You · Questions?"**
- University logos (`docs/report/logos/`)

**Speaker note**: Thank the supervisors, credit both sub-teams explicitly (research *and* engineering), and open the floor warmly. End on the logo.

---

## Slide → Asset Map

Repo-root-relative paths. Screenshots: `docs/report/figures/screenshots/`.
Diagrams (PDF): `docs/report/figures/`. Heatmaps: `docs/presentation/extra_files/heatmaps/`.
Logos: `docs/report/logos/`.

| Slide | Screenshots | Diagrams (PDF) |
|---|---|---|
| 1 Title | — | logos: `Cairo_University_new_logo.png`, `FCAI.jpg` |
| 3 Pitch | `Dashboard.png`, `MobileView.png` | — |
| 10 Solution | — | `01-system-context.pdf` (optional teaser) |
| 12 Architecture 1/2 (system) | — | `01-system-context.pdf`, `02-containers-app.pdf`, `02-containers-datastores.pdf` |
| 13 Architecture 2/2 (pipeline) | — | `04-worker-components-pipeline.pdf` (optional) |
| 14 Faster R-CNN | — | `17-fasterRCNN-architecture.pdf` |
| 18 EfficientNet-B2 | — | `18-Efficient-net-B2.pdf` |
| 19 Heatmaps | heatmaps: `damage/healthy/shriveled/weeveled.png` | — |
| 21 MultiSeedGen | `MultiseedGen-seeds_annotatedWithBB.jpg` | `14-multiseedgen-pipeline.pdf` |
| 22 Segmentation | `seg-tuner.png` | — |
| 27 Speed vs Precision | `YOLO-realtime.png` (label: model demo) | — |
| 30 App Showcase | `MobileView.png`, `Dashboard.png`, `web-batch-detail.png`, `Models_managment.png` | — |
| 31 Two audiences + RTL | *EN + AR screenshots (capture)* | `12a/12b/12c-usecase-*.pdf` (optional) |
| 32 Architecture (detailed) | — | `02-containers-app.pdf`, `02-containers-datastores.pdf`, `01-system-context.pdf` |
| 33 Analyze pipeline | — | `06-analyze-sequence.pdf`, `07-batch-state-machine.pdf` |
| 34 Traceability | `Models_managment.png` (optional) | `09-ml-platform.pdf`, `16-model-resolution.pdf` |
| 35 Secure by design | — | `08-auth-sequence.pdf` (optional) |
| 39 Team | — | logos |

---

## Capture Checklist — screenshots worth adding

The deck works with the assets above, but a handful of **new product screenshots**
would meaningfully strengthen Act VI. Capture each by running the app and navigating:

**Web** (run the frontend, log in, navigate, screenshot the page):
- [ ] **Analyze / upload page** — drag-drop + optional metadata (Slide 30)
- [ ] **Analytics page** — trends, quality-by-seed-type (Slide 30)
- [ ] **Compare page** — 2+ scans side by side (Slide 30)
- [ ] **Datasets & Experiments** admin pages — the ML platform depth (Slide 34)
- [ ] **Dashboard in Arabic** — same screen, RTL-mirrored (Slide 31) ← *high value*

**Mobile** (Expo — device or emulator with a virtual camera):
- [ ] **Camera capture** with framing guide (Slide 30)
- [ ] **Result screen** — good-rate, counts, confidence (Slide 30)
- [ ] **Realtime mode** — live frame streaming + running tally (Slides 27, 30)
- [ ] **History** and **Settings** (Settings shows the EN/AR + theme toggles) (Slide 30)
- [ ] **Any screen in Arabic** — RTL-mirrored (Slide 31) ← *high value*

*(Deliberately out of scope: infra/monitoring screenshots — they don't serve this
deck's narrative.)*

> **Optional tidy-up**: consolidate all deck assets into one `docs/presentation/assets/`
> folder (copy the screenshots, heatmaps, chosen diagram PDFs, and logos there) so the
> presentation folder is self-contained when handed to whoever builds the slides.

---

## The Development / Platform Story (Speaker Notes Summary)

For the presenter delivering Act VI, the through-line:

> **"Everything up to here was research — trained models living in notebooks. A model
> that can't be reached by a real user isn't a product. So we engineered the
> detect→classify pipeline into a live platform, and it had to be three things:
> **usable**, **traceable**, and **secure**.**
>
> **Usable: a React web app and an Expo mobile app, both fully bilingual English/Arabic
> with the entire layout mirrored for right-to-left — serving two role-gated audiences
> (farmers, and AI developers/admins) from one backend.**
>
> **Under the hood it's a cleanly layered, async FastAPI service — seven core services
> that come up with a single `docker compose up`. When you submit a photo, it's
> validated, stored, and processed by background workers that detect every seed, crop
> each one, group by seed type, and classify each group with its own model — all behind
> a concurrency-safe state machine that returns partial results instead of failing.**
>
> **Traceable: every verdict links by foreign key to the exact model version that
> produced it, and models move through a register → evaluate → promote lifecycle —
> swapping the live model is a promotion, not a code change. Secure: rotating refresh
> tokens with replay detection, OAuth, real role-based access, and an audit trail.**
>
> **That's what turned a set of strong models into a product two very different users
> can actually rely on."**

---

## The AI Development Story (Speaker Notes Summary)

For the presenter, the chronological AI story that threads through Acts II–V:

> **"We started by exploring if traditional ML could solve seed quality classification —
> extracting features like size ratios, color histograms, and texture patterns. But
> seeds are morphologically complex, and hand-crafted features couldn't generalize
> across species and conditions. So we pivoted to Computer Vision and deep learning.**
>
> **We designed a two-stage pipeline: detect each seed first, then classify its quality.
> In Phase 1 we used Faster R-CNN for detection and ResNet-18 with 4 custom
> modifications (stride reduction, CBAM attention, hybrid pooling, binary head). We also
> tried YOLO — it performed comparably. Maize worked best because it had the highest
> quality dataset, but even it overfitted.**
>
> **We studied the problem more deeply and realized we need ~100K images per seed type.
> So we made two moves: we upgraded classification to EfficientNet-B2 (which went from
> binary to 7-class multi-label and caught real defects dramatically better — the
> heatmaps prove it), and we built MultiSeedGen to generate unlimited, perfectly-labeled
> detection training data.**
>
> **MultiSeedGen segments seeds from single-seed photos using 6 different backends (from
> simple thresholding to Segment Anything), composites them into dense realistic scenes
> with collision physics and domain-matched augmentations, and exports them with
> automatic bounding-box labels. The single most impactful setting was compositing onto
> real tray backgrounds extracted from source photos.**
>
> **The end result: we trained on 40 total seed types and achieved strong performance —
> especially on the highest quality datasets like maize (0.974 Macro-F1 for
> classification). The system now runs as a full platform with web and mobile apps,
> model traceability, and production-grade engineering."**
