(() => {
  'use strict';

  const form = document.querySelector('[data-quote-form]');
  if (!form) return;

  const typeSelect = form.querySelector('select[name="talep_turu"]');
  const typeButtons = [...form.querySelectorAll('[data-quote-type]')];
  const scoped = [...form.querySelectorAll('[data-quote-scope]')];
  const status = form.querySelector('[data-quote-status]');
  const fileInputs = [...form.querySelectorAll('[data-quote-files]')];
  const fileList = form.querySelector('[data-quote-file-list]');
  const fileSummary = form.querySelector('input[name="dosya_ozeti"]');

  const nfcConfig = form.querySelector('[data-nfc-quote-config]');
  const packageSelect = form.querySelector('#quote-nfc-package');
  const feedbackWrap = form.querySelector('[data-feedback-capacity-wrap]');
  const feedbackSelect = form.querySelector('#quote-feedback-capacity');
  const packageSummary = form.querySelector('[data-nfc-package-summary]');
  const packageTitle = form.querySelector('[data-nfc-package-title]');
  const packageCapacity = form.querySelector('[data-nfc-package-capacity]');
  const packagePrice = form.querySelector('[data-nfc-package-price]');
  const packageRenewal = form.querySelector('[data-nfc-package-renewal]');
  const totalWrap = form.querySelector('[data-nfc-quote-total]');
  const totalValue = form.querySelector('[data-nfc-total-value]');
  const nfcOptions = [...form.querySelectorAll('[data-nfc-option]')];

  const money = value => {
    const n = Number(value);
    if (!Number.isFinite(n)) return 'Özel teklif';
    return `${new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 }).format(n)} TL`;
  };

  const safeJson = () => {
    const node = document.getElementById('quote-pricing-data');
    if (!node) return {};
    try { return JSON.parse(node.textContent || '{}'); }
    catch (_) { return {}; }
  };

  const pricing = safeJson();

  const setStatus = (message = '', tone = '') => {
    if (!status) return;
    status.textContent = message;
    status.dataset.tone = tone;
  };

  const typeLabels = {
    'kisiye-ozel': 'Özel Üretim',
    'kurumsal': 'Kurumsal',
    'prototip': 'Prototip / Parça',
    'nfc': 'NFC & QR',
    'diger': 'Diğer'
  };

  const setScopedEnabled = (node, visible) => {
    node.hidden = !visible;
    node.querySelectorAll('input,select,textarea,button').forEach(control => {
      if (control.matches('[data-quote-type]')) return;
      if (!visible) {
        control.dataset.quoteWasRequired = control.required ? '1' : '0';
        control.required = false;
        control.disabled = true;
      } else {
        control.disabled = false;
        if (control.dataset.quoteWasRequired === '1') control.required = true;
        delete control.dataset.quoteWasRequired;
      }
    });
  };

  const setType = value => {
    const next = typeLabels[value] ? value : 'kisiye-ozel';
    if (typeSelect) typeSelect.value = next;

    typeButtons.forEach(button => {
      const active = button.dataset.quoteType === next;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });

    scoped.forEach(node => {
      const allowed = (node.dataset.quoteScope || '').split(/\s+/).filter(Boolean);
      setScopedEnabled(node, allowed.includes(next));
    });

    // NFC config itself is a scoped node, but keep its pricing UI synchronized.
    if (next === 'nfc') updateNfc();
    setStatus('');
  };

  typeButtons.forEach(button => {
    button.addEventListener('click', () => setType(button.dataset.quoteType || ''));
  });

  const number = value => {
    if (value === null || value === undefined || value === '') return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  };

  const standardMeta = {
    baslangic: { title: 'Başlangıç', tables: 10, nfc: 30 },
    profesyonel: { title: 'Profesyonel', tables: 15, nfc: 45 },
    premium: { title: 'Premium', tables: 20, nfc: 60 },
    'hizli-stand': { title: 'Hızlı Bağlantı Standı', stands: 1, nfc: 3 }
  };

  const selectedPackageFacts = () => {
    const key = packageSelect?.value || '';
    const packages = pricing.packages || {};
    const special = pricing.special_restaurant_packages || {};
    const duo = pricing.feedback_duo_packages || {};

    if (!key) return null;

    if (key === 'feedback-duo') {
      const stands = Number(feedbackSelect?.value || 10);
      const row = duo[String(stands)] || {};
      return {
        key,
        title: 'Premium Feedback Duo',
        base: number(row.price),
        renewal: number(row.renewal),
        stands,
        nfc: number(row.nfc) ?? stands * 2,
        qrCount: stands * 2,
        capacityText: `${stands} stand · ${number(row.nfc) ?? stands * 2} NFC`
      };
    }

    if (key.startsWith('ozel-kapasite-') && key !== 'ozel-kapasite-custom') {
      const tables = Number(key.replace('ozel-kapasite-', ''));
      const row = special[String(tables)] || {};
      return {
        key,
        title: `Özel Restoran · ${tables} masa`,
        base: number(row.price),
        renewal: number(row.renewal),
        tables,
        nfc: number(row.nfc) ?? tables * 3,
        qrCount: tables * 3,
        capacityText: `${tables} masa · ${number(row.nfc) ?? tables * 3} NFC`
      };
    }

    if (key === 'ozel-kapasite-custom') {
      return {
        key,
        title: 'Farklı kapasite · özel teklif',
        base: null,
        renewal: null,
        qrCount: 0,
        capacityText: 'Masa / kapasite ayrıca netleştirilir'
      };
    }

    const meta = standardMeta[key];
    const packageKey = key === 'hizli-stand' ? 'hizli_stand' : key;
    const row = packages[packageKey] || {};
    if (!meta) return null;

    return {
      key,
      title: meta.title,
      base: number(row.price),
      renewal: number(row.renewal),
      tables: meta.tables || null,
      stands: meta.stands || null,
      nfc: meta.nfc,
      qrCount: key === 'hizli-stand' ? 3 : (meta.tables || 0) * 3,
      capacityText: meta.tables
        ? `${meta.tables} masa · ${meta.nfc} NFC`
        : `${meta.stands} stand · ${meta.nfc} NFC`
    };
  };

  const updateNfc = () => {
    if (!nfcConfig || nfcConfig.hidden) return;

    const facts = selectedPackageFacts();
    const feedbackActive = packageSelect?.value === 'feedback-duo';
    if (feedbackWrap) feedbackWrap.hidden = !feedbackActive;
    if (feedbackSelect) feedbackSelect.disabled = !feedbackActive;

    if (!facts) {
      if (packageSummary) packageSummary.hidden = true;
      if (totalWrap) totalWrap.hidden = true;
      return;
    }

    if (packageSummary) packageSummary.hidden = false;
    if (packageTitle) packageTitle.textContent = facts.title;
    if (packageCapacity) packageCapacity.textContent = facts.capacityText || '';
    if (packagePrice) packagePrice.textContent = money(facts.base);
    if (packageRenewal) {
      packageRenewal.textContent = facts.renewal !== null
        ? `Yıllık yenileme: ${money(facts.renewal)}`
        : '';
    }

    const selected = Object.fromEntries(nfcOptions.map(input => [input.name, input.checked]));
    const qrCost = selected.nfc_qr && facts.qrCount
      ? facts.qrCount * (number(pricing.qr_unit) || 0)
      : 0;
    const menuCost = selected.nfc_menu_design ? (number(pricing.menu_design) || 0) : 0;
    const logoCost = selected.nfc_logo_design ? (number(pricing.logo_design) || 0) : 0;

    if (facts.base === null) {
      if (totalWrap) totalWrap.hidden = true;
      return;
    }

    const total = facts.base + qrCost + menuCost + logoCost;
    if (totalWrap) totalWrap.hidden = false;
    if (totalValue) totalValue.textContent = money(total);
  };

  packageSelect?.addEventListener('change', updateNfc);
  feedbackSelect?.addEventListener('change', updateNfc);
  nfcOptions.forEach(input => input.addEventListener('change', updateNfc));

  const validFile = file => {
    const max = 15 * 1024 * 1024;
    if (file.size > max) return { ok: false, reason: `${file.name}: 15 MB sınırını aşıyor.` };
    const ext = `.${String(file.name).split('.').pop()?.toLowerCase() || ''}`;
    const input = fileInputs.find(node => [...node.files].includes(file));
    const accepted = (input?.getAttribute('accept') || '')
      .split(',')
      .map(x => x.trim().toLowerCase())
      .filter(Boolean);
    if (accepted.length && !accepted.includes(ext)) {
      return { ok: false, reason: `${file.name}: dosya türü bu alan için desteklenmiyor.` };
    }
    return { ok: true };
  };

  const updateFiles = () => {
    const files = fileInputs.flatMap(input => [...(input.files || [])]);
    const good = [];
    const errors = [];

    files.forEach(file => {
      const result = validFile(file);
      if (result.ok) good.push(file);
      else errors.push(result.reason);
    });

    if (fileList) {
      fileList.innerHTML = '';
      good.forEach(file => {
        const li = document.createElement('li');
        const mb = Math.max(.01, file.size / 1024 / 1024);
        li.textContent = `${file.name} · ${mb.toFixed(mb >= 10 ? 0 : 1)} MB`;
        fileList.appendChild(li);
      });
      fileList.hidden = good.length === 0;
    }
    if (fileSummary) fileSummary.value = good.map(file => file.name).join(', ');
    if (errors.length) setStatus(errors[0], 'error');
    else setStatus('');
  };

  fileInputs.forEach(input => input.addEventListener('change', updateFiles));

  const labelFor = control => {
    if (!control) return '';
    if (control.id) {
      const label = form.querySelector(`label[for="${CSS.escape(control.id)}"]`);
      if (label) return (label.textContent || '').trim();
    }
    return control.name || '';
  };

  const visibleValueRows = () => {
    const rows = [];
    const seen = new Set();
    [...form.elements].forEach(control => {
      if (!control.name || control.disabled || seen.has(control.name)) return;
      if (control.type === 'file' || control.type === 'submit' || control.type === 'button') return;
      if (control.type === 'checkbox' && !control.checked) return;
      if (control.type === 'radio' && !control.checked) return;
      const value = String(control.value || '').trim();
      if (!value) return;
      seen.add(control.name);

      let display = value;
      if (control.tagName === 'SELECT') {
        display = control.options[control.selectedIndex]?.textContent?.trim() || value;
      } else if (control.type === 'checkbox') {
        display = 'Evet';
      }
      rows.push([labelFor(control), display]);
    });
    return rows;
  };

  const buildNfcPricingLines = () => {
    if (typeSelect?.value !== 'nfc') return [];
    const facts = selectedPackageFacts();
    if (!facts) return [];
    const lines = [`Seçili çözüm: ${facts.title}${facts.capacityText ? ` (${facts.capacityText})` : ''}`];

    if (facts.base !== null) lines.push(`Paket bedeli: ${money(facts.base)}`);
    else lines.push('Paket bedeli: Özel teklif');

    const chosen = Object.fromEntries(nfcOptions.map(input => [input.name, input.checked]));
    let total = facts.base;

    if (chosen.nfc_qr && facts.qrCount) {
      const cost = facts.qrCount * (number(pricing.qr_unit) || 0);
      lines.push(`QR: ${facts.qrCount} adet × ${money(pricing.qr_unit)} = ${money(cost)}`);
      if (total !== null) total += cost;
    }
    if (chosen.nfc_menu_design) {
      const cost = number(pricing.menu_design) || 0;
      lines.push(`Menü Tasarımı: ${money(cost)}`);
      if (total !== null) total += cost;
    }
    if (chosen.nfc_logo_design) {
      const cost = number(pricing.logo_design) || 0;
      lines.push(`Logo Tasarımı: ${money(cost)}`);
      if (total !== null) total += cost;
    }
    if (total !== null) lines.push(`Seçili toplam: ${money(total)}`);
    if (facts.renewal !== null) lines.push(`Yıllık yenileme: ${money(facts.renewal)}`);
    return lines;
  };

  form.addEventListener('submit', event => {
    event.preventDefault();
    setStatus('');

    const requiredVisible = [...form.querySelectorAll('[required]')].filter(node => !node.disabled);
    const invalid = requiredVisible.find(node => !node.checkValidity());
    if (invalid) {
      setStatus('Lütfen gerekli alanları tamamlayın.', 'error');
      invalid.focus({ preventScroll: false });
      invalid.reportValidity?.();
      return;
    }

    const type = typeSelect?.value || 'kisiye-ozel';
    const lines = [
      'Merhaba BG Studio 3D, web sitenizden teklif talebi gönderiyorum.',
      '',
      `Talep türü: ${typeLabels[type] || type}`
    ];

    visibleValueRows().forEach(([label, value]) => {
      if (!label || label === 'Talep türü') return;
      lines.push(`${label}: ${value}`);
    });

    const nfcLines = buildNfcPricingLines();
    if (nfcLines.length) {
      lines.push('', 'NFC + QR kapsamı:', ...nfcLines);
    }

    const files = String(fileSummary?.value || '').trim();
    if (files) {
      lines.push('', `Dosyalar: ${files}`, 'Not: Dosyaları WhatsApp sohbetine ayrıca ekleyeceğim.');
    }

    lines.push('', 'Bu talep için fiyat ve üretim kapsamını netleştirebilir misiniz?');

    const url = `https://wa.me/905302466903?text=${encodeURIComponent(lines.join('\n'))}`;
    const opened = window.open(url, '_blank', 'noopener,noreferrer');
    if (!opened) window.location.href = url;
    setStatus('Teklif özeti WhatsApp için hazırlandı.', 'success');
  });

  // URL-prefill: /teklif/?tur=nfc&paket=profesyonel
  const params = new URLSearchParams(window.location.search);
  const rawType = (params.get('tur') || '').toLowerCase();
  const typeAliases = {
    nfc: 'nfc',
    kurumsal: 'kurumsal',
    prototip: 'prototip',
    'kisiye-ozel': 'kisiye-ozel',
    ozel: 'kisiye-ozel',
    özel: 'kisiye-ozel',
    diger: 'diger',
    diğer: 'diger'
  };
  setType(typeAliases[rawType] || typeSelect?.value || 'kisiye-ozel');

  const packageParam = params.get('paket');
  if (packageParam && packageSelect && [...packageSelect.options].some(opt => opt.value === packageParam)) {
    packageSelect.value = packageParam;
    setType('nfc');
  }
  const capacityParam = params.get('kapasite');
  if (capacityParam && feedbackSelect && [...feedbackSelect.options].some(opt => opt.value === capacityParam)) {
    feedbackSelect.value = capacityParam;
  }

  updateFiles();
  updateNfc();
})();
