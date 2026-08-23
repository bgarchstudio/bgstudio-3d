(() => {
  const STORAGE_KEY = 'bgstudio3d_consent_v1';
  const MEASUREMENT_ID = 'G-WHJ7Y7KN3L';
  let banner = null;

  const readChoice = () => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); }
    catch (_) { return null; }
  };

  const writeChoice = (analytics) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ analytics: !!analytics, updatedAt: new Date().toISOString() }));
    } catch (_) {}
  };

  const removeAnalyticsCookies = () => {
    const cookieNames = document.cookie.split(';').map(x => x.trim().split('=')[0]).filter(Boolean);
    cookieNames.filter(name => name === '_ga' || name === '_gid' || name === '_gat' || name.startsWith('_ga_')).forEach(name => {
      const expires = 'Thu, 01 Jan 1970 00:00:00 GMT';
      document.cookie = `${name}=;expires=${expires};path=/;SameSite=Lax`;
      document.cookie = `${name}=;expires=${expires};path=/;domain=.bgstudio.com.tr;SameSite=Lax`;
      document.cookie = `${name}=;expires=${expires};path=/;domain=3d.bgstudio.com.tr;SameSite=Lax`;
    });
  };

  const loadAnalytics = () => {
    if (window.__bgStudioAnalyticsLoaded) return;
    window.__bgStudioAnalyticsLoaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    window.gtag('js', new Date());
    window.gtag('config', MEASUREMENT_ID, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
    document.head.appendChild(script);
    window.dispatchEvent(new CustomEvent('bg-consent-granted'));
  };

  const setChoice = (analytics) => {
    const hadAnalytics = !!readChoice()?.analytics;
    writeChoice(analytics);
    if (analytics) {
      loadAnalytics();
      if (window.gtag) window.gtag('consent', 'update', { analytics_storage: 'granted' });
      hideBanner();
      return;
    }
    if (window.gtag) window.gtag('consent', 'update', { analytics_storage: 'denied' });
    removeAnalyticsCookies();
    hideBanner();
    if (hadAnalytics) window.location.reload();
  };

  const hideBanner = () => {
    if (!banner) return;
    banner.classList.remove('show');
    banner.setAttribute('aria-hidden', 'true');
  };

  const showBanner = (manageMode = false) => {
    if (!banner) return;
    const saved = readChoice();
    banner.classList.add('show');
    banner.setAttribute('aria-hidden', 'false');
    const status = banner.querySelector('[data-consent-status]');
    if (status) {
      status.textContent = manageMode && saved
        ? `Mevcut tercih: ${saved.analytics ? 'Analitik açık' : 'Sadece gerekli'}`
        : 'İsteğe bağlı analitik, yalnızca izin verirseniz etkinleşir.';
    }
    banner.querySelector('[data-consent-accept]')?.focus();
  };

  const mount = () => {
    if (document.querySelector('[data-consent-banner]')) return;
    banner = document.createElement('aside');
    banner.className = 'consent-banner';
    banner.dataset.consentBanner = '';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Çerez ve analitik tercihleri');
    banner.setAttribute('aria-hidden', 'true');
    banner.innerHTML = `
      <div class="consent-copy">
        <span class="consent-kicker">GİZLİLİK TERCİHİ</span>
        <strong>Analitik kullanımına sen karar ver.</strong>
        <p>Site, zorunlu işlevler için çalışmaya devam eder. Google Analytics yalnızca izin verirsen etkinleşir; reklam kişiselleştirme sinyallerini kullanmıyoruz.</p>
        <small data-consent-status>İsteğe bağlı analitik, yalnızca izin verirseniz etkinleşir.</small>
      </div>
      <div class="consent-actions">
        <a href="/gizlilik/">Detaylar</a>
        <button type="button" class="consent-secondary" data-consent-necessary>Sadece gerekli</button>
        <button type="button" class="consent-primary" data-consent-accept>Analitiğe izin ver</button>
      </div>`;
    document.body.appendChild(banner);
    banner.querySelector('[data-consent-accept]')?.addEventListener('click', () => setChoice(true));
    banner.querySelector('[data-consent-necessary]')?.addEventListener('click', () => setChoice(false));

    const footerLinks = document.querySelector('.footer-links');
    if (footerLinks && !footerLinks.querySelector('[data-open-consent]')) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'footer-consent-button';
      button.dataset.openConsent = '';
      button.textContent = 'Çerez tercihleri';
      button.addEventListener('click', () => showBanner(true));
      footerLinks.appendChild(button);
    }

    if (!readChoice()) showBanner(false);
  };

  const choice = readChoice();
  if (choice?.analytics) loadAnalytics();

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();

  window.BGStudioConsent = {
    get: readChoice,
    open: () => showBanner(true),
    acceptAnalytics: () => setChoice(true),
    necessaryOnly: () => setChoice(false)
  };
})();
