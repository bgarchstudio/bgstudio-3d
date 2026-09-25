/* BG Studio 3D navigation v3.1.83 */
(() => {
  const INIT_VERSION = '3.1.83';
  const init = () => {
    const header = document.querySelector('.site-header');
    const nav = document.querySelector('.main-nav');
    if (!header || !nav) return;
    if (nav.dataset.bgNavigationReady === INIT_VERSION) return;
    nav.dataset.bgNavigationReady = INIT_VERSION;

    const groups = [...nav.querySelectorAll('.nav-group')];
    const mobileMq = window.matchMedia('(max-width: 1040px)');
    const closeTimers = new WeakMap();

    const clearCloseTimer = (group) => {
      const timer = closeTimers.get(group);
      if (timer) window.clearTimeout(timer);
      closeTimers.delete(group);
    };

    const closeGroup = (group) => {
      if (!group) return;
      clearCloseTimer(group);
      group.classList.remove('is-open');
      const toggle = group.querySelector(':scope > .nav-group-toggle');
      toggle?.setAttribute('aria-expanded', 'false');
    };

    const closeAllGroups = (except = null) => {
      groups.forEach((group) => {
        if (group !== except) closeGroup(group);
      });
    };

    const openGroup = (group) => {
      if (!group) return;
      clearCloseTimer(group);
      closeAllGroups(group);
      group.classList.add('is-open');
      group.querySelector(':scope > .nav-group-toggle')?.setAttribute('aria-expanded', 'true');
    };

    const scheduleClose = (group, delay = 240) => {
      clearCloseTimer(group);
      closeTimers.set(group, window.setTimeout(() => closeGroup(group), delay));
    };

    groups.forEach((group) => {
      const toggle = group.querySelector(':scope > .nav-group-toggle');
      const submenu = group.querySelector(':scope > .nav-submenu');
      if (!toggle || !submenu) return;

      toggle.addEventListener('click', (event) => {
        event.preventDefault();
        const next = !group.classList.contains('is-open');
        if (next) openGroup(group); else closeGroup(group);
      });

      toggle.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown') {
          event.preventDefault();
          openGroup(group);
          submenu.querySelector('a')?.focus();
        }
      });

      submenu.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        closeGroup(group);
        toggle.focus();
      });

      // Desktop hover intent. The short grace period bridges the visual gap
      // between the pill and the floating submenu, so it cannot disappear while
      // the pointer travels down to the first option.
      group.addEventListener('pointerenter', (event) => {
        if (mobileMq.matches || event.pointerType === 'touch') return;
        openGroup(group);
      });
      group.addEventListener('pointerleave', (event) => {
        if (mobileMq.matches || event.pointerType === 'touch') return;
        scheduleClose(group, 260);
      });
      submenu.addEventListener('pointerenter', () => clearCloseTimer(group));
      submenu.addEventListener('pointerleave', () => {
        if (!mobileMq.matches) scheduleClose(group, 220);
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
  };

  window.BGStudioNavigationInit = init;
  init();
})();
