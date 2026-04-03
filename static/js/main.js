// ===== SCROLL REVEAL =====
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const siblings = Array.from(entry.target.parentElement.querySelectorAll('.reveal'));
      const idx = siblings.indexOf(entry.target);
      setTimeout(() => entry.target.classList.add('visible'), idx * 80);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.08 });
document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ===== HERO ENTRANCE =====
window.addEventListener('DOMContentLoaded', () => {
  const h = document.querySelector('.hero-content');
  if (h) {
    h.style.cssText = 'opacity:0;transform:translateY(20px);transition:opacity .8s ease,transform .8s ease';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      h.style.opacity = '1'; h.style.transform = 'none';
    }));
  }
});

// ===== TAB SWITCHER =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(id).classList.add('active');
    if (id === 'efficiency') renderAblationChart();
  });
});

// ===== ABLATION CHART =====
let chartDone = false;
function renderAblationChart() {
  if (chartDone) return; chartDone = true;
  const ctx = document.getElementById('ablationChart').getContext('2d');
  Chart.defaults.color = '#8b949e';
  Chart.defaults.borderColor = '#30363d';
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['LongVideoBench', 'MLVU', 'VideoMME Long', 'LVBench'],
      datasets: [
        { label:'SFT',  data:[49.9,52.3,45.8,26.5], backgroundColor:'rgba(31,111,235,.7)',  borderColor:'#1f6feb', borderWidth:1, borderRadius:4 },
        { label:'KTO',  data:[53.2,57.4,45.1,36.0], backgroundColor:'rgba(255,209,102,.7)', borderColor:'#ffd166', borderWidth:1, borderRadius:4 },
        { label:'GRPO', data:[55.1,68.3,48.4,43.3], backgroundColor:'rgba(6,214,160,.7)',   borderColor:'#06d6a0', borderWidth:1, borderRadius:4 },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color:'#e6edf3', font:{family:'Inter',size:13} } },
        tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.raw}%` } },
        title: { display:true, text:'Ablation: Training Stage Progression (Accuracy %)',
                 color:'#e6edf3', font:{family:'Inter',size:14,weight:'600'}, padding:{bottom:16} }
      },
      scales: {
        x: { ticks:{color:'#8b949e',font:{family:'Inter'}}, grid:{color:'#30363d'} },
        y: { ticks:{color:'#8b949e',font:{family:'Inter'},callback:v=>v+'%'}, grid:{color:'#30363d'}, min:20 }
      }
    }
  });
}

// ===== COPY BIBTEX =====
function copyBibtex() {
  const code = document.querySelector('.bibtex code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!'; btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 2000);
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
//   EVA DEMO — Canvas-based step animation
// ═══════════════════════════════════════════════════════════════════════════════

const STEP_MS   = 4500;
const N_STEPS   = 6;

// Deterministic PRNG for consistent frame colors
function seededRng(seed) {
  let s = seed >>> 0;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 0xffffffff; };
}

const C = {
  bg:     '#06080c',
  border: '#1e2330',
  accent: '#00b4d8',
  good:   '#06d6a0',
  bad:    '#ef476f',
  mid:    '#ffd166',
  muted:  '#606878',
  panel:  '#0c0e14',
  text:   '#e0e6f0',
};

// ─── Drawing helpers ──────────────────────────────────────────────────────────

function rr(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
  ctx.closePath();
}

function drawGrid(ctx, x0, y0, cols, rows, fw, fh, gap, opts = {}) {
  const { seed = 42, lowRes = false, hlRange = null, hlColor = C.bad, nShow = cols * rows } = opts;
  const rng = seededRng(seed);
  let n = 0;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (n >= nShow) return;
      const x = x0 + c * (fw + gap), y = y0 + r * (fh + gap);
      const h = Math.floor(rng() * 360);
      const sat = lowRes ? 12 : (20 + Math.floor(rng() * 20));
      const lig = lowRes ? (10 + Math.floor(rng() * 8)) : (18 + Math.floor(rng() * 16));
      ctx.fillStyle = `hsl(${h},${sat}%,${lig}%)`;
      ctx.fillRect(x, y, fw, fh);
      // content stripe
      ctx.fillStyle = `hsl(${h},${sat + 6}%,${lig + 10}%)`;
      ctx.fillRect(x + 2, y + Math.floor(fh * .35), fw - 4, Math.max(2, Math.floor(fh * .2)));

      if (hlRange && n >= hlRange[0] && n <= hlRange[1]) {
        ctx.strokeStyle = hlColor; ctx.lineWidth = 2;
        ctx.strokeRect(x - 1, y - 1, fw + 2, fh + 2);
      } else {
        ctx.strokeStyle = C.border; ctx.lineWidth = 0.5;
        ctx.strokeRect(x, y, fw, fh);
      }
      n++;
    }
  }
}

function drawTimeline(ctx, W, H, winS, winE, total) {
  const tx = 18, ty = H - 44, tw = W - 36, th = 6;
  rr(ctx, tx, ty, tw, th, 3); ctx.fillStyle = '#101418'; ctx.fill();
  if (winE > winS) {
    const wx = tx + tw * winS / total, ww = tw * (winE - winS) / total;
    ctx.fillStyle = C.mid;
    ctx.shadowColor = C.mid; ctx.shadowBlur = 6;
    rr(ctx, wx, ty - 2, Math.max(ww, 3), th + 4, 2); ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = C.mid; ctx.font = '600 10px "JetBrains Mono",monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${winS}–${winE}s`, wx + ww / 2, ty - 6);
  }
  ctx.fillStyle = C.muted; ctx.font = '10px "JetBrains Mono",monospace';
  ctx.textAlign = 'left';  ctx.fillText('0s', tx, ty + th + 12);
  ctx.textAlign = 'right'; ctx.fillText('6630s', tx + tw, ty + th + 12);
}

function label(ctx, text, x, y, color = C.muted, bold = false) {
  ctx.fillStyle = color;
  ctx.font = `${bold ? '700' : '500'} 11px Inter,sans-serif`;
  ctx.textAlign = 'left'; ctx.fillText(text, x, y);
}

function clearBg(ctx, W, H) {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#0e1016'; ctx.lineWidth = 1;
  for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
  for (let y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
}

// ─── Per-step renders ─────────────────────────────────────────────────────────

const renders = {
  // 0: Question received, no frames
  0(ctx, W, H) {
    clearBg(ctx, W, H);
    // Ghost frame slots
    for (let c = 0; c < 16; c++) for (let r = 0; r < 4; r++) {
      ctx.fillStyle = '#0b0d13'; ctx.fillRect(18 + c * 30, 28 + r * 22, 26, 18);
      ctx.strokeStyle = '#181c24'; ctx.lineWidth = 0.5;
      ctx.strokeRect(18 + c * 30, 28 + r * 22, 26, 18);
    }
    ctx.fillStyle = '#20242e'; ctx.font = '500 12px Inter,sans-serif';
    ctx.textAlign = 'center'; ctx.fillText('Awaiting strategy — no frames loaded', W/2, H/2 + 48);
    drawTimeline(ctx, W, H, 0, 0, 6630);
  },
  // 1: Still no frames, planning overlay
  1(ctx, W, H) {
    renders[0](ctx, W, H);
    rr(ctx, 18, H/2 - 28, W - 36, 54, 8);
    ctx.fillStyle = 'rgba(0,180,216,0.07)'; ctx.fill();
    ctx.strokeStyle = 'rgba(0,180,216,0.18)'; ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = C.accent; ctx.font = '500 12px Inter,sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Forming plan from text alone — no visual tokens spent', W/2, H/2 + 6);
  },
  // 2: Low-res full survey
  2(ctx, W, H) {
    clearBg(ctx, W, H);
    label(ctx, 'Round 1 \u00b7 Low-Res Survey \u00b7 256 frames \u00b7 resize 0.1\u00d7', 18, 20, C.accent);
    const cols=24, rows=5, fw=17, fh=11, gap=2;
    const gx = (W - cols*(fw+gap)) / 2;
    drawGrid(ctx, gx, 30, cols, rows, fw, fh, gap, { seed:77, lowRes:true });
    label(ctx, '\u223810K tokens   (uniform sampling would need 499K)', 18, 30+rows*(fh+gap)+16, C.good, true);
    drawTimeline(ctx, W, H, 0, 6630, 6630);
  },
  // 3: Window highlighted
  3(ctx, W, H) {
    clearBg(ctx, W, H);
    label(ctx, 'Window Found \u00b7 t\u00a0=\u00a03500\u20134000s', 18, 20, C.mid, true);
    const cols=24, rows=5, fw=17, fh=11, gap=2;
    const gx = (W - cols*(fw+gap)) / 2;
    const total = cols * rows;
    const hl0 = Math.floor(total * 0.528), hl1 = Math.floor(total * 0.600);
    drawGrid(ctx, gx, 30, cols, rows, fw, fh, gap,
      { seed:77, lowRes:true, hlRange:[hl0, hl1], hlColor:C.mid });
    // arrow label
    const hlCol = hl0 % cols, hlRow = Math.floor(hl0 / cols);
    const px = gx + hlCol*(fw+gap), py = 30 + hlRow*(fh+gap);
    ctx.fillStyle = C.mid; ctx.font = '600 10px Inter,sans-serif';
    ctx.textAlign = 'left'; ctx.fillText('\u2191 relevant', px, py + fh + 10);
    drawTimeline(ctx, W, H, 3500, 4000, 6630);
  },
  // 4: High-res zoom
  4(ctx, W, H) {
    clearBg(ctx, W, H);
    label(ctx, 'Round 2 \u00b7 High-Res Zoom \u00b7 50 frames \u00b7 resize 1.0\u00d7', 18, 20, C.accent);
    const cols=10, rows=5, fw=42, fh=26, gap=4;
    const gx = (W - cols*(fw+gap)) / 2;
    drawGrid(ctx, gx, 32, cols, rows, fw, fh, gap, { seed:200 });
    label(ctx, 'Full resolution \u00b7 action sequence clearly visible', 18, 32+rows*(fh+gap)+16, C.good);
    drawTimeline(ctx, W, H, 3500, 4000, 6630);
  },
  // 5: Efficiency summary
  5(ctx, W, H) {
    clearBg(ctx, W, H);
    label(ctx, 'Token Efficiency', 18, 22, C.accent, true);
    const rows = [
      { name:'EVA (ours)', pct:0.02, color:C.good,  note:'~10K tokens \u2713' },
      { name:'Trad. Agent', pct:0.60, color:C.mid,  note:'~300K \u00b7 wrong' },
      { name:'Qwen2.5-VL', pct:1.00, color:C.bad,  note:'499K tokens' },
    ];
    const bx=18, bw=W-130, bh=20, gap=14;
    rows.forEach((row, i) => {
      const by = 36 + i*(bh+gap);
      // track
      rr(ctx, bx, by, bw, bh, 4); ctx.fillStyle='#101418'; ctx.fill();
      // bar
      const filled = Math.max(row.pct * bw, 4);
      rr(ctx, bx, by, filled, bh, 4);
      ctx.fillStyle = row.color;
      if (i === 0) { ctx.shadowColor = row.color; ctx.shadowBlur = 8; }
      ctx.fill(); ctx.shadowBlur = 0;
      // model name
      ctx.fillStyle = C.muted; ctx.font = '500 11px Inter,sans-serif';
      ctx.textAlign = 'left'; ctx.fillText(row.name, bx + bw + 8, by + 14);
      // note inside bar if wide enough
      if (filled > 30) {
        ctx.fillStyle = '#000'; ctx.font = '600 10px "JetBrains Mono",monospace';
        ctx.fillText(i===0 ? '~10K' : '', bx + 5, by + 14);
      }
    });

    // Accuracy vs token scatter
    label(ctx, 'Accuracy vs Tokens  (VideoMME Overall)', 18, 140, C.muted);
    const sx=18, sy=154, sw=W-36, sh=80;
    rr(ctx, sx, sy, sw, sh, 6); ctx.fillStyle='#0c0e14'; ctx.fill();
    const pts = [
      { n:'EVA',  acc:60.2, tok:0.02, c:C.good, r:8 },
      { n:'Qwen', acc:63.3, tok:1.00, c:'#607080', r:5 },
      { n:'VC-R1',acc:56.5, tok:0.55, c:'#506070', r:5 },
    ];
    pts.forEach(p => {
      const px = sx + 10 + p.tok*(sw-20), py = sy+sh-8-(p.acc-54)/14*(sh-16);
      ctx.fillStyle=p.c; ctx.shadowColor=p.c; ctx.shadowBlur = p.r>6 ? 10 : 0;
      ctx.beginPath(); ctx.arc(px,py,p.r,0,Math.PI*2); ctx.fill(); ctx.shadowBlur=0;
      ctx.fillStyle=p.c; ctx.font=`${p.r>6?'700':'400'} 10px Inter,sans-serif`;
      ctx.textAlign = p.tok<0.5 ? 'left' : 'right';
      ctx.fillText(`${p.n} ${p.acc}%`, px+(p.tok<0.5?p.r+4:-p.r-4), py+4);
    });
    ctx.fillStyle=C.muted; ctx.font='10px Inter,sans-serif';
    ctx.textAlign='center'; ctx.fillText('\u2190 fewer tokens', sx+30, sy+sh+14);
    ctx.fillText('higher accuracy \u2192', sx+sw-30, sy+sh-8);

    drawTimeline(ctx, W, H, 3500, 4000, 6630);
  },
};

// ─── Step metadata ────────────────────────────────────────────────────────────

const rightLabels = [
  'Video Timeline', 'Planning State', 'Round 1: Low-Res Survey',
  'Round 1: Window Located', 'Round 2: High-Res Zoom', 'Token Efficiency',
];
const captions = [
  'No frames loaded. EVA begins with the question text only.',
  'EVA forms a strategy entirely in text — zero visual tokens spent so far.',
  '256 frames fetched at 0.1\u00d7 resolution to survey the full video (\u223810K tokens).',
  'Low-res scan reveals the relevant temporal window: t\u00a0=\u00a03500\u20134000s.',
  '50 high-resolution frames zoomed into the target window — sufficient for action identification.',
  'Total \u223810K tokens. Correct answer with 98% fewer tokens than Qwen2.5-VL.',
];

// ─── Controller ──────────────────────────────────────────────────────────────

const canvas   = document.getElementById('demoCanvas');
const progBar  = document.getElementById('demoProgress');
const rlabel   = document.getElementById('demoRightLabel');
const rcaption = document.getElementById('demoRightCaption');

let step = 0, autoTimer = null, progTimer = null;

function renderStep(s) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  (renders[s] || renders[0])(ctx, canvas.width, canvas.height);
}

function goTo(s) {
  step = s;
  document.querySelectorAll('.demo-step-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === s);
    btn.classList.toggle('done', i < s);
  });
  document.querySelectorAll('.demo-panel').forEach((p, i) => p.classList.toggle('active', i === s));
  renderStep(s);
  if (rlabel)   rlabel.textContent   = rightLabels[s];
  if (rcaption) rcaption.textContent = captions[s];

  // Progress bar
  clearInterval(progTimer);
  let pct = 0;
  if (progBar) progBar.style.width = '0%';
  progTimer = setInterval(() => {
    pct = Math.min(100, pct + 100 / (STEP_MS / 60));
    if (progBar) progBar.style.width = pct + '%';
    if (pct >= 100) clearInterval(progTimer);
  }, 60);
}

function startAuto() {
  clearInterval(autoTimer);
  autoTimer = setInterval(() => goTo((step + 1) % N_STEPS), STEP_MS);
}

document.querySelectorAll('.demo-step-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    clearInterval(autoTimer);
    goTo(parseInt(btn.dataset.step));
    startAuto();
  });
});

const demoEl = document.querySelector('.eva-demo');
if (demoEl) {
  demoEl.addEventListener('mouseenter', () => clearInterval(autoTimer));
  demoEl.addEventListener('mouseleave', startAuto);
}

// Start when scrolled into view
new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) { goTo(0); startAuto(); }
  });
}, { threshold: 0.25 }).observe(canvas || document.body);
