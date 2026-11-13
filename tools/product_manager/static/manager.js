let products=[], colors=[], siteSettings=null, currentSlug=null, slugLocked=false, listFilter='all', draggedSlug=null;
const $=id=>document.getElementById(id);
const fields=['name','slug','category','price_text','price_value','sale_price_value','card_description','description','options','features','tags','production_note','sort_order','seo_title','seo_description'];
const toast=(msg,error=false)=>{const t=$('toast');t.textContent=msg;t.className='toast'+(error?' error':'');t.hidden=false;clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.hidden=true,4200)};
const splitLines=v=>(v||'').split(/\n+/).map(x=>x.trim()).filter(Boolean);
const esc=s=>String(s??'').replace(/[&<>'"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
function slugify(s){return (s||'').toLocaleLowerCase('tr-TR').replaceAll('ç','c').replaceAll('ğ','g').replaceAll('ı','i').replaceAll('ö','o').replaceAll('ş','s').replaceAll('ü','u').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,80)}
const PANEL_VERSION=(document.querySelector('.brand-copy em')?.textContent||'').replace(/^v/i,'').trim();
async function api(path,opts={}){
  let r;
  try{r=await fetch(path,{headers:{'Content-Type':'application/json'},cache:'no-store',...opts})}
  catch(_){throw new Error('Panel servisiyle bağlantı kesildi. “Paneli kapat” ile kapatıp Ürün Yöneticisi’ni yeniden aç.')}
  const text=await r.text();
  let d={};
  try{d=text?JSON.parse(text):{}}catch(_){throw new Error(`Panel beklenmeyen yanıt verdi (${r.status}). Paneli kapatıp yeniden aç.`)}
  if(!r.ok||d.ok===false)throw new Error(d.error||`İşlem başarısız (${r.status})`);
  return d
}
async function load(){
  const status=await api('/api/status');
  if(PANEL_VERSION&&status.version!==PANEL_VERSION)throw new Error(`Panel sürümleri eşleşmiyor (arayüz ${PANEL_VERSION}, sunucu ${status.version||'bilinmiyor'}). Paneli tamamen kapatıp Ürün Yöneticisi kısayolunu yeniden aç.`);
  const d=await api('/api/products');products=d.products;colors=d.colors||[];const vault=d.storage?.app_home||status.storage?.app_home||'';$('repoPath').textContent='Repo: '+d.root+(vault?' · Kalıcı veri: '+vault:'');renderList();resetForm()
}
function stats(){$('countAll').textContent=products.length;$('countLive').textContent=products.filter(p=>p.active!==false).length;$('countFeatured').textContent=products.filter(p=>p.active!==false&&p.featured).length}
function categoryLabel(k){return {'dekoratif-duvar':'Dekoratif & Duvar',aydinlatma:'Aydınlatma','ev-duzen':'Ev & Düzen','gaming-masaustu':'Gaming & Masaüstü','anahtarlik-aksesuar':'Anahtarlık & Aksesuar','hediye-kisiye-ozel':'Hediye & Kişiye Özel','pratik-fonksiyonel':'Pratik & Fonksiyonel','pet-urunleri':'Pet Ürünleri','taki-makyaj':'Takı & Makyaj','oyun-oyuncak':'Oyun & Oyuncak',dekoratif:'Dekoratif & Duvar',fonksiyonel:'Pratik & Fonksiyonel','kisiye-ozel':'Hediye & Kişiye Özel',pet:'Pet Ürünleri'}[k]||k}
function parsePriceInput(value){let s=String(value??'').trim().toUpperCase().replaceAll('TL','').replaceAll('₺','').replace(/\s+/g,'');if(!s||!/^[0-9.,]+$/.test(s))return NaN;if(s.includes('.')&&s.includes(',')){if(s.lastIndexOf(',')>s.lastIndexOf('.'))s=s.replaceAll('.','').replace(',','.');else s=s.replaceAll(',','')}else if(s.includes('.')){if(/^\d{1,3}(?:\.\d{3})+$/.test(s))s=s.replaceAll('.','')}else if(s.includes(',')){if(/^\d{1,3}(?:,\d{3})+$/.test(s))s=s.replaceAll(',','');else s=s.replace(',','.')}return Number(s)}
function formatTL(value){const n=parsePriceInput(value);return Number.isFinite(n)?new Intl.NumberFormat('tr-TR',{maximumFractionDigits:2}).format(n)+' TL':''}
function discountState(p={}){const base=parsePriceInput(p.price_value),sale=parsePriceInput(p.sale_price_value);const active=Number.isFinite(base)&&base>0&&Number.isFinite(sale)&&sale>0&&sale<base;return {base,sale,active,percent:active?Math.max(1,Math.round((1-sale/base)*100)):0}}
function formDiscountState(){return discountState({price_value:$('price_value').value,sale_price_value:$('sale_price_value').value})}
function updateDiscountHint(){const el=$('discountPriceHint');if(!el)return;const baseRaw=$('price_value').value.trim(),saleRaw=$('sale_price_value').value.trim();const s=formDiscountState();el.className='discount-price-hint'+(s.active?' active':saleRaw?' invalid':'');if(s.active)el.textContent=`%${s.percent} indirim · ${formatTL(s.base)} → ${formatTL(s.sale)}`;else if(saleRaw&&!baseRaw)el.textContent='Önce normal sayısal fiyatı gir.';else if(saleRaw)el.textContent='İndirimli fiyat normal fiyattan düşük olmalı.';else el.textContent='İndirim yok.'}
function colorById(id){return colors.find(c=>c.id===id)}
function colorIdsForProduct(p){
  const explicit=(p?.color_ids||[]).filter(id=>colorById(id));
  if(explicit.length)return explicit;
  const byName=new Map(colors.map(c=>[String(c.name||'').trim().toLocaleLowerCase('tr-TR'),c.id]));
  return (p?.options||[]).map(x=>byName.get(String(x).trim().toLocaleLowerCase('tr-TR'))).filter(Boolean);
}
function legacyOptionsForProduct(p){
  const opts=[...(p?.options||[])];
  if((p?.color_ids||[]).length)return opts;
  const names=new Set(colors.map(c=>String(c.name||'').trim().toLocaleLowerCase('tr-TR')));
  return opts.filter(x=>!names.has(String(x).trim().toLocaleLowerCase('tr-TR')));
}
function selectedProductColorIds(){return [...document.querySelectorAll('#productColorChoices input[type="checkbox"]:checked')].map(x=>x.value)}
function renderProductColors(selected=[]){
  const wrap=$('productColorChoices');if(!wrap)return;
  const chosen=new Set(selected||[]);wrap.innerHTML='';
  if(!colors.length){wrap.innerHTML='<div class="color-empty">Henüz renk stoğu yok. “Renk stoğunu düzenle” ile ilk renklerini ekle.</div>';return}
  colors.forEach(c=>{
    const label=document.createElement('label');label.className='product-color-card'+(c.in_stock?'':' out-of-stock');
    const stockText=c.in_stock?(c.stock_qty==null?'Stokta':`${c.stock_qty} adet stok`):'Stok dışı';
    label.innerHTML=`<input type="checkbox" value="${esc(c.id)}" ${chosen.has(c.id)?'checked':''}><i style="--swatch:${esc(c.hex||'#c7b9a6')}"></i><span><strong>${esc(c.name)}</strong><small>${esc(stockText)}</small></span>`;
    label.querySelector('input').addEventListener('change',updateQuality);wrap.append(label)
  })
}
function colorInventoryRow(item={}){
  const row=document.createElement('div');row.className='color-inventory-row';
  const hex=/^#[0-9a-fA-F]{6}$/.test(item.hex||'')?item.hex:'#c7b9a6';
  row.innerHTML=`<input class="color-name" maxlength="60" placeholder="Renk adı" aria-label="Renk adı" value="${esc(item.name||'')}"><input class="color-picker" type="color" aria-label="Renk tonu seç" title="Renk tonu seç" value="${esc(hex)}"><input class="color-hex" maxlength="7" aria-label="Renk kodu (HEX)" title="Renk kodu (HEX)" value="${esc(hex)}"><label class="color-stock-toggle"><input class="color-stock" type="checkbox" ${item.in_stock!==false?'checked':''}><span>Stokta</span></label><input class="color-qty" type="number" min="0" step="1" placeholder="Adet ∞" value="${item.stock_qty??''}" aria-label="Stok adedi (boş bırakılırsa sınırsız)" title="Stok adedi · boş = sınırsız"><button class="tier-remove color-remove" type="button" aria-label="Bu rengi listeden kaldır" title="Rengi kaldır">×</button>`;
  const picker=row.querySelector('.color-picker'),hexInput=row.querySelector('.color-hex');picker.addEventListener('input',()=>hexInput.value=picker.value);hexInput.addEventListener('input',()=>{if(/^#[0-9a-fA-F]{6}$/.test(hexInput.value))picker.value=hexInput.value});row.querySelector('.color-remove').onclick=()=>row.remove();return row
}
function renderColorInventory(){const wrap=$('colorInventoryList');wrap.innerHTML='';colors.forEach(c=>wrap.append(colorInventoryRow(c)));if(!wrap.children.length)wrap.append(colorInventoryRow({in_stock:true}))}
function collectColors(){return [...$('colorInventoryList').querySelectorAll('.color-inventory-row')].map((row,i)=>({id:slugify(row.querySelector('.color-name').value),name:row.querySelector('.color-name').value.trim(),hex:row.querySelector('.color-hex').value.trim(),in_stock:row.querySelector('.color-stock').checked,stock_qty:row.querySelector('.color-qty').value===''?null:Number(row.querySelector('.color-qty').value),sort_order:(i+1)*10})).filter(x=>x.name)}
function openColorsModal(){renderColorInventory();$('colorsModal').hidden=false;document.body.classList.add('modal-open')}
const PRICING_NOTE_PRESETS=['Tekli Fiyat','Avantajlı Fiyat','Set Fiyatı'];
function packageSuffixForQuantity(qty){
  const n=Math.abs(Number(qty)||0);
  if(!Number.isInteger(n)||n<2)return 'li';
  const last=n%10, lastTwo=n%100;
  if(lastTwo===0)return 'lü';
  if(last===0)return ({10:'lu',20:'li',30:'lu',40:'lı',50:'li',60:'lı',70:'li',80:'li',90:'lı'}[lastTwo]||'li');
  return ({1:'li',2:'li',3:'lü',4:'lü',5:'li',6:'lı',7:'li',8:'li',9:'lu'}[last]||'li')
}
function packageLabelForQuantity(qty){
  const n=Number(qty);
  if(!Number.isInteger(n)||n<1)return '';
  if(n===1)return 'Tekli';
  return `${n}’${packageSuffixForQuantity(n)} alım`
}
function quantityFromPackageLabel(label){
  if(String(label||'').trim().toLocaleLowerCase('tr-TR')==='tekli')return 1;
  const m=String(label||'').match(/^(\d+)/);
  return m?Number(m[1]):null
}
function defaultPricingNote(qty){
  const n=Number(qty);
  if(n===1)return 'Tekli Fiyat';
  if(n>=4)return 'Set Fiyatı';
  return 'Avantajlı Fiyat'
}
function pricingPackageOptions(current='',qty=''){
  const values=[1,2,3,4,5,6,7,8,9,10].map(packageLabelForQuantity);
  const automatic=packageLabelForQuantity(Number(qty));
  if(automatic&&!values.includes(automatic))values.push(automatic);
  if(current&&!values.includes(current))values.push(current);
  return '<option value="">Paket seç</option>'+values.map(v=>`<option value="${esc(v)}" ${v===current?'selected':''}>${esc(v)}</option>`).join('')
}
function pricingNoteOptions(current=''){
  const values=[...PRICING_NOTE_PRESETS];
  if(current&&!values.includes(current))values.push(current);
  return values.map(v=>`<option value="${esc(v)}" ${v===current?'selected':''}>${esc(v)}</option>`).join('')
}
function ensurePackageOption(select,value){
  if(!value)return;
  if(![...select.options].some(o=>o.value===value)){const option=document.createElement('option');option.value=value;option.textContent=value;select.append(option)}
}
function pricingTierRow(item={}){
  const row=document.createElement('div');row.className='pricing-tier-row';
  const initialQty=Number(item.quantity)||'';
  const initialLabel=item.label||packageLabelForQuantity(initialQty);
  const initialNote=item.note||defaultPricingNote(initialQty);
  row.innerHTML=`<label><span>Paket adı</span><select class="tier-label" title="Hazır paket adları">${pricingPackageOptions(initialLabel,initialQty)}</select></label><label><span>Ürün adedi</span><input class="tier-qty" type="number" min="1" max="999" inputmode="numeric" placeholder="2" value="${esc(initialQty)}"></label><label><span>Set fiyatı (TL)</span><input class="tier-price" inputmode="decimal" placeholder="499" value="${esc(item.price_value||'')}"></label><label><span>Kısa not</span><select class="tier-note" title="Hazır fiyat açıklamaları">${pricingNoteOptions(initialNote)}</select></label><button class="tier-remove" type="button" title="Fiyat seçeneğini kaldır">×</button>`;
  const label=row.querySelector('.tier-label'),qty=row.querySelector('.tier-qty'),note=row.querySelector('.tier-note');
  const syncFromQty=()=>{
    const n=Number(qty.value);
    const autoLabel=packageLabelForQuantity(n);
    if(autoLabel){ensurePackageOption(label,autoLabel);label.value=autoLabel}
    if(Number.isInteger(n)&&n>0)note.value=defaultPricingNote(n);
    updatePricingEmpty();updateQuality()
  };
  const syncFromLabel=()=>{
    const n=quantityFromPackageLabel(label.value);
    if(n){qty.value=String(n);note.value=defaultPricingNote(n)}
    updatePricingEmpty();updateQuality()
  };
  qty.addEventListener('input',syncFromQty);
  label.addEventListener('change',syncFromLabel);
  note.addEventListener('change',()=>{updatePricingEmpty();updateQuality()});
  row.querySelector('.tier-price').addEventListener('input',()=>{updatePricingEmpty();updateQuality()});
  row.querySelector('.tier-remove').onclick=()=>{row.remove();updatePricingEmpty();updateQuality()};
  return row
}
function updatePricingEmpty(){const wrap=$('pricingTiers');if(!wrap)return;const empty=wrap.querySelector('.pricing-empty');if(empty)empty.remove();if(!wrap.querySelector('.pricing-tier-row')){const note=document.createElement('div');note.className='pricing-empty';note.textContent='Set fiyatı yok. Normal ürünlerde bu alanı boş bırakabilirsin.';wrap.append(note)}}
function renderPricingTiers(items=[]){const wrap=$('pricingTiers');if(!wrap)return;wrap.innerHTML='';(items||[]).forEach(item=>wrap.append(pricingTierRow(item)));updatePricingEmpty()}
function effectivePreviewTiers(){let items=collectPricingTiers().filter(t=>+t.quantity>1);const ds=formDiscountState();const base=ds.active?ds.sale:parsePriceInput($('price_value').value);if(Number.isFinite(base)&&base>0)items=[{label:'Tekli',quantity:1,price_value:String(base),note:ds.active?'İndirimli Tekli Fiyat':'Tekli fiyat',_auto:true},...items];return items.sort((a,b)=>a.quantity-b.quantity)}
function collectPricingTiers(){const rows=[...$('pricingTiers').querySelectorAll('.pricing-tier-row')];const items=[];const used=new Set();rows.forEach((row,i)=>{const qty=Number(row.querySelector('.tier-qty').value);const raw=row.querySelector('.tier-price').value.trim();const price=parsePriceInput(raw);let label=row.querySelector('.tier-label').value.trim();let note=row.querySelector('.tier-note').value.trim();if(!qty&&!raw&&!label&&!note)return;if(!Number.isInteger(qty)||qty<1)throw new Error(`${i+1}. set fiyatında ürün adedi geçersiz.`);if(!Number.isFinite(price)||price<=0)throw new Error(`${i+1}. set fiyatında fiyat geçersiz.`);if(used.has(qty))throw new Error(`${qty} adet için iki ayrı set fiyatı tanımlanamaz.`);used.add(qty);label=packageLabelForQuantity(qty);note=note||defaultPricingNote(qty);items.push({label,quantity:qty,price_value:String(price),note})});return items.sort((a,b)=>a.quantity-b.quantity)}
function pricingIssues(){const issues=[];try{collectPricingTiers()}catch(e){issues.push(e.message)}const saleRaw=$('sale_price_value').value.trim();if(saleRaw&&!formDiscountState().active)issues.push('İndirimli fiyat normal sayısal fiyattan düşük olmalı');return issues}
$('addPricingTier').onclick=()=>{const wrap=$('pricingTiers');wrap.querySelector('.pricing-empty')?.remove();wrap.append(pricingTierRow({}));wrap.lastElementChild.querySelector('.tier-qty')?.focus()};
function sortedProducts(){return [...products].sort((a,b)=>(+a.sort_order||9999)-(+b.sort_order||9999)||a.name.localeCompare(b.name,'tr'))}
function featuredRank(p){const n=parseInt(p.featured_order,10);return Number.isFinite(n)?[0,n,0]:[1,0,+p.sort_order||9999]}
function featuredSorted(list){return [...list].sort((a,b)=>{const x=featuredRank(a),y=featuredRank(b);return x[0]-y[0]||x[1]-y[1]||x[2]-y[2]})}
function filteredProducts(){const q=$('search').value.trim().toLocaleLowerCase('tr-TR');const base=listFilter==='featured'?featuredSorted(products):sortedProducts();return base.filter(p=>{const text=(p.name+' '+p.slug+' '+(p.price_text||'')+' '+categoryLabel(p.category)+' '+(p.tags||[]).join(' ')).toLocaleLowerCase('tr-TR');const qok=!q||text.includes(q);const fok=listFilter==='all'||(listFilter==='live'&&p.active!==false)||(listFilter==='draft'&&p.active===false)||(listFilter==='featured'&&p.active!==false&&p.featured);return qok&&fok})}
function renderList(){stats();const wrap=$('productList');wrap.innerHTML='';const canDrag=(listFilter==='all'||listFilter==='featured')&&!$('search').value.trim();$('dragNote').textContent=!canDrag?'Sürükle-bırak için “Tümü” veya “Öne çıkan” filtresinde aramayı temizle.':listFilter==='featured'?'Öne çıkanların ana sayfadaki sırasını sürükleyerek değiştir. İlk 3 ürün en üstte görünür; katalog sırası değişmez.':'Katalog sırasını değiştirmek için ürünleri sürükle.';filteredProducts().forEach(p=>{const row=document.createElement('div');row.className='product-item'+(p.slug===currentSlug?' active':'');row.dataset.slug=p.slug;row.draggable=canDrag;const live=p.active!==false;row.innerHTML=`<span class="drag-handle" title="Sürükle">⋮⋮</span><button class="product-main" type="button"><img src="/${esc(p.main_image)}" alt="" loading="lazy" onerror="this.style.visibility='hidden'"><span class="product-text"><strong>${esc(p.name)}</strong><small>${esc(discountState(p).active?`${p.price_text||formatTL(p.price_value)} → ${formatTL(p.sale_price_value)}`:p.price_text)} · ${esc(categoryLabel(p.category))}</small></span></button><div class="product-flags"><button class="feature-toggle ${p.featured?'on':''}" type="button" title="★ Öne çıkan ürün">★</button><span class="status-dot ${live?'live':'draft'}" title="${live?'Yayında':'Arşivde'}"></span></div>`;row.querySelector('.product-main').onclick=()=>{if(p.slug===currentSlug||confirmDiscardChanges())editProduct(p.slug)};row.querySelector('.feature-toggle').onclick=async e=>{e.stopPropagation();const btn=e.currentTarget;const prev={featured:!!p.featured,active:p.active};p.featured=!prev.featured;if(p.featured)p.active=true;btn.classList.toggle('on',p.featured);btn.disabled=true;stats();if(p.slug===currentSlug){$('featured').checked=p.featured;if(p.featured)$('active').checked=true}try{const d=await api('/api/feature',{method:'POST',body:JSON.stringify({slug:p.slug})});Object.assign(p,{featured:!!d.product.featured,active:d.product.active});toast('✅ '+(p.featured?'Öne çıkanlara eklendi':'Öne çıkanlardan çıkarıldı'));watchBuild(d.build)}catch(err){Object.assign(p,prev);toast(err.message,true)}finally{btn.disabled=false;renderList();if(p.slug===currentSlug){$('featured').checked=!!p.featured;$('active').checked=p.active!==false}}};if(canDrag){row.addEventListener('dragstart',()=>{draggedSlug=p.slug;row.classList.add('dragging')});row.addEventListener('dragend',()=>{draggedSlug=null;row.classList.remove('dragging')});row.addEventListener('dragover',e=>{e.preventDefault();row.classList.add('drag-over')});row.addEventListener('dragleave',()=>row.classList.remove('drag-over'));row.addEventListener('drop',async e=>{e.preventDefault();row.classList.remove('drag-over');if(!draggedSlug||draggedSlug===p.slug)return;const isFeat=listFilter==='featured';const order=(isFeat?featuredSorted(products.filter(x=>x.featured)):sortedProducts()).map(x=>x.slug);const from=order.indexOf(draggedSlug),to=order.indexOf(p.slug);if(from<0||to<0)return;order.splice(from,1);order.splice(to,0,draggedSlug);try{const d=await api(isFeat?'/api/featured-reorder':'/api/reorder',{method:'POST',body:JSON.stringify({order})});products=d.products;toast('✅ '+d.message);watchBuild(d.build);if(currentSlug&&formDirty){syncLiveFieldsFromRecord();renderList()}else{renderList();if(currentSlug)editProduct(currentSlug)}}catch(err){toast(err.message,true)}})}wrap.append(row)})}
function resetForm(){currentSlug=null;slugLocked=false;$('form').reset();$('active').checked=true;$('sort_order').value=(Math.max(0,...products.map(p=>+p.sort_order||0))+1);$('formTitle').textContent='Yeni ürün';$('slug').disabled=false;setDefaultNote();clearPreviews();renderPricingTiers([]);renderProductColors([]);syncTagPresetState();setActionState(null);renderList();updateDiscountHint();updateQuality();updateSeoMeter()}
function setDefaultNote(){if(!$('production_note').value)$('production_note').value='3D baskı ürünlerde katman dokusu üretim yönteminin doğal bir parçasıdır. Renk, adet ve kişiselleştirme seçenekleri sipariş öncesi netleştirilir.'}
function setActionState(p){$('duplicateProduct').hidden=!p;$('archiveProduct').hidden=!p;$('deleteProduct').hidden=!p;if(p)$('archiveProduct').textContent=p.active===false?'Yayına al':'Arşivle'}
function editProduct(slug){const p=products.find(x=>x.slug===slug);if(!p)return;currentSlug=slug;slugLocked=true;$('formTitle').textContent=p.name;fields.forEach(id=>{const el=$(id);if(id==='features'||id==='tags')el.value=(p[id]||[]).join('\n');else if(id==='options')el.value=legacyOptionsForProduct(p).join('\n');else el.value=p[id]??''});renderProductColors(colorIdsForProduct(p));syncTagPresetState();$('active').checked=p.active!==false;$('featured').checked=!!p.featured;$('slug').disabled=true;loadSlotsFromProduct(p);renderPricingTiers(p.pricing_tiers||[]);setActionState(p);renderList();updateDiscountHint();updateQuality();updateSeoMeter();window.scrollTo({top:0,behavior:'smooth'})}
function showExistingPreview(imgId,placeId,path){const i=$(imgId);i.src='/'+path;i.hidden=false;$(placeId).hidden=true}
function clearOne(imgId,placeId,text){const i=$(imgId);i.removeAttribute('src');i.hidden=true;const p=$(placeId);p.hidden=false;p.textContent=text}
function clearPreviews(){loadSlotsFromProduct(null)}
// v3.3.39 — tek tip ürün görselleri: en fazla 5 slot, hepsi 1000×760. 1. slot kapaktır (ürün kartı, katalog, Google);
// tek görsel yüklenirse ürün sayfası tek fotoğraf gösterir, 2–5 görselde küçük resim şeridi çıkar. Afiş/galeri ayrımı yok.
const IMG_W=1000,IMG_H=760,MAX_SLOTS=5;
var imageSlots=[];
let slotReplaceIndex=-1;
function currentProductRecord(){return currentSlug?products.find(x=>x.slug===currentSlug):null}
function slotSrc(s){return s.file?s.url:'/'+s.path}
function productSlotsFromRecord(p){const out=[];const seen=new Set();const add=(path,w,h)=>{if(!path||seen.has(path))return;seen.add(path);out.push({path,width:+w||IMG_W,height:+h||IMG_H})};if(!p)return out;add(p.main_image,p.main_image_width,p.main_image_height);if(p.poster_image)add(p.poster_image,p.poster_image_width||1254,p.poster_image_height||1254);(p.gallery_images||[]).forEach(it=>typeof it==='string'?add(it,1000,1000):add(it?.path,it?.width,it?.height));return out}
function loadSlotsFromProduct(p){imageSlots.forEach(s=>s.url&&URL.revokeObjectURL(s.url));imageSlots=productSlotsFromRecord(p).slice(0,MAX_SLOTS);renderSlots()}
function slotMarkup(s,i){const total=imageSlots.length;const legacy=!s.file&&!ratioMatches(s.width,s.height,IMG_W,IMG_H);const crop=s.file&&s.ratioOk===false;return `<div class="img-slot filled${i===0?' is-cover':''}${s.file?' is-new':''}" data-i="${i}"><img src="${esc(slotSrc(s))}" alt="${i+1}. ürün görseli"><span class="slot-badge">${i===0?'1 · Kapak':i+1}</span>${s.file?'<span class="slot-flag">Yeni</span>':''}${legacy?`<span class="slot-flag warn" title="Eski görsel ${s.width}×${s.height}. Değiştir ile yeniden yüklersen 1000×760 olur.">Eski ölçü</span>`:crop?'<span class="slot-flag warn" title="Oran farklı; merkezden kırpılacak">Kırpılacak</span>':''}<div class="slot-actions">${i>0?`<button type="button" data-act="left" title="Sola taşı" aria-label="${i+1}. görseli sola taşı">‹</button>`:''}${i<total-1?`<button type="button" data-act="right" title="Sağa taşı" aria-label="${i+1}. görseli sağa taşı">›</button>`:''}${i>0?'<button type="button" data-act="cover" title="Bu görseli kapak yap">Kapak yap</button>':''}<button type="button" data-act="replace" title="Bu görseli değiştir">Değiştir</button><button type="button" data-act="remove" class="slot-remove" title="Görseli kaldır" aria-label="${i+1}. görseli kaldır">×</button></div></div>`}
function renderSlots(){const wrap=$('imageSlots');if(!wrap)return;let html=imageSlots.map(slotMarkup).join('');for(let i=imageSlots.length;i<MAX_SLOTS;i++){const first=i===imageSlots.length;html+=`<button type="button" class="img-slot empty${first?' is-next':''}" data-act="add"${first?'':' tabindex="-1"'}><span>${i===0?'+ Kapak görseli ekle':'+ Görsel ekle'}</span><small>${i===0?'Zorunlu · 1000×760':`${i+1}. görsel · isteğe bağlı`}</small></button>`}wrap.innerHTML=html;updateSlotStatus()}
function updateSlotStatus(){const st=$('images_status');if(!st)return;const before=productSlotsFromRecord(currentProductRecord()).map(s=>s.path);const keptPaths=new Set(imageSlots.filter(s=>!s.file).map(s=>s.path));const removed=before.filter(x=>!keptPaths.has(x)).length;const added=imageSlots.filter(s=>s.file).length;const crop=imageSlots.filter(s=>s.file&&s.ratioOk===false).length;const parts=[`${imageSlots.length}/${MAX_SLOTS} görsel`];if(imageSlots.length===1)parts.push('ürün sayfasında tek fotoğraf gösterilir');if(added)parts.push(`${added} yeni görsel kaydedince 1000×760 WebP olacak`);if(crop)parts.push(`${crop} görselin oranı farklı, merkezden kırpılacak`);if(removed)parts.push(`${removed} görsel kaydedince silinecek`);if(!imageSlots.length)parts.push('kapak görseli zorunlu');st.textContent=parts.join(' · ');st.className='image-spec-status'+((!imageSlots.length||crop||removed)?' warn':added?' ok':'')}
async function newSlot(file){const s={file,url:URL.createObjectURL(file),ratioOk:true};try{const d=await fileDimensions(file);s.ratioOk=ratioMatches(d.w,d.h,IMG_W,IMG_H)}catch(_){}return s}
async function addSlotFiles(files,replaceAt=-1){const list=[...files].filter(f=>f&&(!f.type||f.type.startsWith('image/')));if(!list.length)return;if(replaceAt>=0){const old=imageSlots[replaceAt];if(old?.url)URL.revokeObjectURL(old.url);imageSlots[replaceAt]=await newSlot(list[0])}else{const room=MAX_SLOTS-imageSlots.length;if(room<=0){toast(`En fazla ${MAX_SLOTS} görsel eklenebilir. Önce bir görseli kaldır ya da “Değiştir” kullan.`,true);return}if(list.length>room)toast(`En fazla ${MAX_SLOTS} görsel: ${list.length-room} dosya eklenmedi.`,true);for(const f of list.slice(0,room))imageSlots.push(await newSlot(f))}markFormDirty();renderSlots();updateQuality()}
function slotAction(act,i){if(act==='add'){slotReplaceIndex=-1;$('slotFiles').click();return}if(act==='replace'){slotReplaceIndex=i;$('slotReplace').click();return}if(act==='remove'){if(imageSlots.length===1){toast('Kapak görseli zorunlu. Önce “+ Görsel ekle” ile yeni görsel ekle ya da “Değiştir” kullan.',true);return}const [gone]=imageSlots.splice(i,1);if(gone?.url)URL.revokeObjectURL(gone.url);if(i===0)toast('Kapak kaldırıldı; 2. görsel artık kapak.')}else if(act==='cover'){const [s]=imageSlots.splice(i,1);imageSlots.unshift(s)}else if(act==='left'&&i>0){[imageSlots[i-1],imageSlots[i]]=[imageSlots[i],imageSlots[i-1]]}else if(act==='right'&&i<imageSlots.length-1){[imageSlots[i+1],imageSlots[i]]=[imageSlots[i],imageSlots[i+1]]}else return;markFormDirty();renderSlots();updateQuality()}
$('imageSlots')?.addEventListener('click',e=>{const b=e.target.closest('[data-act]');if(!b)return;e.preventDefault();e.stopPropagation();const slot=b.closest('.img-slot');slotAction(b.dataset.act,slot?.dataset.i!=null?+slot.dataset.i:-1)});
$('slotFiles')?.addEventListener('change',async e=>{const files=[...e.target.files];e.target.value='';await addSlotFiles(files)});
$('slotReplace')?.addEventListener('change',async e=>{const files=[...e.target.files];e.target.value='';if(slotReplaceIndex>=0)await addSlotFiles(files,slotReplaceIndex);slotReplaceIndex=-1});
{const zone=$('imageSlots');if(zone){['dragenter','dragover'].forEach(t=>zone.addEventListener(t,e=>{if(![...(e.dataTransfer?.types||[])].includes('Files'))return;e.preventDefault();zone.classList.add('drop-hover')}));['dragleave','drop'].forEach(t=>zone.addEventListener(t,()=>zone.classList.remove('drop-hover')));zone.addEventListener('drop',async e=>{if(!e.dataTransfer?.files?.length)return;e.preventDefault();const target=e.target.closest('.img-slot.filled');await addSlotFiles(e.dataTransfer.files,target&&e.dataTransfer.files.length===1?+target.dataset.i:-1)})}}
async function collectSlotImages(){const out=[];for(const s of imageSlots){if(s.file){const c=await convertImage(s.file,IMG_W,IMG_H,.90,320);out.push({data:c.data,width:IMG_W,height:IMG_H})}else out.push({keep:s.path})}return out}
$('name').addEventListener('input',()=>{if(!slugLocked)$('slug').value=slugify($('name').value)});$('search').addEventListener('input',renderList);$('newProduct').onclick=resetForm;
['price_text','price_value','sale_price_value'].forEach(id=>$(id)?.addEventListener('input',()=>{updateDiscountHint();updateQuality()}));
$('listFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;listFilter=b.dataset.filter;[...$('listFilters').querySelectorAll('button')].forEach(x=>x.classList.toggle('active',x===b));renderList()});
function clipSeoText(text,max=160){text=(text||'').replace(/\s+/g,' ').trim();if(text.length<=max)return text;let clipped=text.slice(0,max+1);const lastSpace=clipped.lastIndexOf(' ');if(lastSpace>0)clipped=clipped.slice(0,lastSpace);return clipped.replace(/[,:;.!?\-–—]+$/g,'')+'.'}
function escapeRegExp(text){return text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
function buildSeoValues(){const name=$('name').value.trim();if(!name)return{title:'',description:''};let source=$('card_description').value.trim()||$('description').value.trim();if(source){const productNameRegex=new RegExp('^'+escapeRegExp(name)+'\\s*[-—–:,.]*\\s*','i');source=source.replace(productNameRegex,'').replace(/\s+/g,' ').replace(/[.!?]+$/g,'').trim()}const full=`${name} | 3D Baskı | BG Studio 3D`;const title=full.length<=60?full:`${name} | BG Studio 3D`;const suffix='3D baskı ile üretilir, Türkiye geneli kargo.';const lead=source?(source.toLocaleLowerCase('tr-TR').includes(name.toLocaleLowerCase('tr-TR'))?`${source}.`:`${name}: ${source}.`):`${name}:`;const description=`${lead} ${suffix}`;return{title,description:clipSeoText(description,160)}}
function autoSeo(){const seo=buildSeoValues();$('seo_title').value=seo.title;$('seo_description').value=seo.description;updateSeoMeter();updateQuality()}$('autoSeo').onclick=autoSeo;
async function fileDimensions(file){if(!file)return null;const bmp=await createImageBitmap(file);const d={w:bmp.width,h:bmp.height};bmp.close();return d}
function ratioMatches(w,h,targetW,targetH,tolerance=.025){return Math.abs((w/h)-(targetW/targetH))/(targetW/targetH)<=tolerance}
function dimensionMessage(d,targetW,targetH,label=''){if(!d)return 'Henüz görsel seçilmedi.';const ok=ratioMatches(d.w,d.h,targetW,targetH);return `Seçilen: ${d.w}×${d.h} px · ${ok?'✓ Oran uygun':'⚠ Oran farklı; panel merkezden kırpacak'}${label?` · ${label}`:''}`}
async function previewFile(input,imgId,placeId,statusId,targetW,targetH){const f=input.files[0];if(!f)return;const u=URL.createObjectURL(f);const i=$(imgId);i.src=u;i.hidden=false;$(placeId).hidden=true;try{const d=await fileDimensions(f);const status=$(statusId);status.textContent=dimensionMessage(d,targetW,targetH);status.classList.toggle('ok',ratioMatches(d.w,d.h,targetW,targetH));status.classList.toggle('warn',!ratioMatches(d.w,d.h,targetW,targetH))}catch(_){ }updateQuality()}
async function blobToDataURL(blob){return await new Promise((res,rej)=>{const r=new FileReader;r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(blob)})}
async function optimizedWebPBlob(canvas,targetBytes,startQ=.90,minQ=.78){let quality=startQ,blob=null;while(quality>=minQ-.001){blob=await new Promise(res=>canvas.toBlob(res,'image/webp',quality));if(!blob)throw new Error('Görsel WebP formatına dönüştürülemedi.');if(blob.size<=targetBytes||quality<=minQ+.001)break;quality=Math.max(minQ,quality-.03)}return {blob,quality}}
async function convertImage(file,w,h,q=.90,targetKB=320){if(!file)return null;const bmp=await createImageBitmap(file);const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d',{alpha:false});x.fillStyle='#f5ede2';x.fillRect(0,0,w,h);const scale=Math.max(w/bmp.width,h/bmp.height);const dw=bmp.width*scale,dh=bmp.height*scale;x.imageSmoothingEnabled=true;x.imageSmoothingQuality='high';x.drawImage(bmp,(w-dw)/2,(h-dh)/2,dw,dh);const {blob,quality}=await optimizedWebPBlob(c,targetKB*1024,q,.78);const data=await blobToDataURL(blob);const originalSize=file.size||0;bmp.close();return {data,width:w,height:h,bytes:blob.size,original_bytes:originalSize,quality:Number(quality.toFixed(2))}}
function updateSeoMeter(){$('seoTitleCount').textContent=`${$('seo_title').value.length}/70`;$('seoDescCount').textContent=`${$('seo_description').value.length}/160`}
function qualityIssues(){const issues=[];if(!$('name').value.trim())issues.push('Ürün adı');if(!$('price_text').value.trim())issues.push('Gösterilen fiyat');if(!$('card_description').value.trim())issues.push('Kart açıklaması');if(!$('description').value.trim())issues.push('Ürün açıklaması');if(!selectedProductColorIds().length&&!splitLines($('options').value).length)issues.push('Renk / seçenek');if(!splitLines($('features').value).length)issues.push('Öne çıkan özellik');if(!imageSlots.length)issues.push('Kapak görseli');if(!$('seo_title').value.trim()||!$('seo_description').value.trim())issues.push('SEO');if($('featured').checked&&!$('active').checked)issues.push('Öne çıkan ürün yayında olmalı');issues.push(...pricingIssues());return issues}
function updateQuality(){const issues=qualityIssues();const total=9;const good=total-issues.length;$('qualityState').textContent=issues.length?`${issues.length} eksik · ${good}/${total}`:`Hazır · ${total}/${total}`;$('qualityState').classList.toggle('good',!issues.length);const p=$('qualityPanel');p.hidden=!issues.length;p.innerHTML=issues.length?`<strong>Kaydetmeden önce göz at:</strong> ${issues.map(esc).join(' · ')}`:''}
[...$('form').querySelectorAll('input,textarea,select')].forEach(el=>{el.addEventListener('input',()=>{updateQuality();updateSeoMeter()});el.addEventListener('change',()=>{updateQuality();updateSeoMeter()})});$('featured').addEventListener('change',()=>{if($('featured').checked)$('active').checked=true;updateQuality()});
function buildPreview(){const img=imageSlots[0]?new URL(slotSrc(imageSlots[0]),location.href).href:'';$('pvImage').src=img;$('pvName').textContent=$('name').value.trim()||'Ürün adı';$('pvCategory').textContent=categoryLabel($('category').value).toLocaleUpperCase('tr-TR');$('pvDescription').textContent=$('description').value.trim()||$('card_description').value.trim()||'Ürün açıklaması burada görünecek.';const ds=formDiscountState();$('pvPrice').innerHTML=ds.active?`<del>${esc($('price_text').value.trim()||formatTL(ds.base))}</del><b>${esc(formatTL(ds.sale))}</b><em>%${ds.percent} İNDİRİM</em>`:esc($('price_text').value.trim()||'Fiyat için iletişim');let pvTiers=[];try{pvTiers=effectivePreviewTiers()}catch(_){};$('pvPricing').innerHTML=pvTiers.map(t=>`<span><b>${esc(t.label)}</b>${esc(formatTL(t.price_value))}${t.note?`<small>${esc(t.note)}</small>`:''}</span>`).join('');$('pvTags').innerHTML=[...selectedProductColorIds().map(id=>{const c=colorById(id);return c?`<span class="pv-color"><i style="--swatch:${esc(c.hex)}"></i>${esc(c.name)}</span>`:''}),...splitLines($('options').value).slice(0,8).map(x=>`<span>${esc(x)}</span>`),...splitLines($('tags').value).slice(0,8).map(x=>`<span>${esc(x)}</span>`)].join('');$('previewModal').hidden=false;document.body.classList.add('modal-open')}
$('previewProduct').onclick=buildPreview;document.addEventListener('click',e=>{if(e.target.matches('[data-close-preview]')){$('previewModal').hidden=true;document.body.classList.remove('modal-open')}});document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('previewModal').hidden=true;document.body.classList.remove('modal-open')}});
$('duplicateProduct').onclick=async()=>{if(!currentSlug)return;if(!confirm('Bu ürünü kopyalayıp arşivde yeni bir ürün olarak oluşturayım mı?'))return;try{const d=await api('/api/duplicate',{method:'POST',body:JSON.stringify({slug:currentSlug})});toast('✅ '+d.message);await refreshProducts(d.product.slug)}catch(err){toast(err.message,true)}};
$('archiveProduct').onclick=async()=>{if(!currentSlug)return;const p=products.find(x=>x.slug===currentSlug);const active=p?.active===false;if(!confirm(active?'Ürünü tekrar yayına alalım mı?':'Ürünü katalogdan arşive alalım mı?'))return;try{const d=await api('/api/archive',{method:'POST',body:JSON.stringify({slug:currentSlug,active})});toast('✅ '+d.message);watchBuild(d.build);await refreshProducts(currentSlug)}catch(err){toast(err.message,true)}};
$('deleteProduct').onclick=async()=>{if(!currentSlug)return;const p=products.find(x=>x.slug===currentSlug);const answer=prompt(`“${p.name}” kalıcı olarak silinecek. Ürün sayfası ve görselleri de kaldırılır. Devam etmek için SİL yaz:`);if(answer===null)return;if(answer.trim().toLocaleUpperCase('tr-TR')!=='SİL'&&answer.trim().toUpperCase()!=='SIL'){toast('Silme iptal edildi: onay için SİL yazmalısın.',true);return}formDirty=false;try{const d=await api('/api/delete',{method:'POST',body:JSON.stringify({slug:currentSlug})});toast('✅ '+d.message);const r=await api('/api/products');products=r.products;colors=r.colors||colors;resetForm()}catch(err){toast(err.message,true)}};
var saving=false;
$('form').addEventListener('submit',async e=>{e.preventDefault();if(saving)return;saving=true;const saveBtn=$('form').querySelector('button[type=submit]');if(saveBtn){saveBtn.disabled=true;saveBtn.dataset.label=saveBtn.dataset.label||saveBtn.textContent;saveBtn.textContent='Kaydediliyor…'}try{$('saveState').textContent='Hazırlanıyor…';if(!$('seo_title').value.trim()||!$('seo_description').value.trim())autoSeo();const product={};fields.forEach(id=>product[id]=$(id).value);product.options=splitLines($('options').value);product.color_ids=selectedProductColorIds();product.features=splitLines($('features').value);product.tags=splitLines($('tags').value).slice(0,16);product.pricing_tiers=collectPricingTiers();product.active=$('active').checked;product.featured=$('featured').checked;product.sort_order=+$('sort_order').value||999;if(!imageSlots.length)throw new Error('En az 1 ürün görseli (kapak) eklemelisin.');const panelStatus=await api('/api/status');if(!panelStatus.image_slots)throw new Error('Panel sunucusu eski sürümde çalışıyor; görsel değişiklikleri kaydedilemez. “Paneli kapat” ile kapatıp Ürün Yöneticisi’ni yeniden aç, sonra tekrar kaydet. Formdaki değişikliklerin duruyor.');$('saveState').textContent=imageSlots.some(x=>x.file)?'Görseller optimize ediliyor…':'Site hazırlanıyor…';const images=await collectSlotImages();const d=await api('/api/save',{method:'POST',body:JSON.stringify({original_slug:currentSlug,product,images})});toast('✅ '+d.message);formDirty=false;await refreshProducts(d.product.slug);$('saveState').textContent='Kaydedildi · GitHub Desktop’ta Commit + Push'}catch(err){$('saveState').textContent='Hata · değişikliklerin formda duruyor';toast(err.message,true)}finally{saving=false;if(saveBtn){saveBtn.disabled=false;saveBtn.textContent=saveBtn.dataset.label}}})
async function refreshProducts(slug){const d=await api('/api/products');products=d.products;colors=d.colors||colors;if(formDirty&&slug&&slug===currentSlug){syncLiveFieldsFromRecord();renderList();return}renderList();if(slug)editProduct(slug);else resetForm()}
// v3.3.37 — kaydedilmemiş değişiklik koruması: başka ürüne geçerken, yıldız/arşiv/sıralama sonrası ve sekmeyi kapatırken düzenlemeler sessizce kaybolmaz.
var formDirty=false;
function markFormDirty(){formDirty=true;const s=$('saveState');if(s&&!saving)s.textContent='Kaydedilmemiş değişiklik var'}
function confirmDiscardChanges(){if(!formDirty)return true;return confirm('Bu üründe kaydedilmemiş değişiklikler var. Kaydetmeden devam edersen kaybolacak. Devam edilsin mi?')}
function syncLiveFieldsFromRecord(){const p=currentProductRecord();if(!p)return;$('sort_order').value=p.sort_order??'';$('active').checked=p.active!==false;$('featured').checked=!!p.featured;setActionState(p)}
['input','change'].forEach(type=>$('form').addEventListener(type,e=>{if(e.isTrusted)markFormDirty()},true));
{const _editProduct=editProduct,_resetForm=resetForm;editProduct=function(...a){const r=_editProduct.apply(this,a);formDirty=false;return r};resetForm=function(...a){const r=_resetForm.apply(this,a);formDirty=false;return r}}
$('newProduct').onclick=()=>{if(confirmDiscardChanges())resetForm()};
window.addEventListener('beforeunload',e=>{if(formDirty){e.preventDefault();e.returnValue=''}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&!e.altKey&&e.key.toLowerCase()==='s'&&!$('form').closest('[hidden]')){e.preventDefault();$('form').requestSubmit()}});
$('rebuild').onclick=async()=>{try{$('saveState').textContent='Site oluşturuluyor…';const d=await api('/api/rebuild',{method:'POST',body:'{}'});$('saveState').textContent='Hazır';toast(`✅ Site hazır: ${d.result.active} aktif ürün`)}catch(e){toast(e.message,true)}};$('openSite').onclick=()=>window.open('https://3d.bgstudio.com.tr','_blank');$('shutdown').onclick=async()=>{try{await api('/api/shutdown',{method:'POST',body:'{}'});document.body.innerHTML='<div style="font:20px system-ui;padding:60px">BG Studio 3D Ürün Yöneticisi kapatıldı. Bu sekmeyi kapatabilirsin. 👋</div>'}catch{window.close()}};

// v2.4.1 — panel image lightbox. Main, poster and gallery previews open at full size.
const panelImageLightbox=(()=>{
  const box=document.createElement('div');
  box.className='panel-image-lightbox';
  box.hidden=true;
  box.innerHTML='<button type="button" aria-label="Görseli kapat">×</button><img alt="Ürün görseli">';
  document.body.appendChild(box);
  const image=box.querySelector('img');
  const close=()=>{box.classList.remove('open');box.hidden=true;document.body.classList.remove('modal-open')};
  const open=src=>{if(!src)return;image.src=src;box.hidden=false;requestAnimationFrame(()=>box.classList.add('open'));document.body.classList.add('modal-open')};
  box.querySelector('button').onclick=close;
  box.addEventListener('click',e=>{if(e.target===box)close()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!box.hidden)close()});
  document.addEventListener('click',e=>{
    const img=e.target.closest?.('.preview img:not([hidden]), .gallery-mini img, .img-slot img, .preview-product-image img');
    if(!img)return;
    e.preventDefault();e.stopPropagation();open(img.currentSrc||img.src)
  });
  return {open,close};
})();

$('manageColors').onclick=openColorsModal;$('manageColorsInline').onclick=openColorsModal;
$('addColor').onclick=()=>{$('colorInventoryList').append(colorInventoryRow({in_stock:true}));$('colorInventoryList').lastElementChild.querySelector('.color-name')?.focus()};
$('saveColors').onclick=async()=>{try{const selectedBefore=selectedProductColorIds();const d=await api('/api/colors/save',{method:'POST',body:JSON.stringify({colors:collectColors()})});colors=d.colors||[];renderProductColors(selectedBefore.filter(id=>colorById(id)));$('colorsModal').hidden=true;document.body.classList.remove('modal-open');syncTagPresetState();updateQuality();toast('✅ '+d.message+' Formdaki ürün bilgileri korundu.')}catch(err){toast(err.message,true)}};
document.addEventListener('click',e=>{if(e.target.matches('[data-close-colors]')){$('colorsModal').hidden=true;document.body.classList.remove('modal-open')}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('colorsModal').hidden){$('colorsModal').hidden=true;document.body.classList.remove('modal-open')}});

// v3.1.30 — campaign manager performance pass: debounced preview + no layout-thrash
const campaignPreviewPixelsPerSecond=speed=>({slow:55,normal:85,fast:130}[String(speed||'').toLowerCase()]||85);
let campaignPreviewTimer=0;
let campaignPreviewLastSignature='';
let campaignPreviewResizeTimer=0;

function campaignMessageRow(item={}){
  const row=document.createElement('div');row.className='campaign-message-row';
  row.dataset.sourceType=item.source_type||'manual';row.dataset.sourceRef=item.source_ref||'';row.dataset.messageId=item.id||'';
  row.innerHTML=`<label class="campaign-message-enabled" title="Mesajı yayınla"><input type="checkbox" aria-label="Mesajı yayınla" ${item.enabled!==false?'checked':''}></label><input class="campaign-text" aria-label="Şerit mesajı" maxlength="180" placeholder="Örn. Seçili ürünlerde %20 indirim" value="${esc(item.text||'')}"><input class="campaign-link" aria-label="Mesaj bağlantısı (isteğe bağlı)" maxlength="500" placeholder="İsteğe bağlı: /urunler/... veya https://..." value="${esc(item.url||'')}"><span class="campaign-source-chip">${esc((item.source_type||'manual')==='manual'?'MANUEL':'BAĞLI')}</span><button class="campaign-message-remove" type="button" aria-label="Mesajı kaldır">×</button>`;
  const textInput=row.querySelector('.campaign-text');
  const linkInput=row.querySelector('.campaign-link');
  textInput.addEventListener('input',()=>{scheduleCampaignPreview();$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
  linkInput.addEventListener('input',()=>{$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
  row.querySelector('input[type="checkbox"]').addEventListener('change',()=>{scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
  row.querySelector('.campaign-message-remove').onclick=()=>{row.remove();scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'};
  return row
}
function renderCampaignMessages(items=[]){const wrap=$('campaignMessageList');wrap.innerHTML='';(items||[]).forEach(item=>wrap.append(campaignMessageRow(item)));if(!wrap.children.length)wrap.innerHTML='<div class="campaign-empty">Henüz mesaj yok. “+ Mesaj ekle” ile ilk duyuruyu ekle.</div>';campaignPreviewLastSignature='';scheduleCampaignPreview(0)}
function collectCampaignMessages(){return [...$('campaignMessageList').querySelectorAll('.campaign-message-row')].map((row,index)=>({id:row.dataset.messageId||`mesaj-${index+1}`,text:row.querySelector('.campaign-text').value.trim(),url:row.querySelector('.campaign-link').value.trim(),enabled:row.querySelector('input[type="checkbox"]').checked,source_type:row.dataset.sourceType||'manual',source_ref:row.dataset.sourceRef||''})).filter(x=>x.text)}
function campaignPreviewSequence(texts){return texts.map(text=>`<span class="campaign-preview-item">${esc(text)}</span><span class="campaign-preview-separator" aria-hidden="true">✦</span>`).join('')}
function campaignPreviewRepeatCount(texts,viewportWidth){
  const chars=Math.max(1,texts.reduce((sum,text)=>sum+String(text||'').length+3,0));
  const estimatedSequenceWidth=Math.max(150,chars*7.2);
  return Math.max(1,Math.min(14,Math.ceil((Math.max(320,viewportWidth)*1.15)/estimatedSequenceWidth)));
}
function scheduleCampaignPreview(delay=120){
  clearTimeout(campaignPreviewTimer);
  campaignPreviewTimer=setTimeout(()=>{campaignPreviewTimer=0;updateCampaignPreview()},Math.max(0,delay));
}
function updateCampaignPreview(force=false){
  const modal=$('campaignModal'),out=$('campaignPreviewLine'),viewport=$('campaignPreviewViewport'),meta=$('campaignPreviewMeta');
  if(!out||!viewport||!modal||modal.hidden)return;
  const enabled=$('campaignEnabled')?.checked;
  const texts=collectCampaignMessages().filter(x=>x.enabled).map(x=>x.text);
  if(!enabled){campaignPreviewLastSignature='disabled';out.removeAttribute('data-direction');out.style.animation='none';out.innerHTML='<span class="campaign-preview-placeholder">ŞERİT KAPALI</span>';if(meta)meta.textContent='Şerit sitede görünmez';return}
  if(!texts.length){campaignPreviewLastSignature='empty';out.removeAttribute('data-direction');out.style.animation='none';out.innerHTML='<span class="campaign-preview-placeholder">AKTİF MESAJ YOK · ŞERİT SİTEDE GİZLENİR</span>';if(meta)meta.textContent='Aktif mesaj bekleniyor';return}
  const direction=['rtl','ltr'].includes($('campaignDirection')?.value)?$('campaignDirection').value:'rtl';
  const speed=['slow','normal','fast'].includes($('campaignSpeed')?.value)?$('campaignSpeed').value:'normal';
  const speedLabel={slow:'Yavaş',normal:'Normal',fast:'Hızlı'}[speed];const directionLabel=direction==='rtl'?'Sağdan sola':'Soldan sağa';
  if(meta)meta.textContent=`${speedLabel} · ${directionLabel} · üzerine gelince durur`;
  out.dataset.direction=direction;out.style.animation='';out.style.animationPlayState='running';
  const viewportWidth=Math.round(viewport.getBoundingClientRect().width||viewport.clientWidth||900);
  const repeatCount=campaignPreviewRepeatCount(texts,viewportWidth);
  const signature=JSON.stringify([texts,direction,repeatCount]);
  if(!force&&signature===campaignPreviewLastSignature){
    const group=out.querySelector('.campaign-preview-group');
    if(group){const width=Math.max(1,group.scrollWidth||1);const duration=Math.max(4,width/campaignPreviewPixelsPerSecond(speed));out.style.setProperty('--campaign-preview-duration',`${duration.toFixed(3)}s`)}
    return
  }
  campaignPreviewLastSignature=signature;
  const sequence=campaignPreviewSequence(texts).repeat(repeatCount);
  out.innerHTML=`<div class="campaign-preview-group">${sequence}</div><div class="campaign-preview-group" aria-hidden="true">${sequence}</div>`;
  requestAnimationFrame(()=>{
    const group=out.querySelector('.campaign-preview-group');
    const width=Math.max(1,group?.scrollWidth||1);
    const duration=Math.max(4,width/campaignPreviewPixelsPerSecond(speed));
    out.style.setProperty('--campaign-preview-duration',`${duration.toFixed(3)}s`);
  });
}
async function openCampaignModal(){try{const d=await api('/api/site-settings');siteSettings=d.settings||{};const bar=siteSettings.announcement_bar||{};$('campaignEnabled').checked=bar.enabled!==false;$('campaignSpeed').value=['slow','normal','fast'].includes(bar.speed)?bar.speed:'normal';$('campaignDirection').value=['rtl','ltr'].includes(bar.direction)?bar.direction:'rtl';$('campaignModal').hidden=false;document.body.classList.add('modal-open');renderCampaignMessages(bar.messages||[]);setCampaignColors(bar.colors);$('campaignSaveState').textContent='Ayarlar yüklendi.';requestAnimationFrame(()=>updateCampaignPreview(true))}catch(err){toast(err.message,true)}}
$('manageCampaign').onclick=openCampaignModal;
$('addCampaignMessage').onclick=()=>{const wrap=$('campaignMessageList');wrap.querySelector('.campaign-empty')?.remove();const row=campaignMessageRow({enabled:true,source_type:'manual'});wrap.append(row);row.querySelector('.campaign-text').focus();campaignPreviewLastSignature='';scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'};
$('campaignEnabled').addEventListener('change',()=>{campaignPreviewLastSignature='';scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
$('campaignSpeed').addEventListener('change',()=>{scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
$('campaignDirection').addEventListener('change',()=>{campaignPreviewLastSignature='';scheduleCampaignPreview(0);$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'});
$('saveCampaign').onclick=async()=>{try{const messages=collectCampaignMessages();const settings={announcement_bar:{enabled:$('campaignEnabled').checked,speed:$('campaignSpeed').value,direction:$('campaignDirection').value,separator:'✦',colors:getCampaignColors(),messages,integration:siteSettings?.announcement_bar?.integration||{discounts_enabled:false,mode:'manual'}}};$('campaignSaveState').textContent='Kaydediliyor ve site hazırlanıyor…';const d=await api('/api/site-settings/save',{method:'POST',body:JSON.stringify({settings})});siteSettings=d.settings||settings;const bar=siteSettings.announcement_bar||{};$('campaignEnabled').checked=bar.enabled!==false;$('campaignSpeed').value=bar.speed||'normal';$('campaignDirection').value=bar.direction||'rtl';renderCampaignMessages(bar.messages||[]);setCampaignColors(bar.colors);$('campaignSaveState').textContent='Kaydedildi · GitHub Desktop’ta Commit + Push hazır.';toast('✅ '+d.message)}catch(err){$('campaignSaveState').textContent='Hata';toast(err.message,true)}};
function closeCampaignModal(){clearTimeout(campaignPreviewTimer);$('campaignModal').hidden=true;document.body.classList.remove('modal-open');const track=$('campaignPreviewLine');if(track)track.style.animationPlayState='paused'}
document.addEventListener('click',e=>{if(e.target.matches('[data-close-campaign]'))closeCampaignModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('campaignModal').hidden)closeCampaignModal()});
window.addEventListener('resize',()=>{if($('campaignModal')?.hidden)return;clearTimeout(campaignPreviewResizeTimer);campaignPreviewResizeTimer=setTimeout(()=>{campaignPreviewLastSignature='';updateCampaignPreview(true)},180)},{passive:true});

function normalizedTags(){const seen=new Set(),out=[];splitLines($('tags').value).forEach(tag=>{const clean=tag.replace(/\s+/g,' ').trim();const key=clean.toLocaleLowerCase('tr-TR');if(clean&&!seen.has(key)){seen.add(key);out.push(clean)}});return out.slice(0,16)}
function syncTagPresetState(){const selected=new Set(normalizedTags().map(x=>x.toLocaleLowerCase('tr-TR')));document.querySelectorAll('#tagPresets [data-tag]').forEach(b=>b.classList.toggle('active',selected.has(String(b.dataset.tag||'').toLocaleLowerCase('tr-TR'))))}
$('tags').addEventListener('input',syncTagPresetState);$('tagPresets').addEventListener('click',e=>{const b=e.target.closest('[data-tag]');if(!b)return;const tag=b.dataset.tag;let values=normalizedTags();const key=tag.toLocaleLowerCase('tr-TR'),index=values.findIndex(x=>x.toLocaleLowerCase('tr-TR')===key);if(index>=0)values.splice(index,1);else if(values.length<16)values.push(tag);$('tags').value=values.join('\n');syncTagPresetState();updateQuality()});

load().catch(e=>toast(e.message,true));

// v2.7 — panel headings use native text; no runtime ampersand rewriting.

// v2.3 — publish preflight + local backup/restore center
function formatBytes(bytes){const n=Number(bytes||0);if(n<1024)return `${n} B`;if(n<1024*1024)return `${(n/1024).toFixed(1)} KB`;return `${(n/1024/1024).toFixed(1)} MB`}
function formatBackupDate(value){try{return new Date(value).toLocaleString('tr-TR',{dateStyle:'short',timeStyle:'short'})}catch{return value||''}}
function renderPreflight(data){const list=$('preflightList');const summary=$('preflightSummary');list.innerHTML='';const checks=data.checks||[];checks.forEach(c=>{const row=document.createElement('div');row.className='preflight-item';const statusLabel={pass:'TEMİZ',warn:'UYARI',fail:'HATA'}[c.status]||c.status;row.innerHTML=`<span class="preflight-badge ${esc(c.status)}">${esc(statusLabel)}</span><strong>${esc(c.label)}</strong><span>${esc(c.detail)}</span>`;list.append(row)});const failures=data.summary?.failures??checks.filter(x=>x.status==='fail').length;const warnings=data.summary?.warnings??checks.filter(x=>x.status==='warn').length;summary.className='preflight-summary '+(failures?'bad':'good');summary.textContent=failures?`${failures} kritik hata var. Push etmeden önce düzelt.`:warnings?`Kritik hata yok · ${warnings} uyarı var. Uyarıları kontrol ederek devam edebilirsin.`:'Her şey temiz. GitHub Desktop’ta Commit + Push için hazır.'}
function renderBackups(items){const wrap=$('backupList');wrap.innerHTML='';(items||[]).slice(0,16).forEach(b=>{const row=document.createElement('div');row.className='backup-item';const kind=b.type==='full'?'Tam veri + medya yedeği':b.type==='database'?'Kalıcı veri yedeği':'Ürün verisi yedeği';row.innerHTML=`<div><strong>${esc(kind)}</strong><small>${esc(formatBackupDate(b.modified))} · ${esc(formatBytes(b.size))} · ${esc(b.name)}</small></div><button type="button">Geri yükle</button>`;row.querySelector('button').onclick=()=>restoreBackup(b);wrap.append(row)});if(!wrap.children.length)wrap.innerHTML='<div class="backup-empty">Henüz yerel yedek yok. “Şimdi tam yedek al” ile ilk yedeği oluşturabilirsin.</div>'}
async function refreshPublishCenter(){try{$('preflightSummary').className='preflight-summary';$('preflightSummary').textContent='Kontrol ediliyor…';const [preflight,backups]=await Promise.all([fetch('/api/preflight',{cache:'no-store'}).then(async r=>{const d=await r.json().catch(()=>null);if(!d||!Array.isArray(d.checks))throw new Error(d?.error||`Yayın kontrolü alınamadı (${r.status}).`);return d}),api('/api/backups')]);renderPreflight(preflight);renderBackups(backups.backups)}catch(err){$('preflightSummary').className='preflight-summary bad';$('preflightSummary').textContent=err.message;toast(err.message,true)}}
async function restoreBackup(backupItem){const extra=backupItem.type==='database'?' Bu yedek kalıcı veri tabanını geri getirir; medya mevcut haliyle kalır.':'';if(!confirm(`${formatBackupDate(backupItem.modified)} tarihli yedeğe dönülsün mü?${extra}\n\nGeri yüklemeden önce mevcut durumun tam yedeği otomatik alınacak.`))return;try{$('saveState').textContent='Yedek geri yükleniyor…';const d=await api('/api/restore',{method:'POST',body:JSON.stringify({name:backupItem.name})});toast('✅ '+d.message);$('saveState').textContent='Yedek geri yüklendi · Commit + Push';const r=await api('/api/products');products=r.products;colors=r.colors||colors;resetForm();await refreshPublishCenter()}catch(err){$('saveState').textContent='Hata';toast(err.message,true)}}
$('publishCheck').onclick=async()=>{$('publishModal').hidden=false;document.body.classList.add('modal-open');await refreshPublishCenter()};
$('refreshPreflight').onclick=refreshPublishCenter;
$('createBackup').onclick=async()=>{try{const d=await api('/api/backup',{method:'POST',body:'{}'});toast('✅ '+d.message);renderBackups(d.backups||[]);await refreshPublishCenter()}catch(err){toast(err.message,true)}};
document.addEventListener('click',e=>{if(e.target.matches('[data-close-publish]')){$('publishModal').hidden=true;document.body.classList.remove('modal-open')}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('publishModal').hidden){$('publishModal').hidden=true;document.body.classList.remove('modal-open')}});

$('openContent').onclick=()=>location.href='content.html';

// v3.3.43 — "Ürünler sayfası açıklaması" artık ürün yöneticisinde (önceden NFC ekranındaydı).
// Mevcut /api/nfc-site-settings/save uç noktası yalnızca website_copy gönderildiğinde fiyat ve görselleri korur.
(()=>{const btn=document.createElement('button');btn.type='button';btn.id='openCatalogIntro';btn.className='ghost catalog-intro-launch';btn.textContent='Ürünler sayfası açıklaması';$('newProduct').after(btn);
const modal=document.createElement('div');modal.className='modal';modal.id='catalogIntroModal';modal.hidden=true;
modal.innerHTML=`<div class="modal-backdrop" data-close-catalog-intro></div><div class="modal-card catalog-intro-card" role="dialog" aria-modal="true" aria-labelledby="catalogIntroTitle"><button class="modal-close" type="button" data-close-catalog-intro aria-label="Kapat">×</button><p class="eyebrow-preview">ÜRÜNLER SAYFASI</p><h2 id="catalogIntroTitle">“Atölyeden çıkanlar” açıklaması</h2><p class="publish-intro">Ürünler sayfasının üstündeki tanıtım metni. Kategoriler büyüdükçe buradan güncelleyebilirsin.</p><textarea id="catalogIntroText" maxlength="520" rows="6" aria-label="Ürünler sayfası açıklaması"></textarea><div class="catalog-intro-foot"><small><span id="catalogIntroCount">0</span>/520 karakter</small><span id="catalogIntroState" role="status"></span><button id="saveCatalogIntro" class="primary" type="button">Kaydet ve siteyi hazırla</button></div></div>`;
document.body.append(modal);
const close=()=>{modal.hidden=true;document.body.classList.remove('modal-open');btn.focus()};
const count=()=>{$('catalogIntroCount').textContent=$('catalogIntroText').value.length};
btn.onclick=async()=>{try{const d=await api('/api/nfc-site-settings');$('catalogIntroText').value=d.website_copy?.catalog_intro||'';count();$('catalogIntroState').textContent='';modal.hidden=false;document.body.classList.add('modal-open');$('catalogIntroText').focus()}catch(e){toast(e.message,true)}};
$('catalogIntroText').addEventListener('input',()=>{count();$('catalogIntroState').textContent='Kaydedilmemiş değişiklik var.'});
modal.addEventListener('click',e=>{if(e.target.closest('[data-close-catalog-intro]'))close()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!modal.hidden)close()});
$('saveCatalogIntro').onclick=async()=>{const b=$('saveCatalogIntro');const text=$('catalogIntroText').value.trim();if(!text){toast('Açıklama boş olamaz.',true);return}b.disabled=true;$('catalogIntroState').textContent='Kaydediliyor, site hazırlanıyor…';try{await api('/api/nfc-site-settings/save',{method:'POST',body:JSON.stringify({website_copy:{catalog_intro:text}})});$('catalogIntroState').textContent='Kaydedildi · 1 dk bekleyip Commit + Push';toast('✅ Ürünler sayfası açıklaması kaydedildi ve site hazırlandı.')}catch(e){$('catalogIntroState').textContent='Hata · metin pencerede duruyor';toast(e.message,true)}finally{b.disabled=false}};})();

// v3.3.43 — Başlığın yanında "Hazır · 9/9" ve "Hazır" yan yana iki kez yazıyordu: sistem boştayken ikinci "Hazır" gizlenir;
// kaydetme, hata ve "kaydedilmemiş değişiklik" mesajları görünmeye devam eder.
(()=>{const s=$('saveState');if(!s)return;const sync=()=>{s.hidden=/^\s*Hazır\s*$/.test(s.textContent)};new MutationObserver(sync).observe(s,{childList:true,characterData:true,subtree:true});sync()})();

// v3.3.44 — arka plan build takibi: yıldız / arşiv / sıralama anında kaydedilir, site arka planda hazırlanır.
// Build bitene kadar durum satırında uyarı görünür; bu sırada commit atılırsa sayfalar yarım gidebilir.
var buildWatchTimer=0;
function watchBuild(state){clearTimeout(buildWatchTimer);const s=$('saveState');const tick=async()=>{let b=state;state=null;if(!b){try{b=(await api('/api/status')).build}catch(_){b=null}}if(!b)return;if(b.running){if(!saving)s.textContent='Site hazırlanıyor… bitene kadar commit etme';buildWatchTimer=setTimeout(tick,1500);return}if(b.last_ok===false){s.textContent='Site hazırlanamadı';toast('Site hazırlanamadı: '+(b.last_error||'bilinmeyen hata'),true);return}if(/Site hazırlanıyor/.test(s.textContent)){s.textContent='Hazır';toast('✅ Site hazır · GitHub Desktop’ta Commit + Push yapabilirsin')}};tick()}
setTimeout(()=>api('/api/status').then(d=>{if(d.build&&d.build.running)watchBuild(d.build)}).catch(()=>{}),800);

// v3.3.46 — liste filtrelerinde sayı rozetleri (Tümü / Yayında / Arşiv / Öne çıkan); her stats() çağrısında güncellenir.
{const _stats=stats;stats=function(...a){const r=_stats.apply(this,a);const counts={all:products.length,live:products.filter(p=>p.active!==false).length,draft:products.filter(p=>p.active===false).length,featured:products.filter(p=>p.active!==false&&p.featured).length};document.querySelectorAll('#listFilters button[data-filter]').forEach(b=>{const n=counts[b.dataset.filter];if(n==null)return;let c=b.querySelector('.catalog-admin-filter-count');if(!c){c=document.createElement('span');c.className='catalog-admin-filter-count';b.append(c)}c.textContent=n;b.setAttribute('aria-label',`${b.firstChild.textContent.trim()} (${n})`)});return r};stats()}

// v3.3.51 — Google puanı ve yorum sayısı (ana sayfadaki Google İşletme Profili kartı)
(()=>{const anchor=$('openCatalogIntro')||$('newProduct');if(!anchor)return;
const btn=document.createElement('button');btn.type='button';btn.id='openGoogleRating';btn.className='ghost catalog-intro-launch';btn.textContent='★ Google puanı';anchor.after(btn);
const modal=document.createElement('div');modal.className='modal';modal.id='googleRatingModal';modal.hidden=true;
modal.innerHTML=`<div class="modal-backdrop" data-close-grating></div><div class="modal-card catalog-intro-card grating-card" role="dialog" aria-modal="true" aria-labelledby="gratingTitle"><button class="modal-close" type="button" data-close-grating aria-label="Kapat">×</button><p class="eyebrow-preview">ANA SAYFA · GOOGLE KARTI</p><h2 id="gratingTitle">Google puanı ve yorum sayısı</h2><p class="publish-intro">Google İşletme Profilindeki değerleri buraya gir. Yıldıza tıkla ya da ortalamayı ondalıklı yaz (ör. 4,8).</p><div class="grating-stars" role="radiogroup" aria-label="Puan">${[1,2,3,4,5].map(n=>`<button type="button" class="grating-star" data-star="${n}" role="radio" aria-label="${n} yıldız">★</button>`).join('')}</div><div class="grating-fields"><label>Ortalama puan<input id="gratingValue" type="number" min="1" max="5" step="0.1" inputmode="decimal"></label><label>Yorum sayısı<input id="gratingCount" type="number" min="0" step="1" inputmode="numeric"></label></div><div class="catalog-intro-foot"><span id="gratingState" role="status"></span><button id="saveGrating" class="primary" type="button">Kaydet ve siteyi hazırla</button></div></div>`;
document.body.append(modal);
const stars=[...modal.querySelectorAll('.grating-star')];
const paint=()=>{const v=parseFloat(String($('gratingValue').value).replace(',','.'))||0;stars.forEach(s=>{const n=+s.dataset.star;s.classList.toggle('on',v>=n-0.25);s.setAttribute('aria-checked',String(Math.round(v)===n))})};
const dirty=()=>{$('gratingState').textContent='Kaydedilmemiş değişiklik var.'};
stars.forEach(s=>s.onclick=()=>{$('gratingValue').value=(+s.dataset.star).toFixed(1);paint();dirty()});
$('gratingValue').addEventListener('input',()=>{paint();dirty()});$('gratingCount').addEventListener('input',dirty);
const close=()=>{modal.hidden=true;document.body.classList.remove('modal-open');btn.focus()};
modal.addEventListener('click',e=>{if(e.target.closest('[data-close-grating]'))close()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!modal.hidden)close()});
btn.onclick=async()=>{try{const d=await api('/api/nfc-site-settings');const c=d.website_copy||{};$('gratingValue').value=Number(c.google_rating??5).toFixed(1);$('gratingCount').value=c.google_review_count??0;paint();$('gratingState').textContent='';modal.hidden=false;document.body.classList.add('modal-open');$('gratingCount').focus()}catch(e){toast(e.message,true)}};
$('saveGrating').onclick=async()=>{const b=$('saveGrating');const v=parseFloat(String($('gratingValue').value).replace(',','.'));const c=parseInt($('gratingCount').value,10);if(!(v>=1&&v<=5)){toast('Puan 1 ile 5 arasında olmalı.',true);return}if(!(c>=0)){toast('Yorum sayısı 0 veya daha büyük olmalı.',true);return}b.disabled=true;$('gratingState').textContent='Kaydediliyor, site hazırlanıyor…';try{const r=await api('/api/nfc-site-settings/save',{method:'POST',body:JSON.stringify({website_copy:{google_rating:Math.round(v*10)/10,google_review_count:c}})});const w=r.website_copy||{};$('gratingState').textContent=`Kaydedildi: ${String(Number(w.google_rating).toFixed(1)).replace('.',',')} ★ · ${w.google_review_count} yorum · 1 dk bekleyip Commit + Push`;toast('✅ Google puanı kaydedildi ve site hazırlandı.')}catch(e){$('gratingState').textContent='Hata · değerler pencerede duruyor';toast(e.message,true)}finally{b.disabled=false}};})();

// v3.3.98 — kampanya şeridi renkleri: önizleme canlı sitedeki şeritle aynı renkleri kullanır
const CAMPAIGN_COLOR_DEFAULTS={bg:'#14110f',fg:'#ffffff',accent:'#c8894a'};
const campaignHex=v=>/^#[0-9a-f]{6}$/i.test(String(v||''))?String(v).toLowerCase():'';
function getCampaignColors(){return{bg:campaignHex($('campaignColorBg')?.value)||CAMPAIGN_COLOR_DEFAULTS.bg,fg:campaignHex($('campaignColorFg')?.value)||CAMPAIGN_COLOR_DEFAULTS.fg,accent:campaignHex($('campaignColorAccent')?.value)||CAMPAIGN_COLOR_DEFAULTS.accent}}
function paintCampaignPreview(){const c=getCampaignColors();const box=document.querySelector('.campaign-preview-box');if(box){box.style.setProperty('--ann-bg',c.bg);box.style.setProperty('--ann-fg',c.fg);box.style.setProperty('--ann-accent',c.accent)}document.querySelectorAll('[data-ann-preset]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.bg===c.bg&&b.dataset.fg===c.fg&&b.dataset.accent===c.accent)))}
function setCampaignColors(colors){const c=Object.assign({},CAMPAIGN_COLOR_DEFAULTS,colors||{});[['campaignColorBg','bg'],['campaignColorFg','fg'],['campaignColorAccent','accent']].forEach(([id,k])=>{const el=$(id);if(el)el.value=campaignHex(c[k])||CAMPAIGN_COLOR_DEFAULTS[k]});paintCampaignPreview()}
document.querySelectorAll('[data-ann-preset]').forEach(b=>b.addEventListener('click',()=>{setCampaignColors({bg:b.dataset.bg,fg:b.dataset.fg,accent:b.dataset.accent});$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'}));
['campaignColorBg','campaignColorFg','campaignColorAccent'].forEach(id=>$(id)?.addEventListener('input',()=>{paintCampaignPreview();$('campaignSaveState').textContent='Kaydedilmemiş değişiklik var.'}));
paintCampaignPreview();
