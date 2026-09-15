// BG Studio 3D · V3.1.76 Site Content + Placement Center
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
    launcher.innerHTML='<span>Site İçerikleri</span><b>V3.1.76</b>';
    launcher.addEventListener('click', open);
    document.body.appendChild(launcher);

    const modal=document.createElement('div');
    modal.id='bgSiteContentModal'; modal.className='bg-site-content-modal'; modal.hidden=true;
    modal.innerHTML=`<div class="bg-site-content-backdrop" data-site-content-close></div>
      <section class="bg-site-content-shell" role="dialog" aria-modal="true" aria-labelledby="bgSiteContentTitle">
        <header class="bg-site-content-header"><div><p>BG STUDIO 3D · İÇERİK MERKEZİ</p><h2 id="bgSiteContentTitle">Site İçerik Yönetimi</h2><span>Metinleri ve ana sayfadaki ürün yerleşimlerini, hangi ürünün hangi kartta görüneceğine kadar yönet.</span></div><button type="button" data-site-content-close aria-label="Kapat">×</button></header>
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

  function productOptions(selected='', allowHide=false){
    const hide = allowHide ? '<option value="__hide__" '+(selected==='__hide__'?'selected':'')+'>Bu kartı gizle</option>' : '';
    return '<option value="" '+(!selected?'selected':'')+'>Otomatik seçim</option>'+hide+state.products.map(p=>`<option value="${esc(p.slug)}" ${p.slug===selected?'selected':''}>${esc(p.name||p.slug)}</option>`).join('');
  }

  function productBySlug(slug){ return state.products.find(p=>String(p.slug||'')===String(slug||'')) || null; }

  function slotPreview(slug){
    const p=productBySlug(slug);
    if(!p || !p.image) return '<div class="bg-placement-preview is-auto"><span>BG</span><small>'+(slug==='__hide__'?'Gizli':'Otomatik')+'</small></div>';
    return `<div class="bg-placement-preview"><img src="/${esc(p.image).replace(/^\/+/, '')}" alt=""><small>${esc(p.name||p.slug)}</small></div>`;
  }

  function placementSlot({label, note='', key, index=null, value='', allowHide=false}){
    const dataAttr=index===null?`data-placement-single="${key}"`:`data-placement-list="${key}" data-placement-index="${index}"`;
    return `<label class="bg-placement-slot"><span>${esc(label)}</span>${note?`<small>${esc(note)}</small>`:''}<div data-placement-preview>${slotPreview(value)}</div><select ${dataAttr}>${productOptions(value,allowHide)}</select></label>`;
  }

  function bindPlacementPreviews(){
    document.querySelectorAll('[data-placement-list],[data-placement-single]').forEach(select=>select.addEventListener('change',()=>{
      const slot=select.closest('.bg-placement-slot'); const preview=slot?.querySelector('[data-placement-preview]');
      if(preview) preview.innerHTML=slotPreview(select.value);
    }));
  }


  function renderEditor(section){
    const editor=$('#bgSiteContentEditor'); if(!editor) return;
    const values=state.content?.[section]||{};
    const rows=(fields[section]||[]).map(([key,label,type])=>{
      const value=values[key]??'';
      return `<label class="${type==='textarea'?'wide':''}"><span>${esc(label)}</span>${type==='textarea'?`<textarea data-key="${key}" rows="4">${esc(value)}</textarea>`:`<input data-key="${key}" value="${esc(value)}">`}</label>`;
    }).join('');
    const placementManager=section==='home'?`<section class="bg-site-content-card bg-placement-manager"><div class="bg-site-content-card-head"><div><b>Ana Sayfa · Ürün Yerleşimi</b><small>Bu alanlar birbirinden bağımsızdır. Hero seçimi artık ürün vitrini veya Özel Üretim görselini değiştirmez.</small></div></div><div class="bg-placement-group"><div class="bg-placement-title"><strong>01 · Giriş Hero</strong><span>Soldaki büyük görsel + sağdaki iki küçük görsel</span></div><div class="bg-placement-grid three">${[
        ['Büyük ana görsel','Girişte en baskın ürün'],['Sağ üst görsel','Küçük ürün kartı'],['Sağ alt görsel','Küçük ürün kartı']
      ].map((row,i)=>placementSlot({label:row[0],note:row[1],key:'hero_product_slugs',index:i,value:(values.hero_product_slugs||[])[i]||''})).join('')}</div></div>
      <div class="bg-placement-group"><div class="bg-placement-title"><strong>02 · Ürün Vitrini</strong><span>“Tasarlandı. Basıldı. Kullanıma hazır.” bölümündeki kartların sırası</span></div><div class="bg-placement-grid three">${[
        ['Vitrin 01 · Büyük sol','İlk büyük kart'],['Vitrin 02 · Sağ üst','İlk sıradaki sağ kart'],['Vitrin 03 · Alt sol','İkinci sıra sol'],['Vitrin 04 · Alt orta','İkinci sıra orta'],['Vitrin 05 · Alt sağ','İkinci sıra sağ'],['Vitrin 06 · Devam','Sonraki kart']
      ].map((row,i)=>placementSlot({label:row[0],note:row[1],key:'showcase_product_slugs',index:i,value:(values.showcase_product_slugs||[])[i]||'',allowHide:true})).join('')}</div></div>
      <div class="bg-placement-group"><div class="bg-placement-title"><strong>03 · Özel Üretim Görseli</strong><span>“Aklındaki parçayı üretelim.” alanındaki sağ büyük görsel</span></div><div class="bg-placement-grid one">${placementSlot({label:'Özel Üretim ürün görseli',note:'Bu seçim yalnız bu bölümü etkiler.',key:'production_product_slug',value:values.production_product_slug||''})}</div></div></section>`:'';
    editor.innerHTML=`<form id="bgSiteContentForm" data-section="${section}">
      <section class="bg-site-content-card"><div class="bg-site-content-card-head"><div><b>${esc(SECTIONS.find(x=>x[0]===section)?.[1]||section)}</b><small>Boş bırakırsan mevcut güvenli varsayılan korunur. Bağlantılarda site içi yol veya https adresi kullan.</small></div></div><div class="bg-site-content-grid">${rows}</div></section>
      ${placementManager}
      <div class="bg-site-content-savebar"><span id="bgSiteContentState">Değişiklik bekleniyor.</span><button class="primary" type="submit">Kaydet ve siteyi oluştur</button></div>
    </form>`;
    $('#bgSiteContentForm')?.addEventListener('submit', save);
    bindPlacementPreviews();
  }

  async function save(event){
    event.preventDefault();
    const form=event.currentTarget; const section=form.dataset.section; const next=JSON.parse(JSON.stringify(state.content||{}));
    next[section]=next[section]||{};
    form.querySelectorAll('[data-key]').forEach(el=>{ next[section][el.dataset.key]=el.value.trim(); });
    if(section==='home'){
      const collectList=(key,count)=>Array.from({length:count},(_,i)=>form.querySelector(`[data-placement-list="${key}"][data-placement-index="${i}"]`)?.value||'');
      next.home.hero_product_slugs=collectList('hero_product_slugs',3);
      next.home.showcase_product_slugs=collectList('showcase_product_slugs',6);
      next.home.production_product_slug=form.querySelector('[data-placement-single="production_product_slug"]')?.value||'';
    }
    const button=form.querySelector('button[type="submit"]'); const status=$('#bgSiteContentState');
    button.disabled=true; status.textContent='Kaydediliyor ve site oluşturuluyor...';
    try{
      const data=await api('/api/site-content-v3175/save',{method:'POST',body:JSON.stringify({content:next})});
      state.content=data.content||next; status.textContent='Kaydedildi. Site güncellendi.'; renderEditor(section);
    }catch(err){ status.textContent=err.message; button.disabled=false; }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true}); else mount();
})();
