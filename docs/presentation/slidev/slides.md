---
title: Seed Bank — AI-Powered Seed Quality Intelligence
info: Graduation project — Faculty of Computers and AI, Cairo University
transition: fade
aspectRatio: 16/9
canvasWidth: 1280
fonts:
  provider: none
  sans: Inter
drawings:
  persist: false
class: cover-slide
---

<!-- SLIDE 1 — Title -->

<div v-motion :initial="{ opacity: 0, y: 30 }" :enter="{ opacity: 1, y: 0, transition: { duration: 700 } }">

# Seed Bank

## AI-Powered Seed Quality Intelligence

</div>

<div class="inst">Faculty of Computers and Artificial Intelligence · Cairo University</div>
<div class="sup">Supervisors: Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed</div>

<div class="teams">
  <div><span class="tag">AI</span> Omar Ez-Eldin Abdullah · Yussuf Ahmed Awad</div>
  <div><span class="tag">IS</span> Ali Abdelrahman · Mohamed Amr · Youssef Tarek Ali</div>
</div>

<div class="logos" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 400 } }">
  <img src="./media/logos/Cairo_University_new_logo.png" alt="Cairo University" />
  <img src="./media/logos/FCAI.jpg" alt="FCAI" />
</div>

<!--
Open warm and confident — "We built an AI platform that grades seed quality from a single
photo — usable by a farmer in a field or a QA lab." Name the two sub-teams (AI + IS) so the
audience knows the project spans research and a production system.
→ Next: the playful hook — why a "seed bank" in computer science?
-->

---
class: center-slide
---

<!-- SLIDE 2 — A Seed Bank in Computer Science? -->

<div class="act-tag">Act I · The Problem</div>

# A Seed Bank… in Computer Science?

<div class="grid2" style="margin-top:1.6rem; align-items:center;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
  <div class="card accent center" style="padding:2rem 1rem;">
    <div class="chip-ic" style="margin:0 auto 0.6rem; width:3.4rem; height:3.4rem;"><img src="./media/icons/warehouse.png" /></div>
    <h3>A storage vault?</h3>
    <p class="mut">Preserving seeds for the future</p>
  </div>
  <div class="card accent center" style="padding:2rem 1rem;">
    <div class="chip-ic" style="margin:0 auto 0.6rem; width:3.4rem; height:3.4rem;"><img src="./media/icons/brain-circuit.png" /></div>
    <h3>…or seed intelligence?</h3>
    <p class="mut">AI that grades seed quality</p>
  </div>
</div>

<div class="center" style="font-size:4rem; font-weight:700; color:var(--amber); margin-top:0.8rem;">?</div>

<!--
Let the visual do the work — pause on the "?". Ask the room what "seed bank" evokes, then
reveal we mean seed-quality intelligence, not a storage vault.
→ Next: the 30-second version of what it actually does.
-->

---

<!-- SLIDE 3 — The 30-Second Pitch -->

<div class="act-tag">Act I · The Problem</div>

# The 30-Second Pitch

<div class="pipeline" style="margin:0.6rem 0 1.2rem;">
  <div class="stage io"><img class="ic" src="./media/icons/camera.png" /> Photograph seeds</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/cpu.png" /> AI analyzes</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/bar-chart-3.png" /> Quality report</div>
</div>

<div class="grid2" v-motion :initial="{ opacity: 0, y: 26 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 250 } }">
  <div class="diagram"><img src="./media/screenshots/Dashboard.png" /></div>
  <div class="diagram"><img src="./media/screenshots/MobileView.png" /></div>
</div>

<p class="lead center" style="margin-top:0.9rem;">A platform for farmers and QA labs to <strong>instantly grade seed quality</strong> using computer vision — on web and mobile.</p>

<!--
The whole product in one breath — photograph → analyze → report, on web and mobile. Keep it
to three beats; details come later. → Next: who actually needs this.
-->

---

<!-- SLIDE 4 — Who Is This For? -->

<div class="act-tag">Act I · The Problem</div>

# Who Is This For?

<div class="grid2" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/tractor.png" /></div><div class="tx"><h3>The Farmer</h3><p class="mut">Checking quality in the field</p></div></div>
    <div class="pills" style="justify-content:flex-start; margin-top:0.8rem;">
      <span class="pill"><img src="./media/icons/clock.png" /> Slow counting</span>
      <span class="pill"><img src="./media/icons/help-circle.png" /> Subjective</span>
      <span class="pill"><img src="./media/icons/smartphone.png" /> No digital tools</span>
    </div>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/flask-conical.png" /></div><div class="tx"><h3>The QA Laboratory</h3><p class="mut">Grading at throughput</p></div></div>
    <div class="pills" style="justify-content:flex-start; margin-top:0.8rem;">
      <span class="pill"><img src="./media/icons/bar-chart-3.png" /> Needs throughput</span>
      <span class="pill"><img src="./media/icons/target.png" /> Needs objectivity</span>
      <span class="pill"><img src="./media/icons/dollar-sign.png" /> Machines too costly</span>
    </div>
  </div>
</div>

<p class="lead center" style="margin-top:1rem;">Two audiences, two pains — and <strong>one backend serves both</strong>.</p>

<!--
Two audiences, two different pains — the farmer wants speed and objectivity; the lab wants
throughput without a six-figure machine. Stress that one backend serves both (paid off in the
platform act). → Next: what today's manual grading looks like.
-->

---

<!-- SLIDE 5 — The Problem: Manual Grading -->

<div class="act-tag">Act I · The Problem</div>

# The Problem: Manual Grading

<div class="center" style="margin:1.2rem 0;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 200 } }">
  <div class="chip-ic" style="width:5rem; height:5rem; margin:0 auto; border-radius:1rem;"><img src="./media/icons/hand.png" style="width:2.8rem; height:2.8rem;" /></div>
  <p class="mut" style="margin-top:0.5rem;">Sorting seeds by hand, one tray at a time</p>
</div>

<div class="pills" style="margin-top:0.6rem;">
  <span class="pill"><img src="./media/icons/clock.png" /> Slow</span>
  <span class="pill"><img src="./media/icons/help-circle.png" /> Subjective</span>
  <span class="pill"><img src="./media/icons/x-red.png" /> Inconsistent</span>
  <span class="pill"><img src="./media/icons/trending-down-red.png" /> Can't scale</span>
</div>

<!--
Manual grading is slow, subjective, inconsistent, and doesn't scale — the core pain in four
words. → Next: the market gap between manual and industrial.
-->

---

<!-- SLIDE 6 — The Technology Gap -->

<div class="act-tag">Act I · The Problem</div>

# The Technology Gap

<div class="pipeline" style="margin-top:1.4rem; gap:1rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/factory.png" /></div>
    <h3>Industrial Optical Sorters</h3>
    <p class="bad" style="font-weight:700; font-size:1.1rem;">$$$$$</p>
  </div>
  <div class="card amber center" style="flex:1.1;">
    <h3 style="color:var(--leaf-deep);">Nothing affordable here</h3>
    <div class="chip-ic" style="margin:0.4rem auto; background:transparent;"><img src="./media/icons/leaf.png" style="width:1.8rem;height:1.8rem;" /></div>
    <p style="color:var(--leaf-deep); font-weight:700;">Seed Bank fills this gap</p>
  </div>
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/hand.png" /></div>
    <h3>Manual Counting</h3>
    <p class="mut">Cheap, but slow &amp; subjective</p>
  </div>
</div>

<!--
There's nothing affordable between hand-counting and industrial optical sorters — that empty
middle is our wedge. → Next: why this is genuinely hard for AI.
-->

---

<!-- SLIDE 7 — Why Seeds Are Hard for AI -->

<div class="act-tag">Act I · The Problem</div>

# Why Seeds Are Hard for AI

<div class="grid4" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/layers.png" /></div><h3>Overlap &amp; Clutter</h3></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/sun.png" /></div><h3>Lighting Variation</h3></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/zoom-in.png" /></div><h3>Subtle Defects</h3></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/help-circle.png" /></div><h3>Natural ≈ Damaged</h3></div>
</div>

<p class="lead center" style="margin-top:1.1rem;"><em>Seeds aren't manufactured parts — they're organic and irregular.</em></p>

<!--
Seeds are organic — overlap, lighting, subtle defects, and healthy-looks-damaged ambiguity.
Not clean manufactured parts. → Next: and the data behind that difficulty.
-->

---

<!-- SLIDE 8 — The Data Problem -->

<div class="act-tag">Act I · The Problem</div>

# The Data Problem

<div class="grid3" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/bar-chart-3.png" /></div><div class="tx"><h3>Volume Gap</h3><p>Need ~100K images; best public sets have &lt;20K</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/tags.png" /></div><div class="tx"><h3>Annotation Mismatch</h3><p>Detection sets have boxes but no quality. Classification sets have labels but no boxes. None has both.</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/microscope.png" /></div><div class="tx"><h3>Lab ≠ Real World</h3><p>Lab-trained models fail on real-world phone photos</p></div></div></div>
</div>

<p class="lead center" style="margin-top:1.1rem;">These three problems set up the entire AI journey that follows.</p>

<!--
Three data problems — volume, annotation mismatch, lab≠real-world — are the seeds (pun
intended) of the whole journey. Plant them now; Acts III–IV pay them off.
→ Next: could classic machine learning even solve this?
-->

---

<!-- SLIDE 9 — Can Machine Learning Solve This? -->

<div class="act-tag">Act II · From ML to Computer Vision</div>

# Can Machine Learning Solve This?

<div class="grid2" style="margin-top:0.4rem; align-items:center;">
<div>

<p class="lead">We began by asking: can we hand-craft features — size, shape, colour, texture ratios — and classify quality with traditional ML?</p>

<div class="pipeline" style="justify-content:flex-start;" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 200 } }">
  <div class="stage io"><img class="ic" src="./media/icons/image.png" /> Seed image</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/ruler.png" /> Measure features</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/cpu.png" /> ML classifier</div>
</div>

</div>

<div class="warn" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 550, delay: 350 } }">
  <div class="icard"><img class="ic" src="./media/icons/alert-amber.png" style="width:1.6rem;height:1.6rem;" /><div><strong>The discovery:</strong> seeds are morphologically complex — hand-crafted features can't generalize across species, defects, and environments.</div></div>
</div>

</div>

<!--
We started honestly with hand-crafted features and classic ML — frame it as diligent, not
naive. The discovery: those features don't generalize across species and conditions.
→ Next: the solution we propose.
-->

---
class: arch-slide
---

<!-- SLIDE 10 — The Proposed Solution -->

<div class="act-tag">Act II · From ML to Computer Vision</div>

# The Proposed Solution

<div class="thesis">"Grade seed quality from an ordinary photo — and manufacture the training data that makes it possible."</div>

<div class="grid2" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/sprout.png" /></div><div class="tx"><h3>Seed Bank — the platform</h3></div></div>
    <ul style="margin-top:0.5rem;">
      <li>Photo → <strong>find every seed</strong> → <strong>grade each</strong> → aggregate report</li>
      <li>Every verdict <strong>traceable</strong> to its model</li>
      <li>Model management + offline evaluation</li>
      <li>A <strong>web + mobile</strong> app a farmer can use</li>
    </ul>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/dna.png" /></div><div class="tx"><h3>MultiSeedGen — the data factory</h3></div></div>
    <ul style="margin-top:0.5rem;">
      <li>Cut real seeds from single-seed photos</li>
      <li><strong>Composite</strong> onto realistic backgrounds + camera noise</li>
      <li>Export <strong>fully-labelled</strong> detection datasets</li>
      <li><em>The tool places every seed — labels come for free</em></li>
    </ul>
  </div>
</div>

<div class="pills" style="margin-top:0.9rem;">
  <span class="pill"><img src="./media/icons/dollar-sign.png" /> No expensive rig — ordinary single-view photos</span>
  <span class="pill"><img src="./media/icons/database.png" /> Closes the ~100K-image data gap</span>
</div>

<!--
Before any model details, here's the entire solution on one slide — a platform that grades
seeds from a normal photo, and a data factory that generates the labelled images the detector
needs. Two problems from earlier — cost and data — one deliverable each.
→ Next: why this had to be a computer-vision solution.
-->

---

<!-- SLIDE 11 — Pivoting to Computer Vision -->

<div class="act-tag">Act II · From ML to Computer Vision</div>

# Pivoting to Computer Vision

<div class="pipeline" style="margin:0.4rem 0 1rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="stage io" style="text-decoration:line-through; opacity:0.6;">Hand-crafted features → classifier</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/cpu.png" /> Raw image → CNN → learned features → classifier</div>
</div>

<p class="lead center">Deep learning extracts generalized features automatically — so we reframed this as a <strong>Computer Vision</strong> problem, with two distinct tasks:</p>

<div class="grid2" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/scan.png" /></div><div class="tx"><h3>Task 1 — Where is each seed?</h3><p>Object Detection</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/badge-check.png" /></div><div class="tx"><h3>Task 2 — What's wrong with it?</h3><p>Quality Classification</p></div></div></div>
</div>

<div class="fwd center" style="margin-top:0.9rem;">▸ This led us to the proposed system architecture — Slides 12–13</div>

<!--
The pivot to deep learning, plus the key reframe: two distinct tasks — where is each seed, and
what's wrong with it. → Next: those two tasks shape our proposed system architecture.
-->

---
class: arch-slide
---

<!-- SLIDE 12 — Proposed System Architecture (1/2) -->

<div class="act-tag">Act II · From ML to Computer Vision</div>

# Proposed System Architecture <span class="amber">(1/2)</span>

<h2>The System at a Glance</h2>

<div class="arch-grid">

<div>
<div class="pieces">
  <div class="piece"><div class="ico"><img src="./media/icons/clients.png" alt="" /></div><div><div class="t">Clients</div><div class="d">A React web app + an Expo mobile app (English / Arabic)</div></div></div>
  <div class="piece"><div class="ico"><img src="./media/icons/backend.png" alt="" /></div><div><div class="t">FastAPI backend</div><div class="d">Accepts a batch, records it, responds fast — async & cleanly layered</div></div></div>
  <div class="piece"><div class="ico"><img src="./media/icons/workers.png" alt="" /></div><div><div class="t">Background workers</div><div class="d">The heavy <strong>detect → classify</strong> work runs <em>off</em> the request path</div></div></div>
  <div class="piece"><div class="ico"><img src="./media/icons/datastores.png" alt="" /></div><div><div class="t">Datastores</div><div class="d">PostgreSQL · ClickHouse · MinIO · Redis</div></div></div>
</div>

<div class="callout">Inference is heavy, so it never runs inside the request the user is waiting on — the API stays responsive.</div>
<div class="fwd">▸ Full container topology at Slide 32 · a live request traced end-to-end at Slide 33</div>
</div>

<img src="./media/diagrams/01-system-context.png" class="hero" alt="System context diagram"
  v-motion :initial="{ opacity: 0, scale: 0.9 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 700, delay: 250 } }" />

</div>

<!--
The system in one picture — clients talk to a fast API, which hands the heavy model work to
background workers, with four datastores behind them. The one idea to land: inference never
blocks the user's request. Keep it conceptual; the deep dive is in the platform act.
→ Next: the two-stage pipeline at the core of it.
-->

---

<!-- SLIDE 13 — Proposed System Architecture (2/2) -->

<div class="act-tag">Act II · From ML to Computer Vision</div>

# Proposed System Architecture <span class="amber">(2/2)</span>

<h2>The Two-Stage Detect → Classify Pipeline</h2>

<div class="pipeline" style="margin:0.8rem 0;" v-motion :initial="{ opacity: 0, scale: 0.95 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
  <div class="stage io"><img class="ic" src="./media/icons/camera.png" /> Input image</div>
  <span class="arrow">→</span>
  <div class="stage detect"><img class="ic" src="./media/icons/scan.png" /> Stage 1 · Detection<small>Find every seed + type</small></div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/crop.png" /> Crop + group<small>by seed type</small></div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/badge-check.png" /> Stage 2 · Classification<small>Grade good / bad</small></div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/bar-chart-3.png" /> Quality report</div>
</div>

<div class="grid2" style="align-items:center;">
  <p class="lead">One detector for all seeds. One classifier per crop type. Each stage <strong>versioned &amp; optimized independently.</strong></p>
  <div class="card accent center"><div class="stat-huge" style="font-size:1.8rem;">1 image → N detections → N labels</div><p class="mut">the data fan-out</p></div>
</div>

<div class="fwd center" style="margin-top:0.7rem;">▸ The engineering behind it — concurrency-safe batching, per-type routing — is at Slide 33</div>

<!--
This is the architectural spine of the entire project — detect, then classify — and we'll point
back to it repeatedly, including in the platform act. → Next: Phase 1, how we first built the detector.
-->

---

<!-- SLIDE 14 — Phase 1 Detection: Faster R-CNN -->

<div class="act-tag">Act III · Phase 1 — First Pipeline</div>

# Phase 1 Detection: Faster R-CNN

<div class="grid2" style="align-items:center; margin-top:0.4rem;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.92 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/17-fasterRCNN-architecture.png" />
  </div>
  <div>
    <p class="lead">ResNet-50 backbone + FPN → region proposals → 3 classes <span class="mut">[background, coffee, maize]</span>. YOLOv8 tested alongside — comparable at this stage.</p>
    <div class="badges" style="margin-top:0.4rem;">
      <div class="badge"><div class="num">0.98</div><div class="lab">Faster R-CNN mAP@50</div></div>
      <div class="badge"><div class="num">0.975</div><div class="lab">YOLOv8 mAP@50 · ~30ms</div></div>
    </div>
    <div class="warn" style="margin-top:0.8rem;"><strong>The problem:</strong> high test metrics, but the model <em>overfitted</em> — it learned the training images, not the concept of "seed".</div>
  </div>
</div>

<!--
Phase 1 detection with Faster R-CNN (YOLOv8 tested alongside). Strong test metrics but
overfitting — foreshadow the data problem. Keep the diagram conceptual.
→ Next: the Phase 1 classifier and our four custom modifications.
-->

---

<!-- SLIDE 15 — Phase 1 Classification: ResNet-18 + 4 mods -->

<div class="act-tag">Act III · Phase 1 — First Pipeline</div>

# Phase 1 Classification: ResNet-18 + 4 Custom Modifications

<div class="grid4" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/zoom-in.png" /></div><h3>1 · Stride → (1,1)</h3><p>Less downsampling — sees hairline cracks &amp; tiny discolorations</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/eye.png" /></div><h3>2 · CBAM attention</h3><p>Forces focus on defect-relevant regions, not background</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/shuffle.png" /></div><h3>3 · Hybrid pooling</h3><p>GMP + GAP — general patterns AND sharp anomalies</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/binary.png" /></div><h3>4 · Binary head</h3><p>good vs. bad with BCEWithLogitsLoss</p></div>
</div>

<div class="badges" style="margin-top:0.9rem; justify-content:center;">
  <div class="badge"><div class="num">83.18%</div><div class="lab">Maize accuracy · F1 0.769 · Recall 0.889</div></div>
  <div class="badge"><div class="num">0.910</div><div class="lab">Coffee V3 F1 · Recall 0.934</div></div>
</div>

<!--
The core AI contribution of Phase 1 — four deliberate modifications to ResNet-18 so it can
catch tiny defects. Number them clearly and tie each to why.
→ Next: an honest scorecard of what worked and what didn't.
-->

---

<!-- SLIDE 16 — Phase 1 Results: What Worked / What Didn't -->

<div class="act-tag">Act III · Phase 1 — First Pipeline</div>

# Phase 1 Results: What Worked, What Didn't

<div class="grid2" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card win">
    <h3><img class="ic" src="./media/icons/check-green.png" /> What worked</h3>
    <ul>
      <li>Detection localized seeds accurately in controlled conditions</li>
      <li>ResNet-18 modifications improved classification meaningfully</li>
      <li>Two-stage decoupling proved correct — each stage diagnosable alone</li>
      <li>Maize performed best — it had the highest-quality dataset</li>
    </ul>
  </div>
  <div class="card prob">
    <h3><img class="ic" src="./media/icons/alert-amber.png" /> What didn't</h3>
    <ul>
      <li>Detection overfitted — poor generalization to new images</li>
      <li>YOLO performed comparably (same data limitation)</li>
      <li>Accuracy decent, but not production-grade</li>
      <li><strong>The dataset was the bottleneck, not the architecture</strong></li>
    </ul>
  </div>
</div>

<!--
Honest scorecard — decoupling worked, maize was best (best data), but detection overfit and
accuracy wasn't production-grade. The punchline: the bottleneck was data, not architecture.
→ Next: the insight that reframed the whole project.
-->

---
class: center-slide
---

<!-- SLIDE 17 — We Hit a Wall — The Data Insight -->

<div class="act-tag">Act III · Phase 1 — First Pipeline</div>

# We Hit a Wall — The Data Insight

<div class="center" style="margin:0.6rem 0;" v-motion :initial="{ opacity: 0, scale: 0.9 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 150 } }">
  <span class="stat-huge">~100,000</span>
  <p class="mut">images per seed type needed to generalize — best public sets have <strong>&lt;20,000</strong></p>
</div>

<div class="grid2" style="margin-top:0.4rem;">
  <div class="card"><h3>The dual problem</h3><p>Detection sets have boxes but no quality · classification sets have quality but no boxes · <strong>no dataset has both</strong>.</p></div>
  <div class="card accent"><h3>The decision</h3><p><strong>Upgrade the classifier</strong> → EfficientNet-B2<br/><strong>Build our own data</strong> → MultiSeedGen</p></div>
</div>

<!--
The turning point — we need ~100K images per type, and no public set has both boxes and quality
labels. Two responses follow: a stronger classifier and our own data factory.
→ Next: the classifier upgrade.
-->

---

<!-- SLIDE 18 — Phase 2: Upgrading to EfficientNet-B2 -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# Phase 2: Upgrading to EfficientNet-B2

<div class="grid2" style="align-items:center; margin-top:0.3rem;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.92 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/18-Efficient-net-B2.png" />
  </div>
  <div>
    <p class="lead">Same Faster R-CNN detector; swapped <strong>ResNet-18 → EfficientNet-B2</strong> for classification. CBAM + hybrid pooling retained (→ 1024 features).</p>
    <p class="mut" style="font-size:0.86rem;">Now <strong>7-class multi-label</strong>: Broken · Damage · Fungus · Healthy · Immature · Shriveled · Weeveled</p>
    <div class="badges" style="margin-top:0.5rem;">
      <div class="badge amber"><div class="num">0.769</div><div class="lab">ResNet-18 Maize F1</div></div>
      <div class="badge"><div class="num">0.974</div><div class="lab">EfficientNet-B2 Macro-F1</div></div>
    </div>
  </div>
</div>

<!--
EfficientNet-B2 replaces ResNet-18, keeps CBAM + hybrid pooling, and goes from binary to
7-class multi-label. Land the metric jump (0.769 → 0.974).
→ Next: proof it's actually looking at the right thing.
-->

---
class: heatmap-slide
---

<!-- SLIDE 19 — Grad-CAM heatmaps -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

<h2>EfficientNet-B2 + CBAM learns a <span class="amber">different attention pattern</span> for each defect class</h2>

<div class="hmstack">
  <div class="hmrow" v-motion :initial="{ opacity: 0, x: -30 }" :enter="{ opacity: 1, x: 0, transition: { duration: 450, delay: 150 } }"><div class="lbl">Damage <span class="verdict">1.00</span> — focuses on the dark lesion</div><img src="./media/heatmaps/damage.png" alt="Damage Grad-CAM" /></div>
  <div class="hmrow" v-motion :initial="{ opacity: 0, x: -30 }" :enter="{ opacity: 1, x: 0, transition: { duration: 450, delay: 300 } }"><div class="lbl">Healthy <span class="verdict">1.00</span> — uniform activation across the clean surface</div><img src="./media/heatmaps/healthy.png" alt="Healthy Grad-CAM" /></div>
  <div class="hmrow" v-motion :initial="{ opacity: 0, x: -30 }" :enter="{ opacity: 1, x: 0, transition: { duration: 450, delay: 450 } }"><div class="lbl">Shriveled <span class="verdict">1.00</span> — focus on the wrinkled deformation</div><img src="./media/heatmaps/shriveled.png" alt="Shriveled Grad-CAM" /></div>
  <div class="hmrow" v-motion :initial="{ opacity: 0, x: -30 }" :enter="{ opacity: 1, x: 0, transition: { duration: 450, delay: 600 } }"><div class="lbl">Weeveled <span class="verdict">1.00</span> — concentrated hotspot on the bore-hole</div><img src="./media/heatmaps/weeveled.png" alt="Weeveled Grad-CAM" /></div>
</div>

<div class="hmcallout">The attention mechanism isn't guessing — it's looking at the right features. (Input + 7 class maps; red/yellow = high activation)</div>

<!--
The show-stopper — Grad-CAM proves the attention mechanism focuses on the actual defect for
each class, not the background. Minimal words; let the heatmaps land, maybe one per beat.
→ Next: but detection still needed help.
-->

---
class: center-slide
---

<!-- SLIDE 20 — Detection Still Overfits — We Need Our Own Data -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# Detection Still Overfits — We Need Our Own Data

<p class="lead center">EfficientNet-B2 <strong>solved classification</strong>. But object detection still overfitted — the models memorized training images instead of learning "what a seed looks like."</p>

<div class="grid3" style="margin:0.6rem 0;">
  <div class="card"><p>Need ~100K annotated images per type</p></div>
  <div class="card"><p>Manual bounding-box annotation is prohibitively slow &amp; error-prone</p></div>
  <div class="card"><p>Public datasets are lab-only — don't match the real world</p></div>
</div>

<div class="card amber center" v-motion :initial="{ opacity: 0, scale: 0.92 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 250 } }">
  <div class="icard" style="justify-content:center;"><div class="chip-ic" style="background:transparent;"><img src="./media/icons/dna.png" style="width:1.8rem;height:1.8rem;" /></div><h3 style="color:var(--leaf-deep); font-size:1.2rem;">We built MultiSeedGen — a synthetic data factory generating unlimited, perfectly-labelled detection data</h3></div>
</div>

<!--
Classification is solved; detection still overfits, and manual annotation can't scale. That's
exactly why we built MultiSeedGen. → Next: how MultiSeedGen works.
-->

---

<!-- SLIDE 21 — MultiSeedGen: Building Our Own Training Data -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# MultiSeedGen: Building Our Own Training Data

<div class="pipeline" style="margin:0.4rem 0 0.8rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="stage io"><img class="ic" src="./media/icons/image.png" /> Single-seed photos</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/scissors.png" /> Segment</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/combine.png" /> Composite<small>collision physics</small></div>
  <span class="arrow">→</span>
  <div class="stage detect"><img class="ic" src="./media/icons/camera.png" /> Degrade<small>camera sim</small></div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/file-output.png" /> Export<small>YOLO / COCO</small></div>
</div>

<div class="grid2" style="align-items:center;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 300 } }"><img src="./media/screenshots/MultiseedGen-seeds_annotatedWithBB.jpg" /></div>
  <div>
    <div class="warn"><strong>Labels come for free</strong> — the engine placed each seed, so it knows exactly where every one is.</div>
    <div class="pills" style="justify-content:flex-start; margin-top:0.7rem;">
      <span class="pill">6 segmentation backends</span>
      <span class="pill">15+ augmentation params</span>
      <span class="pill">byte-reproducible</span>
      <span class="pill">~20 species</span>
    </div>
  </div>
</div>

<!--
MultiSeedGen is a synthetic data factory — and the killer property is that labels are free,
because the engine placed each seed. Show the annotated output as proof.
→ Next: how we cut seeds out cleanly.
-->

---

<!-- SLIDE 22 — Segmentation: 6 Ways to Cut a Seed -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# Segmentation: 6 Ways to Cut a Seed

<div class="grid2" style="align-items:center; margin-top:0.3rem;">
<div>
  <div class="tl">
    <div class="step"><span class="n">1</span> <strong>auto</strong> — classical cascade + confidence gate + rembg fallback</div>
    <div class="step"><span class="n">2</span> <strong>threshold</strong> — border-colour distance (clean backgrounds)</div>
    <div class="step"><span class="n">3</span> <strong>otsu</strong> — grayscale Otsu (high-contrast)</div>
    <div class="step"><span class="n">4</span> <strong>grabcut</strong> — OpenCV GrabCut (textured backgrounds)</div>
    <div class="step"><span class="n">5</span> <strong>rembg (U²-Net)</strong> — learned ONNX, GPU-capable</div>
    <div class="step"><span class="n">6</span> <strong>SAM</strong> — prompt-driven: auto, box, or point</div>
  </div>
</div>
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 250 } }"><img src="./media/screenshots/seg-tuner.png" /></div>
</div>

<p class="lead center" style="margin-top:0.6rem; font-size:0.9rem;">Content-hash cached — the first pass is the only cost. Per-source override via segment-map.</p>

<!--
Six segmentation backends, from simple thresholding to Segment Anything, chosen per image with
a tuner UI. Don't read all six — group as "classical → learned → promptable."
→ Next: how we make synthetic data look real.
-->

---

<!-- SLIDE 23 — Augmentation & Domain Bridging -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# Augmentation & Domain Bridging

<div class="grid3" style="margin-top:0.3rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card"><h3><img class="ic" src="./media/icons/rotate-cw.png" /> Geometric</h3><ul><li>Scale jitter · rotation · flip</li><li>Shear · perspective warp</li><li>Collision-aware placement (IoU reject)</li></ul></div>
  <div class="card"><h3><img class="ic" src="./media/icons/camera.png" /> Photometric</h3><ul><li>Sensor noise (Gaussian + Poisson)</li><li>JPEG artifacts · motion blur</li><li>Gamma + directional drop shadows</li></ul></div>
  <div class="card amber"><h3 style="color:var(--leaf-deep);"><img class="ic" src="./media/icons/mountain.png" /> Domain matching</h3><ul><li><strong>bg_from_sources</strong> — real inpainted trays <em>(biggest lever)</em></li><li><strong>neg_frac</strong> — 10% negatives</li><li><strong>val_seed_holdout</strong> · determinism</li></ul></div>
</div>

<p class="lead center" style="margin-top:0.8rem; font-size:0.9rem;"><em>Bridging the gap between synthetic and real</em> — compositing onto <strong>real</strong> tray backgrounds was the single biggest quality lever.</p>

<!--
Augmentation plus domain bridging — and the single biggest lever was compositing onto real tray
backgrounds. Emphasize the amber column; the before/after is the proof.
→ Next: the tool itself and the self-improving data loop.
-->

---

<!-- SLIDE 24 — MultiSeedGen Web UI + Data Loop -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# MultiSeedGen Web UI + Data Loop

<div class="grid2" style="align-items:center; margin-top:0.3rem;">
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/monitor.png" /></div><div class="tx"><h3>Its own Web UI</h3><p class="mut">React + TypeScript + Tailwind, served by FastAPI</p></div></div>
    <ul style="margin-top:0.5rem;"><li>Run tab — config form + live WebSocket logs</li><li>Seg-tuner — per-method preview + quality scoring</li><li>Dataset browser · config presets (YAML)</li></ul>
  </div>
  <div v-motion :initial="{ opacity: 0, scale: 0.92 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 250 } }">
    <div class="pipeline" style="flex-direction:column; gap:0.35rem;">
      <div class="stage classify" style="width:100%;"><img class="ic" src="./media/icons/dna.png" /> Generate training data</div>
      <span class="arrow">↓</span>
      <div class="stage detect" style="width:100%;"><img class="ic" src="./media/icons/cpu.png" /> Models train on it</div>
      <span class="arrow">↓</span>
      <div class="stage io" style="width:100%;"><img class="ic" src="./media/icons/target.png" /> Real-world edge cases found</div>
      <span class="arrow">↺</span>
      <div class="stage io" style="width:100%;"><img class="ic" src="./media/icons/refresh-cw.png" /> Fed back into augmentation</div>
    </div>
  </div>
</div>

<p class="lead center" style="margin-top:0.7rem; font-size:0.9rem;">Each turn of this loop targets the generator at the system's <strong>measured weaknesses</strong>.</p>

<!--
MultiSeedGen is a full tool with its own web UI, and the data feedback loop aims the generator at
the system's measured weaknesses — it's a strategy, not a one-shot script.
→ Next: the detection results after all of this.
-->

---

<!-- SLIDE 25 — Detection Experiments: The Full Journey -->

<div class="act-tag">Act V · Final Results & Evidence</div>

# Detection Experiments: The Full Journey

<div class="tl" style="margin-top:0.3rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="step"><span class="n">1</span> Swin Transformer + FPN <img class="ic" src="./media/icons/alert-amber.png" /> <span class="mut">overfitted (too powerful for small data)</span> <span class="m">0.949</span></div>
  <div class="step"><span class="n">2</span> + CIoU loss <span class="mut">better box regression, still overfitting</span> <span class="m">0.981</span></div>
  <div class="step"><span class="n">3</span> ResNet-50 + Faster R-CNN <img class="ic" src="./media/icons/check-green.png" /> <span class="mut">lower metric, better real-world generalization</span> <span class="m">0.870</span></div>
  <div class="step"><span class="n">4</span> + PANet <span class="mut">improved localization at stricter IoU</span> <span class="m">0.852</span></div>
  <div class="step"><span class="n">5</span> YOLOv8 <img class="ic" src="./media/icons/star-amber.png" /> <span class="mut">fast + accurate, best all-round</span> <span class="m">0.975</span></div>
</div>

<p class="lead center" style="margin-top:0.7rem; font-size:0.92rem;"><strong>Lower test metrics ≠ worse model.</strong> After MultiSeedGen, detection trained on 40 seed types with great performance.</p>

<!--
The full detection experiment journey — and the counter-intuitive lesson: lower test metrics can
mean better real-world generalization. → Next: the same lesson, seen in classification.
-->

---

<!-- SLIDE 26 — Classification: Data Quality > Model Architecture -->

<div class="act-tag">Act V · Final Results & Evidence</div>

# Classification: Data Quality > Model Architecture

<div class="grid2" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card prob">
    <h3><img class="ic" src="./media/icons/x-red.png" /> Soybean — Lab Data</h3>
    <p>Sterile backgrounds → <strong class="bad">0.9936 F1</strong></p>
    <p class="mut">Overfitted — fails on real images</p>
  </div>
  <div class="card win">
    <h3><img class="ic" src="./media/icons/check-green.png" /> Maize — Real-World Data</h3>
    <p>Natural sunlight, phone captures → <strong class="ok">0.974 F1</strong></p>
    <p class="mut">Generalizes to the real world</p>
  </div>
</div>

<div class="pipeline" style="margin-top:0.9rem; font-size:0.85rem;">
  <span class="pill">Epoch 1 · 0.808</span><span class="arrow">→</span>
  <span class="pill">Epoch 3 · 0.925</span><span class="arrow">→</span>
  <span class="pill">Epoch 5 · 0.964</span><span class="arrow">→</span>
  <span class="pill" style="border-color:var(--leaf);"><strong>Epoch 7 · 0.974</strong></span>
</div>

<p class="lead center" style="margin-top:0.7rem; font-size:0.9rem;"><em>The model that scored lower on the test set performed better in the real world.</em></p>

<!--
Data quality beats architecture — the real-world maize model generalizes; the sterile-lab soybean
model overfits despite a higher score. → Next: how we deploy for two very different needs.
-->

---

<!-- SLIDE 27 — Speed vs. Precision -->

<div class="act-tag">Act V · Final Results & Evidence</div>

# Speed vs. Precision: Two Deployment Modes

<div class="grid2" style="margin-top:0.3rem;">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/target.png" /></div><div class="tx"><h3>Precision Mode</h3><p>Faster R-CNN + EfficientNet-B2</p></div></div><div class="pills" style="justify-content:flex-start; margin-top:0.5rem;"><span class="pill">~230ms · 4.3 FPS</span><span class="pill">7-class multi-label</span><span class="pill">QA labs</span></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/zap.png" /></div><div class="tx"><h3>Speed Mode</h3><p>YOLOv8</p></div></div><div class="pills" style="justify-content:flex-start; margin-top:0.5rem;"><span class="pill">~80ms · 12.5 FPS</span><span class="pill">Real-time</span><span class="pill">Conveyor belts</span></div></div>
</div>

<div class="diagram" style="margin-top:0.7rem; max-height:2.6in; overflow:hidden;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 250 } }"><img src="./media/screenshots/YOLO-realtime.png" /></div>

<p class="lead center" style="margin-top:0.4rem; font-size:0.82rem;"><strong>876 seeds</strong> detected in one dense frame — a detection-model demo of speed-mode throughput (both run on an RTX 3060).</p>

<!--
Two deployment modes — precision vs speed. Be precise: the 876-seed image is a model demo of
dense detection; the product realtime experience is the mobile frame-streaming mode shown in Act VI.
→ Next: how we compare to what's already out there.
-->

---

<!-- SLIDE 28 — Competitor Landscape -->

<div class="act-tag">Act V · Final Results & Evidence</div>

# Competitor Landscape

<div v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">

| Feature | Seed Bank | LemnaTec | PCS Agri Track | Seedy | GerminationPrediction |
|---|---|---|---|---|---|
| Cost | <span class="ok">Low</span> | <span class="bad">Very high</span> | <span class="mid">Medium</span> | <span class="mid">Subscription</span> | <span class="ok">Free</span> |
| Accessibility | <span class="ok">Web + Mobile</span> | <span class="bad">Custom HW</span> | <span class="mid">Needs internet</span> | <span class="mid">iOS only</span> | <span class="bad">CLI only</span> |
| Multi-crop | <span class="ok">~20 species</span> | <span class="ok">Many</span> | <span class="mid">Limited</span> | <span class="ok">Good DB</span> | <span class="bad">Germination only</span> |
| Defect granularity | <span class="ok">7-class multi-label</span> | <span class="ok">Industrial</span> | <span class="mid">Basic</span> | <span class="bad">Visual ID</span> | <span class="bad">No quality</span> |
| Mobile | <span class="ok">Native app</span> | <span class="bad">No</span> | <span class="mid">Web</span> | <span class="ok">iOS</span> | <span class="bad">No</span> |
| Open / extensible | <span class="ok">Pluggable</span> | <span class="bad">Proprietary</span> | <span class="bad">Proprietary</span> | <span class="bad">Proprietary</span> | <span class="ok">OSS</span> |

</div>

<p class="lead center" style="margin-top:0.7rem; font-size:0.9rem;">Affordable, accessible, multi-crop, fine-grained, and extensible — the all-green column is <strong>Seed Bank</strong>.</p>

<!--
Where we sit — affordable, accessible, multi-crop, fine-grained, and extensible. Highlight the
column that's all-green (us). → Next: the models are only half the story — now the platform.
-->

---
class: center-slide
---

<!-- SLIDE 29 — From Trained Models to a Real Product -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# A Model in a Notebook Helps No One

<div class="pipeline" style="margin:1.2rem 0; gap:1.2rem;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 200 } }">
  <div class="card center" style="flex:1;"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/file-text.png" /></div><h3>Trained model</h3><p class="mut">a lone .pth file</p></div>
  <span class="arrow" style="font-size:2rem;">→</span>
  <div class="card accent center" style="flex:1.2;"><div class="icard" style="justify-content:center;"><div class="chip-ic"><img src="./media/icons/monitor-smartphone.png" /></div><div class="chip-ic"><img src="./media/icons/users.png" /></div></div><h3 style="margin-top:0.4rem;">A platform two audiences use every day</h3></div>
</div>

<div class="pills">
  <span class="pill"><img src="./media/icons/hand.png" /> Usable</span>
  <span class="pill"><img src="./media/icons/link.png" /> Traceable</span>
  <span class="pill"><img src="./media/icons/shield.png" /> Secure</span>
</div>

<!--
This is the seam. Everything so far was research; now we turn it into something a farmer and a QA
lab actually use — the IS/backend team's contribution. The three anchor words map to the next slides.
→ Next: let's see it running.
-->

---

<!-- SLIDE 30 — Live App Showcase -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# Live App Showcase

<div class="grid4" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div><div class="diagram"><img src="./media/screenshots/MobileView.png" /></div><p class="mut center" style="font-size:0.78rem; margin-top:0.3rem;">Capture on mobile</p></div>
  <div><div class="diagram"><img src="./media/screenshots/Dashboard.png" /></div><p class="mut center" style="font-size:0.78rem; margin-top:0.3rem;">Review on web</p></div>
  <div><div class="diagram"><img src="./media/screenshots/web-batch-detail.png" /></div><p class="mut center" style="font-size:0.78rem; margin-top:0.3rem;">AI insights + boxes</p></div>
  <div><div class="diagram"><img src="./media/screenshots/Models_managment.png" /></div><p class="mut center" style="font-size:0.78rem; margin-top:0.3rem;">ML platform behind it</p></div>
</div>

<p class="lead center" style="margin-top:0.8rem; font-size:0.92rem;">Capture → analyze → review the insights — with a whole ML platform behind it.</p>

<!--
Walk the real farmer journey through the screenshots — capture, analyze, review the insights —
then reveal there's a whole ML platform behind it. Keep captions to one line each.
→ Next: who uses which part, and in which language.
-->

---

<!-- SLIDE 31 — One Platform, Two Audiences, Two Languages -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# One Platform, Two Audiences — in Two Languages

<div class="grid2" style="margin-top:0.3rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/tractor.png" /></div><div class="tx"><h3>Farmer (end user)</h3><p>Capture · analyze · history · share a read-only report</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/flask-conical.png" /></div><div class="tx"><h3>AI developer / admin</h3><p>Models · datasets · experiments · user management</p></div></div></div>
</div>

<div class="card amber" style="margin-top:0.9rem;">
  <div class="icard"><div class="chip-ic" style="background:transparent;"><img src="./media/icons/languages.png" style="width:1.7rem;height:1.7rem;" /></div><div><h3 style="color:var(--leaf-deep);">Fully bilingual — English + Arabic with complete RTL mirroring</h3><p class="mut">Every user-facing string translated; the whole layout flips for Arabic — on web AND mobile, not an afterthought.</p></div></div>
</div>

<!--
One platform, two role-gated audiences, and it's fully bilingual EN/AR with mirrored RTL on both
web and mobile — a real accessibility win most projects skip. → Next: what's under the hood.
-->

---

<!-- SLIDE 32 — System Architecture -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# System Architecture

<div class="grid2" style="align-items:center; margin-top:0.2rem;">
  <div class="grid2" style="grid-template-columns:1fr 1fr; gap:0.6rem;" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <div class="diagram"><img src="./media/diagrams/02-containers-app.png" /></div>
    <div class="diagram"><img src="./media/diagrams/02-containers-datastores.png" /></div>
  </div>
  <div>
    <ul>
      <li><strong>Clients</strong> — React 18 web + Expo mobile (EN/AR)</li>
      <li><strong>Backend</strong> — FastAPI, async end-to-end, layered (routers → services → repos), JWT + RBAC</li>
      <li><strong>Datastores</strong> — PostgreSQL (16 tables, UUIDv7) · Redis · MinIO · ClickHouse</li>
      <li><strong>Workers</strong> — worker-inference (torch) · worker-cpu (no torch)</li>
    </ul>
    <div class="pill" style="margin-top:0.5rem;">7 core services · <code>docker compose up</code></div>
  </div>
</div>

<p class="lead center" style="margin-top:0.5rem; font-size:0.85rem;">The deep dive on the high-level view from Slide 12 — clean layering is <em>why</em> each piece is swappable and testable.</p>

<!--
The payoff of the high-level architecture we teased at Slide 12 — clean layered design, async
end-to-end, seven core services that come up with one command. Don't go deeper than that.
→ Next: let's follow one photo all the way through.
-->

---
class: dense
---

<!-- SLIDE 33 — The Analyze Pipeline, End-to-End -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# The Analyze Pipeline, End-to-End

<ol class="steps-2col">
  <li><code>POST /analyze</code> — photos + optional metadata</li>
  <li>Validate → upload to MinIO → create batch (pending) → commit</li>
  <li>Dispatch one background job per image</li>
  <li><strong>DETECT → CROP → GROUP by type → CLASSIFY</strong> each group</li>
  <li>State machine: pending → running → succeeded / partial / failed</li>
  <li>Client polls until a terminal status</li>
</ol>

<div class="grid2" style="margin-top:0.6rem;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }"><img src="./media/diagrams/06-analyze-sequence.png" /><p class="mut center" style="font-size:0.72rem; margin-top:0.2rem;">Analyze sequence</p></div>
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 350 } }"><img src="./media/diagrams/07-batch-state-machine.png" /><p class="mut center" style="font-size:0.72rem; margin-top:0.2rem;">Batch state machine</p></div>
</div>

<div class="fwd center" style="margin-top:0.5rem;">Concurrency-safe state machine · per-seed-type routing · graceful partial results</div>

<!--
Trace a single analyze request end-to-end — the two-stage pipeline from Slide 13 in motion: the
fan-out, per-seed-type routing, and the concurrency-safe state machine that degrades gracefully to
"partial" instead of failing. → Next: how every result stays traceable to a model.
-->

---

<!-- SLIDE 34 — Model Traceability & Lifecycle -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# Model Traceability & Lifecycle

<div class="pipeline" style="margin:0.4rem 0 0.9rem;" v-motion :initial="{ opacity: 0, x: -24 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 150 } }">
  <div class="stage io"><img class="ic" src="./media/icons/scan.png" /> Seed Detection</div>
  <span class="arrow">→ FK →</span>
  <div class="stage detect"><img class="ic" src="./media/icons/layers.png" /> Inference</div>
  <span class="arrow">→ FK →</span>
  <div class="stage classify"><img class="ic" src="./media/icons/package.png" /> Model Artifact</div>
</div>

<p class="lead center" style="font-size:0.9rem;"><em>Every single verdict traces back to the exact model version that produced it.</em></p>

<div class="grid3" style="margin-top:0.5rem;">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/package.png" /></div><div class="tx"><h3>Register</h3><p>Upload weights, assign builder, set config</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/flask-conical.png" /></div><div class="tx"><h3>Evaluate</h3><p>Offline experiments vs labelled datasets</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/rocket.png" /></div><div class="tx"><h3>Promote</h3><p>registered → staging → production → archived</p></div></div></div>
</div>

<div class="fwd center" style="margin-top:0.6rem;">ModelResolver serves the production model per (kind, seed_type) — swapping the live model is a <strong>promotion, not a code change</strong>.</div>

<!--
The seam back to the AI story — every detection links by foreign key to the exact model version,
and models move register → evaluate → promote, with the resolver always serving the current
production model. Swapping models is a promotion, not a redeploy. → Next: how we keep it secure.
-->

---

<!-- SLIDE 35 — Secure by Design -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# Secure by Design

<div class="grid4" style="margin-top:0.5rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/key.png" /></div><h3>JWT + refresh rotation</h3><p>Short-lived tokens; a reused refresh token invalidates the chain</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/link.png" /></div><h3>Google OAuth</h3><p>Social sign-in alongside email / password</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/users.png" /></div><h3>Role-based access</h3><p>end_user · ai_developer · admin — on every route</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/scroll-text.png" /></div><h3>Audit log + one error shape</h3><p>Append-only trail; consistent typed errors (RFC 9457)</p></div>
</div>

<!--
Security done properly for a student project — rotating refresh tokens with replay detection,
OAuth, real role-based access, an audit trail, and one consistent error contract. Keep it to the
four tiles; don't rabbit-hole. → Next: the full toolset at a glance.
-->

---

<!-- SLIDE 36 — Tech Stack at a Glance -->

<div class="act-tag">Act VI · The Platform & Engineering</div>

# Tech Stack at a Glance

<div class="tstack" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="trow"><div class="chip-ic"><img src="./media/icons/cpu.png" /></div><span class="grp">AI / ML</span><span class="items">PyTorch · torchvision (Faster R-CNN) · EfficientNet-B2 · Ultralytics YOLOv8 · OpenCV · rembg · Pillow · NumPy</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/dna.png" /></div><span class="grp">MultiSeedGen</span><span class="items">classical-CV + rembg + SAM segmentation · React + FastAPI web UI</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/monitor.png" /></div><span class="grp">Web</span><span class="items">React 18 · TypeScript · Vite · Tailwind · shadcn/ui · TanStack Query · Zod · openapi-fetch · lucide-react</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/smartphone.png" /></div><span class="grp">Mobile</span><span class="items">Expo SDK 56 · React Native 0.85 · expo-camera · React Navigation</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/server.png" /></div><span class="grp">Backend</span><span class="items">FastAPI · Python 3.12 · Celery · SQLAlchemy 2 (async) · Pydantic v2 · Alembic</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/database.png" /></div><span class="grp">Data</span><span class="items">PostgreSQL 16 · ClickHouse · Redis 7 · MinIO</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/box.png" /></div><span class="grp">Infra</span><span class="items">Docker · multi-stage Dockerfile (CPU / GPU) · nginx</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/lock.png" /></div><span class="grp">Security</span><span class="items">JWT + refresh rotation · OAuth (Google) · RBAC</span></div>
</div>

<!--
A quick grouped inventory — don't read every item, let it convey breadth and coherence. Note that
SAM lives in MultiSeedGen, our separate data tool, not the runtime backend. → Next: what we learned.
-->

---

<!-- SLIDE 37 — Key Takeaways -->

<div class="act-tag">Act VII · Closing</div>

# Key Takeaways

<div class="grid3" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/bar-chart-3.png" /></div><h3>Data quality &gt; architecture</h3><p>The maize model won because its training data matched the real world.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/git-branch.png" /></div><h3>Decouple detection from classification</h3><p>Independent stages let us diagnose and swap each without disturbing the other.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/factory.png" /></div><h3>Synthetic data narrows the gap</h3><p>MultiSeedGen removed the annotation bottleneck — but always test on real photos.</p></div>
</div>

<!--
Three durable lessons — data > architecture, decouple the two stages, and synthetic data narrows
the gap but real evaluation is the only fair test. → Next: where it goes from here.
-->

---

<!-- SLIDE 38 — Future Roadmap -->

<div class="act-tag">Act VII · Closing</div>

# Future Roadmap

<div class="tl" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/sprout.png" /></div> <strong>More Crops</strong> — expand real-world datasets for all 20+ species</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/cpu.png" /></div> <strong>Edge AI</strong> — on-device quantized inference, no internet needed</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/refresh-cw.png" /></div> <strong>Active Learning</strong> — low-confidence scans feed back into MultiSeedGen</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/factory.png" /></div> <strong>Hardware-Integrated Conveyor</strong> — realtime already ships on mobile; next is fixed-camera lines + instance segmentation</div>
</div>

<!--
Future work — more crops, edge AI, active learning; and note honestly that a realtime frame mode
already ships, so the frontier is hardware-integrated conveyor lines and instance segmentation for
overlap, not realtime itself. → Next: thanks and questions.
-->

---
class: cover-slide
---

<!-- SLIDE 39 — Team + Thank You + Questions -->

<div v-motion :initial="{ opacity: 0, y: 26 }" :enter="{ opacity: 1, y: 0, transition: { duration: 650 } }">

# Thank You

## Questions?

</div>

<div class="teams">
  <div><span class="tag">AI</span> Omar Ez-Eldin Abdullah · Yussuf Ahmed Awad</div>
  <div><span class="tag">IS</span> Ali Abdelrahman · Mohamed Amr · Youssef Tarek Ali</div>
</div>

<div class="sup" style="margin-top:1rem;">Special thanks to Dr. Ali Zidane · Dr. Ghada Dahy · Dr. Heba Sherif · Dr. Eman Ahmed</div>

<div class="logos" v-motion :initial="{ opacity: 0, y: 18 }" :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 350 } }">
  <img src="./media/logos/Cairo_University_new_logo.png" alt="Cairo University" />
  <img src="./media/logos/FCAI.jpg" alt="FCAI" />
</div>

<!--
Thank the supervisors, credit both sub-teams explicitly (research and engineering), and open the
floor warmly. End on the logo.
-->
