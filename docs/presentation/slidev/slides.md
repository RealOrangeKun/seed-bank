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

<!-- SLIDE 1 - Title -->

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
Open warm and confident. "We built an AI platform that grades seed quality from a single
photo, usable by a farmer in a field or a QA lab." Name the two sub-teams (AI + IS) so the
audience knows the project spans research and a production system.
→ Next: the playful hook, why a "seed bank" in computer science?
-->

---

<!-- SLIDE 2 - Two Groups, One Problem -->

<div class="act-tag">PROBLEM</div>

# Two Groups, One Big Problem

<p class="lead center" style="margin-top:0.2rem;">Nearly everyone who works with seeds falls into one of two groups. And both face the same hard question: are these seeds <strong>good, or bad</strong>?<sup class="cite"><a href="https://www.fao.org/4/i1853e/i1853e01.pdf#:~:text=And%20governments%20complained.%20that%2C%20years%20after%20national,donors%20were%20once%20again%20emphasizing%20improved%20seed." target="_blank" rel="noreferrer">1</a></sup></p>

<div class="grid2" style="margin-top:1rem;">
  <div class="card accent" v-click>
    <div class="icard"><div class="chip-ic"><img src="./media/icons/tractor.png" /></div><div class="tx"><h3>The Small Farmer</h3><p class="mut">Little money.<sup class="cite"><a href="https://documents1.worldbank.org/curated/en/099042424185030624/pdf/P1804801d17e9208184851221aa3cdbbfb.pdf#:~:text=Moreover%2C%20access%20to%20finance%20by%20small%20agri-food,water%20quality%20challenges%2C%20both%20of%20which%20constrain." target="_blank" rel="noreferrer">2</a></sup> Only a few seeds.</p></div></div>
    <div class="pills" style="justify-content:flex-start; margin-top:0.8rem;">
      <span class="pill"><img src="./media/icons/help-circle.png" /> Judged by eye</span>
      <span class="pill"><img src="./media/icons/hand.png" /> Slow hand work</span>
    </div>
    <p class="mut" style="margin-top:0.7rem; font-size:0.9rem;">They judge each seed by eye, so two people can easily disagree. And sorting by hand, seed by seed, takes forever.</p>
  </div>
  <div class="card accent" v-click>
    <div class="icard"><div class="chip-ic"><img src="./media/icons/factory.png" /></div><div class="tx"><h3>The Big Factory</h3><p class="mut">A lot of money. A huge amount of seeds.</p></div></div>
    <div class="pills" style="justify-content:flex-start; margin-top:0.8rem;">
      <span class="pill"><img src="./media/icons/dollar-sign.png" /> High repair cost</span>
      <span class="pill"><img src="./media/icons/refresh-cw.png" /> Costs a lot to run</span>
    </div>
    <p class="mut" style="margin-top:0.7rem; font-size:0.9rem;">Big machines do the sorting on their own. But they cost a fortune to buy, to fix, and to run every day.</p>
  </div>
</div>

<div class="refs">
  <strong>1.</strong> <a href="https://www.fao.org/4/i1853e/i1853e01.pdf" target="_blank" rel="noreferrer">FAO: Promoting the growth and development of smallholder seed enterprises</a>
  &nbsp;·&nbsp;
  <strong>2.</strong> <a href="https://documents1.worldbank.org/curated/en/099042424185030624/pdf/P1804801d17e9208184851221aa3cdbbfb.pdf" target="_blank" rel="noreferrer">World Bank: Small agri-food firms and access to finance</a>
</div>

<!--
Two groups with the same problem: the small farmer (little money, a few seeds) and the big factory
(lots of money, huge volume). Click to reveal each side while you talk about it. Sources: FAO on
seed quality mattering to smallholders, World Bank on their limited access to finance.
Next: both old ways of solving this have a problem.
-->

---

<!-- SLIDE 3 - Both Old Ways Have a Problem -->

<div class="act-tag">PROBLEM</div>

# Both Old Ways Have a Problem

<div class="grid2" style="margin-top:1.2rem;">
  <div class="card prob" v-click>
    <h3><img class="ic" src="./media/icons/hand.png" /> Human Labor</h3>
    <p>It is <strong class="bad">cheap</strong> to start. But people judge by eye, so the answer shifts from one person to the next. It is <strong class="bad">slow</strong>, too, and it can not keep up with big loads.</p>
    <p class="mut" style="margin-top:0.5rem; font-size:0.82rem;"><img class="ic" src="./media/icons/tractor.png" style="vertical-align:middle;" /> The small farmer's only choice.</p>
  </div>
  <div class="card prob" v-click>
    <h3><img class="ic" src="./media/icons/factory.png" /> Mechanical Sorters</h3>
    <p>They are <strong>fast</strong>, and they never change their mind. But the machines are <strong class="bad">very costly</strong> to buy and to keep running.</p>
    <p class="mut" style="margin-top:0.5rem; font-size:0.82rem;"><img class="ic" src="./media/icons/warehouse.png" style="vertical-align:middle;" /> Only big factories can pay for them.</p>
  </div>
</div>

<p class="lead center" style="margin-top:1.2rem;">One way is <strong>not fair</strong>. The other <strong>costs too much</strong>. And neither one helps <em>both</em> groups.</p>

<!--
The tension: the two old options sit at opposite ends. Human labor is cheap but not fair and slow.
Machines are fast but far too costly. Each one fits only one group, and neither fits both. Click to
bring in each card as you talk. Next: our answer.
-->

---

<!-- SLIDE 4 - Our Answer: Seed Bank -->

<div class="act-tag">SOLUTION</div>

# Our Answer: Seed Bank

<div class="card center" style="margin-top:0.5rem; padding:1.1rem 1.8rem; background: rgba(30,122,64,0.05); border:1px solid var(--leaf-line);">
  <p style="font-size:1.15rem; color:var(--text); line-height:1.5; margin:0; font-weight:500;">Seed Bank is an app that checks seed quality with <strong>AI</strong>. You just take a photo. It finds every seed and tells you which ones are good and which are bad.</p>
</div>

<div class="pipeline" style="margin-top:1.3rem; gap:1.2rem;">
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/hand.png" /></div>
    <h3>Human Labor</h3>
    <p class="bad" style="font-weight:700; margin-top:0.4rem;">Not fair. Too slow.</p>
  </div>
  <span class="arrow">→</span>
  <div class="card center" style="flex:1.25; border: 2px solid var(--leaf); background: rgba(30,122,64,0.06); transform: scale(1.05);" v-click>
    <div class="chip-ic" style="margin:0.2rem auto 0.4rem; background:transparent;"><img src="./media/icons/leaf.png" style="width:2rem;height:2rem;" /></div>
    <h3 style="color:var(--leaf-deep);">Seed Bank</h3>
    <p style="color:var(--text); font-weight:600; margin-top:0.3rem;">The best of both</p>
    <p class="mut" style="font-size:0.88rem; margin-top:0.3rem;">More sure than the eye. Much cheaper than machines.</p>
  </div>
  <span class="arrow">←</span>
  <div class="card center" style="flex:1;">
    <div class="chip-ic" style="margin:0 auto 0.5rem;"><img src="./media/icons/factory.png" /></div>
    <h3>Mechanical Sorters</h3>
    <p class="bad" style="font-weight:700; margin-top:0.4rem;">Works well. Too costly.</p>
  </div>
</div>

<p class="lead center" style="margin-top:1rem;" v-click>It works in two simple steps. First it <strong>finds each seed</strong>. Then it <strong>grades each one</strong>, good or bad.</p>

<!--
The answer sits in the middle. The two side options are already familiar from the last slide, so
click to pop in the Seed Bank card as the resolution, then click to reveal the two AI steps
(find each seed, then grade it). The deep dive comes later in the AI pipeline section.
Next: the idea in one line.
-->

---

<!-- SLIDE 5 - The Idea in One Line -->

<div class="act-tag">SOLUTION</div>

# The Idea in One Line

<div class="grid2" style="align-items:center; margin-top:0.3rem;">
  <div class="center">
    <div class="diagram" style="display:inline-block; padding:0.5rem;" v-motion :initial="{ opacity: 0, y: 26 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }"><img src="./media/screenshots/Dashboard.png" style="max-height:5.2in; width:auto; max-width:100%; display:block; border-radius:0.3rem;" /></div>
  </div>
  <div v-motion :initial="{ opacity: 0, x: 24 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 300 } }">
    <p class="lead">Seed Bank puts a seed-quality check right in your pocket.</p>
    <p class="mut" style="margin-top:0.5rem;">Show it your seeds and get a clear good-or-bad report, on your phone in the field, or on the web in a lab.</p>
    <div class="pills" style="justify-content:flex-start; margin-top:1rem;">
      <span class="pill"><img src="./media/icons/smartphone.png" /> On mobile</span>
      <span class="pill"><img src="./media/icons/monitor.png" /> On web</span>
      <span class="pill"><img src="./media/icons/languages.png" /> English / Arabic</span>
    </div>
  </div>
</div>

<!--
The whole product in one breath: take a photo, the AI checks it, you get a report. It runs on web
and on mobile. Keep it to three beats; details come later.
-->

---

<!-- SLIDE 6 - One Tool for Both Groups -->

<div class="act-tag">SOLUTION</div>

# One Tool for Both Groups

<div class="grid2" style="margin-top:0.5rem;">
  <div class="card accent" v-click>
    <div class="icard"><div class="chip-ic"><img src="./media/icons/smartphone.png" /></div><div class="tx"><h3>Mobile app, for the farmer</h3><p class="mut">Take a photo in the field</p></div></div>
    <p style="margin-top:0.7rem; font-size:0.95rem;">Just point your phone and snap. The answer comes back right there in the field. No lab, no costly machine.</p>
  </div>
  <div class="card accent" v-click>
    <div class="icard"><div class="chip-ic"><img src="./media/icons/factory.png" /></div><div class="tx"><h3>Conveyor mode, for the factory</h3><p class="mut">A fixed camera over a moving belt</p></div></div>
    <p style="margin-top:0.7rem; font-size:0.95rem;">A fixed camera watches the moving belt, and the same app grades seed after seed. It brings automation without the very costly machine.</p>
  </div>
</div>

<p class="lead center" style="margin-top:0.9rem;">The same AI runs in two ways, and <strong>one system powers both</strong>.</p>

<div class="grid4" style="margin-top:0.9rem;" v-click>
  <div class="card center" style="padding:0.85rem 0.6rem;"><h3 style="margin:0; font-size:1rem;">Quality check</h3></div>
  <div class="card center" style="padding:0.85rem 0.6rem;"><h3 style="margin:0; font-size:1rem;">Quick results</h3></div>
  <div class="card center" style="padding:0.85rem 0.6rem;"><h3 style="margin:0; font-size:1rem;">Charts &amp; history</h3></div>
  <div class="card center" style="padding:0.85rem 0.6rem;"><h3 style="margin:0; font-size:1rem;">Your account</h3></div>
</div>

<!--
The same AI ships in two forms: a mobile app for the small farmer, and a conveyor mode for the big
factory (a fixed camera over a belt). One backend serves both. Click through the two cards, then the
four things it does. Next: our proposed system and what it does.
-->

---

<!-- SLIDE 7 - Our Answer: The Seed Bank System -->

<div class="act-tag">SOLUTION</div>

# Our Answer: The Seed Bank System

<div class="thesis">"Show Seed Bank your seeds: a photo, a batch, or live video, and get a clear good-or-bad report, on a phone in the field or on the web in a lab."</div>

<div class="pipeline" style="margin:1.1rem 0;" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 150 } }">
  <div class="stage io"><img class="ic" src="./media/icons/camera.png" /> Capture<small>photo · batch · video / live</small></div>
  <span class="arrow">→</span>
  <div class="stage detect"><img class="ic" src="./media/icons/scan.png" /> Find every seed</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/badge-check.png" /> Grade each one</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/bar-chart-3.png" /> Get a report</div>
</div>

<div class="grid2" style="margin-top:0.7rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 300 } }">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/tractor.png" /></div><div class="tx"><h3>For the farmer</h3><p class="mut">Snap a batch, get the analysis, and look back over your history, on web or mobile, in English or Arabic.</p></div></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/flask-conical.png" /></div><div class="tx"><h3>For the AI team</h3><p class="mut">Manage the models, run evaluations, and trace every result back to the exact model that made it.</p></div></div></div>
</div>

<!--
The whole system in one breath: photo in, quality report out. Two kinds of user: the farmer
checking a batch, and the AI team running the models behind it. No tooling detail yet.
→ Next: how we stack up against what already exists.
-->

---

<!-- SLIDE 8 - Competitor Landscape -->

<div class="act-tag">RELATED WORK</div>

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

<p class="lead center" style="margin-top:0.7rem; font-size:0.9rem;">Affordable, works anywhere, many crops, fine-grained, and open to extend. The all-green column is us, <strong>Seed Bank</strong>.</p>

<!--
Where we sit: affordable, accessible, multi-crop, fine-grained, and extensible. Highlight the
column that's all-green (us). → Next: how the system works, at a glance.
-->

---

<!-- SLIDE 11 — Why did we use Deep Learning? -->

<div class="act-tag">AI PIPELINE · APPROACH</div>

# Why did we use Deep Learning?

<div class="grid2" style="margin-top:0.6rem; align-items:center;">
<div>

<p class="lead">For complex Computer Vision tasks, traditional Machine Learning hits a hard ceiling due to its reliance on <strong>manual feature engineering</strong>.</p>

<div class="pipeline" style="justify-content:flex-start; margin: 1.2rem 0;" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 200 } }">
  <div class="stage io"><img class="ic" src="./media/icons/image.png" /> Raw Pixels</div>
  <span class="arrow">→</span>
  <div class="stage classify"><img class="ic" src="./media/icons/cpu.png" /> Hidden Layers</div>
  <span class="arrow">→</span>
  <div class="stage io"><img class="ic" src="./media/icons/badge-check.png" /> Abstract Features</div>
</div>

<div class="warn" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 550, delay: 350 } }">
  <div class="icard"><img class="ic" src="./media/icons/alert-amber.png" style="width:1.6rem;height:1.6rem;" /><div><em>"Deep learning allows models... to learn representations of data with multiple levels of abstraction."</em> <br/><small>— LeCun, Bengio, &amp; Hinton (Nature, 2015)</small></div></div>
</div>

</div>

<div style="display:flex; flex-direction:column; gap:0.6rem;" v-motion :initial="{ opacity: 0, x: 20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 550, delay: 350 } }">
  <div class="card accent" style="padding: 1rem;">
    <h3 style="margin-bottom:0.2rem;"><img class="ic" src="./media/icons/layers.png" /> Automatic Feature Extraction</h3>
    <p class="mut" style="font-size:0.85rem; margin:0;">Unlike classic ML, Deep Learning doesn't require hand-crafted features (shape, color). It directly extracts optimal high-level features from raw images.</p>
  </div>
  <div class="card accent" style="padding: 1rem;">
    <h3 style="margin-bottom:0.2rem;"><img class="ic" src="./media/icons/cpu.png" /> Multiple Hidden Parameters</h3>
    <p class="mut" style="font-size:0.85rem; margin:0;">Seeds are organic with massive unstructured variance. The deep architecture's hidden parameters capture these complex, non-linear patterns perfectly.</p>
  </div>
  <div class="card accent" style="padding: 1rem;">
    <h3 style="margin-bottom:0.2rem;"><img class="ic" src="./media/icons/target.png" /> Unmatched CV Performance</h3>
    <p class="mut" style="font-size:0.85rem; margin:0;">In visual classification, DL is the industry standard because its performance dynamically scales, easily surpassing the structural limits of traditional ML.</p>
  </div>
</div>

</div>

<!--
Explain that manual feature engineering fails on organic, irregular objects like seeds.
Deep layers extract high-level features automatically with millions of hidden parameters, making DL structurally superior for CV.
-->


---

<!-- SLIDE 13 — Splitting the Problem -->

<div class="act-tag">AI PIPELINE · Phase 1</div>

# Splitting the Problem

<p class="lead center" style="margin-top: 1.2rem; font-weight: 600;">To solve this effectively, we split the challenge based on Inter-class and Intra-class variance.</p>

<div class="grid2" style="margin-top:1.5rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent">
    <div class="icard">
      <div class="chip-ic"><img src="./media/icons/scan.png" /></div>
      <div class="tx">
        <h3>Inter-class Variance</h3>
        <p class="mut">Differences BETWEEN species</p>
      </div>
    </div>
    <ul style="margin-top:0.8rem; font-size:0.9rem; color:var(--text); line-height: 1.4;">
      <li><strong>Macro-level traits:</strong> Core shape, size, and texture differences between Maize, Cotton, etc.</li>
      <li><strong>Easier to learn:</strong> Species are visually distinct from one another.</li>
      <li><strong>Our Use Case:</strong> Detection (finding the seed vs background).</li>
    </ul>
    <div style="margin-top: 1.2rem; display: flex; gap: 0.5rem; justify-content: center; height: 100px;">
      <div style="flex: 1; background: rgba(30,122,64,0.05); border: 2px dashed var(--leaf-line); border-radius: 0.5rem; display: flex; align-items: center; justify-content: center;">
        <span class="mut" style="font-size: 0.8rem; font-weight: 600; text-align: center;">[Seed Type A Image]</span>
      </div>
      <div style="flex: 1; background: rgba(30,122,64,0.05); border: 2px dashed var(--leaf-line); border-radius: 0.5rem; display: flex; align-items: center; justify-content: center;">
        <span class="mut" style="font-size: 0.8rem; font-weight: 600; text-align: center;">[Seed Type B Image]</span>
      </div>
    </div>
  </div>
  <div class="card accent">
    <div class="icard">
      <div class="chip-ic"><img src="./media/icons/badge-check.png" /></div>
      <div class="tx">
        <h3>Intra-class Variance</h3>
        <p class="mut">Differences WITHIN the same species</p>
      </div>
    </div>
    <ul style="margin-top:0.8rem; font-size:0.9rem; color:var(--text); line-height: 1.4;">
      <li><strong>Micro-level traits:</strong> Subtle cracks, discoloration, or tiny fungal spots on the exact same seed type.</li>
      <li><strong>Harder to learn:</strong> The core object remains identical, requiring fine-grained analysis.</li>
      <li><strong>Our Use Case:</strong> Quality Classification (Healthy vs Defective).</li>
    </ul>
    <div style="margin-top: 1.2rem; display: flex; gap: 0.5rem; justify-content: center; height: 100px;">
      <div style="flex: 1; background: rgba(30,122,64,0.05); border: 2px dashed var(--leaf-line); border-radius: 0.5rem; display: flex; align-items: center; justify-content: center;">
        <span class="mut" style="font-size: 0.8rem; font-weight: 600; text-align: center;">[Healthy Seed Image]</span>
      </div>
      <div style="flex: 1; background: rgba(30,122,64,0.05); border: 2px dashed var(--leaf-line); border-radius: 0.5rem; display: flex; align-items: center; justify-content: center;">
        <span class="mut" style="font-size: 0.8rem; font-weight: 600; text-align: center;">[Defective Seed Image]</span>
      </div>
    </div>
  </div>
</div>

<!--
We split based on variance: Inter-class (macro differences between species used for Detection) and Intra-class (micro differences within a species used for Classification).
-->

---

<!-- SLIDE 14 — Detection Results -->

<div class="act-tag">AI PIPELINE · Phase 1</div>

# Inter-class research results

<div class="grid2" style="margin-bottom: 0.8rem; align-items:center;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }">
  <div style="font-size: 0.85rem; line-height: 1.4; color: var(--text);">
    <p>We first used <strong>Faster R-CNN with a ResNet-50 backbone</strong> to compare initial results on single-class (maize) versus multi-class (maize & coffee).</p>
    <p style="margin-top:0.4rem;">These predicted coordinates are then used to crop and extract the specific seed region, passing only the isolated <strong>"Region of Interest" (RoI)</strong> to the classification model. This two-stage approach ensures the classifier focuses exclusively on the seed features, eliminating noise from the background or adjacent seeds.</p>
  </div>
  <div style="display:flex; justify-content:center;">
    <img src="./media/heatmaps/FASTERRCNN_HEATMAP.png" style="max-height: 160px; border-radius: 0.4rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" />
  </div>
</div>

<div class="card accent" style="padding: 0.4rem 0.6rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 100 } }"><table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.75rem;"><thead><tr style="border-bottom: 1px solid var(--leaf-line);"><th style="padding: 0.2rem;">Metric</th><th style="padding: 0.2rem;">Std Faster R-CNN<br/><small>(Maize only)</small></th><th style="padding: 0.2rem;">+ CBAM<br/><small>(Maize only)</small></th><th style="padding: 0.2rem;">Std Faster R-CNN<br/><small>(Maize & Coffee)</small></th><th style="padding: 0.2rem;">+ CBAM<br/><small>(Maize & Coffee)</small></th><th style="padding: 0.2rem;">YOLOv8s<br/><small>(Alternative)</small></th></tr></thead><tbody><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.2rem; font-weight: 600;">Avg Inference Time</td><td style="padding: 0.2rem;">0.1511s</td><td style="padding: 0.2rem;">0.0621s</td><td style="padding: 0.2rem;">0.1038s</td><td style="padding: 0.2rem;">0.1106s</td><td style="padding: 0.2rem; font-weight:bold; color:var(--leaf-deep);">5.5ms</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.2rem; font-weight: 600;">mAP@50 (Standard)</td><td style="padding: 0.2rem;">0.9780</td><td style="padding: 0.2rem;">0.9768</td><td style="padding: 0.2rem;">0.9838</td><td style="padding: 0.2rem;">0.9835</td><td style="padding: 0.2rem;">0.9410</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.2rem; font-weight: 600;">mAP@75 (Strict)</td><td style="padding: 0.2rem;">0.6574</td><td style="padding: 0.2rem;">0.6576</td><td style="padding: 0.2rem;">0.8015</td><td style="padding: 0.2rem;">0.8020</td><td style="padding: 0.2rem; color:var(--mut);">-</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.2rem; font-weight: 600;">mAP@.5:.95 (COCO)</td><td style="padding: 0.2rem;">0.5903</td><td style="padding: 0.2rem;">0.5867</td><td style="padding: 0.2rem;">0.7038</td><td style="padding: 0.2rem;">0.7211</td><td style="padding: 0.2rem; color:var(--mut);">-</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.2rem; font-weight: 600;">Precision</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem;">0.9390</td></tr><tr><td style="padding: 0.2rem; font-weight: 600;">Recall</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem; color:var(--mut);">-</td><td style="padding: 0.2rem;">0.9410</td></tr></tbody></table></div>

<!--
The Faster R-CNN metrics compared with and without CBAM for single vs multi class.
YOLOv8s added as a high-speed alternative reference.
-->

<!-- SLIDE 15 — Optimizing Inter-class Detection (Table) -->

<div class="act-tag">AI PIPELINE · Phase 1</div>

# Optimizing Inter-class Detection

<div class="card accent" style="padding: 0.8rem 1rem; margin: 1.5rem 0;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }"><table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.85rem;"><thead><tr style="border-bottom: 1px solid var(--leaf-line);"><th style="padding: 0.4rem;">Architecture Setup</th><th style="padding: 0.4rem;">Training Time (Avg)</th><th style="padding: 0.4rem;">mAP@50</th><th style="padding: 0.4rem;">mAP@75</th><th style="padding: 0.4rem;">mAP@0.50:0.95</th></tr></thead><tbody><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.4rem; font-weight: 600;">Test 1: Swin backbone + FPN</td><td style="padding: 0.4rem;">430.08 s</td><td style="padding: 0.4rem;">0.9487</td><td style="padding: 0.4rem;">0.5543</td><td style="padding: 0.4rem;">0.5827</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05); background: rgba(30,122,64,0.05);"><td style="padding: 0.4rem; font-weight: 600;">Test 2: Swin backbone + FPN + CIoU Loss</td><td style="padding: 0.4rem; color: #d97706; font-weight: bold;">729.53 s (↑)</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.9805 (↑)</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.7078 (↑)</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.6585 (↑)</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.4rem; font-weight: 600;">Test 3: ResNet-50 + Faster R-CNN</td><td style="padding: 0.4rem; color: var(--mut);">-</td><td style="padding: 0.4rem;">0.8697</td><td style="padding: 0.4rem;">0.5466</td><td style="padding: 0.4rem;">0.5253</td></tr><tr><td style="padding: 0.4rem; font-weight: 600;">Test 4: ResNet-50 + Faster R-CNN + PANet</td><td style="padding: 0.4rem;">391.98 s</td><td style="padding: 0.4rem; color: #dc2626; font-weight: bold;">0.8524 (↓)</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.6952 (↑)</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.6142 (↑)</td></tr></tbody></table></div>

<!--
Analysis of Inter-class detection metrics.
-->

---

<!-- SLIDE 16 — Optimizing Inter-class Detection (Explanations) -->

<div class="act-tag">AI PIPELINE · Phase 1</div>

# Optimizing Inter-class Detection

<div class="grid2" style="margin-top: 2rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 150 } }">
  <div class="card win" style="padding: 1.2rem;">
    <h3 style="font-size: 1.1rem; margin: 0 0 0.5rem 0;"><img class="ic" src="./media/icons/trending-up.png" /> Adding CIoU Loss (Test 1 → 2)</h3>
    <p style="font-size: 0.95rem; line-height: 1.4; margin:0;"><strong>Why mAP soared:</strong> CIoU penalizes bounding box aspect ratio and center-point distance, not just overlap. This forces the model to draw much tighter boundaries around seeds, drastically improving strict localization metrics (mAP@75 jumped from 0.55 to 0.70).</p>
    <p style="font-size: 0.95rem; line-height: 1.4; margin-top:0.6rem; color: #b45309;"><strong>The tradeoff:</strong> The complex geometric calculations of CIoU nearly doubled the training time (430s to 729s).</p>
  </div>
  
  <div class="card win" style="padding: 1.2rem;">
    <h3 style="font-size: 1.1rem; margin: 0 0 0.5rem 0;"><img class="ic" src="./media/icons/layers.png" /> Adding PANet (Test 3 → 4)</h3>
    <p style="font-size: 0.95rem; line-height: 1.4; margin:0;"><strong>Why mAP@75 increased:</strong> PANet adds a bottom-up path augmentation, preserving low-level edge details. This makes localization highly precise, jumping mAP@75 by +0.15.</p>
    <p style="font-size: 0.95rem; line-height: 1.4; margin-top:0.6rem; color: #dc2626;"><strong>Why mAP@50 dropped:</strong> The enhanced feature fusion made the model's confidence threshold overly rigid. It became so strict about perfectly tight boundaries that it rejected slightly loose boxes it previously accepted, causing a tiny drop in loose mAP@50.</p>
  </div>
</div>

<!--
Analysis of Inter-class detection architectural upgrades.
-->

---

<!-- SLIDE 17 — Intra-class Quality Models (First Results) -->

<div class="act-tag">AI PIPELINE · Phase 2</div>

# Intra-class Quality Models (Maize)

<p style="font-size: 0.95rem; line-height: 1.4; color: var(--text); margin-bottom: 1rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }">To tackle <strong>intra-class variance</strong> (quality classification), we began with a Baseline ResNet-18 and systematically introduced architectural modifications. These initial tests evaluate the model's ability to classify healthy versus defective <strong>maize seeds</strong>.</p>

<div class="card accent" style="padding: 0.8rem 1rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 100 } }"><table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.85rem;"><thead><tr style="border-bottom: 1px solid var(--leaf-line);"><th style="padding: 0.4rem;">Model Version</th><th style="padding: 0.4rem;">Architecture Modifications</th><th style="padding: 0.4rem;">F1-Score</th><th style="padding: 0.4rem;">Precision</th><th style="padding: 0.4rem;">Recall</th></tr></thead><tbody><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.4rem; font-weight: 600;">V1</td><td style="padding: 0.4rem;">Baseline ResNet-18</td><td style="padding: 0.4rem;">0.9056</td><td style="padding: 0.4rem;">0.8898</td><td style="padding: 0.4rem;">0.9219</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 0.4rem; font-weight: 600;">V2</td><td style="padding: 0.4rem;">+ CBAM</td><td style="padding: 0.4rem;">0.9023</td><td style="padding: 0.4rem;">0.8988</td><td style="padding: 0.4rem;">0.9058</td></tr><tr style="border-bottom: 1px solid rgba(0,0,0,0.05); background: rgba(30,122,64,0.05);"><td style="padding: 0.4rem; font-weight: 600;">V3</td><td style="padding: 0.4rem;">+ CBAM + GMP</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.9101</td><td style="padding: 0.4rem;">0.8877</td><td style="padding: 0.4rem; color: var(--leaf-deep); font-weight: bold;">0.9335</td></tr><tr><td style="padding: 0.4rem; font-weight: 600;">V4</td><td style="padding: 0.4rem;">+ CBAM + GMP + Stride (1,1)</td><td style="padding: 0.4rem;">0.9000</td><td style="padding: 0.4rem;">0.8803</td><td style="padding: 0.4rem;">0.9206</td></tr></tbody></table></div>

<div class="grid2" style="margin-top: 1.2rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 200 } }">
  <div class="card win" style="padding: 1rem;">
    <h3 style="font-size: 0.95rem; margin: 0 0 0.4rem 0;"><img class="ic" src="./media/icons/check-green.png" /> The V3 Sweet Spot</h3>
    <p style="font-size: 0.85rem; line-height: 1.4; margin:0;">Adding <strong>Global MaxPooling (GMP)</strong> alongside CBAM (V3) forced the network to identify the single most discriminative feature (like a tiny defect crack on the maize surface), pushing both F1 and Recall to their highest points.</p>
  </div>
  <div class="card prob" style="padding: 1rem;">
    <h3 style="font-size: 0.95rem; margin: 0 0 0.4rem 0;"><img class="ic" src="./media/icons/alert-amber.png" /> Stride (1,1) Degradation</h3>
    <p style="font-size: 0.85rem; line-height: 1.4; margin:0;">Attempting to retain ultra-fine spatial resolution by altering the early convolution stride (V4) actually harmed the network. It introduced too much background noise, causing a regression across all metrics compared to V3.</p>
  </div>
</div>

<!--
Initial intra-class variance classification results on Maize using ResNet-18.
-->

---

<!-- SLIDE 18 — EfficientNet-B2: Maize vs Soybean -->

<div class="act-tag">AI PIPELINE · Phase 2</div>

# Upgrading to EfficientNet-B2

<div style="font-size: 0.85rem; line-height: 1.4; margin-bottom: 1rem;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500 } }">
  <p>To improve fine-grained, multi-label defect classification, we upgraded to <strong>EfficientNet-B2</strong>. Its compound scaling dynamically balances depth, width, and resolution, allowing it to extract much richer feature representations. Crucially, we maintained the exact same <strong>V3 configuration</strong> that succeeded previously, integrating <strong>CBAM block attention</strong> and <strong>Hybrid Pooling (GMP)</strong> into the new architecture.</p>
</div>

<div class="grid2" style="align-items:start;" v-motion :initial="{ opacity: 0, y: 15 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 100 } }">
  <div class="card win" style="padding: 0.8rem 1rem;">
    <h3 style="font-size: 0.95rem; margin: 0 0 0.4rem 0;"><img class="ic" src="./media/icons/check-green.png" /> Maize (Robust Generalization)</h3>
    <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.75rem; margin-bottom: 0.6rem;">
      <thead><tr style="border-bottom: 1px solid rgba(0,0,0,0.1);"><th style="padding:0.2rem;">Epoch</th><th style="padding:0.2rem;">Val Loss</th><th style="padding:0.2rem;">Macro-F1</th><th style="padding:0.2rem;">Micro-F1</th><th style="padding:0.2rem;">Exact Match</th></tr></thead>
      <tbody>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">001</td><td style="padding:0.2rem;">0.2695</td><td style="padding:0.2rem;">0.8078</td><td style="padding:0.2rem;">0.8016</td><td style="padding:0.2rem;">0.6224</td></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">003</td><td style="padding:0.2rem;">0.1027</td><td style="padding:0.2rem;">0.9253</td><td style="padding:0.2rem;">0.9242</td><td style="padding:0.2rem;">0.8658</td></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">005</td><td style="padding:0.2rem;">0.0555</td><td style="padding:0.2rem;">0.9641</td><td style="padding:0.2rem;">0.9640</td><td style="padding:0.2rem;">0.9387</td></tr>
        <tr><td style="padding:0.2rem; font-weight:bold;">007</td><td style="padding:0.2rem; font-weight:bold;">0.0447</td><td style="padding:0.2rem; color:var(--leaf-deep); font-weight:bold;">0.9740</td><td style="padding:0.2rem; font-weight:bold;">0.9740</td><td style="padding:0.2rem; font-weight:bold;">0.9565</td></tr>
      </tbody>
    </table>
    <p style="font-size: 0.75rem; line-height: 1.4; margin:0; color:var(--mut);">Photographed under natural sunlight with variable background noise. The model successfully learned robust, generalizable features, achieving stable convergence.</p>
  </div>
  
  <div class="card prob" style="padding: 0.8rem 1rem;">
    <h3 style="font-size: 0.95rem; margin: 0 0 0.4rem 0;"><img class="ic" src="./media/icons/alert-amber.png" /> Soybean (Severe Overfitting)</h3>
    <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 0.75rem; margin-bottom: 0.6rem;">
      <thead><tr style="border-bottom: 1px solid rgba(0,0,0,0.1);"><th style="padding:0.2rem;">Epoch</th><th style="padding:0.2rem;">Val Loss</th><th style="padding:0.2rem;">Macro-F1</th><th style="padding:0.2rem;">Micro-F1</th><th style="padding:0.2rem;">Exact Match</th></tr></thead>
      <tbody>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">001</td><td style="padding:0.2rem;">0.2614</td><td style="padding:0.2rem;">0.8114</td><td style="padding:0.2rem;">0.7977</td><td style="padding:0.2rem;">0.6464</td></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">004</td><td style="padding:0.2rem;">0.0516</td><td style="padding:0.2rem;">0.9603</td><td style="padding:0.2rem;">0.9597</td><td style="padding:0.2rem;">0.9278</td></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding:0.2rem;">008</td><td style="padding:0.2rem;">0.0235</td><td style="padding:0.2rem;">0.9889</td><td style="padding:0.2rem;">0.9888</td><td style="padding:0.2rem;">0.9829</td></tr>
        <tr><td style="padding:0.2rem; font-weight:bold;">012</td><td style="padding:0.2rem; font-weight:bold;">0.0203</td><td style="padding:0.2rem; color:#dc2626; font-weight:bold;">0.9936</td><td style="padding:0.2rem; font-weight:bold;">0.9936</td><td style="padding:0.2rem; font-weight:bold;">0.9916</td></tr>
      </tbody>
    </table>
    <p style="font-size: 0.75rem; line-height: 1.4; margin:0; color:var(--mut);">Pre-segmented boxes in sterile, lab-controlled environments. The network merely memorized clean pixel distributions (reaching an artificially high 0.9936) and failed to learn robust real-world features.</p>
  </div>
</div>

<!--
Comparing EfficientNet-B2 classification on Maize vs Soybean datasets, proving data quality dictates generalizability.
-->

---
class: center-slide
---

<!-- SLIDE 18 — Detection Still Overfits — We Need Our Own Data -->

<div class="act-tag">AI PIPELINE · Phase 2 + MultiSeedGen</div>

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

<!-- SLIDE 19 — MultiSeedGen: Building Our Own Training Data -->

<div class="act-tag">AI PIPELINE · Phase 2 + MultiSeedGen</div>

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

<!-- SLIDE 20 — Segmentation: 6 Ways to Cut a Seed -->

<div class="act-tag">AI PIPELINE · Phase 2 + MultiSeedGen</div>

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

<!-- SLIDE 21 — Augmentation & Domain Bridging -->

<div class="act-tag">AI PIPELINE · Phase 2 + MultiSeedGen</div>

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

<!-- SLIDE 22 — MultiSeedGen Web UI + Data Loop -->

<div class="act-tag">AI PIPELINE · Phase 2 + MultiSeedGen</div>

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

<!-- SLIDE 23 — Detection Experiments: The Full Journey -->

<div class="act-tag">RESULTS</div>

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

<!-- SLIDE 24 — Classification: Data Quality > Model Architecture -->

<div class="act-tag">RESULTS</div>

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

<!-- SLIDE 25 — Speed vs. Precision -->

<div class="act-tag">RESULTS</div>

# Speed vs. Precision: Two Deployment Modes

<div class="grid2" style="margin-top:0.3rem;">
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/target.png" /></div><div class="tx"><h3>Precision Mode</h3><p>Faster R-CNN + EfficientNet-B2</p></div></div><div class="pills" style="justify-content:flex-start; margin-top:0.5rem;"><span class="pill">~230ms · 4.3 FPS</span><span class="pill">7-class multi-label</span><span class="pill">QA labs</span></div></div>
  <div class="card accent"><div class="icard"><div class="chip-ic"><img src="./media/icons/zap.png" /></div><div class="tx"><h3>Speed Mode</h3><p>YOLOv8</p></div></div><div class="pills" style="justify-content:flex-start; margin-top:0.5rem;"><span class="pill">~80ms · 12.5 FPS</span><span class="pill">Real-time</span><span class="pill">Conveyor belts</span></div></div>
</div>

<div class="diagram" style="margin-top:0.7rem; max-height:2.6in; overflow:hidden;" v-motion :initial="{ opacity: 0, scale: 0.94 }" :enter="{ opacity: 1, scale: 1, transition: { duration: 600, delay: 250 } }"><img src="./media/screenshots/YOLO-realtime.png" /></div>

<p class="lead center" style="margin-top:0.4rem; font-size:0.82rem;"><strong>876 seeds</strong> detected in one dense frame — a detection-model demo of speed-mode throughput (both run on an RTX 3060).</p>

<!--
Two deployment modes — precision vs speed. Be precise: the 876-seed image is a model demo of
dense detection; the product realtime experience is the mobile frame-streaming mode shown in the platform section.
→ Next: how we compare to what's already out there.
-->

---
class: center-slide
---

<!-- SLIDE 26 — From Trained Models to a Real Product -->

<div class="act-tag">THE PLATFORM</div>

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



---

<!-- SLIDE 28 — One Platform, Two Audiences, Two Languages -->

<div class="act-tag">THE PLATFORM</div>

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

<!-- SLIDE 29 — System Architecture -->

<div class="act-tag">THE PLATFORM</div>

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

<p class="lead center" style="margin-top:0.5rem; font-size:0.85rem;">The deep dive on the high-level view from Slide 9 — clean layering is <em>why</em> each piece is swappable and testable.</p>

<!--
The payoff of the high-level architecture we teased at Slide 9 — clean layered design, async
end-to-end, seven core services that come up with one command. Don't go deeper than that.
→ Next: let's follow one photo all the way through.
-->

---
class: dense
---

<!-- SLIDE 30 — The Analyze Pipeline, End-to-End -->

<div class="act-tag">THE PLATFORM</div>

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
Trace a single analyze request end-to-end — the two-stage pipeline from Slide 10 in motion: the
fan-out, per-seed-type routing, and the concurrency-safe state machine that degrades gracefully to
"partial" instead of failing. → Next: how every result stays traceable to a model.
-->

---

<!-- SLIDE 31 — Model Traceability & Lifecycle -->

<div class="act-tag">THE PLATFORM</div>

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

<!-- SLIDE 32 - Secure by Design -->

<div class="act-tag">THE PLATFORM</div>

# Secure by Design

<div class="grid4" style="margin-top:0.5rem;" v-motion :initial="{ opacity: 0, y: 22 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/key.png" /></div><h3>JWT + refresh rotation</h3><p>Short-lived tokens; a reused refresh token invalidates the chain</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/link.png" /></div><h3>Google OAuth</h3><p>Social sign-in alongside email / password</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/users.png" /></div><h3>Role-based access</h3><p>end_user · ai_developer · admin, on every route</p></div>
  <div class="card"><div class="chip-ic" style="margin-bottom:0.4rem;"><img src="./media/icons/scroll-text.png" /></div><h3>Audit log + one error shape</h3><p>Append-only trail; consistent typed errors (RFC 9457)</p></div>
</div>

<!--
Security done properly for a student project: rotating refresh tokens with replay detection,
OAuth, real role-based access, an audit trail, and one consistent error contract. Keep it to the
four tiles; don't rabbit-hole. → Next: the full toolset at a glance.
-->

---

<!-- SLIDE 33 - Tech Stack at a Glance -->

<div class="act-tag">THE PLATFORM</div>

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
A quick grouped inventory: don't read every item, let it convey breadth and coherence. Note that
SAM lives in MultiSeedGen, our separate data tool, not the runtime backend. → Next: what we learned.
-->

---

<!-- SLIDE 34 — Key Takeaways -->

<div class="act-tag">CONCLUSION</div>

# Key Takeaways

<div class="grid3" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/bar-chart-3.png" /></div><h3>Data quality &gt; architecture</h3><p>The maize model won not because it was fancier, but because its data looked like the real world.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/git-branch.png" /></div><h3>Decouple detection from classification</h3><p>Keeping the two stages apart let us fix or upgrade one without ever touching the other.</p></div>
  <div class="card accent"><div class="chip-ic" style="margin-bottom:0.5rem;"><img src="./media/icons/factory.png" /></div><h3>Synthetic data narrows the gap</h3><p>MultiSeedGen freed us from hand-labelling — but real photos are still the only honest test.</p></div>
</div>

<!--
Three durable lessons — data > architecture, decouple the two stages, and synthetic data narrows
the gap but real evaluation is the only fair test. → Next: where it goes from here.
-->

---

<!-- SLIDE 35 — Future Roadmap -->

<div class="act-tag">FUTURE WORK</div>

# Future Roadmap

<div class="tl" style="margin-top:0.6rem;" v-motion :initial="{ opacity: 0, y: 24 }" :enter="{ opacity: 1, y: 0, transition: { duration: 550, delay: 200 } }">
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/sprout.png" /></div> <strong>More crops</strong> — grow real-world datasets to cover all 20+ species</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/cpu.png" /></div> <strong>Edge AI</strong> — run it right on the phone, with no internet needed</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/refresh-cw.png" /></div> <strong>Active learning</strong> — the scans it finds hardest flow back in to make it sharper</div>
  <div class="step"><div class="chip-ic" style="width:2rem;height:2rem;"><img src="./media/icons/factory.png" /></div> <strong>Real conveyor lines</strong> — realtime already runs on mobile; next we take it to fixed cameras over the belt itself</div>
</div>

<!--
Future work — more crops, edge AI, active learning; and note honestly that a realtime frame mode
already ships, so the frontier is hardware-integrated conveyor lines and instance segmentation for
overlap, not realtime itself. → Next: thanks and questions.
-->

---
class: cover-slide
---

<!-- SLIDE 36 — Team + Thank You + Questions -->

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
