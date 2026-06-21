/* ============================================================================
   Seed Bank — Dashboard / Analytics / Compare / Export + UI-UX enhancements.
   Self-contained module that augments the existing `App` object. Loaded after
   script.js. Uses Chart.js (CDN) for charts.
   ============================================================================ */
(function () {
  const API = (window.App && window.App.API_URL) || 'http://localhost:8000';

  /* ----------------------------- Toasts ---------------------------------- */
  const Toast = {
    wrap: null,
    ensure() {
      if (!this.wrap) {
        this.wrap = document.createElement('div');
        this.wrap.id = 'sb-toast-wrap';
        document.body.appendChild(this.wrap);
      }
    },
    show(message, type = 'success', timeout = 3600) {
      this.ensure();
      const el = document.createElement('div');
      el.className = `sb-toast ${type}`;
      const icon = type === 'error' ? 'alert-triangle' : type === 'info' ? 'info' : 'check-circle';
      el.innerHTML = `<i data-lucide="${icon}" class="w-5 h-5 sb-toast-icon"></i><div>${message}</div>`;
      this.wrap.appendChild(el);
      if (window.lucide) lucide.createIcons({ nodes: [el] });
      const kill = () => {
        el.classList.add('sb-out');
        setTimeout(() => el.remove(), 320);
      };
      el.addEventListener('click', kill);
      setTimeout(kill, timeout);
    },
  };
  window.SBToast = Toast;

  /* --------------------------- Dark mode --------------------------------- */
  const Theme = {
    KEY: 'sb-theme',
    apply(theme) {
      document.documentElement.classList.toggle('dark', theme === 'dark');
      const btn = document.getElementById('sb-theme-toggle');
      if (btn) {
        btn.innerHTML = `<i data-lucide="${theme === 'dark' ? 'sun' : 'moon'}" class="w-5 h-5"></i>`;
        if (window.lucide) lucide.createIcons({ nodes: [btn] });
      }
      // repaint charts for the new palette
      if (window.SBDashboard) window.SBDashboard.repaintCharts();
    },
    current() {
      return localStorage.getItem(this.KEY) ||
        (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    },
    toggle() {
      const next = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
      localStorage.setItem(this.KEY, next);
      this.apply(next);
      Toast.show(`${next === 'dark' ? 'Dark' : 'Light'} mode`, 'info', 1400);
    },
    init() { this.apply(this.current()); },
  };
  window.SBTheme = Theme;

  /* --------------------------- Count-up ---------------------------------- */
  function countUp(el, to, { duration = 900, decimals = 0, suffix = '' } = {}) {
    if (!el) return;
    const start = performance.now();
    const from = 0;
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const val = from + (to - from) * eased;
      el.textContent = (decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString()) + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  window.SBCountUp = countUp;

  /* ---------------------- Section navigation helper ---------------------- */
  function showSection(id) {
    ['upload-section', 'results-section', 'history-section', 'loading-section',
      'analytics-section', 'compare-section'].forEach((s) => {
      const el = document.getElementById(s);
      if (el) el.classList.add('hidden');
    });
    const target = document.getElementById(id);
    if (target) {
      target.classList.remove('hidden');
      target.classList.remove('sb-enter');
      void target.offsetWidth; // reflow to restart animation
      target.classList.add('sb-enter');
    }
  }
  window.SBShowSection = showSection;

  /* --------------------------- Charts theme ------------------------------ */
  function chartColors() {
    const dark = document.documentElement.classList.contains('dark');
    return {
      text: dark ? '#cbd5e1' : '#475569',
      grid: dark ? 'rgba(148,163,184,.15)' : 'rgba(100,116,139,.12)',
      green: '#16a34a',
      greenSoft: 'rgba(22,163,74,.18)',
      red: '#dc2626',
      redSoft: 'rgba(220,38,38,.18)',
      blue: '#2563eb',
      amber: '#d97706',
      palette: ['#16a34a', '#2563eb', '#d97706', '#7c3aed', '#db2777', '#0891b2'],
    };
  }

  /* --------------------------- Dashboard --------------------------------- */
  const Dashboard = {
    charts: {},
    lastData: null,

    async open(days = null) {
      showSection('analytics-section');
      this.renderSkeleton();
      try {
        const url = new URL(`${API}/api/analytics`);
        if (days) url.searchParams.set('days', days);
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Analytics failed: ${res.status}`);
        const data = (await res.json()).analytics;
        this.lastData = data;
        this.render(data);
      } catch (e) {
        console.error(e);
        Toast.show('Could not load analytics', 'error');
        const host = document.getElementById('analytics-body');
        if (host) host.innerHTML = `<div class="sb-card">Failed to load analytics. Is the API running?</div>`;
      }
    },

    renderSkeleton() {
      const host = document.getElementById('analytics-body');
      if (!host) return;
      const sk = (h) => `<div class="sb-skel" style="height:${h}"></div>`;
      host.innerHTML = `
        <div class="sb-kpi-grid" style="margin-bottom:1.25rem">
          ${[1, 2, 3, 4].map(() => `<div class="sb-kpi">${sk('64px')}</div>`).join('')}
        </div>
        <div class="sb-dash-grid">
          ${[1, 2, 3, 4].map(() => `<div class="sb-card">${sk('260px')}</div>`).join('')}
        </div>`;
    },

    render(d) {
      const host = document.getElementById('analytics-body');
      if (!host) return;
      const t = d.totals;
      host.innerHTML = `
        <div class="sb-kpi-grid" style="margin-bottom:1.25rem">
          <div class="sb-kpi blue"><div class="label">Batches</div><div class="value sb-countup" id="kpi-batches">0</div><div class="sub">${t.images} images</div></div>
          <div class="sb-kpi"><div class="label">Seeds analyzed</div><div class="value sb-countup" id="kpi-seeds">0</div><div class="sub">all time${d.period && d.period.days ? ` · last ${d.period.days}d` : ''}</div></div>
          <div class="sb-kpi"><div class="label">Good</div><div class="value sb-countup" id="kpi-good">0</div><div class="sub" id="kpi-good-pct">0%</div></div>
          <div class="sb-kpi red"><div class="label">Bad</div><div class="value sb-countup" id="kpi-bad">0</div><div class="sub" id="kpi-bad-pct">0%</div></div>
        </div>
        <div class="sb-dash-grid">
          <div class="sb-card"><h3>Quality split</h3><div class="sb-chart-wrap"><canvas id="ch-quality"></canvas></div></div>
          <div class="sb-card" style="grid-column: span 2; min-width:0"><h3>Daily quality trend</h3><div class="sb-chart-wrap"><canvas id="ch-trend"></canvas></div></div>
          <div class="sb-card"><h3>Seed types</h3><div class="sb-chart-wrap"><canvas id="ch-types"></canvas></div></div>
          <div class="sb-card"><h3>Seed size distribution (px²)</h3><div class="sb-chart-wrap"><canvas id="ch-size"></canvas></div></div>
          <div class="sb-card"><h3>Confidence distribution</h3><div class="sb-chart-wrap"><canvas id="ch-conf"></canvas></div></div>
        </div>`;

      countUp(document.getElementById('kpi-batches'), t.batches);
      countUp(document.getElementById('kpi-seeds'), t.seeds);
      countUp(document.getElementById('kpi-good'), t.good);
      countUp(document.getElementById('kpi-bad'), t.bad);
      document.getElementById('kpi-good-pct').textContent = `${t.good_percentage}%`;
      document.getElementById('kpi-bad-pct').textContent = `${t.bad_percentage}%`;

      this.buildCharts(d);
    },

    destroyCharts() {
      Object.values(this.charts).forEach((c) => c && c.destroy());
      this.charts = {};
    },

    repaintCharts() {
      if (this.lastData && document.getElementById('analytics-section') &&
          !document.getElementById('analytics-section').classList.contains('hidden')) {
        this.buildCharts(this.lastData);
      }
    },

    buildCharts(d) {
      if (!window.Chart) return;
      this.destroyCharts();
      const c = chartColors();
      Chart.defaults.color = c.text;
      Chart.defaults.font.family = 'Inter, sans-serif';

      const t = d.totals;
      // Quality doughnut
      this.charts.quality = new Chart(document.getElementById('ch-quality'), {
        type: 'doughnut',
        data: {
          labels: ['Good', 'Bad'],
          datasets: [{ data: [t.good, t.bad], backgroundColor: [c.green, c.red], borderWidth: 0 }],
        },
        options: { cutout: '68%', plugins: { legend: { position: 'bottom' } }, animation: { animateRotate: true } },
      });

      // Daily trend (good vs bad area)
      const tr = d.daily_trend || [];
      this.charts.trend = new Chart(document.getElementById('ch-trend'), {
        type: 'line',
        data: {
          labels: tr.map((r) => r.date),
          datasets: [
            { label: 'Good', data: tr.map((r) => r.good), borderColor: c.green, backgroundColor: c.greenSoft, fill: true, tension: .35 },
            { label: 'Bad', data: tr.map((r) => r.bad), borderColor: c.red, backgroundColor: c.redSoft, fill: true, tension: .35 },
          ],
        },
        options: {
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          scales: { x: { grid: { color: c.grid } }, y: { grid: { color: c.grid }, beginAtZero: true } },
          plugins: { legend: { position: 'bottom' } },
        },
      });

      // Seed types (horizontal bar)
      const ts = d.seed_type_split || [];
      this.charts.types = new Chart(document.getElementById('ch-types'), {
        type: 'bar',
        data: {
          labels: ts.map((s) => s.seed_type),
          datasets: [
            { label: 'Good', data: ts.map((s) => s.good), backgroundColor: c.green, stack: 's' },
            { label: 'Bad', data: ts.map((s) => s.bad), backgroundColor: c.red, stack: 's' },
          ],
        },
        options: {
          indexAxis: 'y', maintainAspectRatio: false,
          scales: { x: { stacked: true, grid: { color: c.grid }, beginAtZero: true }, y: { stacked: true, grid: { display: false } } },
          plugins: { legend: { position: 'bottom' } },
        },
      });

      // Size histogram
      this.charts.size = this.histogram('ch-size', d.size_distribution, c.blue);
      // Confidence histogram
      this.charts.conf = this.histogram('ch-conf', d.confidence_distribution, c.amber);
    },

    histogram(canvasId, dist, color) {
      const el = document.getElementById(canvasId);
      if (!el || !window.Chart) return null;
      const bins = dist.bins || [];
      const counts = dist.counts || [];
      const labels = counts.map((_, i) => {
        const a = bins[i], b = bins[i + 1];
        return a != null && b != null ? `${Math.round(a)}–${Math.round(b)}` : '';
      });
      const c = chartColors();
      return new Chart(el, {
        type: 'bar',
        data: { labels, datasets: [{ data: counts, backgroundColor: color, borderRadius: 4 }] },
        options: {
          maintainAspectRatio: false,
          scales: { x: { grid: { display: false } }, y: { grid: { color: c.grid }, beginAtZero: true } },
          plugins: { legend: { display: false } },
        },
      });
    },
  };
  window.SBDashboard = Dashboard;

  /* ----------------------------- Compare --------------------------------- */
  const Compare = {
    selection: new Set(),

    toggle(batchId, cardEl) {
      batchId = Number(batchId);
      if (this.selection.has(batchId)) {
        this.selection.delete(batchId);
        cardEl && cardEl.classList.remove('sb-selected');
      } else {
        if (this.selection.size >= 10) { Toast.show('Compare up to 10 batches', 'info'); return; }
        this.selection.add(batchId);
        cardEl && cardEl.classList.add('sb-selected');
      }
      this.updateBar();
    },

    updateBar() {
      const bar = document.getElementById('sb-compare-bar');
      const count = document.getElementById('sb-compare-count');
      if (!bar) return;
      if (this.selection.size >= 1) {
        bar.classList.remove('hidden');
        if (count) count.textContent = this.selection.size;
      } else {
        bar.classList.add('hidden');
      }
    },

    clear() {
      this.selection.clear();
      document.querySelectorAll('.sb-selected').forEach((e) => e.classList.remove('sb-selected'));
      this.updateBar();
    },

    async run() {
      if (this.selection.size < 2) { Toast.show('Select at least 2 batches to compare', 'info'); return; }
      const ids = [...this.selection];
      try {
        const res = await fetch(`${API}/api/compare`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ batch_ids: ids }),
        });
        if (!res.ok) throw new Error(`Compare failed: ${res.status}`);
        const data = await res.json();
        this.render(data.batches);
        showSection('compare-section');
      } catch (e) {
        console.error(e);
        Toast.show('Comparison failed', 'error');
      }
    },

    render(batches) {
      const host = document.getElementById('compare-body');
      if (!host) return;
      const maxSeeds = Math.max(...batches.map((b) => b.total_seeds || 0), 1);
      const rows = batches.map((b) => `
        <tr>
          <td><strong>#${b.id}</strong><div style="font-size:.72rem;color:var(--sb-text-muted)">${(b.created_at || '').slice(0, 10)}</div></td>
          <td>${b.image_count}</td>
          <td>${b.total_seeds}<div class="sb-bar" style="margin-top:.35rem"><span style="width:${(b.total_seeds / maxSeeds) * 100}%"></span></div></td>
          <td><span class="sb-chip">${b.good_percentage}% good</span></td>
          <td>${b.bad_seeds_count}</td>
          <td>${b.avg_confidence_score != null ? (b.avg_confidence_score * 100).toFixed(1) + '%' : '—'}</td>
          <td>${b.processing_duration_ms != null ? (b.processing_duration_ms / 1000).toFixed(2) + 's' : '—'}</td>
          <td>${Object.entries(b.seed_types || {}).map(([k, v]) => `<span class="sb-chip" style="margin-right:.25rem">${k}: ${v}</span>`).join('') || '—'}</td>
        </tr>`).join('');
      host.innerHTML = `
        <div class="sb-card" style="overflow-x:auto">
          <table class="sb-compare-table">
            <thead><tr>
              <th>Batch</th><th>Images</th><th>Total seeds</th><th>Quality</th>
              <th>Bad</th><th>Avg conf.</th><th>Time</th><th>Types</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        <div class="sb-card" style="margin-top:1.25rem"><h3>Good-quality % by batch</h3>
          <div class="sb-chart-wrap"><canvas id="ch-compare"></canvas></div></div>`;

      if (window.Chart) {
        const c = chartColors();
        if (this._chart) this._chart.destroy();
        this._chart = new Chart(document.getElementById('ch-compare'), {
          type: 'bar',
          data: {
            labels: batches.map((b) => `#${b.id}`),
            datasets: [{ label: 'Good %', data: batches.map((b) => b.good_percentage), backgroundColor: c.green, borderRadius: 6 }],
          },
          options: {
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, max: 100, grid: { color: c.grid } }, x: { grid: { display: false } } },
            plugins: { legend: { display: false } },
          },
        });
      }
    },
  };
  window.SBCompare = Compare;

  /* ------------------------------ Export --------------------------------- */
  function exportBatch(batchId, format) {
    const url = `${API}/api/batches/${batchId}/export.${format}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch_${batchId}_detections.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    Toast.show(`Exporting batch #${batchId} as ${format.toUpperCase()}`, 'success');
  }
  window.SBExport = exportBatch;

  /* ----------------------- Wire-up after load ---------------------------- */
  function wire() {
    Theme.init();

    document.getElementById('sb-theme-toggle')?.addEventListener('click', () => Theme.toggle());
    document.getElementById('btn-analytics')?.addEventListener('click', () => Dashboard.open());
    document.getElementById('sb-analytics-range')?.addEventListener('change', (e) => {
      const v = e.target.value;
      Dashboard.open(v === 'all' ? null : Number(v));
    });
    document.getElementById('sb-compare-run')?.addEventListener('click', () => Compare.run());
    document.getElementById('sb-compare-clear')?.addEventListener('click', () => Compare.clear());
    document.querySelectorAll('[data-sb-back]')?.forEach((b) =>
      b.addEventListener('click', () => {
        showSection('upload-section');
        if (window.App) window.App.reset && window.App.reset();
      }));

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.target.matches('input, textarea, select')) return;
      if (e.key === 'd' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); Theme.toggle(); }
      else if (e.key === 'a' && !e.ctrlKey && !e.metaKey) { Dashboard.open(); }
      else if (e.key === 'h' && !e.ctrlKey && !e.metaKey) { if (window.App?.showHistory) window.App.showHistory(); }
      else if (e.key === 'Escape') { showSection('upload-section'); }
    });

    if (window.lucide) lucide.createIcons();

    // Deep-link support: ?view=analytics|history opens that view directly.
    const params = new URLSearchParams(location.search);
    const view = params.get('view');
    if (view === 'analytics') Dashboard.open();
    else if (view === 'history' && window.App?.showHistory) window.App.showHistory();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();
