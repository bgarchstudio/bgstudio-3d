// BG Studio 3D · V3.1.75 Site Content Center
(() => {
  const state = { content: null, products: [] };
  const $ = (s, root=document) => root.querySelector(s);
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const api = async (path, options={}) => {
    const res = await fetch(path, {cache:'no-store', headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options});
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.message || 'İşlem tamamlanamadı.');
    return data;
  };

  const SECTIONS = [
    ['home','Ana Sayfa'], ['corporate','Kurumsal'], ['prototype','Prototip / Parça'], ['about','Hakkımızda'], ['contact','İletişim']
  ];

  const fields = {
    home: [
      ['hero_eyebrow','Hero üst etiketi','text'], ['hero_title','Hero başlığı','text'], ['hero_lead','Hero açıklaması','textarea'],
      ['hero_primary_label','1. CTA yazısı','text'], ['hero_primary_url','1. CTA bağlantısı','text'],
      ['hero_secondary_label','2. CTA yazısı','text'], ['hero_secondary_url','2. CTA bağlantısı','text'],
      ['production_eyebrow','Özel üretim üst etiketi','text'], ['production_title','Özel üretim başlığı','text'], ['production_lead','Özel üretim açıklaması','textarea'],
      ['production_cta_label','Özel üretim CTA','text'], ['production_cta_url','Özel üretim CTA bağlantısı','text'],
      ['why_eyebrow','Neden BG Studio etiketi','text'], ['why_title','Neden BG Studio başlığı','text'],
      ['final_eyebrow','Final CTA üst etiketi','text'], ['final_title','Final CTA başlığı','text'], ['final_lead','Final CTA açıklaması','textarea'],
      ['final_primary_label','Final CTA yazısı','text'], ['final_primary_url','Final CTA bağlantısı','text'],
    ],
    corporate: [
      ['hero_eyebrow','Hero üst etiketi','text'], ['hero_title','Hero başlığı','text'], ['hero_lead','Hero açıklaması','textarea'],
      ['primary_label','Ana CTA yazısı','text'], ['primary_url','Ana CTA bağlantısı','text'], ['secondary_label','İkinci CTA yazısı','text'], ['secondary_url','İkinci CTA bağlantısı','text'],
    ],
    prototype: [
      ['hero_eyebrow','Hero üst etiketi','text'], ['hero_title','Hero başlığı','text'], ['hero_lead','Hero açıklaması','textarea'],
      ['primary_label','Ana CTA yazısı','text'], ['primary_url','Ana CTA bağlantısı','text'], ['secondary_label','İkinci CTA yazısı','text'], ['secondary_url','İkinci CTA bağlantısı','text'],
    ],
    about: [
      ['hero_eyebrow','Hero üst etiketi','text'], ['hero_title','Hero başlığı','text'], ['hero_lead','Hero açıklaması','textarea'],
      ['primary_label','Ana CTA yazısı','text'], ['primary_url','Ana CTA bağlantısı','text'], ['secondary_label','İkinci CTA yazısı','text'], ['secondary_url','İkinci CTA bağlantısı','text'],
    ],
    contact: [
      ['hero_eyebrow','Hero üst etiketi','text'], ['hero_title','Hero başlığı','text'], ['hero_lead','Hero açıklaması','textarea'],
    ],
  };

  function mount() {
    if ($('#bgSiteContentLauncher')) return;
    const launcher = document.createElement('button');
    launcher.id = 'bgSiteContentLauncher'; launcher.className='bg-site-content-launcher'; launcher.type='button';
    launcher.innerHTML='<span>Site İçerikleri</span><b>V3.1.75</b>';
    launcher.addEventListener('click', open);
    document.body.appendChild(launcher);

    const modal=document.createElement('div');
    modal.id='bgSiteContentModal'; modal.className='bg-site-content-modal'; modal.hidden=true;
    modal.innerHTML=`<div class="bg-site-content-backdrop" data-site-content-close></div>
      <section class="bg-site-content-shell" role="dialog" aria-modal="true" aria-labelledby="bgSiteContentTitle">
        <header class="bg-site-content-header"><div><p>BG STUDIO 3D · İÇERİK MERKEZİ</p><h2 id="bgSiteContentTitle">Site İçerik Yönetimi</h2><span>Ana sayfa ve temel hizmet sayfalarının başlık, açıklama, CTA ve ana sayfa hero ürünlerini yönet.</span></div><button type="button" data-site-content-close aria-label="Kapat">×</button></header>
        <div class="bg-site-content-body"><nav id="bgSiteContentTabs" class="bg-site-content-tabs"></nav><main id="bgSiteContentEditor" class="bg-site-content-editor"><div class="bg-site-content-loading">İçerikler yükleniyor...</div></main></div>
      </section>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', e => { if(e.target.closest('[data-site-content-close]')) close(); });
    document.addEventListener('keydown', e => { if(e.key==='Escape' && !modal.hidden) close(); });
  }

  async function open(){
    const modal=$('#bgSiteContentModal'); if(!modal) return;
    modal.hidden=false; document.body.classList.add('bg-site-content-open');
    try {
      const data=await api('/api/site-content-v3175');
      state.content=data.content||{}; state.products=Array.isArray(data.products)?data.products:[];
      renderTabs('home'); renderEditor('home');
    } catch(err){ $('#bgSiteContentEditor').innerHTML=`<div class="bg-site-content-error">${esc(err.message)}</div>`; }
  }
  function close(){ const modal=$('#bgSiteContentModal'); if(modal) modal.hidden=true; document.body.classList.remove('bg-site-content-open'); }

  function renderTabs(active){
    const tabs=$('#bgSiteContentTabs'); if(!tabs) return;
    tabs.innerHTML=SECTIONS.map(([key,label])=>`<button type="button" data-section="${key}" class="${key===active?'is-active':''}">${esc(label)}</button>`).join('');
    tabs.querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{ renderTabs(btn.dataset.section); renderEditor(btn.dataset.section); }));
  }

  function productOptions(selected=''){
    return '<option value="">Otomatik seçim</option>'+state.products.map(p=>`<option value="${esc(p.slug)}" ${p.slug===selected?'selected':''}>${esc(p.name||p.slug)}</option>`).join('');
  }

  function renderEditor(section){
    const editor=$('#bgSiteContentEditor'); if(!editor) return;
    const values=state.content?.[section]||{};
    const rows=(fields[section]||[]).map(([key,label,type])=>{
      const value=values[key]??'';
      return `<label class="${type==='textarea'?'wide':''}"><span>${esc(label)}</span>${type==='textarea'?`<textarea data-key="${key}" rows="4">${esc(value)}</textarea>`:`<input data-key="${key}" value="${esc(value)}">`}</label>`;
    }).join('');
    const heroPickers=section==='home'?`<section class="bg-site-content-card"><div class="bg-site-content-card-head"><div><b>Hero ürün görselleri</b><small>Soldaki büyük kart ve sağdaki iki küçük kart için ürün seç. Boş bırakırsan öne çıkan ürünlerden otomatik seçilir.</small></div></div><div class="bg-site-content-grid three">${[0,1,2].map((i)=>`<label><span>${i===0?'Büyük görsel':`Sağ görsel ${i}`}</span><select data-hero-slot="${i}">${productOptions((values.hero_product_slugs||[])[i]||'')}</select></label>`).join('')}</div></section>`:'';
    editor.innerHTML=`<form id="bgSiteContentForm" data-section="${section}">
      <section class="bg-site-content-card"><div class="bg-site-content-card-head"><div><b>${esc(SECTIONS.find(x=>x[0]===section)?.[1]||section)}</b><small>Boş bırakırsan mevcut güvenli varsayılan korunur. Bağlantılarda site içi yol veya https adresi kullan.</small></div></div><div class="bg-site-content-grid">${rows}</div></section>
      ${heroPickers}
      <div class="bg-site-content-savebar"><span id="bgSiteContentState">Değişiklik bekleniyor.</span><button class="primary" type="submit">Kaydet ve siteyi oluştur</button></div>
    </form>`;
    $('#bgSiteContentForm')?.addEventListener('submit', save);
  }

  async function save(event){
    event.preventDefault();
    const form=event.currentTarget; const section=form.dataset.section; const next=JSON.parse(JSON.stringify(state.content||{}));
    next[section]=next[section]||{};
    form.querySelectorAll('[data-key]').forEach(el=>{ next[section][el.dataset.key]=el.value.trim(); });
    if(section==='home') next.home.hero_product_slugs=[...form.querySelectorAll('[data-hero-slot]')].map(x=>x.value).filter(Boolean);
    const button=form.querySelector('button[type="submit"]'); const status=$('#bgSiteContentState');
    button.disabled=true; status.textContent='Kaydediliyor ve site oluşturuluyor...';
    try{
      const data=await api('/api/site-content-v3175/save',{method:'POST',body:JSON.stringify({content:next})});
      state.content=data.content||next; status.textContent='Kaydedildi. Site güncellendi.'; renderEditor(section);
    }catch(err){ status.textContent=err.message; button.disabled=false; }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true}); else mount();
})();
