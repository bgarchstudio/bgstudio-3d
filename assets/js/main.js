const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href || window.location.href;


// Google Analytics helper. gtag is defined in every page head and queues events until GA4 loads.
const trackEvent = (name, params = {}) => {
  if (typeof window.gtag === 'function') {
    window.gtag('event', name, params);
  }
};

const analyticsProductContext = () => {
  const config = document.querySelector('[data-order-config]');
  if (!config) return null;
  const itemName = config.dataset.productName || document.querySelector('.product-info h1')?.textContent?.trim() || 'Ürün';
  const itemId = canonicalUrl.match(/\/urunler\/([^/]+)\/?$/)?.[1] || itemName;
  const priceText = config.dataset.productPrice || '';
  const numeric = Number(String(priceText).replace(/[^0-9,]/g, '').replace(',', '.')) || undefined;
  return { item_name: itemName, item_id: itemId, price: numeric };
};

let initialAnalyticsTracked = false;
const trackInitialAnalyticsContext = () => {
  if (initialAnalyticsTracked || typeof window.gtag !== 'function') return;
  const product = analyticsProductContext();
  if (product) {
    const item = { item_id: product.item_id, item_name: product.item_name };
    if (product.price) item.price = product.price;
    const payload = { currency: 'TRY', items: [item] };
    if (product.price) payload.value = product.price;
    trackEvent('view_item', payload);
  }
  initialAnalyticsTracked = true;
};
trackInitialAnalyticsContext();
window.addEventListener('bg-consent-granted', trackInitialAnalyticsContext);

// Track high-intent outbound actions without changing navigation behavior.
document.addEventListener('click', (event) => {
  const link = event.target.closest?.('a[href]');
  if (!link) return;
  const href = link.getAttribute('href') || '';
  if (href.includes('wa.me/')) {
    // Dedicated order/quick-contact buttons have richer event payloads below; avoid double counting.
    if (link.classList.contains('floating-whatsapp') && link.getAttribute('aria-haspopup') === 'dialog') return;
    if (link.matches('[data-order-whatsapp],[data-mobile-order-whatsapp],.wa-panel-send')) return;
    const payload = {
      method: 'whatsapp_generic',
      link_text: (link.textContent || '').trim().slice(0, 100),
      page_location: canonicalUrl
    };
    trackEvent('whatsapp_click', payload);
    trackEvent('generate_lead', payload);
  } else if (href.includes('instagram.com/bgstudio.3dtr')) {
    trackEvent('social_click', {
      network: 'instagram',
      link_text: (link.textContent || '').trim().slice(0, 100),
      page_location: canonicalUrl
    });
  } else if (href.includes('facebook.com/bgstudio.3dtr')) {
    trackEvent('social_click', {
      network: 'facebook',
      link_text: (link.textContent || '').trim().slice(0, 100),
      page_location: canonicalUrl
    });
  }
});

// Mobile navigation
const setMenuState = (open) => {
  if (!nav || !menuButton) return;
  nav.classList.toggle('open', open);
  menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
  menuButton.setAttribute('aria-label', open ? 'Menüyü kapat' : 'Menüyü aç');
  document.body.classList.toggle('nav-open', open);
};

menuButton?.addEventListener('click', () => setMenuState(!nav?.classList.contains('open')));
document.querySelectorAll('.main-nav a').forEach(link => link.addEventListener('click', () => setMenuState(false)));
document.addEventListener('click', (event) => {
  if (!nav?.classList.contains('open')) return;
  if (nav.contains(event.target) || menuButton?.contains(event.target)) return;
  setMenuState(false);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && nav?.classList.contains('open')) {
    setMenuState(false);
    menuButton?.focus();
  }
});
window.addEventListener('resize', () => {
  if (window.innerWidth > 1040 && nav?.classList.contains('open')) setMenuState(false);
}, { passive: true });

// Reveal animations with graceful fallback
const revealItems = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealItems.forEach(el => observer.observe(el));
} else {
  revealItems.forEach(el => el.classList.add('visible'));
}

// Product catalog filters + live search
const filterButtons = document.querySelectorAll('.filter-btn');
const catalogCards = document.querySelectorAll('.catalog-grid .product-card');
const productSearch = document.querySelector('#product-search');
const catalogCount = document.querySelector('#catalog-count');
const catalogEmpty = document.querySelector('#catalog-empty');
if (catalogCards.length) {
  let activeFilter = 'all';
  let searchTerm = '';
  const normalize = (value) => String(value || '').toLocaleLowerCase('tr-TR').trim();
  const applyCatalog = () => {
    let visible = 0;
    catalogCards.forEach(card => {
      const categoryOK = activeFilter === 'all' || card.dataset.category === activeFilter;
      const searchOK = !searchTerm || normalize(card.dataset.search || card.textContent).includes(searchTerm);
      const show = categoryOK && searchOK;
      card.classList.toggle('hidden', !show);
      card.setAttribute('aria-hidden', show ? 'false' : 'true');
      if (show) visible += 1;
    });
    filterButtons.forEach(btn => {
      const active = btn.dataset.filter === activeFilter;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    if (catalogCount) catalogCount.textContent = `${visible} ürün gösteriliyor`;
    if (catalogEmpty) catalogEmpty.hidden = visible !== 0;
    try {
      const url = new URL(window.location.href);
      if (activeFilter !== 'all') url.searchParams.set('kategori', activeFilter); else url.searchParams.delete('kategori');
      if (searchTerm && productSearch) url.searchParams.set('q', productSearch.value.trim()); else url.searchParams.delete('q');
      history.replaceState({}, '', url);
    } catch (_) {}
  };
  filterButtons.forEach(btn => btn.addEventListener('click', () => {
    activeFilter = btn.dataset.filter || 'all';
    applyCatalog();
  }));
  productSearch?.addEventListener('input', () => {
    searchTerm = normalize(productSearch.value);
    applyCatalog();
  });
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('kategori');
  if (requested && [...filterButtons].some(btn => btn.dataset.filter === requested)) activeFilter = requested;
  const query = params.get('q');
  if (query && productSearch) {
    productSearch.value = query;
    searchTerm = normalize(query);
  }
  applyCatalog();
}

// Product image lightbox
const zoomableMedia = document.querySelectorAll('.zoomable-media');
if (zoomableMedia.length) {
  const lightbox = document.createElement('div');
  lightbox.className = 'image-lightbox';
  lightbox.setAttribute('role', 'dialog');
  lightbox.setAttribute('aria-modal', 'true');
  lightbox.setAttribute('aria-label', 'Ürün görseli');
  lightbox.hidden = true;

  const close = document.createElement('button');
  close.type = 'button';
  close.setAttribute('aria-label', 'Görseli kapat');
  close.textContent = '×';
  const img = document.createElement('img');
  img.alt = '';
  lightbox.append(img, close);
  document.body.append(lightbox);
  let returnFocus = null;

  const closeBox = () => {
    lightbox.classList.remove('open');
    lightbox.hidden = true;
    document.body.style.overflow = '';
    returnFocus?.focus?.();
  };
  const openBox = (media) => {
    const source = media.querySelector('img');
    if (!source) return;
    returnFocus = media;
    img.src = source.currentSrc || source.src;
    img.alt = source.alt || 'Ürün görseli';
    lightbox.hidden = false;
    requestAnimationFrame(() => lightbox.classList.add('open'));
    document.body.style.overflow = 'hidden';
    close.focus();
  };

  zoomableMedia.forEach(media => {
    media.addEventListener('click', () => openBox(media));
    media.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openBox(media);
      }
    });
  });
  close.addEventListener('click', closeBox);
  lightbox.addEventListener('click', event => { if (event.target === lightbox) closeBox(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !lightbox.hidden) closeBox();
  });
}

// Back to top
const backToTop = document.querySelector('.back-to-top');
if (backToTop) {
  const updateTopButton = () => backToTop.classList.toggle('show', window.scrollY > 650);
  window.addEventListener('scroll', updateTopButton, { passive: true });
  updateTopButton();
  backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// Static-site quote form -> WhatsApp handoff
const quoteForm = document.querySelector('[data-quote-form]');
if (quoteForm) {
  const params = new URLSearchParams(window.location.search);
  const requestedType = params.get('tur');
  const typeSelect = quoteForm.querySelector('[name="talep_turu"]');
  if (requestedType && typeSelect && [...typeSelect.options].some(option => option.value === requestedType)) typeSelect.value = requestedType;
  quoteForm.addEventListener('submit', event => {
    event.preventDefault();
    if (!quoteForm.reportValidity()) return;
    const data = new FormData(quoteForm);
    const labels = {
      'kisiye-ozel': 'Kişiye özel üretim',
      'kurumsal': 'Kurumsal / toplu üretim',
      'nfc': 'NFC & QR sistemi',
      'urun': 'Mevcut ürün hakkında',
      'diger': 'Diğer'
    };
    const lines = [
      'Merhaba BG Studio 3D, web sitesinden bir talep oluşturuyorum.',
      '',
      `Talep türü: ${labels[data.get('talep_turu')] || data.get('talep_turu')}`,
      `Ad / Soyad: ${data.get('ad') || '-'}`,
      `İşletme / Marka: ${data.get('isletme') || '-'}`,
      `Adet: ${data.get('adet') || '-'}`,
      `Şehir: ${data.get('sehir') || '-'}`,
      '',
      `Talep: ${data.get('detay') || '-'}`
    ];
    const leadPayload = {
      method: 'quote_form_whatsapp',
      lead_type: data.get('talep_turu') || 'unknown',
      page_location: canonicalUrl
    };
    trackEvent('quote_request', leadPayload);
    trackEvent('generate_lead', leadPayload);
    window.open('https://wa.me/905302466903?text=' + encodeURIComponent(lines.join('\n')), '_blank', 'noopener');
  });
}

// Product gallery switcher
const galleryMain = document.querySelector('[data-gallery-main]');
const galleryStage = document.querySelector('[data-gallery-stage]');
const galleryThumbs = document.querySelectorAll('[data-gallery-src]');
if (galleryMain && galleryThumbs.length) {
  galleryThumbs.forEach(btn => btn.addEventListener('click', () => {
    galleryMain.src = btn.dataset.gallerySrc || galleryMain.src;
    galleryMain.alt = btn.dataset.galleryAlt || '';
    galleryStage?.setAttribute('aria-label', `${galleryMain.alt || 'Ürün görseli'} büyüt`);
    galleryThumbs.forEach(item => {
      const active = item === btn;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }));
}

// Share product URL. Canonical URL prevents local file paths from being shared during PC testing.
const shareProduct = document.querySelector('.share-product');
if (shareProduct) {
  const originalText = shareProduct.textContent;
  shareProduct.addEventListener('click', async () => {
    const title = shareProduct.dataset.shareTitle || document.title;
    try {
      if (navigator.share && location.protocol.startsWith('http')) {
        await navigator.share({ title, url: canonicalUrl });
        trackEvent('share', { method: 'native_share', content_type: 'product', item_id: canonicalUrl });
        return;
      }
      await navigator.clipboard.writeText(canonicalUrl);
      trackEvent('share', { method: 'copy_link', content_type: 'product', item_id: canonicalUrl });
      shareProduct.textContent = 'Link kopyalandı ✓';
      shareProduct.classList.add('copied');
      setTimeout(() => {
        shareProduct.textContent = originalText;
        shareProduct.classList.remove('copied');
      }, 1800);
    } catch (_) {
      shareProduct.textContent = 'Link: 3d.bgstudio.com.tr';
      setTimeout(() => { shareProduct.textContent = originalText; }, 1800);
    }
  });
}

// Smart product order configurator
const orderConfig = document.querySelector('[data-order-config]');
if (orderConfig) {
  const name = orderConfig.dataset.productName || document.querySelector('.product-info h1')?.textContent?.trim() || 'Ürün';
  const price = orderConfig.dataset.productPrice || '';
  const option = orderConfig.querySelector('[data-order-option]');
  const qty = orderConfig.querySelector('[data-order-qty]');
  const note = orderConfig.querySelector('[data-order-note]');
  const summary = orderConfig.querySelector('[data-order-summary]');
  const send = orderConfig.querySelector('[data-order-whatsapp]');
  const mobileSend = document.querySelector('[data-mobile-order-whatsapp]');
  const choiceBtns = document.querySelectorAll('[data-order-choice]');

  const clampQty = () => {
    let value = parseInt(qty?.value || '1', 10);
    if (!Number.isFinite(value)) value = 1;
    value = Math.min(99, Math.max(1, value));
    if (qty) qty.value = value;
    return value;
  };
  const buildMessage = () => {
    const amount = clampQty();
    const selected = option?.value || 'Standart';
    if (summary) summary.textContent = `${selected} • ${amount} adet`;
    const lines = [
      'Merhaba BG Studio 3D, web sitesinden sipariş için yazıyorum.',
      '',
      `Ürün: ${name}`,
      `Seçenek: ${selected}`,
      `Adet: ${amount}`,
      price ? `Sayfadaki fiyat: ${price}` : '',
      note?.value.trim() ? `Not: ${note.value.trim()}` : '',
      '',
      `Ürün sayfası: ${canonicalUrl}`
    ].filter(Boolean);
    const href = 'https://wa.me/905302466903?text=' + encodeURIComponent(lines.join('\n'));
    if (send) send.href = href;
    if (mobileSend) mobileSend.href = href;
  };
  const trackProductOrder = () => {
    const amount = clampQty();
    const selected = option?.value || 'Standart';
    const product = analyticsProductContext();
    const payload = {
      method: 'product_order_whatsapp',
      item_id: product?.item_id || name,
      item_name: product?.item_name || name,
      option: selected,
      quantity: amount,
      page_location: canonicalUrl
    };
    if (product?.price) { payload.value = product.price * amount; payload.currency = 'TRY'; }
    trackEvent('whatsapp_order', payload);
    trackEvent('generate_lead', payload);
  };
  send?.addEventListener('click', trackProductOrder);
  mobileSend?.addEventListener('click', trackProductOrder);

  orderConfig.querySelector('[data-qty-minus]')?.addEventListener('click', () => {
    if (qty) qty.value = clampQty() - 1;
    clampQty();
    buildMessage();
  });
  orderConfig.querySelector('[data-qty-plus]')?.addEventListener('click', () => {
    if (qty) qty.value = clampQty() + 1;
    clampQty();
    buildMessage();
  });
  qty?.addEventListener('input', buildMessage);
  option?.addEventListener('change', () => {
    choiceBtns.forEach(btn => btn.classList.toggle('selected', btn.dataset.orderChoice === option.value));
    buildMessage();
  });
  note?.addEventListener('input', buildMessage);
  choiceBtns.forEach(btn => btn.addEventListener('click', () => {
    if (option) option.value = btn.dataset.orderChoice;
    choiceBtns.forEach(item => item.classList.toggle('selected', item === btn));
    buildMessage();
  }));
  mobileSend?.addEventListener('click', event => {
    if (mobileSend.getAttribute('href') === '#') {
      event.preventDefault();
      orderConfig.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  buildMessage();
}

// Navigation active state
const normalizePath = (url) => {
  try {
    const parsed = new URL(url, window.location.href);
    let path = parsed.pathname.replace(/\/index\.html$/, '/');
    if (!path.endsWith('/') && !/\.[a-z0-9]+$/i.test(path)) path += '/';
    return path;
  } catch (_) {
    return '';
  }
};
document.querySelectorAll('.main-nav a[href]').forEach(link => {
  const href = link.getAttribute('href') || '';
  if (href.startsWith('http') || href.startsWith('https://wa.me')) return;
  const current = normalizePath(link.href) === normalizePath(window.location.href);
  if (current) {
    link.setAttribute('aria-current', 'page');
    link.classList.add('is-active');
  }
});

// Footer year
const currentYear = String(new Date().getFullYear());
document.querySelectorAll('[data-current-year]').forEach(el => { el.textContent = currentYear; });

// Clean legacy index.html URLs without reloading the page.
(() => {
  const { pathname, search, hash } = window.location;
  if (/\/index\.html$/i.test(pathname)) {
    const cleanPath = pathname.replace(/index\.html$/i, "");
    window.history.replaceState(null, "", `${cleanPath}${search}${hash}`);
  }
})();


// v1.4 — Brand-family icon treatment and Architecture-inspired WhatsApp quick panel.
document.querySelectorAll('a[href*="wa.me/"]').forEach(link => link.classList.add('has-brand-icon', 'icon-whatsapp'));
document.querySelectorAll('a[href*="instagram.com/bgstudio.3dtr"]').forEach(link => link.classList.add('has-brand-icon', 'icon-instagram'));
document.querySelectorAll('a[href*="facebook.com/bgstudio.3dtr"]').forEach(link => link.classList.add('has-brand-icon', 'icon-facebook'));
document.querySelectorAll('a[href^="https://bgstudio.com.tr"]').forEach(link => {
  if (!link.closest('.footer-socials')) link.classList.add('has-brand-icon', 'icon-architecture');
});

const floatingWhatsApp = document.querySelector('.floating-whatsapp');
if (floatingWhatsApp) {
  const originalHref = floatingWhatsApp.href;
  const productName = document.querySelector('.product-info h1')?.textContent?.trim();
  const defaultMessage = productName
    ? `Merhaba BG Studio 3D, ${productName} hakkında bilgi almak istiyorum.`
    : 'Merhaba BG Studio 3D, web sitenizden yazıyorum. Ürün ve üretim seçenekleri hakkında bilgi almak istiyorum.';
  const options = [
    ['Ürün siparişi', productName ? `Merhaba BG Studio 3D, ${productName} hakkında bilgi almak istiyorum.` : 'Merhaba BG Studio 3D, bir ürün hakkında bilgi almak istiyorum.'],
    ['Kişiye özel üretim', 'Merhaba BG Studio 3D, kişiye özel 3D baskı üretim için teklif almak istiyorum.'],
    ['Toplu / kurumsal', 'Merhaba BG Studio 3D, işletmem için toplu veya kurumsal üretim hakkında görüşmek istiyorum.'],
    ['NFC & QR', 'Merhaba BG Studio 3D, NFC & QR sistemleri hakkında bilgi almak istiyorum.']
  ];

  const panel = document.createElement('aside');
  panel.className = 'wa-quick-panel';
  panel.setAttribute('aria-label', 'WhatsApp hızlı iletişim');
  panel.setAttribute('aria-hidden', 'true');
  panel.innerHTML = `
    <div class="wa-panel-head">
      <div><h2>Merhaba 👋</h2><p>Ürün, özel üretim veya işletme çözümü için mesajını birkaç saniyede hazırla.</p></div>
      <button class="wa-panel-close" type="button" aria-label="WhatsApp panelini kapat">×</button>
    </div>
    <span class="wa-panel-label">HIZLI SEÇENEKLER</span>
    <div class="wa-panel-options"></div>
    <div class="wa-panel-message" aria-live="polite"></div>
    <a class="wa-panel-send has-brand-icon icon-whatsapp" target="_blank" rel="noopener">WhatsApp'ta Gönder</a>
    <p class="wa-panel-meta">Ortalama yanıt süresi: aynı gün içinde</p>`;
  document.body.append(panel);

  const messageBox = panel.querySelector('.wa-panel-message');
  const sendLink = panel.querySelector('.wa-panel-send');
  const optionWrap = panel.querySelector('.wa-panel-options');
  const closeButton = panel.querySelector('.wa-panel-close');
  let selectedContactType = productName ? 'product' : 'general';
  const setMessage = (message, activeButton = null, contactType = selectedContactType) => {
    selectedContactType = contactType;
    messageBox.textContent = message;
    sendLink.href = 'https://wa.me/905302466903?text=' + encodeURIComponent(message);
    optionWrap.querySelectorAll('.wa-panel-option').forEach(btn => btn.classList.toggle('active', btn === activeButton));
  };
  setMessage(defaultMessage);
  const contactTypeMap = ['product', 'custom_production', 'corporate', 'nfc_qr'];
  options.forEach(([label, message], index) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'wa-panel-option';
    btn.textContent = label;
    btn.addEventListener('click', () => setMessage(message, btn, contactTypeMap[index] || 'general'));
    optionWrap.append(btn);
  });
  sendLink.addEventListener('click', () => {
    const payload = { method: 'quick_whatsapp_panel', contact_type: selectedContactType, page_location: canonicalUrl };
    if (productName) payload.item_name = productName;
    trackEvent('whatsapp_quick_contact', payload);
    trackEvent('generate_lead', payload);
  });

  const setPanel = (open) => {
    panel.classList.toggle('open', open);
    panel.setAttribute('aria-hidden', open ? 'false' : 'true');
    floatingWhatsApp.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) trackEvent('whatsapp_panel_open', { page_location: canonicalUrl });
  };
  floatingWhatsApp.setAttribute('aria-haspopup', 'dialog');
  floatingWhatsApp.setAttribute('aria-expanded', 'false');
  floatingWhatsApp.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    setPanel(!panel.classList.contains('open'));
  });
  closeButton.addEventListener('click', () => { setPanel(false); floatingWhatsApp.focus(); });
  document.addEventListener('click', event => {
    if (!panel.classList.contains('open')) return;
    if (panel.contains(event.target) || floatingWhatsApp.contains(event.target)) return;
    setPanel(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && panel.classList.contains('open')) {
      setPanel(false);
      floatingWhatsApp.focus();
    }
  });
}

// v2.2.1 — Playfair Display renders a very decorative ampersand.
// Replace only ampersands inside display headings with a clean brand-safe glyph.
const normalizeHeadingAmpersands = (root = document) => {
  const headings = root?.matches?.('h1,h2,h3') ? [root] : [...(root?.querySelectorAll?.('h1,h2,h3') || [])];
  headings.forEach((heading) => {
    if (!heading.textContent?.includes('&')) return;
    const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.parentElement?.classList.contains('plain-amp')) continue;
      if (node.nodeValue?.includes('&')) nodes.push(node);
    }
    nodes.forEach((node) => {
      const parts = node.nodeValue.split('&');
      const fragment = document.createDocumentFragment();
      parts.forEach((part, index) => {
        if (part) fragment.append(document.createTextNode(part));
        if (index < parts.length - 1) {
          const amp = document.createElement('span');
          amp.className = 'plain-amp';
          amp.textContent = '&';
          fragment.append(amp);
        }
      });
      node.replaceWith(fragment);
    });
  });
};
normalizeHeadingAmpersands();
