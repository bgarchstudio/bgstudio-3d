(() => {
  'use strict';

  const panel = document.querySelector('[data-bg-assistant="v3.3.00"]');
  const trigger = document.querySelector('[data-bg-assistant-trigger]');
  const dataNode = document.querySelector('[data-bg-assistant-data]');
  if (!panel || !trigger || !dataNode) return;

  let data = {};
  try {
    data = JSON.parse(dataNode.textContent || '{}');
  } catch (_) {
    return;
  }

  const closeButton = panel.querySelector('[data-bg-assistant-close]');
  const messages = panel.querySelector('[data-bg-assistant-messages]');
  const form = panel.querySelector('[data-bg-assistant-form]');
  const input = panel.querySelector('[data-bg-assistant-input]');
  const quickButtons = [...panel.querySelectorAll('[data-bg-assistant-prompt]')];
  const handoff = panel.querySelector('[data-bg-assistant-whatsapp]');
  const state = { started: false, lastUser: '' };

  const fold = value => String(value || '')
    .toLocaleLowerCase('tr-TR')
    .replaceAll('ı', 'i')
    .replaceAll('ğ', 'g')
    .replaceAll('ü', 'u')
    .replaceAll('ş', 's')
    .replaceAll('ö', 'o')
    .replaceAll('ç', 'c');

  const tokens = value => fold(value)
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(token => token.length > 1);

  const hasAny = (query, words) => {
    const normalized = fold(query);
    return words.some(word => normalized.includes(fold(word)));
  };

  const makeAction = (label, href) => ({ label, href });

  const addMessage = (role, text, actions = []) => {
    if (!messages) return;
    const row = document.createElement('div');
    row.className = `bg-assistant-message is-${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bg-assistant-bubble';
    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);

    if (actions.length) {
      const actionWrap = document.createElement('div');
      actionWrap.className = 'bg-assistant-message-actions';
      actions.forEach(action => {
        if (!action || !action.href) return;
        const link = document.createElement('a');
        link.href = action.href;
        link.textContent = action.label || 'İncele';
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
    messages.scrollTop = messages.scrollHeight;
  };

  const currentProduct = () => {
    const path = fold(window.location.pathname);
    return (data.products || []).find(product => {
      const slug = fold(product.slug || '');
      return slug && path.includes(`/urunler/${slug}/`);
    }) || null;
  };

  const scoreProduct = (product, query) => {
    const q = fold(query);
    const qTokens = tokens(query);
    const name = fold(product.name);
    const category = fold(product.category);
    const description = fold(product.description);
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
    .filter(item => item.score >= 3)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map(item => item.product);

  const productActions = products => products.map(product =>
    makeAction(`${product.name} · ${product.price}`, product.href)
  );

  const resolve = query => {
    const links = data.links || {};
    const current = currentProduct();
    const matches = productMatches(query);

    const asksPrice = hasAny(query, ['fiyat', 'kaç tl', 'kac tl', 'kaç para', 'kac para', 'ücret', 'ucret']);
    const refersCurrent = hasAny(query, ['bu ürün', 'bu urun', 'bunun', 'şu ürün', 'su urun']);

    if (current && (refersCurrent || (asksPrice && matches.length === 0))) {
      return {
        text: `${current.name} için sitedeki güncel fiyat ${current.price}. Ürün sayfasındaki seçenekleri inceleyebilir veya WhatsApp üzerinden siparişi netleştirebilirsin.`,
        actions: [makeAction('Ürün sayfası', current.href), makeAction('WhatsApp', links.whatsapp)],
      };
    }

    if (matches.length && (asksPrice || hasAny(query, ['ürün', 'urun', 'bul', 'arıyorum', 'ariyorum', 'lamba', 'stand', 'anahtarlık', 'anahtarlik', 'tutucu', 'kask', 'dekor']))) {
      const first = matches[0];
      const intro = matches.length === 1
        ? `${first.name} eşleşiyor. Güncel site fiyatı ${first.price}.`
        : `Katalogda soruna yakın ${matches.length} seçenek buldum.`;
      return { text: intro, actions: productActions(matches) };
    }

    if (hasAny(query, ['nfc', 'qr', 'restoran', 'dijital menü', 'dijital menu', 'feedback', 'google yorum', 'yorum sistemi'])) {
      const year = data.nfc?.year || '';
      return {
        text: `BG Studio NFC + QR sistemi yalnızca dijital menü değil; masa/stand erişimi, feedback, Google devam akışı, sosyal yönlendirmeler ve işletme analitiğini tek yapıda toplar. ${year ? `${year} paket yapısı` : 'Paket yapısı'} sitedeki güncel veriden beslenir.`,
        actions: [makeAction('NFC + QR sistemleri', links.nfc), makeAction('NFC teklifi al', `${links.quote}?tur=nfc`)],
      };
    }

    if (hasAny(query, ['özel üretim', 'ozel uretim', 'kişiye özel', 'kisiye ozel', 'bana özel', 'bana ozel', 'model yaptır', 'tasarım yaptır'])) {
      return {
        text: 'Özel üretimde fikir, görsel, ölçü veya mevcut parçadan ilerleyebiliriz. Uygun işlerde modelleme, üretim planı ve 3D baskı aynı akışta yürütülür.',
        actions: [makeAction('Özel üretimi incele', links.custom), makeAction('Teklif oluştur', `${links.quote}?tur=ozel-uretim`)],
      };
    }

    if (hasAny(query, ['prototip', 'parça', 'parca', 'yedek', 'ölçülü', 'olculu', 'teknik model'])) {
      return {
        text: 'Prototip ve parça üretiminde ölçü, uyum ve işlev önceliklidir. Elinde çizim, fotoğraf, ölçü veya örnek parça varsa teklif sürecinde paylaşabilirsin.',
        actions: [makeAction('Prototip & Parça', links.prototype), makeAction('Teklif oluştur', `${links.quote}?tur=prototip`)],
      };
    }

    if (hasAny(query, ['kurumsal', 'toptan', 'işletme', 'isletme', 'logolu', 'adetli üretim', 'adetli uretim'])) {
      return {
        text: 'Kurumsal tarafta markalı anahtarlık, stand, masaüstü ürün ve işletmeye özel seri üretimler planlanabilir. Adet ve kullanım senaryosu teklifin ana girdileridir.',
        actions: [makeAction('Kurumsal üretim', links.corporate), makeAction('Sahadan projeler', links.projects)],
      };
    }

    if (hasAny(query, ['kargo', 'teslim', 'kuşadası', 'kusadasi', 'elden'])) {
      return {
        text: `${data.delivery?.local || 'Kuşadası elden teslim'} seçeneği bulunur. Gönderime uygun ürünlerde ${data.delivery?.shipping || 'Türkiye geneli kargo'} yapılır.`,
        actions: [makeAction('İletişim', links.contact)],
      };
    }

    if (hasAny(query, ['mimarlık', 'mimarlik', 'architecture', 'render', 'mimari'])) {
      return {
        text: 'Mimarlık ve mimari görselleştirme tarafı BG Studio Architecture altında ilerliyor.',
        actions: [makeAction('BG Studio Architecture', links.architecture)],
      };
    }

    if (asksPrice || hasAny(query, ['teklif', 'fiyatlandır', 'fiyatlandir', 'sipariş', 'siparis'])) {
      return {
        text: 'Hazır ürünlerde güncel fiyatı ürün sayfasında görebilirsin. Özel üretim, kurumsal ve NFC işlerinde kapsam değiştiği için teklif akışı daha doğru sonuç verir.',
        actions: [makeAction('Ürünleri gör', links.products), makeAction('Teklif al', links.quote)],
      };
    }

    if (hasAny(query, ['whatsapp', 'iletişim', 'iletisim', 'konuşalım', 'konusalim'])) {
      return { text: 'WhatsApp üzerinden doğrudan BG Studio 3D ile devam edebilirsin.', actions: [makeAction('WhatsApp’a geç', links.whatsapp)] };
    }

    if (matches.length) {
      return { text: 'Katalogda soruna yakın ürünler buldum.', actions: productActions(matches) };
    }

    return {
      text: 'Ürün seçimi, NFC + QR sistemleri, özel üretim, prototip, kurumsal işler ve teklif sürecinde yardımcı olabilirim. Konuyu biraz daha tarif edersen doğru sayfaya yönlendireyim.',
      actions: [makeAction('Ürünler', links.products), makeAction('NFC + QR', links.nfc), makeAction('Özel üretim', links.custom), makeAction('Teklif', links.quote)],
    };
  };

  const start = () => {
    if (state.started) return;
    state.started = true;
    addMessage('assistant', 'Selam 👋 BG Studio 3D ürünleri, özel üretim, prototip, kurumsal çözümler ve NFC + QR sistemlerinde yol gösterebilirim. Bir şey yaz veya aşağıdan seç.');
  };

  const openPanel = () => {
    panel.hidden = false;
    panel.setAttribute('aria-hidden', 'false');
    trigger.setAttribute('aria-expanded', 'true');
    document.body.classList.add('bg-assistant-open');
    start();
    window.setTimeout(() => input?.focus({ preventScroll: true }), 60);
  };

  const closePanel = () => {
    panel.hidden = true;
    panel.setAttribute('aria-hidden', 'true');
    trigger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('bg-assistant-open');
    trigger.focus({ preventScroll: true });
  };

  const submitQuery = query => {
    const clean = String(query || '').trim();
    if (!clean) return;
    state.lastUser = clean;
    addMessage('user', clean);
    const response = resolve(clean);
    window.setTimeout(() => addMessage('assistant', response.text, response.actions), 120);
  };

  trigger.addEventListener('click', () => panel.hidden ? openPanel() : closePanel());
  closeButton?.addEventListener('click', closePanel);

  form?.addEventListener('submit', event => {
    event.preventDefault();
    const value = input?.value || '';
    if (input) input.value = '';
    submitQuery(value);
  });

  quickButtons.forEach(button => {
    button.addEventListener('click', () => submitQuery(button.dataset.bgAssistantPrompt || button.textContent));
  });

  handoff?.addEventListener('click', () => {
    const topic = state.lastUser || 'BG Studio 3D ürün ve hizmetleri hakkında bilgi almak istiyorum.';
    const message = `Merhaba BG Studio 3D, sitedeki BG Assistant üzerinden şu konuda bilgi aldım: ${topic}`;
    window.open(`https://wa.me/905302466903?text=${encodeURIComponent(message)}`, '_blank', 'noopener');
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) closePanel();
  });
})();
