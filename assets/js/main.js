const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href || window.location.href;

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
        return;
      }
      await navigator.clipboard.writeText(canonicalUrl);
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
