/* BG Studio 3D navigation v3.1.62 */
(() => {
  const header = document.querySelector('.site-header');
  const nav = document.querySelector('.main-nav');
  if (!header || !nav) return;

  const groups = [...nav.querySelectorAll('.nav-group')];
  const mobileMq = window.matchMedia('(max-width: 1040px)');

  const closeGroup = (group) => {
    if (!group) return;
    group.classList.remove('is-open');
    const toggle = group.querySelector(':scope > .nav-group-toggle');
    toggle?.setAttribute('aria-expanded', 'false');
  };

  const closeAllGroups = (except = null) => {
    groups.forEach((group) => {
      if (group !== except) closeGroup(group);
    });
  };

  groups.forEach((group) => {
    const toggle = group.querySelector(':scope > .nav-group-toggle');
    const submenu = group.querySelector(':scope > .nav-submenu');
    if (!toggle || !submenu) return;

    toggle.addEventListener('click', (event) => {
      event.preventDefault();
      const next = !group.classList.contains('is-open');
      closeAllGroups(group);
      group.classList.toggle('is-open', next);
      toggle.setAttribute('aria-expanded', next ? 'true' : 'false');
    });

    toggle.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        group.classList.add('is-open');
        toggle.setAttribute('aria-expanded', 'true');
        submenu.querySelector('a')?.focus();
      }
    });

    submenu.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      closeGroup(group);
      toggle.focus();
    });
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.nav-group')) closeAllGroups();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeAllGroups();
  });

  const syncHeaderState = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 12);
  };
  syncHeaderState();
  window.addEventListener('scroll', syncHeaderState, { passive: true });

  const menuButton = document.querySelector('.menu-toggle');
  menuButton?.addEventListener('click', () => {
    queueMicrotask(() => {
      if (menuButton.getAttribute('aria-expanded') !== 'true') closeAllGroups();
    });
  });

  const clearDesktopClickState = () => {
    if (!mobileMq.matches) closeAllGroups();
  };
  if (typeof mobileMq.addEventListener === 'function') mobileMq.addEventListener('change', clearDesktopClickState);
  else if (typeof mobileMq.addListener === 'function') mobileMq.addListener(clearDesktopClickState);
})();
