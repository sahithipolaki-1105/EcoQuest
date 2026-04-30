// ── EcoQuest – Main JS ──

// Toast
function showToast(msg, type='green') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast toast-' + type + ' show';
  setTimeout(() => { t.className = 'toast'; }, 2800);
}

// Hamburger nav
document.addEventListener('DOMContentLoaded', () => {
  const ham = document.getElementById('hamburger');
  const menu = document.getElementById('mobileMenu');
  if (ham && menu) {
    ham.addEventListener('click', () => menu.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (!ham.contains(e.target) && !menu.contains(e.target))
        menu.classList.remove('open');
    });
  }

  // Animate stat values on page load
  document.querySelectorAll('.stat-value').forEach(el => {
    const end = parseInt(el.textContent);
    if (isNaN(end)) return;
    let current = 0;
    const step = Math.ceil(end / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, end);
      el.textContent = current;
      if (current >= end) clearInterval(timer);
    }, 25);
  });

  // Animate XP bar
  const xpBar = document.getElementById('xpBar');
  if (xpBar) {
    const target = xpBar.style.width;
    xpBar.style.width = '0%';
    setTimeout(() => { xpBar.style.width = target; }, 200);
  }

  // Animate rewards progress bar
  const rpf = document.querySelector('.rewards-progress-fill');
  if (rpf) {
    const target = rpf.style.width;
    rpf.style.width = '0%';
    setTimeout(() => { rpf.style.width = target; }, 300);
  }

  // Animate ring SVG strokes
  document.querySelectorAll('.ring-svg circle:last-child').forEach(circle => {
    const da = circle.getAttribute('stroke-dasharray');
    if (da) {
      const [fill] = da.split(' ');
      circle.setAttribute('stroke-dasharray', `0 150.8`);
      setTimeout(() => {
        circle.style.transition = 'stroke-dasharray 1s ease';
        circle.setAttribute('stroke-dasharray', `${fill} 150.8`);
      }, 400);
    }
  });

  // Leaderboard row entrance animation
  document.querySelectorAll('.lb-row').forEach((row, i) => {
    row.style.opacity = '0';
    row.style.transform = 'translateX(-20px)';
    setTimeout(() => {
      row.style.transition = 'all .3s ease';
      row.style.opacity = '1';
      row.style.transform = 'translateX(0)';
    }, i * 60 + 100);
  });

  // Challenge card entrance
  document.querySelectorAll('.ch-card, .reward-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(16px)';
    setTimeout(() => {
      card.style.transition = 'opacity .3s ease, transform .3s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, i * 40 + 100);
  });
});
