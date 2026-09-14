// BG Studio 3D · V3.1.68 project archive
(() => {
  const root = document.querySelector('[data-projects-v3168]');
  if (!root) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cards = [...document.querySelectorAll('[data-project-card]')];
  const buttons = [...document.querySelectorAll('[data-project-filter]')];
  const count = document.querySelector('[data-project-count]');
  const empty = document.querySelector('[data-project-empty]');
  const apply = value => {
    let visible = 0;
    cards.forEach(card => {
      const show = value === 'all' || card.dataset.projectKind === value;
      card.hidden = !show;
      if (show) visible += 1;
    });
    buttons.forEach(button => {
      const active = button.dataset.projectFilter === value;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (count) count.textContent = String(visible);
    if (empty) empty.hidden = visible !== 0;
  };
  buttons.forEach(button => button.addEventListener('click', () => apply(button.dataset.projectFilter || 'all')));
  const motion = [...document.querySelectorAll('[data-project-motion]')];
  if (!reduce && motion.length && 'IntersectionObserver' in window) {
    document.documentElement.classList.add('projects-motion-enabled');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: .08, rootMargin: '0px 0px -4% 0px' });
    motion.forEach(item => observer.observe(item));
  } else {
    motion.forEach(item => item.classList.add('is-visible'));
  }
})();
