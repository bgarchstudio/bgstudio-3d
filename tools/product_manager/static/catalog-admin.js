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

  loadState().catch(error => console.warn('[BG Studio catalog admin]', error));
})();
