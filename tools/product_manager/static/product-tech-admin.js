// BG Studio 3D · V3.1.73 product technical metadata companion
(() => {
  const $ = selector => document.querySelector(selector);
  const state = { products: [], activeSlug: null };
  const fieldIds = [
    'dimensions', 'weight', 'print_method', 'production_time', 'estimated_production_time',
    'box_contents', 'technical_info', 'usage_info', 'personalization_info', 'production_status',
    'og_image_source'
  ];

  const nativeFetch = window.fetch.bind(window);

  function ensureOgField() {
    if ($('#og_image_source')) return;
    const seoTitle = $('#seo_title');
    const section = seoTitle?.closest('.section');
    if (!section) return;
    const meter = section.querySelector('.seo-meter');
    const wrap = document.createElement('div');
    wrap.className = 'product-og-admin';
    wrap.innerHTML = `
      <label>Paylaşım / OG görseli
        <select id="og_image_source">
          <option value="main">Ana ürün görseli</option>
          <option value="poster">Afiş / ikinci görsel</option>
          <option value="gallery">İlk galeri görseli</option>
        </select>
        <small>WhatsApp, sosyal medya ve arama paylaşım önizlemelerinde tercih edilen görsel. Seçilen görsel yoksa ana ürün görseline döner.</small>
      </label>`;
    if (meter) meter.before(wrap); else section.appendChild(wrap);
  }

  function ensureTechSection() {
    if ($('#productTechAdmin')) return;
    const form = $('#form');
    if (!form) return;
    const footer = form.querySelector('.form-footer');
    const section = document.createElement('div');
    section.className = 'section product-tech-admin-section';
    section.id = 'productTechAdmin';
    section.innerHTML = `
      <div class="section-head"><div><span>03</span><h2>Teknik &amp; üretim</h2></div><small>Boş bıraktığın bilgiler ürün sayfasında gösterilmez.</small></div>
      <div class="grid two">
        <label>Ölçüler<input id="dimensions" maxlength="120" placeholder="Örn. 18 × 12 × 9 cm"></label>
        <label>Ağırlık<input id="weight" maxlength="120" placeholder="Örn. 240 g"></label>
        <label>Baskı yöntemi<input id="print_method" maxlength="120" placeholder="Örn. FDM · 0.4 mm nozzle"></label>
        <label>Baskı / üretim süresi<input id="production_time" maxlength="120" placeholder="Örn. Yaklaşık 8 saat"></label>
        <label>Tahmini sipariş hazırlık süresi<input id="estimated_production_time" maxlength="120" placeholder="Örn. 1–3 iş günü"></label>
        <label>Üretim durumu<select id="production_status"><option value="">Belirtilmedi</option><option value="active">Üretime açık</option><option value="busy">Yoğunluk yüksek</option><option value="preorder">Ön sipariş</option><option value="paused">Geçici olarak üretimde değil</option></select></label>
      </div>
      <div class="grid two product-tech-textareas">
        <label>Kutu içeriği<textarea id="box_contents" rows="5"></textarea></label>
        <label>Teknik bilgiler<textarea id="technical_info" rows="5"></textarea></label>
        <label>Kullanım bilgisi<textarea id="usage_info" rows="4"></textarea></label>
        <label>Kişiselleştirme bilgisi<textarea id="personalization_info" rows="4"></textarea></label>
      </div>
      <div class="product-tech-preview"><span>Ürün sayfası</span><strong id="productTechPreviewState">Teknik bilgiler boşsa bölüm görünmez.</strong></div>`;
    if (footer) footer.before(section); else form.appendChild(section);
  }

  function currentProduct() {
    const slug = String($('#slug')?.value || '').trim();
    return state.products.find(product => String(product.slug || '') === slug) || null;
  }

  function valueFor(id, product) {
    if (!product) return id === 'og_image_source' ? 'main' : '';
    if (id === 'og_image_source') return product[id] || 'main';
    return product[id] ?? '';
  }

  function updatePreview() {
    const status = $('#production_status')?.value || '';
    const label = {
      active: 'Üretime açık', busy: 'Yoğunluk yüksek', preorder: 'Ön sipariş', paused: 'Geçici olarak üretimde değil'
    }[status];
    const hasTech = ['dimensions','weight','print_method','production_time','estimated_production_time','box_contents','technical_info','usage_info','personalization_info']
      .some(id => String($(`#${id}`)?.value || '').trim());
    const target = $('#productTechPreviewState');
    if (!target) return;
    target.textContent = [label, hasTech ? 'Teknik bölüm yayında' : 'Teknik bölüm boş'].filter(Boolean).join(' · ') || 'Teknik bilgiler boşsa bölüm görünmez.';
  }

  function syncProduct(force = false) {
    ensureTechSection();
    ensureOgField();
    const slug = String($('#slug')?.value || '').trim();
    if (!force && slug === state.activeSlug) return;
    state.activeSlug = slug;
    const product = currentProduct();
    fieldIds.forEach(id => {
      const el = $(`#${id}`);
      if (!el) return;
      el.value = valueFor(id, product);
    });
    updatePreview();
  }

  async function loadState() {
    const response = await nativeFetch('/api/products', { cache: 'no-store' });
    if (!response.ok) throw new Error('Teknik ürün bilgileri alınamadı.');
    const data = await response.json();
    state.products = Array.isArray(data.products) ? data.products : [];
    syncProduct(true);
  }

  function collectProductFields() {
    const out = {};
    fieldIds.forEach(id => {
      const el = $(`#${id}`);
      if (!el) return;
      out[id] = String(el.value ?? '').trim();
    });
    return out;
  }

  window.fetch = async (input, init = {}) => {
    try {
      const url = typeof input === 'string' ? input : (input?.url || '');
      if (url.endsWith('/api/save') && init && typeof init.body === 'string') {
        const payload = JSON.parse(init.body);
        if (payload?.product && typeof payload.product === 'object') {
          Object.assign(payload.product, collectProductFields());
          init = { ...init, body: JSON.stringify(payload) };
        }
      }
    } catch (_) {}
    return nativeFetch(input, init);
  };

  document.addEventListener('input', event => {
    if (event.target && fieldIds.includes(event.target.id)) updatePreview();
  });
  document.addEventListener('change', event => {
    if (event.target && fieldIds.includes(event.target.id)) updatePreview();
  });

  $('#form')?.addEventListener('submit', () => {
    setTimeout(() => loadState().catch(() => {}), 1200);
  });

  setInterval(() => syncProduct(false), 320);
  ensureTechSection();
  ensureOgField();
  loadState().catch(error => console.warn('[BG Studio product tech admin]', error));
})();
