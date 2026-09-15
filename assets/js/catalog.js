// BG Studio 3D · V3.1.73-R1 premium catalog filter accuracy hotfix
window.BGStudioCatalogV3164 = true;

(() => {
  const grid = document.querySelector('.catalog-grid');
  const cards = [...document.querySelectorAll('.catalog-grid .catalog-product-card')];
  if (!grid || !cards.length) return;

  const categoryButtons = [...document.querySelectorAll('.catalog-category-row [data-filter]')];
  const search = document.querySelector('#product-search');
  const sort = document.querySelector('#catalog-sort');
  const material = document.querySelector('#catalog-material');
  const flagButtons = [...document.querySelectorAll('[data-catalog-flag]')];
  const count = document.querySelector('#catalog-count');
  const empty = document.querySelector('#catalog-empty');
  const reset = document.querySelector('[data-catalog-reset]');

  const normalize = value => String(value || '').toLocaleLowerCase('tr-TR').trim();
  const numeric = value => {
    const n = Number(value);
    return Number.isFinite(n) && String(value ?? '').trim() !== '' ? n : null;
  };

  const state = {
    category: 'all',
    query: '',
    sort: 'recommended',
    material: '',
    featured: false,
    personalizable: false,
  };

  const originalOrder = new Map(cards.map((card, index) => [card, index]));

  const matchesBase = (card, { ignoreFeatured = false, ignorePersonalizable = false } = {}) => {
    if (state.category !== 'all' && card.dataset.category !== state.category) return false;
    if (state.query && !normalize(card.dataset.search || card.textContent).includes(state.query)) return false;

    if (state.material) {
      const materials = String(card.dataset.materials || '').split('|').filter(Boolean);
      if (!materials.includes(state.material)) return false;
    }

    if (!ignoreFeatured && state.featured && card.dataset.featured !== '1') return false;
    if (!ignorePersonalizable && state.personalizable && card.dataset.personalizable !== '1') return false;
    return true;
  };

  const cardMatches = card => matchesBase(card);

  const compareCards = (a, b) => {
    if (state.sort === 'price-asc' || state.sort === 'price-desc') {
      const pa = numeric(a.dataset.price);
      const pb = numeric(b.dataset.price);
      if (pa === null && pb === null) return originalOrder.get(a) - originalOrder.get(b);
      if (pa === null) return 1;
      if (pb === null) return -1;
      if (pa !== pb) return state.sort === 'price-asc' ? pa - pb : pb - pa;
      return originalOrder.get(a) - originalOrder.get(b);
    }

    if (state.sort === 'newest') {
      const ar = numeric(a.dataset.addedRank) ?? 0;
      const br = numeric(b.dataset.addedRank) ?? 0;
      if (ar !== br) return br - ar;
    }

    const ao = numeric(a.dataset.order) ?? 999999;
    const bo = numeric(b.dataset.order) ?? 999999;
    if (ao !== bo) return ao - bo;
    return originalOrder.get(a) - originalOrder.get(b);
  };

  const syncUrl = () => {
    try {
      const url = new URL(window.location.href);
      const params = url.searchParams;
      const setOrDelete = (key, value, emptyValue = '') => {
        if (value && value !== emptyValue) params.set(key, value);
        else params.delete(key);
      };
      setOrDelete('kategori', state.category, 'all');
      setOrDelete('q', search?.value.trim() || '');
      setOrDelete('sirala', state.sort, 'recommended');
      setOrDelete('malzeme', state.material);
      state.featured ? params.set('one-cikan', '1') : params.delete('one-cikan');
      state.personalizable ? params.set('kisisellestirilebilir', '1') : params.delete('kisisellestirilebilir');
      history.replaceState({}, '', url);
    } catch (_) {}
  };

  const contextualFlagCount = key => {
    if (key === 'featured') {
      return cards.filter(card => matchesBase(card, { ignoreFeatured: true }) && card.dataset.featured === '1').length;
    }
    if (key === 'personalizable') {
      return cards.filter(card => matchesBase(card, { ignorePersonalizable: true }) && card.dataset.personalizable === '1').length;
    }
    return 0;
  };

  const syncControls = () => {
    categoryButtons.forEach(button => {
      const active = button.dataset.filter === state.category;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });

    flagButtons.forEach(button => {
      const key = button.dataset.catalogFlag;
      const active = Boolean(state[key]);
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
      const badge = button.querySelector('.filter-count');
      if (badge && ['featured', 'personalizable'].includes(key)) {
        const liveCount = contextualFlagCount(key);
        badge.textContent = String(liveCount);
        badge.setAttribute('aria-label', `${liveCount} ürün`);
      }
    });

    if (sort && sort.value !== state.sort) sort.value = state.sort;
    if (material && material.value !== state.material) material.value = state.material;
  };

  const apply = ({ syncHistory = true } = {}) => {
    const ordered = [...cards].sort(compareCards);
    ordered.forEach(card => grid.appendChild(card));

    let visible = 0;
    ordered.forEach(card => {
      const show = cardMatches(card);
      card.hidden = !show;
      card.classList.toggle('hidden', !show);
      card.setAttribute('aria-hidden', show ? 'false' : 'true');
      if (show) visible += 1;
    });

    if (count) count.textContent = `${visible} ürün gösteriliyor`;
    if (empty) empty.hidden = visible !== 0;

    const hasFilter = state.category !== 'all' || state.query || state.sort !== 'recommended'
      || state.material || state.featured || state.personalizable;
    if (reset) reset.hidden = !hasFilter;

    syncControls();
    if (syncHistory) syncUrl();
  };

  categoryButtons.forEach(button => button.addEventListener('click', () => {
    state.category = button.dataset.filter || 'all';
    apply();
  }));

  search?.addEventListener('input', () => {
    state.query = normalize(search.value);
    apply();
  });

  sort?.addEventListener('change', () => {
    state.sort = sort.value || 'recommended';
    apply();
  });

  material?.addEventListener('change', () => {
    state.material = material.value || '';
    apply();
  });

  flagButtons.forEach(button => button.addEventListener('click', () => {
    const key = button.dataset.catalogFlag;
    if (!['featured', 'personalizable'].includes(key)) return;
    state[key] = !state[key];
    apply();
  }));

  reset?.addEventListener('click', () => {
    state.category = 'all';
    state.query = '';
    state.sort = 'recommended';
    state.material = '';
    state.featured = false;
    state.personalizable = false;
    if (search) search.value = '';
    apply();
  });

  const params = new URLSearchParams(window.location.search);
  const requestedCategory = params.get('kategori');
  if (requestedCategory && categoryButtons.some(button => button.dataset.filter === requestedCategory)) {
    state.category = requestedCategory;
  }
  const requestedQuery = params.get('q');
  if (requestedQuery && search) {
    search.value = requestedQuery;
    state.query = normalize(requestedQuery);
  }
  const requestedSort = params.get('sirala');
  if (requestedSort && ['recommended', 'newest', 'price-asc', 'price-desc'].includes(requestedSort)) {
    state.sort = requestedSort;
  }
  const requestedMaterial = params.get('malzeme');
  if (requestedMaterial && material && [...material.options].some(option => option.value === requestedMaterial)) {
    state.material = requestedMaterial;
  }
  state.featured = params.get('one-cikan') === '1';
  state.personalizable = params.get('kisisellestirilebilir') === '1';

  apply({ syncHistory: false });
})();
