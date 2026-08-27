
// v2.4.1 — direct/search-engine landings should start at the top, not at a restored footer position.
(() => {
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  const goTop = () => {
    if (!window.location.hash) window.scrollTo({top:0,left:0,behavior:'auto'});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', goTop, {once:true});
  else goTop();
  window.addEventListener('pageshow', event => { if (!event.persisted) goTop(); });
})();

// v3.1.17 — stronger managed-reference deep jump.
// “İşi incele” links now land on the exact managed card on every listing page,
// including NFC & QR. Native anchor jumps are normalized and then re-positioned
// with repeated center/alignment passes so the target never stays clipped under
// the sticky header on desktop or mobile.
(() => {
  const STORE_KEY = 'bgstudio3d.referenceJump.v3';
  const clean = value => String(value || '').trim().toLocaleLowerCase('tr-TR').replace(/\s+/g, ' ');
  const cssEsc = value => {
    try { return CSS.escape(String(value || '')); }
    catch (_) { return String(value || '').replace(/[\"\\]/g, '\\$&'); }
  };
  const canonicalFromHash = value => String(value || '').replace(/^#/, '').replace(/^referans-/, '').trim();
  const normalizedPath = value => {
    const raw = String(value || '').trim() || '/';
    const noOrigin = raw.replace(/^https?:\/\/[^/]+/i, '');
    const noIndex = noOrigin.replace(/\/index\.html$/i, '/');
    const tidy = noIndex.replace(/\/+/g, '/').replace(/\/$/, '');
    return tidy || '/';
  };

  const findTarget = data => {
    const id = canonicalFromHash(data?.id || data?.key || data?.ref || '');
    const hashKey = id ? 'referans-' + id : String(data?.key || '');
    if (id) {
      try {
        const byIdentity = document.querySelector(`.case-card[data-reference-id="${cssEsc(id)}"]`);
        if (byIdentity) return byIdentity;
      } catch (_) {}
      const byId = document.getElementById(hashKey) || document.getElementById(id);
      if (byId) return byId;
    }

    const wantedName = clean(data?.name);
    if (wantedName) {
      const cards = [...document.querySelectorAll('.case-card')];
      const exactName = cards.find(card => clean(card.dataset.referenceName) === wantedName);
      if (exactName) return exactName;
      const headingName = cards.find(card => clean(card.querySelector('.case-identity .case-type')?.textContent) === wantedName || clean(card.querySelector('h3')?.textContent) === wantedName);
      if (headingName) return headingName;
    }

    const wantedHeadline = clean(data?.headline);
    if (!wantedHeadline) return null;
    return [...document.querySelectorAll('.case-card')].find(card => clean(card.querySelector('h3')?.textContent) === wantedHeadline)
      || [...document.querySelectorAll('.case-card')].find(card => {
        const title = clean(card.querySelector('h3')?.textContent);
        return title && (title.includes(wantedHeadline) || wantedHeadline.includes(title));
      }) || null;
  };

  const headerHeight = () => {
    const header = document.querySelector('.site-header');
    if (!header) return 0;
    return Math.max(0, Math.round(header.getBoundingClientRect().height));
  };

  const viewportGap = () => (window.innerWidth <= 760 ? 14 : 18);

  const computeScrollTop = target => {
    const header = headerHeight();
    const gap = viewportGap();
    const rect = target.getBoundingClientRect();
    const usableHeight = Math.max(120, window.innerHeight - header - gap * 2);
    const targetTopAbs = window.scrollY + rect.top;
    const desiredTop = rect.height <= usableHeight
      ? header + gap + Math.max(0, (usableHeight - rect.height) / 2)
      : header + gap;
    const docMax = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    return Math.max(0, Math.min(docMax, Math.round(targetTopAbs - desiredTop)));
  };

  const highlightTarget = target => {
    target.classList.add('reference-jump-focus');
    window.clearTimeout(target.__bgRefFocusTimer);
    target.__bgRefFocusTimer = window.setTimeout(() => target.classList.remove('reference-jump-focus'), 1700);
  };

  const placeTarget = target => {
    if (!target) return false;
    const top = computeScrollTop(target);
    window.scrollTo({ top, left: 0, behavior: 'auto' });
    highlightTarget(target);
    return true;
  };

  const jump = data => {
    const target = findTarget(data);
    if (!target) return false;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => placeTarget(target)));
    return true;
  };

  const scheduleJump = data => {
    if (!data) return;
    document.documentElement.classList.add('reference-jump-active');
    // Neutralize native anchor placement first, then center precisely.
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    [0, 40, 120, 260, 520, 900, 1400, 2100].forEach(delay => window.setTimeout(() => jump(data), delay));

    const target = findTarget(data);
    if (target && typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver(() => placeTarget(target));
      ro.observe(target);
      window.setTimeout(() => ro.disconnect(), 2400);
    }

    const imgs = [...document.querySelectorAll('.case-card img')];
    imgs.forEach(img => {
      if (img.complete) return;
      img.addEventListener('load', () => jump(data), { once: true });
      img.addEventListener('error', () => jump(data), { once: true });
    });
  };

  const buildPayloadFromLink = link => {
    const card = link.closest('.field-work-card, .case-card, [data-reference-id], [data-reference-target]');
    let url;
    try { url = new URL(link.href, window.location.href); } catch (_) { return null; }
    const id = card?.dataset.referenceId || canonicalFromHash(url.hash) || canonicalFromHash(card?.dataset.referenceTarget);
    const name = card?.dataset.referenceName || card?.querySelector('.case-profile img')?.alt?.replace(/\s+profil(?:\s+fotoğrafı|\s+görseli)?$/i, '') || '';
    const headline = card?.querySelector('h3')?.textContent?.trim() || '';
    const pathname = normalizedPath(url.pathname);
    return { id, ref: id, key: id ? 'referans-' + id : canonicalFromHash(url.hash), name, headline, pathname, at: Date.now() };
  };

  document.addEventListener('click', event => {
    const link = event.target.closest('.field-work-link, a[href*="#referans-"]');
    if (!link) return;
    const payload = buildPayloadFromLink(link);
    if (!payload?.id) return;

    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(payload)); } catch (_) {}

    let url;
    try { url = new URL(link.href, window.location.href); } catch (_) { return; }
    if (/^https?:$/.test(url.protocol) && url.origin === window.location.origin) {
      event.preventDefault();
      url.hash = 'referans-' + payload.id;
      url.searchParams.set('ref', payload.id);
      window.location.assign(url.href);
    }
  }, true);

  const resolveIncomingJump = () => {
    const params = new URLSearchParams(window.location.search);
    const hashRaw = decodeURIComponent((window.location.hash || '').replace(/^#/, ''));
    const hashId = canonicalFromHash(hashRaw);
    const queryRef = canonicalFromHash(params.get('ref') || '');
    let stored = null;
    try { stored = JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null'); } catch (_) {}
    const currentPath = normalizedPath(window.location.pathname);
    const storedIsFresh = stored && Date.now() - Number(stored.at || 0) < 60000;
    const storedMatches = storedIsFresh && normalizedPath(stored.pathname || '/') === currentPath;

    const id = hashId || queryRef || canonicalFromHash(stored?.id || '');
    const payload = id
      ? { ...(storedMatches ? stored : {}), id, ref: id, key: 'referans-' + id }
      : (storedMatches ? stored : null);
    if (!payload?.id) return;
    scheduleJump(payload);
    window.setTimeout(() => {
      try { sessionStorage.removeItem(STORE_KEY); } catch (_) {}
      if (params.has('ref')) {
        params.delete('ref');
        const qs = params.toString();
        const nextUrl = `${window.location.pathname}${qs ? '?' + qs : ''}${window.location.hash || ('#referans-' + payload.id)}`;
        history.replaceState(null, '', nextUrl);
      }
    }, 2600);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', resolveIncomingJump, { once: true });
  else resolveIncomingJump();
  window.addEventListener('load', resolveIncomingJump, { once: true });
  window.addEventListener('pageshow', resolveIncomingJump);
  window.addEventListener('hashchange', resolveIncomingJump);
})();

const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href || window.location.href;

const DEFAULT_ANNOUNCEMENT_BAR_CONFIG = {
  enabled: true,
  speed: 'normal',
  direction: 'rtl',
  separator: '✦',
  messages: [
    { text: '1.000 TL üzeri ücretsiz kargo', url: '', enabled: true },
    { text: 'Kuşadası elden teslim', url: '', enabled: true },
    { text: 'Kişiye özel 3D üretim', url: '/ozel-uretim/', enabled: true },
    { text: 'Kurumsal toplu sipariş', url: '/kurumsal/', enabled: true },
    { text: 'NFC + QR işletme çözümleri', url: '/nfc-qr/', enabled: true }
  ]
};

const announcementPixelsPerSecond = speed => ({ slow: 55, normal: 85, fast: 130 }[String(speed || '').toLowerCase()] || 85);

const safeAnnouncementHref = value => {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (/^(?:javascript|data|vbscript):/i.test(raw)) return '';
  if (raw.startsWith('/') || raw.startsWith('#') || /^https?:\/\//i.test(raw)) return raw;
  return '/' + raw.replace(/^\/+/, '');
};

const loadAnnouncementBarConfig = async () => {
  try {
    const response = await fetch('/data/site_settings.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('site settings unavailable');
    const settings = await response.json();
    const config = settings?.announcement_bar;
    if (!config || typeof config !== 'object') throw new Error('announcement settings unavailable');
    return config;
  } catch (_) {
    return DEFAULT_ANNOUNCEMENT_BAR_CONFIG;
  }
};

const mountAnnouncementBar = async () => {
  const header = document.querySelector('.site-header');
  const navShell = header?.querySelector('.nav-shell');
  if (!header || !navShell || header.querySelector('.announcement-marquee')) return;

  const config = await loadAnnouncementBarConfig();
  if (config?.enabled === false) return;
  const messages = (Array.isArray(config?.messages) ? config.messages : [])
    .filter(item => item && item.enabled !== false && String(item.text || '').trim())
    .slice(0, 30);
  if (!messages.length) return;

  const separator = '✦';
  const direction = ['rtl', 'ltr'].includes(String(config?.direction || '').toLowerCase()) ? String(config.direction).toLowerCase() : 'rtl';
  const makeSequence = duplicate => messages.map(item => {
    const text = String(item.text || '').trim();
    const safeText = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
    const href = safeAnnouncementHref(item.url);
    let itemHtml = '';
    if (!href) itemHtml = `<span class="announcement-marquee-item">${safeText}</span>`;
    else {
      const external = /^https?:\/\//i.test(href) && !href.startsWith(window.location.origin);
      const attrs = duplicate ? ' tabindex="-1"' : '';
      const target = external ? ' target="_blank" rel="noopener"' : '';
      const safeHref = href.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      itemHtml = `<a class="announcement-marquee-item is-link" href="${safeHref}"${target}${attrs}>${safeText}</a>`;
    }
    // A trailing separator is intentional. It makes the boundary between the end
    // of one segment and the beginning of the next visually identical to every
    // internal boundary, so the animation never looks like it restarts.
    return `${itemHtml}<span class="announcement-marquee-separator" aria-hidden="true">${separator}</span>`;
  }).join('');

  const bar = document.createElement('div');
  bar.className = 'announcement-marquee';
  bar.dataset.direction = direction;
  bar.setAttribute('role', 'region');
  bar.setAttribute('aria-label', 'Kampanya ve duyuru şeridi');
  const announcementSpeed = announcementPixelsPerSecond(config?.speed);
  bar.dataset.speed = String(config?.speed || 'normal').toLowerCase();
  bar.innerHTML = `
    <div class="announcement-marquee-viewport">
      <div class="announcement-marquee-track">
        <div class="announcement-marquee-group" data-marquee-primary></div>
        <div class="announcement-marquee-group" data-marquee-clone aria-hidden="true"></div>
      </div>
    </div>`;

  header.insertBefore(bar, navShell);

  const viewport = bar.querySelector('.announcement-marquee-viewport');
  const primary = bar.querySelector('[data-marquee-primary]');
  const clone = bar.querySelector('[data-marquee-clone]');
  const firstSequence = makeSequence(false);
  const duplicateSequence = makeSequence(true);
  primary.innerHTML = firstSequence;
  clone.innerHTML = duplicateSequence;

  // Build two pixel-identical segments and move by the EXACT measured width
  // of one segment. This avoids the small percentage/sub-pixel jump that can
  // appear on mobile when a -50% transform is rounded differently.
  let lastViewportWidth = 0;
  let resizeTimer = 0;
  const fitSegments = (force = false) => {
    const viewportWidth = Math.max(1, Math.round(viewport.getBoundingClientRect().width));
    if (!force && Math.abs(viewportWidth - lastViewportWidth) < 4) return;
    lastViewportWidth = viewportWidth;

    primary.innerHTML = firstSequence;
    clone.innerHTML = duplicateSequence;

    requestAnimationFrame(() => {
      const baseWidth = Math.max(1, primary.scrollWidth);
      // Keep each half comfortably wider than the viewport. The extra headroom
      // prevents mobile browser chrome changes from exposing an empty edge.
      const targetWidth = Math.max(viewportWidth * 1.35, viewportWidth + 120);
      const repeats = Math.max(1, Math.ceil(targetWidth / baseWidth));
      primary.innerHTML = firstSequence + duplicateSequence.repeat(repeats - 1);
      clone.innerHTML = duplicateSequence.repeat(repeats);

      requestAnimationFrame(() => {
        const segmentWidth = Math.max(1, primary.scrollWidth);
        const duration = Math.max(4, segmentWidth / announcementSpeed);
        bar.style.setProperty('--announcement-distance', `${segmentWidth}px`);
        bar.style.setProperty('--announcement-duration', `${duration.toFixed(3)}s`);
      });
    });
  };

  fitSegments(true);
  if (typeof ResizeObserver === 'function') {
    const observer = new ResizeObserver(() => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => fitSegments(false), 140);
    });
    observer.observe(viewport);
  }
};

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { mountAnnouncementBar(); }, { once: true });
else mountAnnouncementBar();



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
      'prototip': 'Prototip / parça üretimi',
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
      `Yaklaşık ölçü / ebat: ${data.get('olcu') || '-'}`,
      `Renk / malzeme: ${data.get('renk') || '-'}`,
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
  const fallbackPriceText = orderConfig.dataset.productPrice || '';
  const basePriceValue = Number(String(orderConfig.dataset.productBasePriceValue || '').replace(',', '.')) || 0;
  const option = orderConfig.querySelector('[data-order-option]');
  const tier = orderConfig.querySelector('[data-order-tier]');
  const qty = orderConfig.querySelector('[data-order-qty]');
  const note = orderConfig.querySelector('[data-order-note]');
  const summary = orderConfig.querySelector('[data-order-summary]');
  const send = orderConfig.querySelector('[data-order-whatsapp]');
  const mobileSend = document.querySelector('[data-mobile-order-whatsapp]');
  const priceDisplay = document.querySelector('[data-product-price-display]');
  const mobilePrice = document.querySelector('[data-mobile-price]');
  const discountListPrices = document.querySelectorAll('[data-discount-list-price]');
  const discountBadges = document.querySelectorAll('[data-discount-badge]');
  const tierBtns = document.querySelectorAll('[data-order-tier-choice]');
  const colorSlotsWrap = orderConfig.querySelector('[data-order-color-slots]');
  const colorDataNode = orderConfig.querySelector('[data-product-colors]');
  let colorOptions = [];
  try { colorOptions = colorDataNode ? JSON.parse(colorDataNode.textContent || '[]') : []; } catch (_) { colorOptions = []; }
  let colorSelections = [];

  const formatTL = value => {
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    return new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 }).format(n) + ' TL';
  };
  const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const clampQty = () => {
    let value = parseInt(qty?.value || '1', 10);
    if (!Number.isFinite(value)) value = 1;
    value = Math.min(12, Math.max(1, value));
    if (qty) qty.value = value;
    return value;
  };
  const selectedTier = () => {
    const opt = tier?.selectedOptions?.[0];
    if (!opt) return null;
    const packQty = parseInt(opt.dataset.tierQty || '1', 10) || 1;
    const packPrice = Number(String(opt.dataset.tierPrice || '').replace(',', '.'));
    return {
      index: opt.value,
      label: opt.dataset.tierLabel || opt.textContent.trim(),
      packQty,
      packPrice: Number.isFinite(packPrice) ? packPrice : 0,
      priceLabel: opt.dataset.tierPriceLabel || (Number.isFinite(packPrice) ? formatTL(packPrice) : '')
    };
  };
  const totalItemCount = () => {
    const amount = clampQty();
    const t = selectedTier();
    return Math.max(1, (t ? t.packQty : 1) * amount);
  };
  const syncTierUi = () => {
    const t = selectedTier();
    const baseSaleSelected = !t || t.packQty === 1;
    discountListPrices.forEach(el => { el.hidden = !baseSaleSelected; });
    discountBadges.forEach(el => { el.hidden = !baseSaleSelected; });
    tierBtns.forEach(btn => {
      const active = !!t && btn.dataset.orderTierChoice === t.index;
      btn.classList.toggle('selected', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    const label = t?.priceLabel || (basePriceValue ? formatTL(basePriceValue) : fallbackPriceText);
    if (priceDisplay && label) priceDisplay.textContent = label;
    if (mobilePrice && label) mobilePrice.textContent = label;
  };
  const renderColorSlots = () => {
    if (!colorSlotsWrap || !colorOptions.length) return;
    const count = totalItemCount();
    const previous = colorSelections.slice();
    colorSelections = Array.from({ length: count }, (_, i) => previous[i] || colorOptions[0]?.name || '');
    colorSlotsWrap.innerHTML = colorSelections.map((selected, index) => {
      const buttons = colorOptions.map(color => {
        const active = color.name === selected;
        return `<button type="button" class="color-choice${active ? ' selected' : ''}" data-color-slot="${index}" data-color-name="${escapeHtml(color.name)}" aria-pressed="${active ? 'true' : 'false'}"><i style="--swatch:${escapeHtml(color.hex || '#c7b9a6')}"></i><span>${escapeHtml(color.name)}</span></button>`;
      }).join('');
      return `<div class="color-slot"><div class="color-slot-title"><strong>${index + 1}. ürün</strong><span data-color-slot-value="${index}">${escapeHtml(selected)}</span></div><div class="color-choice-grid">${buttons}</div></div>`;
    }).join('');
    colorSlotsWrap.querySelectorAll('.color-choice').forEach(btn => {
      btn.addEventListener('click', () => {
        const index = Number(btn.dataset.colorSlot || 0);
        colorSelections[index] = btn.dataset.colorName || colorOptions[0]?.name || '';
        const slot = btn.closest('.color-slot');
        slot?.querySelectorAll('.color-choice').forEach(item => {
          const active = item === btn;
          item.classList.toggle('selected', active);
          item.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
        const value = slot?.querySelector('[data-color-slot-value]');
        if (value) value.textContent = colorSelections[index];
        buildMessage(false);
      });
    });
  };
  const colorSummaryText = () => {
    if (!colorSelections.length) return '';
    if (colorSelections.length === 1) return colorSelections[0];
    return colorSelections.map((color, i) => `${i + 1}. ${color}`).join(' / ');
  };
  const buildMessage = (refreshColors = false) => {
    const amount = clampQty();
    const selected = option?.value || '';
    const t = selectedTier();
    const totalItems = t ? t.packQty * amount : amount;
    let totalValue = basePriceValue ? basePriceValue * amount : 0;
    if (t) totalValue = t.packPrice * amount;
    if (refreshColors && colorOptions.length) renderColorSlots();
    const colors = colorSummaryText();
    const summaryParts = [];
    if (selected) summaryParts.push(selected);
    if (t) summaryParts.push(`${t.label} • ${amount} set (${totalItems} adet)`);
    else summaryParts.push(`${amount} adet`);
    if (colors) summaryParts.push(colors);
    if (totalValue) summaryParts.push(formatTL(totalValue));
    if (summary) summary.textContent = summaryParts.join(' • ');

    const lines = [
      'Merhaba BG Studio 3D, web sitesinden sipariş için yazıyorum.',
      '',
      `Ürün: ${name}`,
      selected ? `Seçenek: ${selected}` : '',
      t ? `Paket: ${t.label}` : '',
      t ? `Paket adedi: ${amount}` : `Adet: ${amount}`,
      t ? `Toplam ürün: ${totalItems} adet` : '',
      colorSelections.length === 1 ? `Renk: ${colorSelections[0]}` : '',
      colorSelections.length > 1 ? 'Renkler:' : '',
      ...colorSelections.map((color, i) => colorSelections.length > 1 ? `  ${i + 1}. ürün: ${color}` : '').filter(Boolean),
      t && t.packPrice ? `Paket fiyatı: ${formatTL(t.packPrice)}` : '',
      totalValue ? `Toplam: ${formatTL(totalValue)}` : (fallbackPriceText ? `Sayfadaki fiyat: ${fallbackPriceText}` : ''),
      note?.value.trim() ? `Not: ${note.value.trim()}` : '',
      '',
      `Ürün sayfası: ${canonicalUrl}`
    ].filter(Boolean);
    const href = 'https://wa.me/905302466903?text=' + encodeURIComponent(lines.join('\n'));
    if (send) send.href = href;
    if (mobileSend) mobileSend.href = href;
    syncTierUi();
  };
  const trackProductOrder = () => {
    const amount = clampQty();
    const selected = option?.value || '';
    const t = selectedTier();
    const product = analyticsProductContext();
    const totalItems = t ? t.packQty * amount : amount;
    const totalValue = t?.packPrice ? t.packPrice * amount : (product?.price ? product.price * amount : basePriceValue * amount);
    const payload = {
      method: 'product_order_whatsapp',
      item_id: product?.item_id || name,
      item_name: product?.item_name || name,
      option: selected || undefined,
      colors: colorSelections.length ? colorSelections.join(' | ') : undefined,
      quantity: totalItems,
      set_count: t ? amount : undefined,
      set_label: t?.label || undefined,
      page_location: canonicalUrl
    };
    if (totalValue) { payload.value = totalValue; payload.currency = 'TRY'; }
    trackEvent('whatsapp_order', payload);
    trackEvent('generate_lead', payload);
  };
  send?.addEventListener('click', trackProductOrder);
  mobileSend?.addEventListener('click', trackProductOrder);

  orderConfig.querySelector('[data-qty-minus]')?.addEventListener('click', () => {
    if (qty) qty.value = clampQty() - 1;
    clampQty();
    buildMessage(true);
  });
  orderConfig.querySelector('[data-qty-plus]')?.addEventListener('click', () => {
    if (qty) qty.value = clampQty() + 1;
    clampQty();
    buildMessage(true);
  });
  qty?.addEventListener('input', () => buildMessage(true));
  option?.addEventListener('change', () => buildMessage(false));
  tier?.addEventListener('change', () => buildMessage(true));
  note?.addEventListener('input', () => buildMessage(false));
  tierBtns.forEach(btn => btn.addEventListener('click', () => {
    if (tier) tier.value = btn.dataset.orderTierChoice;
    buildMessage(true);
  }));
  mobileSend?.addEventListener('click', event => {
    if (mobileSend.getAttribute('href') === '#') {
      event.preventDefault();
      orderConfig.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
  if (colorOptions.length) renderColorSlots();
  buildMessage(false);
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
  if (!link.closest('.footer-socials') && !link.classList.contains('brand-branch-card')) {
    link.classList.add('has-brand-icon', 'icon-architecture');
  }
});

if (document.querySelector('.mobile-product-cta')) document.body.classList.add('has-mobile-product-cta');

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
    ['Prototip / parça', 'Merhaba BG Studio 3D, prototip veya yedek parça üretimi için görüşmek istiyorum. Parçanın fotoğrafını ve yaklaşık ölçülerini paylaşacağım.'],
    ['NFC & QR', 'Merhaba BG Studio 3D, NFC & QR sistemleri hakkında bilgi almak istiyorum.']
  ];

  const panel = document.createElement('aside');
  panel.className = 'wa-quick-panel';
  panel.setAttribute('aria-label', 'WhatsApp hızlı iletişim');
  panel.setAttribute('aria-hidden', 'true');
  panel.innerHTML = `
    <div class="wa-panel-head">
      <div><h2>Merhaba 👋</h2><p>Ürün, özel üretim, prototip veya işletme çözümü için mesajını birkaç saniyede hazırla.</p></div>
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
  const contactTypeMap = ['product', 'custom_production', 'corporate', 'prototype_part', 'nfc_qr'];
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

  const seenKey = 'bgstudio-wa-seen-v1';
  try { if (sessionStorage.getItem(seenKey)) floatingWhatsApp.classList.add('wa-seen'); } catch (_) {}
  floatingWhatsApp.title = 'WhatsApp ile hızlı iletişim';
  const setPanel = (open) => {
    panel.classList.toggle('open', open);
    panel.setAttribute('aria-hidden', open ? 'false' : 'true');
    floatingWhatsApp.classList.toggle('is-open', open);
    floatingWhatsApp.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      floatingWhatsApp.classList.add('wa-seen');
      try { sessionStorage.setItem(seenKey, '1'); } catch (_) {}
      trackEvent('whatsapp_panel_open', { page_location: canonicalUrl });
    }
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

// v2.4 — Playfair Display has an ornamental ampersand.
// Normalize any ampersand rendered with the display serif, not only h1/h2/h3.
const normalizeDisplayAmpersands = (root = document) => {
  const candidates = root?.matches?.('h1,h2,h3,h4,a,span,strong,p') ? [root] : [...(root?.querySelectorAll?.('h1,h2,h3,h4,a,span,strong,p') || [])];
  candidates.forEach((el) => {
    if (!el.textContent?.includes('&') || el.querySelector?.('.plain-amp')) return;
    const family = getComputedStyle(el).fontFamily || '';
    if (!family.toLowerCase().includes('playfair')) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) { const node = walker.currentNode; if (node.nodeValue?.includes('&')) nodes.push(node); }
    nodes.forEach((node) => {
      const parts = node.nodeValue.split('&'); const fragment = document.createDocumentFragment();
      parts.forEach((part, index) => {
        if (part) fragment.append(document.createTextNode(part));
        if (index < parts.length - 1) { const amp = document.createElement('span'); amp.className='plain-amp'; amp.textContent='&'; fragment.append(amp); }
      });
      node.replaceWith(fragment);
    });
  });
};
normalizeDisplayAmpersands();
const displayAmpObserver = new MutationObserver((mutations) => mutations.forEach((m) => {
  if (m.type === 'characterData') normalizeDisplayAmpersands(m.target.parentElement);
  m.addedNodes?.forEach((node) => { if (node.nodeType === 1) normalizeDisplayAmpersands(node); });
}));
displayAmpObserver.observe(document.body,{subtree:true,childList:true,characterData:true});

// v2.8.2 — navigation self-heal: every page must expose the same Prototip & Parça Üretim tab.
(() => {
  const normalizePrototypeNav = () => {
    const nav = document.querySelector('.main-nav');
    if (!nav) return;
    const links = [...nav.querySelectorAll('a[href]')];
    let prototypeLink = links.find(a => (a.getAttribute('href') || '').includes('prototip-parca/'));
    const nfcLink = links.find(a => (a.getAttribute('href') || '').includes('nfc-qr/'));
    if (!prototypeLink && nfcLink) {
      prototypeLink = document.createElement('a');
      prototypeLink.href = (nfcLink.getAttribute('href') || '').replace('nfc-qr/', 'prototip-parca/');
      nfcLink.insertAdjacentElement('afterend', prototypeLink);
    }
    if (!prototypeLink) return;
    prototypeLink.textContent = 'Prototip & Parça Üretim';

    // Active state is also repaired from the URL so static pages cannot drift visually.
    const path = window.location.pathname.replace(/index\.html$/, '');
    const routeMap = [
      ['/urunler/', 'urunler/'],
      ['/ozel-uretim/', 'ozel-uretim/'],
      ['/kurumsal/', 'kurumsal/'],
      ['/nfc-qr/', 'nfc-qr/'],
      ['/prototip-parca/', 'prototip-parca/'],
      ['/hakkimizda/', 'hakkimizda/'],
      ['/iletisim/', 'iletisim/']
    ];
    const matched = routeMap.find(([route]) => path.includes(route));
    if (matched) {
      nav.querySelectorAll('a[aria-current="page"],a.is-active').forEach(a => {
        a.removeAttribute('aria-current');
        a.classList.remove('is-active');
      });
      const active = [...nav.querySelectorAll('a[href]')].find(a => (a.getAttribute('href') || '').includes(matched[1]));
      if (active) {
        active.setAttribute('aria-current', 'page');
        active.classList.add('is-active');
      }
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', normalizePrototypeNav, { once:true });
  else normalizePrototypeNav();
})();
