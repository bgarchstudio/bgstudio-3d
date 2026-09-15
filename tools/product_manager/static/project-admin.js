// BG Studio 3D · V3.1.74 Project / Case Study Manager
(() => {
  const state = { items: [], activeId: '', filter: 'all', query: '', newGallery: [], removedGallery: new Set(), coverFile: null, coverClear: false };
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  }
  function api(path, options = {}) {
    return fetch(path, { cache: 'no-store', headers: { 'Content-Type':'application/json', ...(options.headers || {}) }, ...options });
  }
  function kindLabel(kind) {
    return ({ nfc:'NFC + QR', corporate:'Kurumsal', prototype:'Prototip + Parça' })[kind] || 'Proje';
  }
  function publicProjectUrl(item) {
    return `/projeler/${encodeURIComponent(item?.project_slug || '')}/`;
  }

  function mount() {
    if ($('#bgProjectAdminLauncher')) return;
    const launcher = document.createElement('button');
    launcher.id = 'bgProjectAdminLauncher';
    launcher.className = 'bg-project-admin-launcher';
    launcher.type = 'button';
    launcher.innerHTML = '<span>Projeler</span><b>Case Study</b>';
    launcher.addEventListener('click', openManager);
    document.body.appendChild(launcher);

    const modal = document.createElement('div');
    modal.id = 'bgProjectAdminModal';
    modal.className = 'bg-project-admin-modal';
    modal.hidden = true;
    modal.innerHTML = `
      <div class="bg-project-admin-backdrop" data-project-close></div>
      <section class="bg-project-admin-shell" role="dialog" aria-modal="true" aria-labelledby="bgProjectAdminTitle">
        <header class="bg-project-admin-header">
          <div><p>BG STUDIO 3D · V3.1.74</p><h2 id="bgProjectAdminTitle">Proje / Case Study Yönetimi</h2><span>Projeler sayfasındaki içerik, sıralama, görseller, metrikler ve SEO burada yönetilir.</span></div>
          <div class="bg-project-admin-head-actions"><a href="/projeler/" target="_blank" rel="noopener">Projeleri aç ↗</a><button type="button" data-project-close aria-label="Kapat">×</button></div>
        </header>
        <div class="bg-project-admin-layout">
          <aside class="bg-project-admin-sidebar">
            <div class="bg-project-admin-search"><input id="bgProjectSearch" type="search" placeholder="Proje ara..."></div>
            <div class="bg-project-admin-filters" id="bgProjectFilters">
              <button type="button" data-kind="all" class="is-active">Tümü</button>
              <button type="button" data-kind="nfc">NFC + QR</button>
              <button type="button" data-kind="corporate">Kurumsal</button>
              <button type="button" data-kind="prototype">Prototip</button>
            </div>
            <div class="bg-project-admin-list" id="bgProjectList"></div>
          </aside>
          <main class="bg-project-admin-editor" id="bgProjectEditor">
            <div class="bg-project-admin-empty"><strong>Bir proje seç.</strong><span>Mevcut saha kayıtlarından birini düzenleyebilirsin.</span></div>
          </main>
        </div>
      </section>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', event => {
      if (event.target.closest('[data-project-close]')) closeManager();
    });
    $('#bgProjectSearch', modal)?.addEventListener('input', event => { state.query = event.target.value.trim().toLocaleLowerCase('tr-TR'); renderList(); });
    $('#bgProjectFilters', modal)?.addEventListener('click', event => {
      const btn = event.target.closest('[data-kind]'); if (!btn) return;
      state.filter = btn.dataset.kind || 'all';
      $$('#bgProjectFilters [data-kind]', modal).forEach(x => x.classList.toggle('is-active', x === btn));
      renderList();
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !modal.hidden) closeManager(); });
  }

  async function openManager() {
    const modal = $('#bgProjectAdminModal');
    if (!modal) return;
    modal.hidden = false;
    document.body.classList.add('bg-project-admin-open');
    await loadProjects();
  }
  function closeManager() {
    const modal = $('#bgProjectAdminModal');
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove('bg-project-admin-open');
  }

  async function loadProjects(preserve = true) {
    const list = $('#bgProjectList');
    if (list) list.innerHTML = '<div class="bg-project-admin-loading">Projeler yükleniyor...</div>';
    try {
      const response = await api('/api/projects-admin');
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || 'Projeler alınamadı.');
      state.items = Array.isArray(data.items) ? data.items : [];
      if (!preserve || !state.items.some(x => x.id === state.activeId)) state.activeId = state.items[0]?.id || '';
      renderList();
      renderEditor();
    } catch (error) {
      if (list) list.innerHTML = `<div class="bg-project-admin-error">${escapeHtml(error.message)}</div>`;
    }
  }

  function filteredItems() {
    return state.items.filter(item => {
      if (state.filter !== 'all' && item.source_kind !== state.filter) return false;
      if (!state.query) return true;
      const text = [item.client,item.title,item.sector,item.source_label,item.project_slug].join(' ').toLocaleLowerCase('tr-TR');
      return text.includes(state.query);
    });
  }

  function renderList() {
    const list = $('#bgProjectList'); if (!list) return;
    const items = filteredItems();
    if (!items.length) { list.innerHTML = '<div class="bg-project-admin-empty-list">Eşleşen proje yok.</div>'; return; }
    list.innerHTML = items.map(item => `
      <button type="button" class="bg-project-admin-list-item ${item.id === state.activeId ? 'is-active':''}" data-project-id="${escapeHtml(item.id)}">
        <span class="bg-project-admin-list-top"><b>${escapeHtml(item.client || item.title || 'Proje')}</b><em>${escapeHtml(item.sort_order)}</em></span>
        <small>${escapeHtml(item.source_label || kindLabel(item.source_kind))}</small>
        <span class="bg-project-admin-list-flags"><i class="${item.project_active ? 'is-live':'is-archived'}">${item.project_active ? 'Yayında':'Arşiv'}</i>${item.managed ? '<i>Yönetiliyor</i>':''}</span>
      </button>`).join('');
    $$('.bg-project-admin-list-item', list).forEach(btn => btn.addEventListener('click', () => {
      state.activeId = btn.dataset.projectId || '';
      state.newGallery = []; state.removedGallery = new Set(); state.coverFile = null; state.coverClear = false;
      renderList(); renderEditor();
    }));
  }

  function current() { return state.items.find(x => x.id === state.activeId) || null; }
  function metric(item, key) { return item?.metrics?.[key] ?? ''; }

  function renderEditor() {
    const editor = $('#bgProjectEditor'); if (!editor) return;
    const item = current();
    if (!item) { editor.innerHTML = '<div class="bg-project-admin-empty"><strong>Bir proje seç.</strong><span>Mevcut saha kayıtlarından birini düzenleyebilirsin.</span></div>'; return; }
    state.newGallery = []; state.removedGallery = new Set(); state.coverFile = null; state.coverClear = false;
    const cover = item.cover_image ? `/${String(item.cover_image).replace(/^\//,'')}` : '';
    const gallery = Array.isArray(item.gallery_images) ? item.gallery_images : [];
    editor.innerHTML = `
      <form id="bgProjectForm" class="bg-project-admin-form">
        <div class="bg-project-admin-editor-head">
          <div><p>${escapeHtml(item.source_label || kindLabel(item.source_kind))}</p><h3>${escapeHtml(item.client || item.title || 'Proje')}</h3><span>Kaynak: ${escapeHtml(item.source_slug)} · URL sabit: ${escapeHtml(publicProjectUrl(item))}</span></div>
          <div><a href="${escapeHtml(publicProjectUrl(item))}" target="_blank" rel="noopener">Sayfayı aç ↗</a><button type="button" class="bg-project-admin-reset" id="bgProjectReset">Kaynağa dön</button></div>
        </div>

        <section class="bg-project-admin-section"><div class="bg-project-admin-section-title"><b>Yayın & sıralama</b><span>Projeler sayfasındaki görünürlük ve sıra.</span></div>
          <div class="bg-project-admin-grid two"><label class="check"><input id="pa_active" type="checkbox" ${item.project_active ? 'checked':''}> Projeler sayfasında yayınla</label><label>Sıra<input id="pa_sort" type="number" min="1" max="9999" value="${escapeHtml(item.sort_order || 999)}"></label></div>
        </section>

        <section class="bg-project-admin-section"><div class="bg-project-admin-section-title"><b>Kimlik & anlatım</b><span>Case study sayfasındaki ana içerik.</span></div>
          <div class="bg-project-admin-grid two"><label>Müşteri / işletme<input id="pa_client" maxlength="120" value="${escapeHtml(item.client)}"></label><label>Sektör<input id="pa_sector" maxlength="120" value="${escapeHtml(item.sector)}"></label></div>
          <label>Proje başlığı<input id="pa_title" maxlength="180" value="${escapeHtml(item.title)}"></label>
          <label>Kısa özet<textarea id="pa_summary" rows="3" maxlength="800">${escapeHtml(item.summary)}</textarea></label>
          <div class="bg-project-admin-grid two"><label>İhtiyaç<textarea id="pa_need" rows="5">${escapeHtml(item.need)}</textarea></label><label>BG Studio çözümü<textarea id="pa_solution" rows="5">${escapeHtml(item.solution)}</textarea></label></div>
          <div class="bg-project-admin-grid three"><label>Üretim adedi<input id="pa_quantity" maxlength="120" value="${escapeHtml(item.quantity)}"></label><label>Sistem<input id="pa_system" maxlength="240" value="${escapeHtml(item.system)}"></label><label>Teslim<input id="pa_delivery" maxlength="180" value="${escapeHtml(item.delivery)}"></label></div>
          <label>Sonuç<textarea id="pa_result" rows="5">${escapeHtml(item.result)}</textarea></label>
          <label>Etiketler<input id="pa_tags" value="${escapeHtml((item.tags || []).join(', '))}" placeholder="NFC, QR, Dijital Menü"></label>
        </section>

        <section class="bg-project-admin-section"><div class="bg-project-admin-section-title"><b>Görseller</b><span>Kapak ve en fazla 6 proje detayı. Görseller orijinal oranıyla gösterilir.</span></div>
          <div class="bg-project-admin-media-row">
            <div class="bg-project-admin-cover" id="paCoverPreview">${cover ? `<img src="${escapeHtml(cover)}" alt="Kapak">` : '<span>Kapak görseli yok</span>'}</div>
            <div class="bg-project-admin-media-actions"><label class="file-btn">Kapak seç<input id="pa_cover_file" type="file" accept="image/*" hidden></label><label class="check"><input id="pa_cover_clear" type="checkbox"> Kapak görselini kaldır</label><small>Yeni kapak seçmezsen mevcut kaynak görseli korunur.</small></div>
          </div>
          <div class="bg-project-admin-gallery" id="paGallery">${gallery.map((src, i) => `<div class="bg-project-admin-gallery-item" data-gallery-path="${escapeHtml(src)}"><img src="/${escapeHtml(src.replace(/^\//,''))}" alt="Proje görseli ${i+1}"><button type="button" data-remove-gallery>×</button></div>`).join('')}</div>
          <label class="file-btn gallery-add">+ Galeri görseli ekle<input id="pa_gallery_files" type="file" accept="image/*" multiple hidden></label>
        </section>

        <section class="bg-project-admin-section"><div class="bg-project-admin-section-title"><b>Gerçek metrikler</b><span>Boş bıraktığın değerler sitede görünmez.</span></div>
          <div class="bg-project-admin-grid four"><label>NFC taraması<input id="pa_nfc_scans" type="number" min="0" value="${escapeHtml(metric(item,'nfc_scans'))}"></label><label>Menü açılışı<input id="pa_menu_opens" type="number" min="0" value="${escapeHtml(metric(item,'menu_opens'))}"></label><label>Feedback<input id="pa_feedback_count" type="number" min="0" value="${escapeHtml(metric(item,'feedback_count'))}"></label><label>Google yönlendirmesi<input id="pa_google_redirects" type="number" min="0" value="${escapeHtml(metric(item,'google_redirects'))}"></label></div>
        </section>

        <section class="bg-project-admin-section"><div class="bg-project-admin-section-title"><b>SEO</b><span>Boş bırakılırsa proje başlığı ve özeti otomatik değerlendirilir.</span></div>
          <label>SEO title<input id="pa_seo_title" maxlength="180" value="${escapeHtml(item.seo_title)}"></label><label>SEO description<textarea id="pa_seo_description" rows="3" maxlength="220">${escapeHtml(item.seo_description)}</textarea></label>
        </section>

        <footer class="bg-project-admin-savebar"><span id="bgProjectSaveState">Değişiklik bekleniyor.</span><button class="primary" type="submit">Kaydet ve siteyi güncelle</button></footer>
      </form>`;
    bindEditor();
  }

  async function imageToWebp(file) {
    if (!file || !file.type.startsWith('image/')) throw new Error('Geçerli bir görsel seç.');
    if (file.size > 12 * 1024 * 1024) throw new Error('Görsel 12 MB sınırını aşıyor.');
    const bitmap = await createImageBitmap(file);
    const max = 1800;
    const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close?.();
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/webp', .9));
    if (!blob) throw new Error('Görsel dönüştürülemedi.');
    const data = await new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = reject; r.readAsDataURL(blob); });
    return { name: file.name.replace(/\.[^.]+$/, '.webp'), data };
  }

  function bindEditor() {
    const form = $('#bgProjectForm'); if (!form) return;
    $('#pa_cover_file')?.addEventListener('change', async event => {
      const file = event.target.files?.[0]; if (!file) return;
      try { state.coverFile = await imageToWebp(file); state.coverClear = false; $('#pa_cover_clear').checked = false; $('#paCoverPreview').innerHTML = `<img src="${state.coverFile.data}" alt="Yeni kapak">`; }
      catch (e) { alert(e.message); }
    });
    $('#pa_cover_clear')?.addEventListener('change', event => { state.coverClear = !!event.target.checked; if (state.coverClear) { state.coverFile = null; $('#paCoverPreview').innerHTML = '<span>Kapak kaldırılacak</span>'; } });
    $('#pa_gallery_files')?.addEventListener('change', async event => {
      const files = [...(event.target.files || [])];
      const existing = $$('#paGallery [data-gallery-path]').filter(x => !state.removedGallery.has(x.dataset.galleryPath)).length;
      const room = Math.max(0, 6 - existing - state.newGallery.length);
      for (const file of files.slice(0, room)) {
        try { state.newGallery.push(await imageToWebp(file)); } catch (e) { alert(e.message); break; }
      }
      renderGalleryPreview(); event.target.value = '';
    });
    $('#paGallery')?.addEventListener('click', event => {
      const btn = event.target.closest('[data-remove-gallery]'); if (!btn) return;
      const item = btn.closest('.bg-project-admin-gallery-item');
      const path = item?.dataset.galleryPath;
      const localIndex = item?.dataset.localIndex;
      if (path) state.removedGallery.add(path);
      if (localIndex != null) state.newGallery.splice(Number(localIndex), 1);
      renderGalleryPreview();
    });
    $('#bgProjectReset')?.addEventListener('click', resetProject);
    form.addEventListener('submit', saveProject);
  }

  function renderGalleryPreview() {
    const item = current(); const target = $('#paGallery'); if (!target || !item) return;
    const existing = (item.gallery_images || []).filter(src => !state.removedGallery.has(src));
    target.innerHTML = existing.map((src,i) => `<div class="bg-project-admin-gallery-item" data-gallery-path="${escapeHtml(src)}"><img src="/${escapeHtml(src.replace(/^\//,''))}" alt="Proje görseli ${i+1}"><button type="button" data-remove-gallery>×</button></div>`).join('') + state.newGallery.map((obj,i) => `<div class="bg-project-admin-gallery-item" data-local-index="${i}"><img src="${obj.data}" alt="Yeni proje görseli"><button type="button" data-remove-gallery>×</button></div>`).join('');
  }

  function field(id) { return String($(`#${id}`)?.value ?? '').trim(); }
  function numField(id) { const v = field(id); return v === '' ? '' : Number(v); }
  function payloadFromForm() {
    const item = current();
    return {
      id: item.id,
      project: {
        project_active: !!$('#pa_active')?.checked,
        sort_order: Math.max(1, Number(field('pa_sort') || item.sort_order || 999)),
        client: field('pa_client'), title: field('pa_title'), summary: field('pa_summary'), sector: field('pa_sector'),
        need: field('pa_need'), solution: field('pa_solution'), quantity: field('pa_quantity'), system: field('pa_system'), delivery: field('pa_delivery'), result: field('pa_result'),
        tags: field('pa_tags').split(',').map(x => x.trim()).filter(Boolean),
        metrics: { nfc_scans:numField('pa_nfc_scans'), menu_opens:numField('pa_menu_opens'), feedback_count:numField('pa_feedback_count'), google_redirects:numField('pa_google_redirects') },
        seo_title: field('pa_seo_title'), seo_description: field('pa_seo_description'), cover_image: item.cover_image || ''
      },
      cover_file: state.coverFile,
      cover_clear: state.coverClear,
      gallery_keep: (item.gallery_images || []).filter(src => !state.removedGallery.has(src)),
      gallery_new: state.newGallery
    };
  }

  async function saveProject(event) {
    event.preventDefault(); const status = $('#bgProjectSaveState'); const button = event.submitter;
    if (status) status.textContent = 'Kaydediliyor ve site yeniden üretiliyor...'; if (button) button.disabled = true;
    try {
      const response = await api('/api/projects-admin/save', { method:'POST', body: JSON.stringify(payloadFromForm()) });
      const data = await response.json(); if (!response.ok || !data.ok) throw new Error(data.message || 'Kayıt başarısız.');
      if (status) status.textContent = 'Kaydedildi. Proje sayfaları güncellendi.';
      await loadProjects(true);
    } catch (error) { if (status) status.textContent = error.message; alert(error.message); }
    finally { if (button) button.disabled = false; }
  }

  async function resetProject() {
    const item = current(); if (!item || !item.managed) { alert('Bu proje zaten kaynak kaydı kullanıyor.'); return; }
    if (!confirm('Bu projenin özel Case Study ayarlarını sıfırlayıp kaynak saha kaydına dönmek istiyor musun?')) return;
    try {
      const response = await api('/api/projects-admin/reset', { method:'POST', body:JSON.stringify({ id:item.id }) });
      const data = await response.json(); if (!response.ok || !data.ok) throw new Error(data.message || 'Sıfırlama başarısız.');
      await loadProjects(true);
    } catch (error) { alert(error.message); }
  }

  mount();
})();
