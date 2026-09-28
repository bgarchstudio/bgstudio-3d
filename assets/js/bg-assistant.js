(() => {
  'use strict';

  const panel = document.querySelector('[data-bg-assistant="v3.3.03"]');
  const trigger = document.querySelector('[data-bg-assistant-trigger]');
  const dataNode = document.querySelector('[data-bg-assistant-data]');
  if (!panel || !trigger || !dataNode) return;

  let data = {};
  try { data = JSON.parse(dataNode.textContent || '{}'); } catch (_) { return; }

  const closeButton = panel.querySelector('[data-bg-assistant-close]');
  const messages = panel.querySelector('[data-bg-assistant-messages]');
  const form = panel.querySelector('[data-bg-assistant-form]');
  const input = panel.querySelector('[data-bg-assistant-input]');
  const sendButton = panel.querySelector('.bg-assistant-send');
  const quickButtons = [...panel.querySelectorAll('[data-bg-assistant-prompt]')];
  const handoff = panel.querySelector('[data-bg-assistant-whatsapp]');
  const endpoint = window.BG_ASSISTANT_ENDPOINT || data.assistant_api?.endpoint || 'https://ai.bgstudio.com.tr/api/bg-assistant';
  const brandLogo = document.querySelector('.bg-assistant-mark img')?.getAttribute('src') || 'assets/brand/bgstudio3d-monogram.webp';
  const state = { started: false, lastUser: '', busy: false, history: [] };

  const fold = value => String(value || '')
    .toLocaleLowerCase('tr-TR')
    .replaceAll('ı', 'i').replaceAll('ğ', 'g').replaceAll('ü', 'u')
    .replaceAll('ş', 's').replaceAll('ö', 'o').replaceAll('ç', 'c');

  const tokens = value => fold(value).replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(t => t.length > 1);
  const hasAny = (query, words) => {
    const normalized = fold(query);
    return words.some(word => normalized.includes(fold(word)));
  };
  const makeAction = (label, href) => ({ label, href });

  const addMessage = (role, text, actions = [], extraClass = '') => {
    const row = document.createElement('div');
    row.className = `bg-assistant-message is-${role}${extraClass ? ` ${extraClass}` : ''}`;

    if (role === 'assistant') {
      const avatar = document.createElement('span');
      avatar.className = 'bg-assistant-message-avatar';
      const img = document.createElement('img');
      img.src = brandLogo;
      img.alt = '';
      img.decoding = 'async';
      avatar.appendChild(img);
      row.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'bg-assistant-bubble';

    if (extraClass === 'is-pending') {
      const dots = document.createElement('span');
      dots.className = 'bg-assistant-typing';
      dots.setAttribute('aria-label', text || 'Yanıt hazırlanıyor');
      dots.innerHTML = '<i></i><i></i><i></i>';
      bubble.appendChild(dots);
    } else {
      const p = document.createElement('p');
      p.textContent = text;
      bubble.appendChild(p);
    }

    if (actions.length) {
      const actionWrap = document.createElement('div');
      actionWrap.className = 'bg-assistant-message-actions';
      actions.forEach(action => {
        if (!action?.href) return;
        const link = document.createElement('a');
        link.href = action.href;
        const label = document.createElement('span');
        label.textContent = action.label || 'İncele';
        const arrow = document.createElement('b');
        arrow.setAttribute('aria-hidden', 'true');
        arrow.textContent = '↗';
        link.append(label, arrow);
        if (/^https?:\/\//i.test(action.href)) {
          link.target = '_blank';
          link.rel = 'noopener';
        }
        actionWrap.appendChild(link);
      });
      bubble.appendChild(actionWrap);
    }

    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTo({ top: messages.scrollHeight, behavior: 'smooth' });
    return row;
  };

  const currentProduct = () => {
    const path = fold(window.location.pathname);
    return (data.products || []).find(product => {
      const slug = fold(product.slug || '');
      return slug && path.includes(`/urunler/${slug}/`);
    }) || null;
  };

  const scoreProduct = (product, query) => {
    const q = fold(query), qTokens = tokens(query);
    const name = fold(product.name), category = fold(product.category), description = fold(product.description);
    let score = 0;
    if (name && q.includes(name)) score += 18;
    if (product.slug && q.includes(fold(product.slug))) score += 12;
    qTokens.forEach(token => {
      if (name.includes(token)) score += 4;
      if (category.includes(token)) score += 2;
      if (description.includes(token)) score += 1;
    });
    if (hasAny(query, ['kişiselleştir', 'kisisellestir', 'isimli', 'özel isim']) && product.personalizable) score += 3;
    return score;
  };

  const productMatches = query => (data.products || [])
    .map(product => ({ product, score: scoreProduct(product, query) }))
    .filter(item => item.score >= 3).sort((a,b) => b.score - a.score).slice(0,3).map(item => item.product);
  const productActions = products => products.map(product => makeAction(`${product.name} · ${product.price}`, product.href));

  // Deterministic site links remain available even when OpenAI is unavailable.
  const localResolve = query => {
    const links = data.links || {};
    const current = currentProduct();
    const matches = productMatches(query);
    const asksPrice = hasAny(query, ['fiyat','kaç tl','kac tl','kaç para','kac para','ücret','ucret']);
    const refersCurrent = hasAny(query, ['bu ürün','bu urun','bunun','şu ürün','su urun']);

    if (hasAny(query, ['merhaba','selam','selamlar','hey','sa','günaydın','gunaydin','iyi akşamlar','iyi aksamlar','naber'])) {
      return { text: 'Merhaba 👋 Buradayım. Ürün, NFC + QR, 3D baskı, malzeme, özel üretim, prototip, kurumsal üretim veya teklif hakkında sorabilirsin.', actions: [] };
    }
    if (hasAny(query, ['nfc nedir','nfc ne','nfc nasıl','nfc nasil','nfc ne işe','nfc ne ise'])) {
      return { text: data.nfc?.definition || 'NFC, uyumlu telefonu etikete veya standa yaklaştırınca bağlantı ya da dijital içeriği temassız açabilen kısa menzilli iletişim teknolojisidir.', actions: [makeAction('BG Studio NFC + QR', links.nfc)] };
    }
    if (hasAny(query, ['qr nedir','qr ne','nfc qr fark','qr nfc fark'])) {
      return { text: data.nfc?.qr_definition || 'QR kamerayla taranır; NFC ise uyumlu telefonu etikete veya standa yaklaştırarak çalışır. İkisi aynı hedefe alternatif erişim sağlayabilir.', actions: [makeAction('NFC + QR sistemleri', links.nfc)] };
    }
    if (hasAny(query, ['3d baskı nedir','3d baski nedir','3d yazıcı','3d yazici','fdm nedir'])) {
      return { text: data.services?.['3d_printing_general'] || '3D baskı, dijital bir modeli katman katman fiziksel parçaya dönüştüren üretim yöntemidir. FDM baskıda katman dokusu doğal olarak görülebilir.', actions: [makeAction('Ürünler', links.products), makeAction('Özel üretim', links.custom)] };
    }
    if (hasAny(query, ['pla petg','petg pla','pla nedir','petg nedir','malzeme fark'])) {
      return { text: 'PLA genelde kolay baskı ve iyi yüzey kalitesiyle öne çıkar. PETG ise kullanım senaryosuna göre daha yüksek dayanım ve neme karşı avantaj sağlayabilir. Belirli ürün için ürün kaydındaki malzemeyi esas alırım.', actions: [makeAction('Ürünleri incele', links.products)] };
    }
    if (current && (refersCurrent || (asksPrice && matches.length === 0))) {
      return { text: `${current.name} için sitedeki güncel fiyat ${current.price}.`, actions: [makeAction('Ürün sayfası', current.href), makeAction('WhatsApp', links.whatsapp)] };
    }
    if (matches.length && (asksPrice || hasAny(query, ['ürün','urun','bul','arıyorum','ariyorum','lamba','stand','anahtarlık','anahtarlik','tutucu','kask','dekor']))) {
      const first = matches[0];
      return { text: matches.length === 1 ? `${first.name} eşleşiyor. Güncel site fiyatı ${first.price}.` : `Katalogda soruna yakın ${matches.length} seçenek buldum.`, actions: productActions(matches) };
    }
    if (hasAny(query, ['nfc','qr','restoran','dijital menü','dijital menu','feedback','google yorum','yorum sistemi'])) {
      return { text: data.nfc?.system_summary || 'BG Studio NFC + QR sistemi menü, feedback, sosyal yönlendirmeler ve işletme analitiğini tek yapıda toplar.', actions: [makeAction('NFC + QR sistemleri', links.nfc), makeAction('NFC teklifi al', `${links.quote}?tur=nfc`)] };
    }
    if (hasAny(query, ['özel üretim','ozel uretim','kişiye özel','kisiye ozel','bana özel','bana ozel','model yaptır','tasarım yaptır'])) {
      return { text: data.services?.custom_production || 'Özel üretimde fikir, görsel, ölçü veya mevcut parçadan ilerleyebiliriz.', actions: [makeAction('Özel üretimi incele', links.custom), makeAction('Teklif oluştur', `${links.quote}?tur=ozel-uretim`)] };
    }
    if (hasAny(query, ['prototip','parça','parca','yedek','ölçülü','olculu','teknik model'])) {
      return { text: data.services?.prototype || 'Prototip ve parça üretiminde ölçü, uyum ve işlev önceliklidir.', actions: [makeAction('Prototip & Parça', links.prototype), makeAction('Teklif oluştur', `${links.quote}?tur=prototip`)] };
    }
    if (hasAny(query, ['kurumsal','toptan','işletme','isletme','logolu','adetli üretim','adetli uretim'])) {
      return { text: data.services?.corporate || 'Kurumsal tarafta markalı ve işletmeye özel seri üretimler planlanabilir.', actions: [makeAction('Kurumsal üretim', links.corporate), makeAction('Sahadan projeler', links.projects)] };
    }
    if (hasAny(query, ['kargo','teslim','kuşadası','kusadasi','elden'])) {
      return { text: `${data.delivery?.local || 'Kuşadası elden teslim'} seçeneği bulunur. Gönderime uygun ürünlerde ${data.delivery?.shipping || 'Türkiye geneli kargo'} yapılır.`, actions: [makeAction('İletişim', links.contact)] };
    }
    if (hasAny(query, ['mimarlık','mimarlik','architecture','render','mimari'])) {
      return { text: 'Mimarlık ve mimari görselleştirme tarafı BG Studio Architecture altında ilerliyor.', actions: [makeAction('BG Studio Architecture', links.architecture)] };
    }
    if (asksPrice || hasAny(query, ['teklif','fiyatlandır','fiyatlandir','sipariş','siparis'])) {
      return { text: 'Hazır ürünlerde fiyat ürün sayfasında görünür. Özel üretim, kurumsal ve NFC işlerinde kapsam değiştiği için teklif akışı daha doğru sonuç verir.', actions: [makeAction('Ürünleri gör', links.products), makeAction('Teklif al', links.quote)] };
    }
    if (hasAny(query, ['whatsapp','iletişim','iletisim','konuşalım','konusalim'])) {
      return { text: 'WhatsApp üzerinden doğrudan BG Studio 3D ile devam edebilirsin.', actions: [makeAction('WhatsApp’a geç', links.whatsapp)] };
    }
    if (matches.length) return { text: 'Katalogda soruna yakın ürünler buldum.', actions: productActions(matches) };
    return { text: 'Sorunu biraz daha detaylandırırsan yardımcı olayım. BG Studio ürünleri ve hizmetlerinin yanında NFC, QR ve temel 3D baskı konularını da açıklayabilirim.', actions: [makeAction('Ürünler', links.products), makeAction('NFC + QR', links.nfc), makeAction('Teklif', links.quote)] };
  };

  const setBusy = busy => {
    state.busy = busy;
    if (input) input.disabled = busy;
    if (sendButton) sendButton.disabled = busy;
    panel.classList.toggle('is-thinking', busy);
  };

  const compactCatalog = () => (data.products || []).slice(0, 60).map(product => ({
    name: product.name,
    category: product.category,
    price: product.price,
    description: String(product.description || '').slice(0, 300),
    href: product.href,
    personalizable: Boolean(product.personalizable),
    materials: product.materials || [],
    features: product.features || [],
    tags: product.tags || [],
    dimensions: product.dimensions || '',
    production_time: product.production_time || '',
    technical_info: product.technical_info || '',
    usage_info: product.usage_info || '',
    personalization_info: product.personalization_info || '',
    pricing_tiers: product.pricing_tiers || [],
    production_status: product.production_status || ''
  }));

  const askOpenAI = async message => {
    const payload = {
      message,
      history: state.history.slice(-8),
      page: { path: window.location.pathname, title: document.title },
      context: {
        business: data.business || {},
        products: compactCatalog(),
        nfc: data.nfc || {},
        services: data.services || {},
        references: data.references || {},
        faq: data.faq || [],
        delivery: data.delivery || {},
        links: data.links || {}
      }
    };
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 25000);
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'omit',
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json?.text) throw new Error(json?.error || `HTTP ${response.status}`);
      return String(json.text).trim();
    } finally {
      window.clearTimeout(timer);
    }
  };

  const start = () => {
    if (state.started) return;
    state.started = true;
    addMessage('assistant', 'Merhaba 👋 Ben BG Assistant. BG Studio 3D ürünlerini ve sistemlerini biliyorum; NFC, QR ve 3D baskı gibi genel konuları da sorabilirsin. Ne hakkında konuşalım?');
  };

  const openPanel = () => {
    panel.hidden = false; panel.setAttribute('aria-hidden','false'); trigger.setAttribute('aria-expanded','true');
    document.body.classList.add('bg-assistant-open'); start();
    window.setTimeout(() => input?.focus({ preventScroll: true }), 60);
  };
  const closePanel = () => {
    panel.hidden = true; panel.setAttribute('aria-hidden','true'); trigger.setAttribute('aria-expanded','false');
    document.body.classList.remove('bg-assistant-open'); trigger.focus({ preventScroll: true });
  };

  const submitQuery = async query => {
    const clean = String(query || '').trim().slice(0, 600);
    if (!clean || state.busy) return;
    state.lastUser = clean;
    addMessage('user', clean);
    const fallback = localResolve(clean);
    state.history.push({ role: 'user', content: clean });
    setBusy(true);
    const pending = addMessage('assistant', 'Yanıt hazırlanıyor', [], 'is-pending');
    try {
      const aiText = await askOpenAI(clean);
      pending.remove();
      addMessage('assistant', aiText, fallback.actions || []);
      state.history.push({ role: 'assistant', content: aiText });
    } catch (error) {
      console.warn('[BG Assistant] OpenAI endpoint unavailable, local fallback used.', error);
      pending.remove();
      addMessage('assistant', fallback.text, fallback.actions || []);
      state.history.push({ role: 'assistant', content: fallback.text });
    } finally {
      state.history = state.history.slice(-10);
      setBusy(false);
      window.setTimeout(() => input?.focus({ preventScroll: true }), 30);
    }
  };

  trigger.addEventListener('click', () => panel.hidden ? openPanel() : closePanel());
  closeButton?.addEventListener('click', closePanel);
  form?.addEventListener('submit', event => {
    event.preventDefault();
    const value = input?.value || '';
    if (input) input.value = '';
    submitQuery(value);
  });
  quickButtons.forEach(button => button.addEventListener('click', () => submitQuery(button.dataset.bgAssistantPrompt || button.textContent)));
  handoff?.addEventListener('click', () => {
    const topic = state.lastUser || 'BG Studio 3D ürün ve hizmetleri hakkında bilgi almak istiyorum.';
    const message = `Merhaba BG Studio 3D, sitedeki BG Assistant üzerinden şu konuda bilgi aldım: ${topic}`;
    window.open(`https://wa.me/905302466903?text=${encodeURIComponent(message)}`, '_blank', 'noopener');
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) closePanel(); });
})();
