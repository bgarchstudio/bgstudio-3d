// BG Studio 3D · V3.1.73-R1 project archive filter accuracy hotfix
(() => {
  const root = document.querySelector('[data-projects-v3168]');
  if (!root) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cards = [...root.querySelectorAll('[data-project-card]')];
  const buttons = [...root.querySelectorAll('[data-project-filter]')];
  const count = root.querySelector('[data-project-count]') || document.querySelector('[data-project-count]');
  const empty = root.querySelector('[data-project-empty]') || document.querySelector('[data-project-empty]');

  const validKinds = new Set(['all', ...cards.map(card => card.dataset.projectKind).filter(Boolean)]);

  const apply = (requestedValue, { syncHistory = true } = {}) => {
    const value = validKinds.has(requestedValue) ? requestedValue : 'all';
    let visible = 0;

    cards.forEach(card => {
      const show = value === 'all' || card.dataset.projectKind === value;
      // hidden alone can be defeated by an author display:flex rule, so keep a class too.
      card.hidden = !show;
      card.classList.toggle('project-card-hidden', !show);
      card.setAttribute('aria-hidden', show ? 'false' : 'true');
      if (show) visible += 1;
    });

    buttons.forEach(button => {
      const active = button.dataset.projectFilter === value;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });

    if (count) count.textContent = String(visible);
    if (empty) empty.hidden = visible !== 0;

    if (syncHistory) {
      try {
        const url = new URL(window.location.href);
        if (value === 'all') url.searchParams.delete('tur');
        else url.searchParams.set('tur', value);
        history.replaceState({}, '', url);
      } catch (_) {}
    }
  };

  buttons.forEach(button => button.addEventListener('click', () => {
    apply(button.dataset.projectFilter || 'all');
  }));

  const params = new URLSearchParams(window.location.search);
  apply(params.get('tur') || 'all', { syncHistory: false });

  const motion = [...root.querySelectorAll('[data-project-motion]')];
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
