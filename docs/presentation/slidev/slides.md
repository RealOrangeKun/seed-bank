---
title: Seed Bank — A Seed Quality Classification Service Using Computer Vision
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

## A Seed Quality Classification Service Using Computer Vision

</div>

<div class="inst">Faculty of Computers and Artificial Intelligence / Cairo University</div>
<div class="sup">
  Supervisors<br/>
  Dr. Eman<br/>
  Dr. Ali Zidane<br/>
  Dr. Heba Sherif<br/>
  Dr. Ghada Dahy
</div>

<div class="teams">
  <div><span class="tag">AI</span> Omar Ez-Eldin Abdullah · Yussuf Ahmed Awad</div>
  <div><span class="tag">IS</span> Ali Abdelrahman · Mohamed Amr · Youssef Tarek Ali</div>
</div>

<img src="./media/logos/Cairo_University_new_logo.png" alt="Cairo University" style="position: absolute; top: 2.2rem; left: 3rem; height: 110px;" v-motion :initial="{ opacity: 0, y: -20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 400 } }" />
<img src="./media/logos/FCAI.jpg" alt="FCAI" style="position: absolute; top: 2.2rem; right: 3rem; height: 110px;" v-motion :initial="{ opacity: 0, y: -20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 400 } }" />

<!--
Open warm and confident — "We built an AI platform that grades seed quality from a single
photo — usable by a farmer in a field or a QA lab." Name the two sub-teams (AI + IS) so the
audience knows the project spans research and a production system.
→ Next: the playful hook — why a "seed bank" in computer science?
-->

---
class: center-slide
---

<!-- SLIDE 2 — What is Seed Bank? -->

<div style="position: absolute; inset: 0; pointer-events: none; z-index: 0;">
  <img src="./media/Online-images/a-conveyor.jpeg" style="width: 100%; height: 100%; object-fit: cover; object-position: center; mask-image: radial-gradient(ellipse at center, rgba(0,0,0,1) 30%, rgba(0,0,0,0) 80%); -webkit-mask-image: radial-gradient(ellipse at center, rgba(0,0,0,1) 30%, rgba(0,0,0,0) 80%); opacity: 0.5;" />
</div>

<div class="act-tag">INTRODUCTION</div>

<h1 v-motion :initial="{ opacity: 0, y: 10 }" :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 100 } }">What is Seed Bank?</h1>

<div class="card center" style="margin-top: 1.5rem; padding: 2rem; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); border-radius: 1rem; border: 1px solid var(--leaf-line); box-shadow: 0 8px 30px rgba(20, 83, 45, 0.15);" v-motion :initial="{ opacity: 0, scale: 0.95 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 250 } }">
  <p style="font-size: 1.4rem; color: var(--text); line-height: 1.6; font-weight: 500; margin: 0;">
    Seed bank is a quality control application for seeds that relies on Computer Vision for this task
  </p>
</div>

<div class="grid4" style="margin-top: 2rem;">
  <div v-click class="card accent center" style="padding: 1.5rem 1rem; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); box-shadow: 0 8px 30px rgba(20, 83, 45, 0.1);">
    <h3 style="margin:0;">Quality assessment</h3>
  </div>
  <div v-click class="card accent center" style="padding: 1.5rem 1rem; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); box-shadow: 0 8px 30px rgba(20, 83, 45, 0.1);">
    <h3 style="margin:0;">Realtime inference</h3>
  </div>
  <div v-click class="card accent center" style="padding: 1.5rem 1rem; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); box-shadow: 0 8px 30px rgba(20, 83, 45, 0.1);">
    <h3 style="margin:0;">Data analytics</h3>
  </div>
  <div v-click class="card accent center" style="padding: 1.5rem 1rem; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); box-shadow: 0 8px 30px rgba(20, 83, 45, 0.1);">
    <h3 style="margin:0;">User Management</h3>
  </div>
</div>

<!--
The simplified overview slide.
→ Next: the 30-second pitch.
-->

---

<!-- SLIDE 3 — The Problem -->

<div class="act-tag">INTRODUCTION</div>

# What problem does Seed Bank address?

<div class="grid2" style="margin-top:1.2rem; gap:1rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 100 } }">
  <!-- 1. Human Error -->
  <div v-click style="position: relative; overflow: hidden; border-radius: 0.6rem; height: 160px; display: flex; flex-direction: column; justify-content: flex-end; padding: 1.2rem; border: 1px solid var(--leaf-line);">
    <div style="position: absolute; inset: 0; z-index: 0; background-image: url('./media/Online-images/hands-seeds.jpg'); background-size: cover; background-position: center;"></div>
    <div style="position: absolute; inset: 0; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.1) 100%);"></div>
    <div style="position: relative; z-index: 2;">
      <h3 style="color: white; margin: 0 0 0.3rem 0; font-size: 1.2rem; font-weight: 900;">Human Error</h3>
      <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.3; margin: 0;">Manual sorting is subjective and prone to inconsistencies across different inspectors.</p>
    </div>
  </div>

  <!-- 2. Labor Intensive -->
  <div v-click style="position: relative; overflow: hidden; border-radius: 0.6rem; height: 160px; display: flex; flex-direction: column; justify-content: flex-end; padding: 1.2rem; border: 1px solid var(--leaf-line);">
    <div style="position: absolute; inset: 0; z-index: 0; background-image: url('./media/Online-images/Labor_intensive.jpg'); background-size: cover; background-position: center;"></div>
    <div style="position: absolute; inset: 0; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.1) 100%);"></div>
    <div style="position: relative; z-index: 2;">
      <h3 style="color: white; margin: 0 0 0.3rem 0; font-size: 1.2rem; font-weight: 900;">Labor Intensive</h3>
      <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.3; margin: 0;">Sifting through massive batches of seeds by hand is painstakingly slow and cannot scale.</p>
    </div>
  </div>
</div>

<div style="display: flex; justify-content: center; margin-top: 1rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 250 } }">
  <!-- 3. Mechanical Sorters -->
  <div v-click style="position: relative; overflow: hidden; border-radius: 0.6rem; height: 160px; width: calc(50% - 0.5rem); display: flex; flex-direction: column; justify-content: flex-end; padding: 1.2rem; border: 1px solid var(--leaf-line);">
    <div style="position: absolute; inset: 0; z-index: 0; background-image: url('./media/Online-images/mechanical_sorters.jpg'); background-size: cover; background-position: center;"></div>
    <div style="position: absolute; inset: 0; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.1) 100%);"></div>
    <div style="position: relative; z-index: 2;">
      <h3 style="color: white; margin: 0 0 0.3rem 0; font-size: 1.2rem; font-weight: 900;">Mechanical Sorters</h3>
      <p style="color: #e2e8f0; font-size: 0.95rem; line-height: 1.3; margin: 0;">Massive machines that grade automatically are highly effective, but usually extremely expensive.</p>
    </div>
  </div>
</div>

<!--
Introduce the problem: grading seeds manually is prone to human error and is extremely slow.
-->

---

<!-- SLIDE 4 — The Balanced Choice -->

<div class="act-tag">INTRODUCTION</div>

# The Balanced Choice

<div class="pipeline" style="margin-top:1.4rem; gap:1.2rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/factory.png" /></div>
    <h3>Mechanical Sieves</h3>
    <p class="mut">High effectiveness</p>
    <p class="bad" style="font-weight:700; margin-top:0.5rem;">Extremely Expensive</p>
  </div>
  
  <div class="card center" style="flex:1.2; border: 2px solid var(--leaf); background: rgba(30,122,64,0.05); transform: scale(1.05);">
    <h3 style="color:var(--leaf-deep); margin-bottom:0.3rem;">Seed Bank</h3>
    <div class="chip-ic" style="margin:0.4rem auto; background:transparent;"><img src="./media/icons/leaf.png" style="width:2rem;height:2rem;" /></div>
    <p style="color:var(--text); font-weight:600;">The perfect middle ground</p>
    <p class="mut" style="font-size:0.9rem; margin-top:0.4rem;">More effective than human labor.<br/>Much cheaper than machines.</p>
  </div>
  
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/hand.png" /></div>
    <h3>Human Labor</h3>
    <p class="mut">Lowest cost initially</p>
    <p class="bad" style="font-weight:700; margin-top:0.5rem;">Low Effectiveness</p>
  </div>
</div>

<!--
Seed Bank is the balanced choice: it brings automation without the massive capital investment of industrial machinery.
-->

---

<!-- SLIDE 5 — The 30-Second Pitch -->

<div class="act-tag">INTRODUCTION</div>

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
to three beats; details come later.
-->

---

<!-- SLIDE 6 — Who Is This For? -->

<div class="act-tag">INTRODUCTION</div>

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
throughput without a six-figure machine. Stress that one backend serves both.
-->

---

<!-- SLIDE 7 — Why Seeds Are Hard for AI -->

<div class="act-tag">INTRODUCTION</div>

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

<div class="act-tag">INTRODUCTION</div>

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

<!-- SLIDE 14 — How It Started & Splitting the Problem -->

<div class="act-tag">Act III · Phase 1 — First Pipeline</div>

# How It Started & Splitting the Problem

<div v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <p class="lead">We first thought of what machine learning model to make, and it was naturally a <strong>Computer Vision</strong> one. Then we asked: <em>what's a good model to fine-tune on?</em></p>
  <p class="mut" style="margin-top: 0.5rem; font-size: 1.1rem;">We started very small with a basic ResNet architecture, testing most of its variants from <strong>ResNet-18 up to ResNet-120</strong> to find the optimal balance of speed and feature extraction.</p>
</div>

<p class="lead center" style="margin-top: 1.2rem; font-weight: 600;">To enable better debugging and handling, we split the challenge into two distinct tasks.</p>

<div class="grid2" style="margin-top:0.8rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card accent" style="padding: 1rem;">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/scan.png" /></div><div class="tx"><h3>Inter-class (Detection)</h3><p class="mut">Finding the seeds vs. background</p></div></div>
    <ul style="margin-top:0.5rem; font-size: 0.95rem;">
      <li>After intensive training, we settled on <strong>ResNet-50</strong> for this task.</li>
      <li>Serves as the backbone to locate regions across classes.</li>
    </ul>
  </div>
  <div class="card accent" style="padding: 1rem;">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/badge-check.png" /></div><div class="tx"><h3>Intra-class (Classification)</h3><p class="mut">Grading good vs. bad crops</p></div></div>
    <ul style="margin-top:0.5rem; font-size: 0.95rem;">
      <li>We settled on <strong>ResNet-18</strong> for classifying the cropped seeds.</li>
      <li>Added custom modifications (CBAM attention, hybrid pooling).</li>
    </ul>
  </div>
</div>

<!--
How it started: decided on CV, started small with ResNet, tested 18-120.
Then split into inter-class (Detection via ResNet-50) and intra-class (Classification via ResNet-18) for better debugging.
→ Next: an honest scorecard of what worked and what didn't in this first pipeline.
-->

---

<!-- SLIDE 15 — Phase 1 Results: What Worked / What Didn't -->

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

<!-- SLIDE 16 — We Hit a Wall — The Data Insight -->

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

<!-- SLIDE 17 — Phase 2: Upgrading to EfficientNet-B2 -->

<div class="act-tag">Act IV · Phase 2 — Deeper Models + MultiSeedGen</div>

# Phase 2: Upgrading to EfficientNet-B2

<div class="grid2" style="align-items:center; margin-top:0.5rem;">
  <div class="diagram-mini" v-motion :initial="{ opacity: 0, scale: 0.92 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/18-Efficient-net-B2.png" />
  </div>
  <div>
    <p class="lead">We swapped the <strong>ResNet-18</strong> for the <strong>EfficientNet-B2</strong> for classification. We retained our custom modifications (CBAM + hybrid pooling) to maximize feature extraction.</p>
    <div class="badges" style="margin-top:1.5rem;">
      <div class="badge amber"><div class="num">0.769</div><div class="lab">ResNet-18 Maize F1</div></div>
      <div class="badge"><div class="num">0.974</div><div class="lab">EfficientNet-B2 Macro-F1</div></div>
    </div>
  </div>
</div>

<!--
EfficientNet-B2 replaces ResNet-18 for classification. Land the metric jump (0.769 → 0.974).
→ Next: proof it's actually looking at the right thing.
-->

---
class: heatmap-slide
---

<!-- SLIDE 18 — Grad-CAM heatmaps -->

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

<!-- SLIDE 19 — Detection Still Overfits — We Need Our Own Data -->

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

<!-- SLIDE 20 — MultiSeedGen: Building Our Own Training Data -->

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

<!-- SLIDE 21 — Segmentation: 6 Ways to Cut a Seed -->

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

<!-- SLIDE 22 — Augmentation & Domain Bridging -->

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

<!-- SLIDE 23 — MultiSeedGen Web UI + Data Loop -->

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

<!-- SLIDE 24 — Detection Experiments: The Full Journey -->

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

<!-- SLIDE 25 — Classification: Data Quality > Model Architecture -->

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

<!-- SLIDE 26 — Speed vs. Precision -->

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

<!-- SLIDE 27 — Competitor Landscape -->

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

<!-- SLIDE 28 — From Trained Models to a Real Product -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# A Model in a Notebook Helps No One

<div class="pipeline" style="margin:1.2rem 0; gap:1.2rem;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 200 } }">
  <div class="card center" style="flex:1;"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/file-text.png" /></div><h3>Trained model</h3><p class="mut">a lone .pth file</p></div>
  <span class="arrow" style="font-size:2rem;">→</span>
  <div class="card accent center" style="flex:1.2;"><div class="icard" style="justify-content:center;"><div class="chip-ic"><img src="./media/icons/monitor-smartphone.png" /></div><div class="chip-ic"><img src="./media/icons/users.png" /></div></div><h3 style="margin-top:0.4rem;">A product real users rely on</h3></div>
</div>

<div class="grid3" style="margin-top:1rem;" v-motion :initial="{ opacity: 0, y: 18 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/monitor.png" /></div><h3>React Web App</h3><p class="mut">Dashboard, analytics, ML platform</p></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/smartphone.png" /></div><h3>Expo Mobile App</h3><p class="mut">Camera capture, realtime grading</p></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/server.png" /></div><h3>FastAPI Backend</h3><p class="mut">One API serving both clients</p></div>
</div>

<div class="pills" style="margin-top:0.9rem;">
  <span class="pill"><img src="./media/icons/users.png" /> 3 roles: end_user · ai_developer · admin</span>
  <span class="pill"><img src="./media/icons/hand.png" /> Usable</span>
  <span class="pill"><img src="./media/icons/link.png" /> Traceable</span>
  <span class="pill"><img src="./media/icons/shield.png" /> Secure</span>
</div>

<!--
This is the seam. Everything so far was research; now we turn it into a product.
The backend serves two client apps (web + mobile). Three user roles control access.
Three anchor words (usable, traceable, secure) map to the next slides.
-->

---

<!-- SLIDE 29A - Live App Showcase: The Farmer Journey -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# The Farmer Journey

<div class="grid2" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div><div class="diagram"><img src="./media/screenshots/MobileView.png" /></div><p class="mut center" style="font-size:0.9rem; margin-top:0.4rem;">Capture on Mobile</p></div>
  <div><div class="diagram"><img src="./media/screenshots/Dashboard.png" /></div><p class="mut center" style="font-size:0.9rem; margin-top:0.4rem;">Review on Web Dashboard</p></div>
</div>

<!--
The farmer's workflow starts in the field on the mobile app, and shifts to the web dashboard for reviewing their entire crop history.
-->

---

<!-- SLIDE 29B - Live App Showcase: The AI Journey -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# Deep Insights &amp; ML Platform

<div class="grid2" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div><div class="diagram"><img src="./media/screenshots/web-batch-detail.png" /></div><p class="mut center" style="font-size:0.9rem; margin-top:0.4rem;">AI Insights &amp; Bounding Boxes</p></div>
  <div><div class="diagram"><img src="./media/screenshots/Models_managment.png" /></div><p class="mut center" style="font-size:0.9rem; margin-top:0.4rem;">ML Platform for Developers</p></div>
</div>

<!--
Drilling down into a specific batch reveals the bounding boxes and AI insights. And behind the scenes, AI developers use the built-in ML platform to manage datasets and models.
-->

---

<!-- SLIDE 30 — One Backend, Two Apps, Two Languages -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# One Backend, Two Apps, Two Languages

<div class="grid2" style="margin-top:0.3rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/monitor.png" /></div><div class="tx"><h3>React Web App (Vite + TypeScript)</h3><p>Dashboard, batch detail, analytics, compare, ML platform pages</p></div></div>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/smartphone.png" /></div><div class="tx"><h3>Expo Mobile App (React Native)</h3><p>Camera capture, multi-shot review, realtime grading, history</p></div></div>
  </div>
</div>

<div class="grid3" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 18 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/tractor.png" /></div><h3>end_user</h3><p class="mut">Analyze, history, share reports</p></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/flask-conical.png" /></div><h3>ai_developer</h3><p class="mut">Models, datasets, experiments</p></div>
  <div class="card center"><div class="chip-ic" style="margin:0 auto 0.4rem;"><img src="./media/icons/users.png" /></div><h3>admin</h3><p class="mut">Full platform control</p></div>
</div>

<div class="card amber" style="margin-top:0.6rem;">
  <div class="icard"><div class="chip-ic" style="background:transparent;"><img src="./media/icons/languages.png" style="width:1.7rem;height:1.7rem;" /></div><div><h3 style="color:var(--leaf-deep);">Fully bilingual: English + Arabic with complete RTL mirroring</h3><p class="mut">Every user-facing string translated; the whole layout flips for Arabic on both web and mobile.</p></div></div>
</div>

<!--
One FastAPI backend serves two client applications. Three role-gated user types control
who sees what. Both apps are fully bilingual EN/AR with RTL layout mirroring.
-->

---

<!-- SLIDE 31 — System Architecture: Application Layer -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# How It's Built: Application Layer

<div class="grid2" style="align-items:center; margin-top:0.2rem;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/02-containers-app.png" />
  </div>
  <div>
    <div class="card accent" style="margin-bottom:0.5rem;">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/backend.png" /></div><div class="tx"><h3>FastAPI (async)</h3><p>Routers → Services → Repositories → ORM. Nothing blocks the event loop.</p></div></div>
    </div>
    <div class="card accent" style="margin-bottom:0.5rem;">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/workers.png" /></div><div class="tx"><h3>Two worker types</h3><p><code>worker-inference</code> (GPU, torch) and <code>worker-cpu</code> (analytics, DWH). Split so torch never loads into the lightweight worker.</p></div></div>
    </div>
    <div class="card accent">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/clients.png" /></div><div class="tx"><h3>Two clients, one API</h3><p>React 18 + Vite (web) and Expo SDK 56 (mobile), both hitting <code>/api/v1</code>.</p></div></div>
    </div>
  </div>
</div>

<div class="callout">Inference is heavy, so it never runs inside the request the user is waiting on. The API stays fast.</div>

<!--
How we built it: workers split by dependency weight. The inference worker loads torch (~1.6 GB),
the CPU worker does not. The API itself never imports torch. Everything is async.
-->

---

<!-- SLIDE 32 - System Architecture: Datastores -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# How It's Built: Data Layer

<div class="grid4" style="margin-top:1.5rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 650, delay: 200 } }">
  <div class="card center">
    <div class="chip-ic" style="margin:0 auto 0.8rem; width:3.2rem; height:3.2rem;"><img src="./media/icons/database.png" style="width:1.8rem; height:1.8rem;" /></div>
    <h3 style="font-size:1.15rem; margin-bottom:0.4rem;">PostgreSQL 16</h3>
    <p class="mut">The core relational backbone. Stores batches, detections, model metadata, and users.</p>
  </div>
  <div class="card center">
    <div class="chip-ic" style="margin:0 auto 0.8rem; width:3.2rem; height:3.2rem;"><img src="./media/icons/workflow.png" style="width:1.8rem; height:1.8rem;" /></div>
    <h3 style="font-size:1.15rem; margin-bottom:0.4rem;">Redis 7</h3>
    <p class="mut">Serves three crucial roles: fast caching, Celery task broker, and Celery results backend.</p>
  </div>
  <div class="card center">
    <div class="chip-ic" style="margin:0 auto 0.8rem; width:3.2rem; height:3.2rem;"><img src="./media/icons/box.png" style="width:1.8rem; height:1.8rem;" /></div>
    <h3 style="font-size:1.15rem; margin-bottom:0.4rem;">MinIO</h3>
    <p class="mut">S3-compatible object storage for all binary files: images, model weights, and exported datasets.</p>
  </div>
  <div class="card center">
    <div class="chip-ic" style="margin:0 auto 0.8rem; width:3.2rem; height:3.2rem;"><img src="./media/icons/bar-chart-3.png" style="width:1.8rem; height:1.8rem;" /></div>
    <h3 style="font-size:1.15rem; margin-bottom:0.4rem;">ClickHouse</h3>
    <p class="mut">An OLAP star schema specifically built for high-performance aggregations and analytics.</p>
  </div>
</div>

<!--
Four datastores, each chosen for a specific reason. PostgreSQL is the relational backbone. Redis doubles as cache and task broker. MinIO stores everything binary. ClickHouse handles analytics. How it gets its data is worth its own slide.
-->

---

<!-- SLIDE 33 - Data Warehouse Population -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# OLTP to OLAP: The Dual-Write Pattern

<div class="pipeline" style="margin:1rem 0; font-size: 0.9rem;" v-motion :initial="{ opacity: 0, scale: 0.95 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 200 } }">
  <div class="stage classify"><img class="ic" src="./media/icons/cpu.png" /> Worker finishes inference</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/database.png" /> Commits to Postgres</div>
  <span class="arrow">→</span>
  <div class="stage detect"><img class="ic" src="./media/icons/workflow.png" /> Celery dwh task</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/database.png" /> Reads back from Postgres</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/bar-chart-3.png" /> Writes to ClickHouse</div>
</div>

<div class="grid2" style="margin-top:0.8rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/refresh-cw.png" /></div><div class="tx"><h3>App-level dual-write</h3><p>After every Postgres commit, a Celery task is dispatched to the `dwh` queue on the CPU worker.</p></div></div>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/eye.png" /></div><div class="tx"><h3>Read-back pattern</h3><p>The task reads the authoritative state from Postgres. This makes duplicated messages harmless.</p></div></div>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/layers.png" /></div><div class="tx"><h3>Idempotent by design</h3><p>ClickHouse uses a `ReplacingMergeTree`. A duplicate write is simply collapsed at merge time.</p></div></div>
  </div>
  <div class="card accent">
    <div class="icard"><div class="chip-ic"><img src="./media/icons/shield.png" /></div><div class="tx"><h3>Fire and forget resilience</h3><p>If ClickHouse is down, the dispatch is best-effort. Analytics degrade, but the product keeps working.</p></div></div>
  </div>
</div>

<!--
This is a real data engineering pattern. After the OLTP commit, a lightweight Celery task reads the row back from Postgres and writes dimension and fact rows into ClickHouse. ReplacingMergeTree makes duplicates harmless. The key design decision: ClickHouse can go down without affecting the core product.
-->

---

<!-- SLIDE 34A - The Analyze Request: API Flow -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# What Happens When You Click "Analyze": The API

<div class="grid2" style="margin-top:0.6rem;">
  <div style="overflow: hidden; border-radius: 0.6rem; border: 1px solid var(--border); background: #fff; height: 320px;" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/06-analyze-sequence.png" style="width: 170%; max-width: none; transform: translate(-2%, -2%);" />
  </div>
  <div v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 650, delay: 350 } }">
    <ol class="steps-2col" style="column-count: 1; padding-inline-start: 0; font-size: 0.95rem;">
      <li style="margin-bottom: 0.8rem;"><strong>1. API Request</strong>: The client sends photos via `POST /analyze`.</li>
      <li style="margin-bottom: 0.8rem;"><strong>2. Validate &amp; Upload</strong>: Validate every file, then upload images to MinIO before committing to the database.</li>
      <li style="margin-bottom: 0.8rem;"><strong>3. Database Commit</strong>: Create the pending batch and image rows.</li>
      <li style="margin-bottom: 0.8rem;"><strong>4. Fast Response</strong>: Return a `202 Accepted` status immediately. The user never waits for inference.</li>
    </ol>
  </div>
</div>

<div class="fwd center" style="margin-top:0.5rem;">Validation happens first to fail fast. Storage happens before database commits to prevent broken links.</div>

<!--
Walk through the sequence diagram step by step. The ordering is load-bearing: validate first, store objects, commit to DB. The user gets a response in milliseconds; the heavy work hasn't started yet.
-->

---

<!-- SLIDE 34B - The Analyze Request: Async Call -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# What Happens When You Click "Analyze": Async Workers

<div class="grid2" style="margin-top:0.6rem;">
  <div style="overflow: hidden; border-radius: 0.6rem; border: 1px solid var(--border); background: #fff; height: 320px;" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }">
    <img src="./media/diagrams/06-analyze-sequence.png" style="width: 170%; max-width: none; transform: translate(-30%, -45%);" />
  </div>
  <div v-motion :initial="{ opacity: 0, x: 20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 650, delay: 350 } }">
    <div class="card accent" style="margin-bottom:0.8rem;">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/workflow.png" /></div><div class="tx"><h3>Dispatch Tasks</h3><p>Before the API returns, one Celery task per image is sent to the Redis queue.</p></div></div>
    </div>
    <div class="card accent" style="margin-bottom:0.8rem;">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/cpu.png" /></div><div class="tx"><h3>Inference Pipeline</h3><p>The GPU worker picks up the task, downloads the image, and runs the heavy ML models.</p></div></div>
    </div>
    <div class="card accent">
      <div class="icard"><div class="chip-ic"><img src="./media/icons/database.png" /></div><div class="tx"><h3>Update State</h3><p>The worker updates the database with the final results. The client polls until completion.</p></div></div>
    </div>
  </div>
</div>

<div class="fwd center" style="margin-top:0.5rem;">Decoupling the inference allows the system to scale workers independently of the web API.</div>

<!--
Now the heavy lifting. The Celery worker picks up the job and runs the inference pipeline. The client is just polling for the batch status to change from pending to succeeded.
-->

---

<!-- SLIDE 36 - Concurrency & Resilience: The Batch State Machine -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# Handling Failures Gracefully

<div class="grid2" style="align-items:center; margin-top:0.4rem;">
  <div class="diagram" v-motion :initial="{ opacity: 0, scale: 0.93 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 650, delay: 200 } }"><img src="./media/diagrams/07-batch-state-machine.png" /></div>
  <div v-motion :initial="{ opacity: 0, x: 20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 650, delay: 350 } }">
    <div class="card" style="margin-bottom: 0.8rem;">
      <h3><img class="ic" src="./media/icons/lock.png" /> Compare-And-Set (CAS)</h3>
      <p>State transitions use SQL updates with strict conditions. Two workers on the same batch cannot corrupt state.</p>
    </div>
    <div class="card win" style="margin-bottom: 0.8rem;">
      <h3><img class="ic" src="./media/icons/check-green.png" /> succeeded</h3>
      <p>All images detected and classified successfully.</p>
    </div>
    <div class="card prob" style="margin-bottom: 0.8rem;">
      <h3 style="color: var(--amber);"><img class="ic" src="./media/icons/alert-amber.png" /> partial</h3>
      <p>Detection worked but classification failed on some seeds. We keep the good data instead of throwing it away.</p>
    </div>
    <div class="card" style="margin-bottom: 0.8rem;">
      <h3 style="color: #c0392b;"><img class="ic" src="./media/icons/x-red.png" /> failed</h3>
      <p>No usable results were produced.</p>
    </div>
  </div>
</div>

<!--
The state machine is what makes the system robust. CAS ensures concurrency safety. The partial state is the key design decision. If classification crashes after detection succeeded, we degrade gracefully instead of losing everything.
-->

---

<!-- SLIDE 37 - Model Traceability & Lifecycle -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# Model Traceability: Every Verdict Has a Source

<div class="pipeline" style="margin:0.4rem 0 0.9rem;" v-motion :initial="{ opacity: 0, x: -24 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 150 } }">
  <div class="stage io"><img class="ic" src="./media/icons/scan.png" /> Seed Detection</div>
  <span class="arrow">→ Foreign Key →</span>
  <div class="stage detect"><img class="ic" src="./media/icons/layers.png" /> Inference</div>
  <span class="arrow">→ Foreign Key →</span>
  <div class="stage classify"><img class="ic" src="./media/icons/package.png" /> Model Artifact</div>
</div>

<p class="lead center" style="font-size:0.9rem;"><em>Every single verdict traces back to the exact model version that produced it.</em></p>

<div class="grid3" style="margin-top:0.5rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 300 } }">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/package.png" /></div><div class="tx"><h3>Register</h3><p>Upload weights, assign a builder, and set the config.</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/flask-conical.png" /></div><div class="tx"><h3>Evaluate</h3><p>Run offline experiments against labelled datasets.</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/rocket.png" /></div><div class="tx"><h3>Promote</h3><p>Move from registered to staging, then to production.</p></div></div></div>
</div>

<div class="fwd center" style="margin-top:0.6rem;">Swapping the live model is a <strong>promotion, not a code change</strong>.</div>

<!--
This is where the AI story reconnects with the engineering. The foreign key chain is a hard database constraint. The lifecycle means an AI developer uploads new weights, tests them offline, and promotes to production without touching code.
-->

---

<!-- SLIDE 38 - Model Resolution: How the System Picks the Right Model -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# How the Right Model is Chosen

<div class="grid4" style="margin-top:1.5rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 650, delay: 200 } }">
  <div class="card center">
    <div class="n" style="font-size: 2.2rem; font-weight: 800; color: var(--leaf-soft); margin-bottom: 0.5rem;">1</div>
    <h3 style="font-size: 1.15rem; margin-bottom: 0.4rem;">Per-request override</h3>
    <p class="mut">AI developers can request a specific model ID to test staging models safely on real data.</p>
  </div>
  <div class="card center">
    <div class="n" style="font-size: 2.2rem; font-weight: 800; color: var(--leaf-soft); margin-bottom: 0.5rem;">2</div>
    <h3 style="font-size: 1.15rem; margin-bottom: 0.4rem;">Segment match</h3>
    <p class="mut">The system looks for a production model promoted specifically for this crop type.</p>
  </div>
  <div class="card center">
    <div class="n" style="font-size: 2.2rem; font-weight: 800; color: var(--leaf-soft); margin-bottom: 0.5rem;">3</div>
    <h3 style="font-size: 1.15rem; margin-bottom: 0.4rem;">Global fallback</h3>
    <p class="mut">Uses the global production model if the crop type is unknown, enabling the mobile point-and-shoot flow.</p>
  </div>
  <div class="card center">
    <div class="n" style="font-size: 2.2rem; font-weight: 800; color: var(--amber); margin-bottom: 0.5rem;">4</div>
    <h3 style="font-size: 1.15rem; margin-bottom: 0.4rem;">Graceful errors</h3>
    <p class="mut">Returns a clear, handled error if no suitable model is ready to process the request.</p>
  </div>
</div>

<!--
The ModelResolver decides which model runs for every inference. The global fallback is what makes the mobile point and shoot flow work. Per-request override lets AI developers test a staging model on real data without touching the production path.
-->

---

<!-- SLIDE 39 - Observability & Telemetry -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# Observability &amp; Telemetry

<div class="grid4" style="margin-top:0.5rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/network.png" /></div>
    <h3>Distributed Tracing</h3>
    <p>Every request gets a unique trace ID. It follows the payload from the API, through Celery queues, and into the workers.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/bar-chart-3.png" /></div>
    <h3>Application Metrics</h3>
    <p>We track API latencies, worker queue depths, and inference processing times to spot bottlenecks before they cause timeouts.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/alert-amber.png" /></div>
    <h3>Centralized Errors</h3>
    <p>Sentry catches unhandled exceptions in both the API and background workers, grouping them with full stack traces.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/file-text.png" /></div>
    <h3>Structured Logging</h3>
    <p>JSON logs ensure we can easily search and filter events by user ID, batch ID, or module, instead of parsing plain text.</p>
  </div>
</div>

<!--
When you decouple systems into APIs and background workers, you lose the ability to just check a single console. This is why we built proper telemetry. Tracing lets us follow a request across boundaries. Sentry catches errors. Metrics give us the high-level view.
-->

---

<!-- SLIDE 40 - Secure by Design -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# Security is Not an Afterthought

<div class="grid4" style="margin-top:0.5rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/key.png" /></div>
    <h3>JWT + Refresh Rotation</h3>
    <p>Short-lived access tokens. Refresh tokens rotate on use. Reusing an old token invalidates the entire chain.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/users.png" /></div>
    <h3>Role-Based Access</h3>
    <p>Three roles define access. Gates are enforced on every API route and client navigation.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/scroll-text.png" /></div>
    <h3>Audit Log &amp; Consistent Errors</h3>
    <p>Append-only record of sensitive actions. All API errors return a stable typed error shape.</p>
  </div>
  <div class="card accent">
    <div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/lock.png" /></div>
    <h3>Rate Limiting</h3>
    <p>Per-route caps for login, register, and analyze endpoints, backed by Redis.</p>
  </div>
</div>

<!--
Security done properly. The replay detection on refresh tokens is the standout feature. If someone steals and reuses an old refresh token, the entire token chain is invalidated. Combined with strict access control, rate limiting, and a full audit trail.
-->

---

<!-- SLIDE 41 - Tech Stack at a Glance -->

<div class="act-tag">Act VI · The Platform &amp; Engineering</div>

# The Full Toolset

<div class="tstack" style="margin-top:0.4rem;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="trow"><div class="chip-ic"><img src="./media/icons/cpu.png" /></div><span class="grp">AI / ML</span><span class="items">PyTorch · torchvision (Faster R-CNN) · EfficientNet-B2 · Ultralytics YOLOv8 · OpenCV · rembg · Pillow · NumPy</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/dna.png" /></div><span class="grp">MultiSeedGen</span><span class="items">classical-CV + rembg + SAM segmentation · React + FastAPI web UI</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/monitor.png" /></div><span class="grp">Web</span><span class="items">React 18 · TypeScript · Vite · Tailwind · shadcn/ui · TanStack Query · Zod · openapi-fetch · lucide-react</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/smartphone.png" /></div><span class="grp">Mobile</span><span class="items">Expo SDK 56 · React Native 0.85 · expo-camera · React Navigation</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/server.png" /></div><span class="grp">Backend</span><span class="items">FastAPI · Python 3.12 · Celery · SQLAlchemy 2 (async) · Pydantic v2 · Alembic</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/database.png" /></div><span class="grp">Data</span><span class="items">PostgreSQL 16 · ClickHouse · Redis 7 · MinIO</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/box.png" /></div><span class="grp">Infra</span><span class="items">Docker · multi-stage Dockerfile (CPU / GPU) · nginx</span></div>
  <div class="trow"><div class="chip-ic"><img src="./media/icons/lock.png" /></div><span class="grp">Security</span><span class="items">JWT + refresh rotation · RBAC · Rate limiting</span></div>
</div>

<!--
A quick grouped inventory. Let it convey breadth and coherence. This is a real, full-stack product with well-chosen tools at every layer.
-->

---

<!-- SLIDE 42 - Key Takeaways -->

<div class="act-tag">Act VII · Closing</div>

# Key Takeaways

<div class="grid3" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/bar-chart-3.png" /></div><h3>Data quality &gt; architecture</h3><p>The maize model won because its training data matched the real world.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/git-branch.png" /></div><h3>Decouple detection from classification</h3><p>Independent stages let us diagnose and swap each without disturbing the other.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/factory.png" /></div><h3>Synthetic data narrows the gap</h3><p>MultiSeedGen removed the annotation bottleneck, but always test on real photos.</p></div>
</div>

<!--
Three durable lessons: data > architecture, decouple the two stages, and synthetic data narrows the gap but real evaluation is the only fair test. -> Next: where it goes from here.
-->

---

<!-- SLIDE 43 - Future Roadmap -->

<div class="act-tag">Act VII · Closing</div>

# Future Roadmap

<div class="tl" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/sprout.png" /></div> <strong>More Crops</strong> - expand real-world datasets for all 20+ species</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/cpu.png" /></div> <strong>Edge AI</strong> - on-device quantized inference, no internet needed</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/refresh-cw.png" /></div> <strong>Active Learning</strong> - low-confidence scans feed back into MultiSeedGen</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/factory.png" /></div> <strong>Hardware-Integrated Conveyor</strong> - realtime already ships on mobile; next is fixed-camera lines + instance segmentation</div>
</div>

<!--
Future work: more crops, edge AI, active learning. Note honestly that a realtime frame mode already ships, so the frontier is hardware-integrated conveyor lines and instance segmentation for overlap, not realtime itself. -> Next: thanks and questions.
-->

---
class: cover-slide
---

<!-- SLIDE 44 - Team + Thank You + Questions -->

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
Thank the supervisors, credit both sub-teams explicitly (research and engineering), and open the floor warmly. End on the logo.
-->
