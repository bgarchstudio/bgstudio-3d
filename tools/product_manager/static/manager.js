let products=[], colors=[], currentSlug=null, slugLocked=false, listFilter='all', draggedSlug=null;
const $=id=>document.getElementById(id);
const fields=['name','slug','category','price_text','price_value','card_description','description','options','features','tags','production_note','sort_order','seo_title','seo_description'];
const toast=(msg,error=false)=>{const t=$('toast');t.textContent=msg;t.className='toast'+(error?' error':'');t.hidden=false;clearTimeout(window.__tt);window.__tt=setTimeout(()=>t.hidden=true,4200)};
const splitLines=v=>(v||'').split(/\n+/).map(x=>x.trim()).filter(Boolean);
const esc=s=>String(s??'').replace(/[&<>'"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));
function slugify(s){return (s||'').toLocaleLowerCase('tr-TR').replaceAll('ç','c').replaceAll('ğ','g').replaceAll('ı','i').replaceAll('ö','o').replaceAll('ş','s').replaceAll('ü','u').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,80)}
const PANEL_VERSION='3.1.4';
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
  if(status.version!==PANEL_VERSION)throw new Error(`Panel sunucusu eski sürüm (${status.version||'bilinmiyor'}). Bu sekmeyi kapat, eski CMD/panel penceresini kapat ve Ürün Yöneticisi’ni yeniden başlat.`);
  const d=await api('/api/products');products=d.products;colors=d.colors||[];const vault=d.storage?.app_home||status.storage?.app_home||'';$('repoPath').textContent='Repo: '+d.root+(vault?' · Kalıcı veri: '+vault:'');renderList();resetForm()
}
function stats(){$('countAll').textContent=products.length;$('countLive').textContent=products.filter(p=>p.active!==false).length;$('countFeatured').textContent=products.filter(p=>p.active!==false&&p.featured).length}
function categoryLabel(k){return {'dekoratif-duvar':'Dekoratif & Duvar',aydinlatma:'Aydınlatma','ev-duzen':'Ev & Düzen','gaming-masaustu':'Gaming & Masaüstü','anahtarlik-aksesuar':'Anahtarlık & Aksesuar','hediye-kisiye-ozel':'Hediye & Kişiye Özel','pratik-fonksiyonel':'Pratik & Fonksiyonel','pet-urunleri':'Pet Ürünleri',dekoratif:'Dekoratif & Duvar',fonksiyonel:'Pratik & Fonksiyonel','kisiye-ozel':'Hediye & Kişiye Özel',pet:'Pet Ürünleri'}[k]||k}
function formatTL(value){const n=Number(String(value??'').replace(',','.'));return Number.isFinite(n)?new Intl.NumberFormat('tr-TR',{maximumFractionDigits:2}).format(n)+' TL':''}
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
  row.innerHTML=`<input class="color-name" maxlength="60" placeholder="Renk adı" value="${esc(item.name||'')}"><input class="color-picker" type="color" value="${esc(hex)}"><input class="color-hex" maxlength="7" value="${esc(hex)}"><label class="color-stock-toggle"><input class="color-stock" type="checkbox" ${item.in_stock!==false?'checked':''}><span>Stokta</span></label><input class="color-qty" type="number" min="0" step="1" placeholder="∞" value="${item.stock_qty??''}" title="Boş = sınırsız"><button class="tier-remove color-remove" type="button">×</button>`;
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
function effectivePreviewTiers(){let items=collectPricingTiers().filter(t=>+t.quantity>1);const base=Number(String($('price_value').value||'').replace(',','.'));if(Number.isFinite(base)&&base>0)items=[{label:'Tekli',quantity:1,price_value:String(base),note:'Tekli fiyat',_auto:true},...items];return items.sort((a,b)=>a.quantity-b.quantity)}
function collectPricingTiers(){const rows=[...$('pricingTiers').querySelectorAll('.pricing-tier-row')];const items=[];const used=new Set();rows.forEach((row,i)=>{const qty=Number(row.querySelector('.tier-qty').value);const raw=row.querySelector('.tier-price').value.trim().replace(',','.');const price=Number(raw);let label=row.querySelector('.tier-label').value.trim();let note=row.querySelector('.tier-note').value.trim();if(!qty&&!raw&&!label&&!note)return;if(!Number.isInteger(qty)||qty<1)throw new Error(`${i+1}. set fiyatında ürün adedi geçersiz.`);if(!Number.isFinite(price)||price<=0)throw new Error(`${i+1}. set fiyatında fiyat geçersiz.`);if(used.has(qty))throw new Error(`${qty} adet için iki ayrı set fiyatı tanımlanamaz.`);used.add(qty);label=packageLabelForQuantity(qty);note=note||defaultPricingNote(qty);items.push({label,quantity:qty,price_value:String(price),note})});return items.sort((a,b)=>a.quantity-b.quantity)}
function pricingIssues(){try{collectPricingTiers();return []}catch(e){return [e.message]}}
$('addPricingTier').onclick=()=>{const wrap=$('pricingTiers');wrap.querySelector('.pricing-empty')?.remove();wrap.append(pricingTierRow({}));wrap.lastElementChild.querySelector('.tier-qty')?.focus()};
function sortedProducts(){return [...products].sort((a,b)=>(+a.sort_order||9999)-(+b.sort_order||9999)||a.name.localeCompare(b.name,'tr'))}
function filteredProducts(){const q=$('search').value.trim().toLocaleLowerCase('tr-TR');return sortedProducts().filter(p=>{const text=(p.name+' '+p.slug+' '+(p.price_text||'')+' '+categoryLabel(p.category)+' '+(p.tags||[]).join(' ')).toLocaleLowerCase('tr-TR');const qok=!q||text.includes(q);const fok=listFilter==='all'||(listFilter==='live'&&p.active!==false)||(listFilter==='draft'&&p.active===false)||(listFilter==='featured'&&p.active!==false&&p.featured);return qok&&fok})}
function renderList(){stats();const wrap=$('productList');wrap.innerHTML='';const canDrag=listFilter==='all'&&!$('search').value.trim();$('dragNote').textContent=canDrag?'Sıralamak için ürünleri sürükle.':'Sürükle-bırak için “Tümü” filtresinde aramayı temizle.';filteredProducts().forEach(p=>{const row=document.createElement('div');row.className='product-item'+(p.slug===currentSlug?' active':'');row.dataset.slug=p.slug;row.draggable=canDrag;row.innerHTML=`<span class="drag-handle" title="Sürükle">⋮⋮</span><button class="product-main" type="button"><img src="/${esc(p.main_image)}" onerror="this.style.visibility='hidden'"><span><strong>${esc(p.name)}</strong><small>${esc(p.price_text)} · ${esc(categoryLabel(p.category))}</small></span><i class="dot ${p.active!==false?'live':''}"></i></button><button class="feature-toggle ${p.featured?'on':''}" type="button" title="Öne çıkan">★</button>`;row.querySelector('.product-main').onclick=()=>editProduct(p.slug);row.querySelector('.feature-toggle').onclick=async e=>{e.stopPropagation();try{const d=await api('/api/feature',{method:'POST',body:JSON.stringify({slug:p.slug})});toast('✅ '+d.message);await refreshProducts(currentSlug||p.slug)}catch(err){toast(err.message,true)}};if(canDrag){row.addEventListener('dragstart',()=>{draggedSlug=p.slug;row.classList.add('dragging')});row.addEventListener('dragend',()=>{draggedSlug=null;row.classList.remove('dragging')});row.addEventListener('dragover',e=>{e.preventDefault();row.classList.add('drag-over')});row.addEventListener('dragleave',()=>row.classList.remove('drag-over'));row.addEventListener('drop',async e=>{e.preventDefault();row.classList.remove('drag-over');if(!draggedSlug||draggedSlug===p.slug)return;const order=sortedProducts().map(x=>x.slug);const from=order.indexOf(draggedSlug),to=order.indexOf(p.slug);order.splice(from,1);order.splice(to,0,draggedSlug);try{const d=await api('/api/reorder',{method:'POST',body:JSON.stringify({order})});products=d.products;toast('✅ '+d.message);renderList();if(currentSlug)editProduct(currentSlug)}catch(err){toast(err.message,true)}})}wrap.append(row)})}
function resetForm(){currentSlug=null;slugLocked=false;$('form').reset();$('active').checked=true;$('sort_order').value=(Math.max(0,...products.map(p=>+p.sort_order||0))+1);$('formTitle').textContent='Yeni ürün';$('slug').disabled=false;setDefaultNote();clearPreviews();renderGalleryExisting([]);renderPricingTiers([]);renderProductColors([]);syncTagPresetState();setActionState(null);renderList();updateQuality();updateSeoMeter()}
function setDefaultNote(){if(!$('production_note').value)$('production_note').value='3D baskı ürünlerde katman dokusu üretim yönteminin doğal bir parçasıdır. Renk, adet ve kişiselleştirme seçenekleri sipariş öncesi netleştirilir.'}
function setActionState(p){$('duplicateProduct').hidden=!p;$('archiveProduct').hidden=!p;$('deleteProduct').hidden=!p;if(p)$('archiveProduct').textContent=p.active===false?'Yayına al':'Arşivle'}
function editProduct(slug){const p=products.find(x=>x.slug===slug);if(!p)return;currentSlug=slug;slugLocked=true;$('formTitle').textContent=p.name;fields.forEach(id=>{const el=$(id);if(id==='features'||id==='tags')el.value=(p[id]||[]).join('\n');else if(id==='options')el.value=legacyOptionsForProduct(p).join('\n');else el.value=p[id]??''});renderProductColors(colorIdsForProduct(p));syncTagPresetState();$('active').checked=p.active!==false;$('featured').checked=!!p.featured;$('slug').disabled=true;showExistingPreview('mainPreview','mainPlaceholder',p.main_image);if(p.poster_image)showExistingPreview('posterPreview','posterPlaceholder',p.poster_image);else clearOne('posterPreview','posterPlaceholder','İsteğe bağlı');$('main_image').value='';$('poster_image').value='';$('gallery_images').value='';renderGalleryExisting(p.gallery_images||[]);renderPricingTiers(p.pricing_tiers||[]);setActionState(p);renderList();updateQuality();updateSeoMeter();window.scrollTo({top:0,behavior:'smooth'})}
function showExistingPreview(imgId,placeId,path){const i=$(imgId);i.src='/'+path;i.hidden=false;$(placeId).hidden=true}
function clearOne(imgId,placeId,text){const i=$(imgId);i.removeAttribute('src');i.hidden=true;const p=$(placeId);p.hidden=false;p.textContent=text}
function clearPreviews(){clearOne('mainPreview','mainPlaceholder','Görsel seç');clearOne('posterPreview','posterPlaceholder','İsteğe bağlı');$('main_image').value='';$('poster_image').value='';$('gallery_images').value='';renderGalleryExisting([])}
function renderGalleryExisting(items){const wrap=$('galleryPreview');wrap.innerHTML='';(items||[]).forEach((it,i)=>{const path=typeof it==='string'?it:it.path;if(!path)return;const d=document.createElement('div');d.className='gallery-mini';d.innerHTML=`<img src="/${esc(path)}" alt="Galeri ${i+1}"><span>${i+1}</span>`;wrap.append(d)});if(!wrap.children.length)wrap.innerHTML='<small>Ek galeri görseli yok.</small>'}
function renderGalleryFiles(files){const wrap=$('galleryPreview');wrap.innerHTML='';[...files].slice(0,12).forEach((f,i)=>{const d=document.createElement('div');d.className='gallery-mini';d.innerHTML=`<img src="${URL.createObjectURL(f)}" alt="Yeni galeri ${i+1}"><span>Yeni ${i+1}</span>`;wrap.append(d)});if(!wrap.children.length)renderGalleryExisting(currentSlug?(products.find(x=>x.slug===currentSlug)?.gallery_images||[]):[])}
$('name').addEventListener('input',()=>{if(!slugLocked)$('slug').value=slugify($('name').value)});$('search').addEventListener('input',renderList);$('newProduct').onclick=resetForm;
$('listFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;listFilter=b.dataset.filter;[...$('listFilters').querySelectorAll('button')].forEach(x=>x.classList.toggle('active',x===b));renderList()});
function clipSeoText(text,max=160){text=(text||'').replace(/\s+/g,' ').trim();if(text.length<=max)return text;let clipped=text.slice(0,max+1);const lastSpace=clipped.lastIndexOf(' ');if(lastSpace>0)clipped=clipped.slice(0,lastSpace);return clipped.replace(/[,:;.!?\-–—]+$/g,'')+'.'}
function escapeRegExp(text){return text.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
function buildSeoValues(){const name=$('name').value.trim();if(!name)return{title:'',description:''};let source=$('card_description').value.trim()||$('description').value.trim();if(source){const productNameRegex=new RegExp('^'+escapeRegExp(name)+'\\s*[-—–:,.]*\\s*','i');source=source.replace(productNameRegex,'').replace(/\s+/g,' ').replace(/[.!?]+$/g,'').trim()}const title=`${name} | Kuşadası 3D Baskı | BG Studio 3D`;const suffix='3D baskı ile üretilir. Kuşadası elden teslim ve Türkiye geneli kargo.';const description=source?`${name}, ${source}. ${suffix}`:`${name}, ${suffix}`;return{title,description:clipSeoText(description,160)}}
function autoSeo(){const seo=buildSeoValues();$('seo_title').value=seo.title;$('seo_description').value=seo.description;updateSeoMeter();updateQuality()}$('autoSeo').onclick=autoSeo;
function previewFile(input,imgId,placeId){const f=input.files[0];if(!f)return;const u=URL.createObjectURL(f);const i=$(imgId);i.src=u;i.hidden=false;$(placeId).hidden=true;updateQuality()}$('main_image').onchange=e=>previewFile(e.target,'mainPreview','mainPlaceholder');$('poster_image').onchange=e=>previewFile(e.target,'posterPreview','posterPlaceholder');$('gallery_images').onchange=e=>renderGalleryFiles(e.target.files);
async function blobToDataURL(blob){return await new Promise((res,rej)=>{const r=new FileReader;r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(blob)})}
async function optimizedWebPBlob(canvas,targetBytes,startQ=.90,minQ=.78){let quality=startQ,blob=null;while(quality>=minQ-.001){blob=await new Promise(res=>canvas.toBlob(res,'image/webp',quality));if(!blob)throw new Error('Görsel WebP formatına dönüştürülemedi.');if(blob.size<=targetBytes||quality<=minQ+.001)break;quality=Math.max(minQ,quality-.03)}return {blob,quality}}
async function convertImage(file,w,h,q=.90,targetKB=320){if(!file)return null;const bmp=await createImageBitmap(file);const c=document.createElement('canvas');c.width=w;c.height=h;const x=c.getContext('2d',{alpha:false});x.fillStyle='#f5ede2';x.fillRect(0,0,w,h);const scale=Math.max(w/bmp.width,h/bmp.height);const dw=bmp.width*scale,dh=bmp.height*scale;x.imageSmoothingEnabled=true;x.imageSmoothingQuality='high';x.drawImage(bmp,(w-dw)/2,(h-dh)/2,dw,dh);const {blob,quality}=await optimizedWebPBlob(c,targetKB*1024,q,.78);const data=await blobToDataURL(blob);const originalSize=file.size||0;bmp.close();return {data,width:w,height:h,bytes:blob.size,original_bytes:originalSize,quality:Number(quality.toFixed(2))}}
async function convertGallery(files){const arr=[];for(const f of [...files].slice(0,12))arr.push(await convertImage(f,1000,1000,.90,320));return arr}
function updateSeoMeter(){$('seoTitleCount').textContent=`${$('seo_title').value.length}/70`;$('seoDescCount').textContent=`${$('seo_description').value.length}/160`}
function qualityIssues(){const issues=[];if(!$('name').value.trim())issues.push('Ürün adı');if(!$('price_text').value.trim())issues.push('Gösterilen fiyat');if(!$('card_description').value.trim())issues.push('Kart açıklaması');if(!$('description').value.trim())issues.push('Ürün açıklaması');if(!selectedProductColorIds().length&&!splitLines($('options').value).length)issues.push('Renk / seçenek');if(!splitLines($('features').value).length)issues.push('Öne çıkan özellik');const hasMain=$('main_image').files[0]||currentSlug&&products.find(x=>x.slug===currentSlug)?.main_image;if(!hasMain)issues.push('Ana görsel');if(!$('seo_title').value.trim()||!$('seo_description').value.trim())issues.push('SEO');if($('featured').checked&&!$('active').checked)issues.push('Öne çıkan ürün yayında olmalı');issues.push(...pricingIssues());return issues}
function updateQuality(){const issues=qualityIssues();const total=9;const good=total-issues.length;$('qualityState').textContent=issues.length?`${issues.length} eksik · ${good}/${total}`:`Hazır · ${total}/${total}`;$('qualityState').classList.toggle('good',!issues.length);const p=$('qualityPanel');p.hidden=!issues.length;p.innerHTML=issues.length?`<strong>Kaydetmeden önce göz at:</strong> ${issues.map(esc).join(' · ')}`:''}
[...$('form').querySelectorAll('input,textarea,select')].forEach(el=>{el.addEventListener('input',()=>{updateQuality();updateSeoMeter()});el.addEventListener('change',()=>{updateQuality();updateSeoMeter()})});$('featured').addEventListener('change',()=>{if($('featured').checked)$('active').checked=true;updateQuality()});
function buildPreview(){const img=$('mainPreview').src||'';$('pvImage').src=img;$('pvName').textContent=$('name').value.trim()||'Ürün adı';$('pvCategory').textContent=categoryLabel($('category').value).toLocaleUpperCase('tr-TR');$('pvDescription').textContent=$('description').value.trim()||$('card_description').value.trim()||'Ürün açıklaması burada görünecek.';$('pvPrice').textContent=$('price_text').value.trim()||'Fiyat için iletişim';let pvTiers=[];try{pvTiers=effectivePreviewTiers()}catch(_){};$('pvPricing').innerHTML=pvTiers.map(t=>`<span><b>${esc(t.label)}</b>${esc(formatTL(t.price_value))}${t.note?`<small>${esc(t.note)}</small>`:''}</span>`).join('');$('pvTags').innerHTML=[...selectedProductColorIds().map(id=>{const c=colorById(id);return c?`<span class="pv-color"><i style="--swatch:${esc(c.hex)}"></i>${esc(c.name)}</span>`:''}),...splitLines($('options').value).slice(0,8).map(x=>`<span>${esc(x)}</span>`),...splitLines($('tags').value).slice(0,8).map(x=>`<span>${esc(x)}</span>`)].join('');$('previewModal').hidden=false;document.body.classList.add('modal-open')}
$('previewProduct').onclick=buildPreview;document.addEventListener('click',e=>{if(e.target.matches('[data-close-preview]')){$('previewModal').hidden=true;document.body.classList.remove('modal-open')}});document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('previewModal').hidden=true;document.body.classList.remove('modal-open')}});
$('duplicateProduct').onclick=async()=>{if(!currentSlug)return;if(!confirm('Bu ürünü kopyalayıp arşivde yeni bir ürün olarak oluşturayım mı?'))return;try{const d=await api('/api/duplicate',{method:'POST',body:JSON.stringify({slug:currentSlug})});toast('✅ '+d.message);await refreshProducts(d.product.slug)}catch(err){toast(err.message,true)}};
$('archiveProduct').onclick=async()=>{if(!currentSlug)return;const p=products.find(x=>x.slug===currentSlug);const active=p?.active===false;if(!confirm(active?'Ürünü tekrar yayına alalım mı?':'Ürünü katalogdan arşive alalım mı?'))return;try{const d=await api('/api/archive',{method:'POST',body:JSON.stringify({slug:currentSlug,active})});toast('✅ '+d.message);await refreshProducts(currentSlug)}catch(err){toast(err.message,true)}};
$('deleteProduct').onclick=async()=>{if(!currentSlug)return;const p=products.find(x=>x.slug===currentSlug);const answer=prompt(`“${p.name}” kalıcı olarak silinecek. Ürün sayfası ve görselleri de kaldırılır. Devam etmek için SİL yaz:`);if(answer!=='SİL')return;try{const d=await api('/api/delete',{method:'POST',body:JSON.stringify({slug:currentSlug})});toast('✅ '+d.message);const r=await api('/api/products');products=r.products;colors=r.colors||colors;resetForm()}catch(err){toast(err.message,true)}};
$('form').addEventListener('submit',async e=>{e.preventDefault();try{$('saveState').textContent='Hazırlanıyor…';if(!$('seo_title').value.trim()||!$('seo_description').value.trim())autoSeo();const product={};fields.forEach(id=>product[id]=$(id).value);product.options=splitLines($('options').value);product.color_ids=selectedProductColorIds();product.features=splitLines($('features').value);product.tags=splitLines($('tags').value).slice(0,16);product.pricing_tiers=collectPricingTiers();product.active=$('active').checked;product.featured=$('featured').checked;product.sort_order=+$('sort_order').value||999;const mf=$('main_image').files[0],pf=$('poster_image').files[0],gf=$('gallery_images').files;if(!currentSlug&&!mf)throw new Error('Yeni üründe ana görsel seçmelisin.');$('saveState').textContent=(mf||pf||gf.length)?'Görseller optimize ediliyor…':'Site hazırlanıyor…';const main=mf?await convertImage(mf,1000,760,.90,320):null;const poster=pf?await convertImage(pf,1254,1254,.90,420):null;const gallery=gf.length?await convertGallery(gf):[];const d=await api('/api/save',{method:'POST',body:JSON.stringify({original_slug:currentSlug,product,main_image:main,poster_image:poster,gallery_images:gallery,replace_gallery:gf.length>0})});toast('✅ '+d.message);$('saveState').textContent='Kaydedildi · GitHub Desktop’ta Commit + Push';await refreshProducts(d.product.slug)}catch(err){$('saveState').textContent='Hata';toast(err.message,true)}})
async function refreshProducts(slug){const d=await api('/api/products');products=d.products;colors=d.colors||colors;renderList();if(slug)editProduct(slug);else resetForm()}
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
    const img=e.target.closest?.('.preview img:not([hidden]), .gallery-mini img, .preview-product-image img');
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
async function refreshPublishCenter(){try{$('preflightSummary').className='preflight-summary';$('preflightSummary').textContent='Kontrol ediliyor…';const [preflight,backups]=await Promise.all([api('/api/preflight'),api('/api/backups')]);renderPreflight(preflight);renderBackups(backups.backups)}catch(err){$('preflightSummary').className='preflight-summary bad';$('preflightSummary').textContent=err.message;toast(err.message,true)}}
async function restoreBackup(backupItem){const extra=backupItem.type==='database'?' Bu yedek kalıcı veri tabanını geri getirir; medya mevcut haliyle kalır.':'';if(!confirm(`${formatBackupDate(backupItem.modified)} tarihli yedeğe dönülsün mü?${extra}\n\nGeri yüklemeden önce mevcut durumun tam yedeği otomatik alınacak.`))return;try{$('saveState').textContent='Yedek geri yükleniyor…';const d=await api('/api/restore',{method:'POST',body:JSON.stringify({name:backupItem.name})});toast('✅ '+d.message);$('saveState').textContent='Yedek geri yüklendi · Commit + Push';const r=await api('/api/products');products=r.products;colors=r.colors||colors;resetForm();await refreshPublishCenter()}catch(err){$('saveState').textContent='Hata';toast(err.message,true)}}
$('publishCheck').onclick=async()=>{$('publishModal').hidden=false;document.body.classList.add('modal-open');await refreshPublishCenter()};
$('refreshPreflight').onclick=refreshPublishCenter;
$('createBackup').onclick=async()=>{try{const d=await api('/api/backup',{method:'POST',body:'{}'});toast('✅ '+d.message);renderBackups(d.backups||[]);await refreshPublishCenter()}catch(err){toast(err.message,true)}};
document.addEventListener('click',e=>{if(e.target.matches('[data-close-publish]')){$('publishModal').hidden=true;document.body.classList.remove('modal-open')}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('publishModal').hidden){$('publishModal').hidden=true;document.body.classList.remove('modal-open')}});

$('openContent').onclick=()=>location.href='content.html';
