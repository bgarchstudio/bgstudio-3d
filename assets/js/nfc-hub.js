(() => {
  'use strict';
  const roots = [...document.querySelectorAll('[data-capacity-stepper-root]')];
  roots.forEach(root => {
    const range = root.querySelector('[data-capacity-range]');
    const prev = root.querySelector('[data-capacity-prev]');
    const next = root.querySelector('[data-capacity-next]');
    const display = root.querySelector('[data-capacity-display]');
    const nfcDisplay = root.querySelector('[data-capacity-nfc-display]');
    const buttons = [...root.querySelectorAll('[data-special-capacity]')];
    if (!range || !buttons.length) return;
    const clamp = value => Math.max(0, Math.min(buttons.length - 1, Number(value) || 0));
    const selectIndex = index => {
      index = clamp(index);
      range.value = String(index);
      const button = buttons[index];
      if (!button) return;
      const tables = Number(button.dataset.specialCapacity || 0);
      const nfc = Number(button.dataset.specialNfc || tables * 3);
      if (display) display.textContent = String(tables);
      if (nfcDisplay) nfcDisplay.textContent = `${nfc} NFC`;
      button.click();
      prev?.toggleAttribute('disabled', index <= 0);
      next?.toggleAttribute('disabled', index >= buttons.length - 1);
    };
    range.max = String(buttons.length - 1);
    range.addEventListener('input', () => selectIndex(range.value));
    prev?.addEventListener('click', () => selectIndex(Number(range.value) - 1));
    next?.addEventListener('click', () => selectIndex(Number(range.value) + 1));
    const selected = buttons.findIndex(button => button.getAttribute('aria-pressed') === 'true');
    selectIndex(selected >= 0 ? selected : 0);
  });

  // Premium Feedback Duo uses its own 2-NFC / stand capacity model.
  document.querySelectorAll('[data-duo-calculator]').forEach(root => {
    const buttons = [...root.querySelectorAll('[data-duo-capacity]')];
    const range = root.querySelector('[data-duo-range]');
    const prev = root.querySelector('[data-duo-prev]');
    const next = root.querySelector('[data-duo-next]');
    const qrToggle = root.querySelector('[data-duo-qr-toggle]');
    if (!buttons.length || !range) return;
    const money = value => `${new Intl.NumberFormat('tr-TR').format(Number(value) || 0)} TL`;
    const qrUnit = Number(root.dataset.qrUnit || 0);
    const offerBase = root.dataset.offerBase || '../../teklif/';
    let index = Math.max(0, buttons.findIndex(button => button.getAttribute('aria-pressed') === 'true'));
    let qrSelected = false;
    const get = selector => root.querySelector(selector);
    const setText = (selector, value) => { const node = get(selector); if (node) node.textContent = value; };
    const clamp = value => Math.max(0, Math.min(buttons.length - 1, Number(value) || 0));
    const render = () => {
      index = clamp(index);
      range.value = String(index);
      const button = buttons[index];
      const stands = Number(button.dataset.duoStands || 0);
      const nfc = Number(button.dataset.duoNfc || stands * 2);
      const base = Number(button.dataset.duoPrice || 0);
      const renewal = Number(button.dataset.duoRenewal || 0);
      const qrCount = stands * 2;
      const qrCost = qrCount * qrUnit;
      const total = base + (qrSelected ? qrCost : 0);
      buttons.forEach((item, itemIndex) => item.setAttribute('aria-pressed', itemIndex === index ? 'true' : 'false'));
      setText('[data-duo-stands-display]', String(stands));
      setText('[data-duo-nfc-display]', `${nfc} NFC`);
      setText('[data-duo-live-stands]', String(stands));
      setText('[data-duo-live-nfc]', String(nfc));
      setText('[data-duo-live-qr]', String(qrCount));
      setText('[data-duo-base]', base ? money(base) : 'Özel teklif');
      setText('[data-duo-renewal]', renewal ? `Yıllık yenileme: ${money(renewal)}` : 'Yıllık yenileme: Özel teklif');
      setText('[data-duo-line-base]', base ? money(base) : 'Özel teklif');
      setText('[data-duo-qr-price]', `+${money(qrCost)}`);
      setText('[data-duo-qr-copy]', `${qrCount} QR × ${money(qrUnit)} / QR`);
      setText('[data-duo-line-qr]', `+${money(qrCost)}`);
      setText('[data-duo-total]', base ? money(total) : 'Özel teklif');
      const qrLine = get('[data-duo-qr-line]');
      const qrMetric = get('[data-duo-live-qr-metric]');
      if (qrLine) qrLine.hidden = !qrSelected;
      if (qrMetric) qrMetric.hidden = !qrSelected;
      if (qrToggle) qrToggle.setAttribute('aria-pressed', qrSelected ? 'true' : 'false');
      prev?.toggleAttribute('disabled', index <= 0);
      next?.toggleAttribute('disabled', index >= buttons.length - 1);
      const offer = get('[data-duo-offer]');
      if (offer) {
        offer.href = `${offerBase}?tur=nfc&paket=feedback-duo&masa=${stands}${qrSelected ? '&qr=1' : ''}`;
        offer.textContent = `${stands} stand için bu kapsamla teklif al ↗`;
      }
    };
    range.max = String(buttons.length - 1);
    range.addEventListener('input', () => { index = clamp(range.value); render(); });
    prev?.addEventListener('click', () => { index = clamp(index - 1); render(); });
    next?.addEventListener('click', () => { index = clamp(index + 1); render(); });
    qrToggle?.addEventListener('click', () => { qrSelected = !qrSelected; render(); });
    buttons.forEach((button, buttonIndex) => button.addEventListener('click', () => { index = buttonIndex; render(); }));
    render();
  });

  // Sticky section navigation on detail pages, without interfering with the global header.
  const sectionNav = document.querySelector('.nfc-section-nav');
  if (sectionNav) {
    const links = [...sectionNav.querySelectorAll('a[href^="#"]')];
    const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
    if ('IntersectionObserver' in window && sections.length) {
      const observer = new IntersectionObserver(entries => {
        const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        links.forEach(link => link.classList.toggle('is-active', link.getAttribute('href') === `#${visible.target.id}`));
      }, { rootMargin: '-32% 0px -58% 0px', threshold: [0,.25,.6] });
      sections.forEach(section => observer.observe(section));
    }
  }

  // Gentle reveal for the new NFC cards. Existing .reveal behavior is untouched.
  const motionItems = [...document.querySelectorAll('.nfc-solution-card,.nfc-feature-matrix article,.nfc-software-copy article,.nfc-premium-roadmap-grid article')];
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  if (!reduce && 'IntersectionObserver' in window) {
    motionItems.forEach(item => item.classList.add('nfc-motion-item'));
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: .12, rootMargin: '0px 0px -6% 0px' });
    motionItems.forEach(item => observer.observe(item));
  }
})();
