// ===== SCROLL REVEAL =====
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      // stagger children if multiple in view
      const siblings = Array.from(entry.target.parentElement.querySelectorAll('.reveal'));
      const idx = siblings.indexOf(entry.target);
      setTimeout(() => {
        entry.target.classList.add('visible');
      }, idx * 80);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ===== TAB SWITCHER =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tabId = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(tabId).classList.add('active');

    // Render chart if efficiency tab
    if (tabId === 'efficiency') renderAblationChart();
  });
});

// ===== ABLATION CHART =====
let chartRendered = false;

function renderAblationChart() {
  if (chartRendered) return;
  chartRendered = true;

  const ctx = document.getElementById('ablationChart').getContext('2d');

  Chart.defaults.color = '#8b949e';
  Chart.defaults.borderColor = '#30363d';

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['LongVideoBench', 'MLVU', 'VideoMME Long', 'LVBench'],
      datasets: [
        {
          label: 'SFT',
          data: [49.9, 52.3, 45.8, 26.5],
          backgroundColor: 'rgba(31, 111, 235, 0.7)',
          borderColor: '#1f6feb',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'KTO',
          data: [53.2, 57.4, 45.1, 36.0],
          backgroundColor: 'rgba(255, 209, 102, 0.7)',
          borderColor: '#ffd166',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'GRPO',
          data: [55.1, 68.3, 48.4, 43.3],
          backgroundColor: 'rgba(6, 214, 160, 0.7)',
          borderColor: '#06d6a0',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: { color: '#e6edf3', font: { family: 'Inter', size: 13 } }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw}%`
          }
        },
        title: {
          display: true,
          text: 'Ablation: Training Stage Progression (Accuracy %)',
          color: '#e6edf3',
          font: { family: 'Inter', size: 14, weight: '600' },
          padding: { bottom: 16 }
        }
      },
      scales: {
        x: {
          ticks: { color: '#8b949e', font: { family: 'Inter' } },
          grid: { color: '#30363d' }
        },
        y: {
          ticks: { color: '#8b949e', font: { family: 'Inter' }, callback: v => v + '%' },
          grid: { color: '#30363d' },
          min: 20,
        }
      }
    }
  });
}

// ===== COPY BIBTEX =====
function copyBibtex() {
  const code = document.querySelector('.bibtex code').textContent;
  navigator.clipboard.writeText(code).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 2000);
  });
}

// ===== VIDEO AUTOPLAY ON SCROLL =====
const video = document.getElementById('demo-video');
if (video) {
  const videoObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        video.play().catch(() => {});
      } else {
        video.pause();
      }
    });
  }, { threshold: 0.3 });
  videoObserver.observe(video);
}

// ===== SMOOTH HERO ENTRANCE =====
window.addEventListener('DOMContentLoaded', () => {
  const heroContent = document.querySelector('.hero-content');
  if (heroContent) {
    heroContent.style.opacity = '0';
    heroContent.style.transform = 'translateY(20px)';
    heroContent.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        heroContent.style.opacity = '1';
        heroContent.style.transform = 'none';
      });
    });
  }
});
