/* BG Studio 3D homepage motion v3.1.83 */
(() => {
  const home = document.querySelector('.home-v3163');
  if (!home) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const motionItems = [...home.querySelectorAll('[data-home-motion]')];

  if (!reduceMotion && motionItems.length) {
    document.documentElement.classList.add('home-motion-ready');
    const observer = new IntersectionObserver((entries, io) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in-view');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    motionItems.forEach((item, index) => {
      item.style.transitionDelay = `${Math.min(index % 4, 3) * 45}ms`;
      observer.observe(item);
    });
  } else {
    motionItems.forEach((item) => item.classList.add('is-in-view'));
  }

  if (reduceMotion) return;

  const parallaxMq = window.matchMedia('(min-width: 1101px) and (hover: hover) and (pointer: fine)');
  if (!parallaxMq.matches) return;
  const parallaxItems = [...home.querySelectorAll('[data-home-parallax]')];
  if (!parallaxItems.length) return;

  let raf = 0;
  const updateParallax = () => {
    raf = 0;
    const viewport = window.innerHeight || 1;
    parallaxItems.forEach((item) => {
      const strength = Number.parseFloat(item.dataset.homeParallax || '0.12') || 0.12;
      const rect = item.getBoundingClientRect();
      const center = rect.top + rect.height / 2;
      const delta = (center - viewport / 2) / viewport;
      const offset = Math.max(-18, Math.min(18, delta * -48 * strength));
      item.style.setProperty('--home-parallax', `${offset.toFixed(2)}px`);
    });
  };

  const requestParallax = () => {
    if (raf) return;
    raf = window.requestAnimationFrame(updateParallax);
  };

  updateParallax();
  window.addEventListener('scroll', requestParallax, { passive: true });
  window.addEventListener('resize', requestParallax, { passive: true });
})();

/* BG Studio 3D Google reviews v3.3.28
   Fetches cached Google Business reviews from the BG Assistant worker. If the
   endpoint is not configured or fails, the section keeps its Google links only. */
(() => {
  const section = document.querySelector('[data-google-reviews]');
  if (!section) return;
  const endpoint = section.dataset.reviewsEndpoint;
  const list = section.querySelector('[data-reviews-list]');
  const summary = section.querySelector('[data-reviews-summary]');
  const readLink = section.querySelector('[data-reviews-link]');
  const writeLink = section.querySelector('[data-reviews-write]');
  if (!endpoint || !list) return;

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };
  const stars = rating => {
    const wrap = el('span', 'review-stars-v3328');
    const value = Math.max(0, Math.min(5, Math.round(rating)));
    wrap.setAttribute('role', 'img');
    wrap.setAttribute('aria-label', `5 üzerinden ${value} yıldız`);
    wrap.textContent = '★'.repeat(value) + '☆'.repeat(5 - value);
    return wrap;
  };
  const safeUrl = value => (/^https:\/\//i.test(value || '') ? value : '');

  const render = data => {
    if (!data?.ok || !Array.isArray(data.reviews) || !data.reviews.length) return;
    const mapsUrl = safeUrl(data.url);
    if (mapsUrl && readLink) readLink.href = mapsUrl;
    if (data.id && writeLink) writeLink.href = `https://search.google.com/local/writereview?placeid=${encodeURIComponent(data.id)}`;

    if (summary && data.rating) {
      summary.replaceChildren(
        el('strong', 'review-score-v3328', data.rating.toLocaleString('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })),
        stars(data.rating),
        el('span', 'review-count-v3328', `${data.count} Google yorumu`)
      );
      summary.hidden = false;
    }

    list.replaceChildren(...data.reviews.map(review => {
      const card = el('article', 'review-card-v3328');
      const head = el('div', 'review-card-head-v3328');
      const avatarUrl = safeUrl(review.photo);
      if (avatarUrl) {
        const avatar = el('img', 'review-avatar-v3328');
        avatar.src = avatarUrl;
        avatar.alt = '';
        avatar.width = 40;
        avatar.height = 40;
        avatar.loading = 'lazy';
        avatar.referrerPolicy = 'no-referrer';
        head.append(avatar);
      } else {
        head.append(el('span', 'review-avatar-v3328 review-avatar-letter-v3328', (review.author || '?').trim().charAt(0).toUpperCase()));
      }
      const who = el('div', 'review-who-v3328');
      const authorUrl = safeUrl(review.authorUrl);
      if (authorUrl) {
        const link = el('a', '', review.author);
        link.href = authorUrl;
        link.rel = 'noopener nofollow';
        link.target = '_blank';
        who.append(link);
      } else {
        who.append(el('strong', '', review.author));
      }
      who.append(el('small', '', review.when));
      head.append(who);
      const text = el('p', 'review-text-v3328', review.text);
      card.append(head, stars(review.rating), text, el('span', 'review-source-v3328', 'Google'));
      return card;
    }));
    section.classList.add('has-reviews');
  };

  const load = () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);
    fetch(endpoint, { signal: controller.signal, credentials: 'omit' })
      .then(response => (response.ok ? response.json() : null))
      .then(render)
      .catch(() => {})
      .finally(() => clearTimeout(timer));
  };

  // Reviews sit low on the page; fetch only when the section approaches the viewport.
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { io.disconnect(); load(); }
    }, { rootMargin: '600px 0px' });
    io.observe(section);
  } else {
    load();
  }
})();
