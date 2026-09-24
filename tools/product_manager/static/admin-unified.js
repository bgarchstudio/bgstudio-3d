/* BG Studio 3D Product Manager V3.1.82-R1
   Additive admin UX helpers. Existing ids, handlers and API flows stay intact. */
(() => {
  'use strict';

  const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const fold = (value) => compact(value).toLocaleLowerCase('tr-TR');
  const textIncludes = (el, needle) => el && fold(el.textContent).includes(fold(needle));

  function pageKind() {
    const file = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
    if (file === 'nfc-settings.html') return 'nfc';
    if (file === 'content.html') return 'content';
    return 'manager';
  }

  function bootIdentity() {
    document.documentElement.dataset.bgAdminUi = 'v3182';
    if (document.body) document.body.dataset.bgAdminPage = pageKind();
  }

  function closestReasonable(node, options = {}) {
    if (!node) return null;
    const maxWidth = options.maxWidth || 520;
    const minHeight = options.minHeight || 70;
    const maxDepth = options.maxDepth || 6;
    let current = node.parentElement;
    let best = current;
    for (let i = 0; current && current !== document.body && i < maxDepth; i += 1, current = current.parentElement) {
      const rect = current.getBoundingClientRect();
      if (rect.width <= maxWidth && rect.height >= minHeight) best = current;
      if (rect.width > maxWidth * 1.6) break;
    }
    return best;
  }

  function findByText(selector, needle) {
    return Array.from(document.querySelectorAll(selector)).find((el) => textIncludes(el, needle)) || null;
  }

  function enhanceContentPage() {
    if (pageKind() !== 'content') return;

    const h1 = document.querySelector('h1');
    if (h1) {
      const hero = h1.closest('section') || h1.parentElement;
      if (hero) hero.classList.add('bg-v3182-page-hero');
    }

    const newButton = findByText('button,a,[role="button"]', 'Yeni kayıt ekle');
    if (newButton) {
      const aside = newButton.closest('aside') || closestReasonable(newButton, {maxWidth: 430, minHeight: 180, maxDepth: 7});
      if (aside) aside.classList.add('bg-v3182-record-sidebar');
    }

    const typeButton = Array.from(document.querySelectorAll('button')).find((el) => {
      const t = fold(el.textContent);
      return t.includes('nfc') && t.includes('referans');
    });
    if (typeButton && typeButton.parentElement) typeButton.parentElement.classList.add('bg-v3182-type-tabs');

    document.querySelectorAll('form').forEach((form) => form.classList.add('bg-v3182-editor-form'));

    const explainerTitle = findByText('strong,h2,h3,p', 'Kaydettiğinde ne olur');
    if (explainerTitle) {
      const box = explainerTitle.closest('section,footer') || closestReasonable(explainerTitle, {maxWidth: 1400, minHeight: 55, maxDepth: 4});
      if (box) box.classList.add('bg-v3182-save-explainer');
    }
  }

  function enhanceColors() {
    if (pageKind() !== 'manager') return;
    const card = document.querySelector('.colors-card');
    const list = document.getElementById('colorInventoryList');
    if (!card || !list) return;

    let tools = card.querySelector('.bg-v3182-color-tools');
    if (!tools) {
      tools = document.createElement('div');
      tools.className = 'bg-v3182-color-tools';
      tools.innerHTML = '<input type="search" class="bg-v3182-color-search" placeholder="Renk ara..." aria-label="Renk ara"><select class="bg-v3182-color-filter" aria-label="Renk stok filtresi"><option value="all">Tüm renkler</option><option value="stock">Stokta</option><option value="out">Stok dışı</option></select><span class="bg-v3182-color-count"></span>';
      const toolbar = card.querySelector('.colors-toolbar');
      if (toolbar) toolbar.insertAdjacentElement('afterend', tools);
      else list.insertAdjacentElement('beforebegin', tools);
    }

    const search = tools.querySelector('.bg-v3182-color-search');
    const filter = tools.querySelector('.bg-v3182-color-filter');
    const count = tools.querySelector('.bg-v3182-color-count');

    const apply = () => {
      const query = fold(search.value);
      const mode = filter.value;
      const rows = Array.from(list.querySelectorAll('.color-inventory-row'));
      let visible = 0;
      let inStock = 0;
      rows.forEach((row) => {
        const name = fold(row.querySelector('.color-name')?.value || row.textContent);
        const stock = Boolean(row.querySelector('.color-stock')?.checked);
        if (stock) inStock += 1;
        const matchText = !query || name.includes(query);
        const matchStock = mode === 'all' || (mode === 'stock' && stock) || (mode === 'out' && !stock);
        row.hidden = !(matchText && matchStock);
        if (!row.hidden) visible += 1;
      });
      const nextCount = `${visible} gösteriliyor · ${rows.length} renk · ${inStock} stokta`;
      if (count.textContent !== nextCount) count.textContent = nextCount;
    };

    if (!tools.dataset.bound) {
      tools.dataset.bound = '1';
      search.addEventListener('input', apply);
      filter.addEventListener('change', apply);
      list.addEventListener('input', apply);
      list.addEventListener('change', apply);
      const observer = new MutationObserver(apply);
      observer.observe(list, {childList: true, subtree: true});
    }
    apply();
  }

  function enhancePreflight() {
    if (pageKind() !== 'manager') return;
    const list = document.getElementById('preflightList');
    if (!list) return;

    const rows = Array.from(list.querySelectorAll('.preflight-item'));
    if (!rows.length) return;

    let passCount = 0;
    rows.forEach((row) => {
      row.classList.remove('bg-v3182-preflight-pass','bg-v3182-preflight-warn','bg-v3182-preflight-fail');
      const badge = row.querySelector('.preflight-badge');
      if (badge?.classList.contains('pass')) { row.classList.add('bg-v3182-preflight-pass'); passCount += 1; }
      else if (badge?.classList.contains('warn')) row.classList.add('bg-v3182-preflight-warn');
      else if (badge?.classList.contains('fail')) row.classList.add('bg-v3182-preflight-fail');
    });

    let toggle = list.parentElement?.querySelector(':scope > .bg-v3182-preflight-toggle');
    if (!toggle && passCount > 4) {
      toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'bg-v3182-preflight-toggle';
      list.insertAdjacentElement('afterend', toggle);
      toggle.addEventListener('click', () => {
        const collapsed = list.classList.toggle('bg-v3182-collapse-pass');
        const nextLabel = collapsed ? `Temiz kontrolleri göster (${passCount})` : `Temiz kontrolleri gizle (${passCount})`;
        if (toggle.textContent !== nextLabel) toggle.textContent = nextLabel;
      });
    }

    if (toggle) {
      list.classList.add('bg-v3182-collapse-pass');
      const nextLabel = `Temiz kontrolleri göster (${passCount})`;
      if (toggle.textContent !== nextLabel) toggle.textContent = nextLabel;
    }
  }

  function enhanceManager() {
    if (pageKind() !== 'manager') return;
    enhanceColors();
    enhancePreflight();

    const productList = document.getElementById('productList');
    if (productList && !productList.dataset.bgV3182Observed) {
      productList.dataset.bgV3182Observed = '1';
      const titleRows = () => {
        productList.querySelectorAll('.product-item').forEach((row) => {
          const name = row.querySelector('.product-main strong')?.textContent;
          const meta = row.querySelector('.product-main small')?.textContent;
          if (name) row.title = compact(`${name}${meta ? ' · ' + meta : ''}`);
        });
      };
      new MutationObserver(titleRows).observe(productList, {childList: true, subtree: true});
      titleRows();
    }

    const preflightList = document.getElementById('preflightList');
    if (preflightList && !preflightList.dataset.bgV3182Observed) {
      preflightList.dataset.bgV3182Observed = '1';
      new MutationObserver(() => requestAnimationFrame(enhancePreflight)).observe(preflightList, {childList: true, subtree: true});
    }

    const colorsModal = document.getElementById('colorsModal');
    if (colorsModal && !colorsModal.dataset.bgV3182Observed) {
      colorsModal.dataset.bgV3182Observed = '1';
      new MutationObserver(() => requestAnimationFrame(enhanceColors)).observe(colorsModal, {attributes: true, childList: true, subtree: true, attributeFilter: ['hidden']});
    }
  }

  function scheduleSafeRetries() {
    // Dynamic manager sections are mounted after the first API response.
    // Use a short bounded retry window instead of observing the entire body.
    // This prevents an observer feedback loop from starving fetch/render work.
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      if (pageKind() === 'manager') enhanceManager();
      else if (pageKind() === 'content') enhanceContentPage();
      if (attempts >= 16) window.clearInterval(timer);
    }, 400);
  }

  function boot() {
    bootIdentity();
    if (pageKind() === 'content') enhanceContentPage();
    if (pageKind() === 'manager') enhanceManager();
    scheduleSafeRetries();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
