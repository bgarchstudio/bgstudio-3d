(() => {
  'use strict';

  const panel = document.querySelector('[data-bg-assistant="v3.3.01"]');
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
  const endpoint = window.BG_ASSISTANT_ENDPOINT || data.assistant_api?.endpoint || '/api/bg-assistant';
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
    const bubble = document.createElement('div');
    bubble.className = 'bg-assistant-bubble';
    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);

    if (actions.length) {
      const actionWrap = document.createElement('div');
      actionWrap.className = 'bg-assistant-message-actions';
      actions.forEach(action => {
        if (!action?.href) return;
        const link = document.createElement('a');
        link.href = action.href;
        link.textContent = action.label || 'İncele';
        if (/^https?:\/\//i.test(action.href)) { link.target = '_blank'; link.rel = 'noopener'; }
        actionWrap.appendChild(link);
      });
      bubble.appendChild(actionWrap);
    }

    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
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

    if (hasAny(query, ['merhaba','selam','selamlar','hey','sa','günaydın','gunaydin','iyi akşamlar','iyi aksamlar'])) {
      return { text: 'Merhaba 👋 BG Studio 3D ürünleri, NFC + QR sistemleri, özel üretim ve teklif sürecinde yardımcı olabilirim. Ne bakıyorsun?', actions: [] };
    }
    if (current && (refersCurrent || (asksPrice && matches.length === 0))) {
      return { text: `${current.name} için sitedeki güncel fiyat ${current.price}.`, actions: [makeAction('Ürün sayfası', current.href), makeAction('WhatsApp', links.whatsapp)] };
    }
    if (matches.length && (asksPrice || hasAny(query, ['ürün','urun','bul','arıyorum','ariyorum','lamba','stand','anahtarlık','anahtarlik','tutucu','kask','dekor']))) {
      const first = matches[0];
      return { text: matches.length === 1 ? `${first.name} eşleşiyor. Güncel site fiyatı ${first.price}.` : `Katalogda soruna yakın ${matches.length} seçenek buldum.`, actions: productActions(matches) };
    }
    if (hasAny(query, ['nfc','qr','restoran','dijital menü','dijital menu','feedback','google yorum','yorum sistemi'])) {
      return { text: 'BG Studio NFC + QR sistemi menü, feedback, Google devam akışı, sosyal yönlendirmeler ve işletme analitiğini tek yapıda toplar.', actions: [makeAction('NFC + QR sistemleri', links.nfc), makeAction('NFC teklifi al', `${links.quote}?tur=nfc`)] };
    }
    if (hasAny(query, ['özel üretim','ozel uretim','kişiye özel','kisiye ozel','bana özel','bana ozel','model yaptır','tasarım yaptır'])) {
      return { text: 'Özel üretimde fikir, görsel, ölçü veya mevcut parçadan ilerleyebiliriz.', actions: [makeAction('Özel üretimi incele', links.custom), makeAction('Teklif oluştur', `${links.quote}?tur=ozel-uretim`)] };
    }
    if (hasAny(query, ['prototip','parça','parca','yedek','ölçülü','olculu','teknik model'])) {
      return { text: 'Prototip ve parça üretiminde ölçü, uyum ve işlev önceliklidir.', actions: [makeAction('Prototip & Parça', links.prototype), makeAction('Teklif oluştur', `${links.quote}?tur=prototip`)] };
    }
    if (hasAny(query, ['kurumsal','toptan','işletme','isletme','logolu','adetli üretim','adetli uretim'])) {
      return { text: 'Kurumsal tarafta markalı ve işletmeye özel seri üretimler planlanabilir.', actions: [makeAction('Kurumsal üretim', links.corporate), makeAction('Sahadan projeler', links.projects)] };
    }
    if (hasAny(query, ['kargo','teslim','kuşadası','kusadasi','elden'])) {
      return { text: `${data.delivery?.local || 'Kuşadası elden teslim'} seçeneği bulunur. Gönderime uygun ürünlerde ${data.delivery?.shipping || 'Türkiye geneli kargo'} yapılır.`, actions: [makeAction('İletişim', links.contact)] };
    }
    if (hasAny(query, ['mimarlık','mimarlik','architecture','render','mimari'])) {
      return { text: 'Mimarlık ve mimari görselleştirme tarafı BG Studio Architecture altında ilerliyor.', actions: [makeAction('BG Studio Architecture', links.architecture)] };
    }
    if (asksPrice || hasAny(query, ['teklif','fiyatlandır','fiyatlandir','sipariş','siparis'])) {
      return { text: 'Hazır ürünlerde fiyat ürün sayfasında görünür. Özel üretim, kurumsal ve NFC işlerinde teklif akışı daha doğru sonuç verir.', actions: [makeAction('Ürünleri gör', links.products), makeAction('Teklif al', links.quote)] };
    }
    if (hasAny(query, ['whatsapp','iletişim','iletisim','konuşalım','konusalim'])) {
      return { text: 'WhatsApp üzerinden doğrudan BG Studio 3D ile devam edebilirsin.', actions: [makeAction('WhatsApp’a geç', links.whatsapp)] };
    }
    if (matches.length) return { text: 'Katalogda soruna yakın ürünler buldum.', actions: productActions(matches) };
    return { text: 'Ürün seçimi, NFC + QR, özel üretim, prototip, kurumsal işler ve teklif sürecinde yardımcı olabilirim.', actions: [makeAction('Ürünler', links.products), makeAction('NFC + QR', links.nfc), makeAction('Özel üretim', links.custom), makeAction('Teklif', links.quote)] };
  };

  const setBusy = busy => {
    state.busy = busy;
    if (input) input.disabled = busy;
    if (sendButton) sendButton.disabled = busy;
    panel.classList.toggle('is-thinking', busy);
  };

  const compactCatalog = () => (data.products || []).slice(0, 40).map(product => ({
    name: product.name, category: product.category, price: product.price,
    description: String(product.description || '').slice(0, 220),
    href: product.href, personalizable: Boolean(product.personalizable)
  }));

  const askOpenAI = async message => {
    const payload = {
      message,
      history: state.history.slice(-8),
      page: { path: window.location.pathname, title: document.title },
      context: {
        products: compactCatalog(), nfc: data.nfc || {}, delivery: data.delivery || {}, links: data.links || {}
      }
    };
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 18000);
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'same-origin',
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
    addMessage('assistant', 'Merhaba 👋 Ben BG Assistant. Ürünler, NFC + QR, özel üretim ve teklif tarafında yardımcı olabilirim. Ne hakkında konuşalım?');
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
    const pending = addMessage('assistant', 'Yanıt hazırlanıyor…', [], 'is-pending');
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
