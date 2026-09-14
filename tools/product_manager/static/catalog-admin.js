// BG Studio 3D · V3.1.64-R1 catalog admin companion
(() => {
  const $ = selector => document.querySelector(selector);
  const state = { products: [], materials: [], activeSlug: null, selected: new Set(), dirty: false };

  const personalizable = () => $('#personalizable');
  const choices = () => $('#productMaterialChoices');
  const modal = () => $('#materialsModal');
  const inventory = () => $('#materialInventoryList');

  const slugify = value => String(value || '')
    .toLocaleLowerCase('tr-TR')
    .replace(/[ç]/g, 'c').replace(/[ğ]/g, 'g').replace(/[ı]/g, 'i')
    .replace(/[ö]/g, 'o').replace(/[ş]/g, 's').replace(/[ü]/g, 'u')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80);

  async function loadState() {
    const response = await fetch('/api/products', { cache: 'no-store' });
    if (!response.ok) throw new Error('Ürün ve malzeme bilgileri alınamadı.');
    const data = await response.json();
    state.products = Array.isArray(data.products) ? data.products : [];
    state.materials = Array.isArray(data.materials) ? data.materials : [];
    renderChoices();
    syncCurrentProduct(true);
    ensurePersonalizableListFilter();
    updatePersonalizableFilterUI();
    if (personalizableListFilterActive) schedulePersonalizableFilter();
  }

  function currentProduct() {
    const slug = String($('#slug')?.value || '').trim();
    return state.products.find(product => String(product.slug || '') === slug) || null;
  }

  function renderChoices() {
    const root = choices();
    if (!root) return;
    root.replaceChildren();
    if (!state.materials.length) {
      const empty = document.createElement('span');
      empty.className = 'catalog-admin-empty';
      empty.textContent = 'Malzeme listesi boş. “Malzeme listesini düzenle” ile ekleyebilirsin.';
      root.appendChild(empty);
      return;
    }
    state.materials.forEach(material => {
      const label = document.createElement('label');
      label.className = 'material-choice';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = material.id;
      input.checked = state.selected.has(String(material.id));
      input.addEventListener('change', () => {
        if (input.checked) state.selected.add(String(material.id));
        else state.selected.delete(String(material.id));
        state.dirty = true;
        label.classList.toggle('is-selected', input.checked);
      });
      const span = document.createElement('span');
      span.textContent = material.name || material.id;
      label.classList.toggle('is-selected', input.checked);
      label.append(input, span);
      root.appendChild(label);
    });
  }

  function syncCurrentProduct(force = false) {
    const slug = String($('#slug')?.value || '').trim();
    if (!force && slug === state.activeSlug) return;
    state.activeSlug = slug;
    state.dirty = false;
    const product = currentProduct();
    state.selected = new Set(Array.isArray(product?.material_ids) ? product.material_ids.map(String) : []);
    if (personalizable()) personalizable().checked = Boolean(product?.personalizable);
    renderChoices();
  }

  function selectedMaterialIds() {
    const root = choices();
    if (!root) return [];
    return [...root.querySelectorAll('input[type="checkbox"]:checked')].map(input => String(input.value));
  }

  // Extend the existing Product Manager save payload without replacing manager.js.
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    try {
      const url = typeof input === 'string' ? input : (input?.url || '');
      if (url.endsWith('/api/save') && init && typeof init.body === 'string') {
        const payload = JSON.parse(init.body);
        if (payload && payload.product && typeof payload.product === 'object') {
          payload.product.material_ids = selectedMaterialIds();
          payload.product.personalizable = Boolean(personalizable()?.checked);
          init = { ...init, body: JSON.stringify(payload) };
        }
      }
    } catch (_) {}
    const response = await nativeFetch(input, init);
    return response;
  };



  // V3.1.69-R1 · Product Manager sidebar: explicit personalizable filter.
  let personalizableListFilterActive = false;
  let productListObserver = null;

  function personalizableProducts() {
    return state.products.filter(product => Boolean(product?.personalizable));
  }

  function productForListNode(node) {
    if (!(node instanceof Element)) return null;
    const candidates = [
      node.dataset?.slug,
      node.dataset?.productSlug,
      node.dataset?.product,
      node.getAttribute?.('data-id'),
      node.querySelector?.('[data-slug]')?.getAttribute('data-slug'),
      node.querySelector?.('[data-product-slug]')?.getAttribute('data-product-slug'),
    ].filter(Boolean).map(String);
    for (const value of candidates) {
      const match = state.products.find(product =>
        String(product.slug || '') === value || String(product.id || '') === value
      );
      if (match) return match;
    }

    const text = String(node.textContent || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr-TR');
    if (!text) return null;
    const matches = state.products
      .filter(product => {
        const name = String(product.name || '').trim().toLocaleLowerCase('tr-TR');
        return name && text.includes(name);
      })
      .sort((a, b) => String(b.name || '').length - String(a.name || '').length);
    return matches[0] || null;
  }

  function applyPersonalizableListFilter() {
    const list = $('#productList');
    if (!list) return;
    [...list.children].forEach(node => {
      if (!(node instanceof HTMLElement)) return;
      if (!personalizableListFilterActive) {
        if (node.dataset.catalogPersonalizableHidden === '1') {
          node.hidden = false;
          node.style.removeProperty('display');
          delete node.dataset.catalogPersonalizableHidden;
        }
        return;
      }
      const product = productForListNode(node);
      const visible = Boolean(product?.personalizable);
      if (!visible) {
        node.dataset.catalogPersonalizableHidden = '1';
        node.hidden = true;
        node.style.setProperty('display', 'none', 'important');
      } else if (node.dataset.catalogPersonalizableHidden === '1') {
        node.hidden = false;
        node.style.removeProperty('display');
        delete node.dataset.catalogPersonalizableHidden;
      }
    });
  }

  function updatePersonalizableFilterUI() {
    const button = $('#personalizableListFilter');
    if (!button) return;
    button.classList.toggle('active', personalizableListFilterActive);
    button.setAttribute('aria-pressed', personalizableListFilterActive ? 'true' : 'false');
    const count = button.querySelector('.catalog-admin-filter-count');
    if (count) count.textContent = String(personalizableProducts().length);
  }

  function schedulePersonalizableFilter() {
    requestAnimationFrame(() => {
      applyPersonalizableListFilter();
      setTimeout(applyPersonalizableListFilter, 40);
      setTimeout(applyPersonalizableListFilter, 160);
    });
  }

  function ensurePersonalizableListFilter() {
    const host = $('#listFilters');
    if (!host) return;
    let button = $('#personalizableListFilter');
    if (!button) {
      button = document.createElement('button');
      button.id = 'personalizableListFilter';
      button.type = 'button';
      button.className = 'catalog-personalizable-list-filter';
      button.setAttribute('aria-pressed', 'false');
      button.innerHTML = '<span>Kişiselleştirilebilir</span><span class="catalog-admin-filter-count">0</span>';
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        const all = host.querySelector('[data-filter="all"]');
        if (!personalizableListFilterActive) {
          if (all && !all.classList.contains('active')) all.click();
          personalizableListFilterActive = true;
        } else {
          personalizableListFilterActive = false;
          if (all) all.click();
        }
        [...host.querySelectorAll('[data-filter]')].forEach(nativeButton => {
          if (personalizableListFilterActive) nativeButton.classList.remove('active');
        });
        updatePersonalizableFilterUI();
        schedulePersonalizableFilter();
      });
      host.appendChild(button);
      host.querySelectorAll('[data-filter]').forEach(nativeButton => {
        nativeButton.addEventListener('click', () => {
          if (!personalizableListFilterActive) return;
          personalizableListFilterActive = false;
          updatePersonalizableFilterUI();
          applyPersonalizableListFilter();
        });
      });
    }
    updatePersonalizableFilterUI();
    const list = $('#productList');
    if (list && !productListObserver) {
      productListObserver = new MutationObserver(() => {
        if (personalizableListFilterActive) schedulePersonalizableFilter();
      });
      productListObserver.observe(list, { childList: true, subtree: true });
    }
  }

  function openMaterials() {
    renderInventory();
    const el = modal();
    if (!el) return;
    el.hidden = false;
    document.body.classList.add('modal-open');
  }

  function closeMaterials() {
    const el = modal();
    if (!el) return;
    el.hidden = true;
    if (!document.querySelector('.modal:not([hidden])')) document.body.classList.remove('modal-open');
  }

  function materialRow(material = {}) {
    const row = document.createElement('div');
    row.className = 'material-inventory-row';
    row.dataset.materialId = material.id || '';

    const grip = document.createElement('span');
    grip.className = 'material-order';
    grip.textContent = '⋮⋮';
    grip.setAttribute('aria-hidden', 'true');

    const field = document.createElement('label');
    field.innerHTML = '<span>Malzeme adı</span>';
    const input = document.createElement('input');
    input.type = 'text';
    input.maxLength = 60;
    input.placeholder = 'Örn. PLA Silk';
    input.value = material.name || '';
    input.addEventListener('input', () => $('#materialsSaveState') && ($('#materialsSaveState').textContent = 'Kaydedilmemiş değişiklik var.'));
    field.appendChild(input);

    const id = document.createElement('small');
    id.className = 'material-id-preview';
    id.textContent = material.id ? `Kod: ${material.id}` : 'Kod kaydederken otomatik oluşur.';

    const remove = document.createElement('button');
    remove.className = 'tiny danger-text';
    remove.type = 'button';
    remove.textContent = 'Kaldır';
    remove.addEventListener('click', () => {
      row.remove();
      if ($('#materialsSaveState')) $('#materialsSaveState').textContent = 'Kaydedilmemiş değişiklik var.';
    });

    row.append(grip, field, id, remove);
    return row;
  }

  function renderInventory() {
    const root = inventory();
    if (!root) return;
    root.replaceChildren(...state.materials.map(material => materialRow(material)));
    if ($('#materialsSaveState')) $('#materialsSaveState').textContent = 'Değişiklik bekleniyor.';
  }

  function collectInventory() {
    return [...(inventory()?.querySelectorAll('.material-inventory-row') || [])].map((row, index) => {
      const name = row.querySelector('input')?.value.trim() || '';
      return {
        id: row.dataset.materialId || slugify(name),
        name,
        sort_order: (index + 1) * 10,
      };
    }).filter(item => item.name);
  }

  async function saveMaterials() {
    const button = $('#saveMaterials');
    if (button) button.disabled = true;
    if ($('#materialsSaveState')) $('#materialsSaveState').textContent = 'Kaydediliyor…';
    try {
      const response = await nativeFetch('/api/materials/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ materials: collectInventory() }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || data.message || 'Malzemeler kaydedilemedi.');
      state.materials = Array.isArray(data.materials) ? data.materials : [];
      state.selected = new Set([...state.selected].filter(id => state.materials.some(material => String(material.id) === id)));
      renderChoices();
      renderInventory();
      if ($('#materialsSaveState')) $('#materialsSaveState').textContent = 'Kalıcı kaydedildi. Site yeniden üretildi.';
    } catch (error) {
      if ($('#materialsSaveState')) $('#materialsSaveState').textContent = error.message || 'Kayıt başarısız.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  $('#manageMaterialsInline')?.addEventListener('click', openMaterials);
  $('[data-close-materials]')?.addEventListener('click', closeMaterials);
  modal()?.querySelectorAll('[data-close-materials]').forEach(button => button.addEventListener('click', closeMaterials));
  $('#addMaterial')?.addEventListener('click', () => {
    inventory()?.appendChild(materialRow({}));
    inventory()?.querySelector('.material-inventory-row:last-child input')?.focus();
    if ($('#materialsSaveState')) $('#materialsSaveState').textContent = 'Kaydedilmemiş değişiklik var.';
  });
  $('#saveMaterials')?.addEventListener('click', saveMaterials);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && modal() && !modal().hidden) closeMaterials();
  });

  // Existing manager.js changes slug/value programmatically. Poll only the slug;
  // selections are not overwritten while the same product is being edited.
  setInterval(() => syncCurrentProduct(false), 300);

  document.querySelector('#form')?.addEventListener('submit', () => {
    setTimeout(async () => {
      try { await loadState(); } catch (_) {}
    }, 1200);
  });

  ensurePersonalizableListFilter();
  loadState().catch(error => console.warn('[BG Studio catalog admin]', error));
})();
