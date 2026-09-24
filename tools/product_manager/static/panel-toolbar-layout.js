/* BG Studio 3D Product Manager · V3.1.81
   Safe toolbar consolidation.
   Only the two compact shortcut cards are moved. Project manager panels/modals
   are explicitly excluded and the existing toolbar layout is never rewritten. */
(() => {
  'use strict';

  const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const fold = (value) => compact(value).toLocaleLowerCase('tr-TR');

  const LABELS = {
    field: 'saha / kurumsal / prototip & parça',
    rebuild: 'siteyi yeniden oluştur',
    close: 'paneli kapat',
    content: 'site içerikleri',
    projects: 'projeler',
    caseStudy: 'case study'
  };

  const visible = (el) => {
    if (!el || !el.isConnected) return false;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const interactiveCandidates = () => Array.from(document.querySelectorAll(
    'button, a, [role="button"], [onclick], [tabindex], .quick-card, .shortcut, .action-card, .admin-card, .tool-card, .panel-card'
  )).filter(visible);

  function shortControlMatch(predicate) {
    const hits = interactiveCandidates().filter((el) => {
      const text = fold(el.textContent);
      const r = el.getBoundingClientRect();
      if (!predicate(text, el)) return false;
      if (r.width < 38 || r.width > 260 || r.height < 24 || r.height > 125) return false;
      if (el.querySelector('input, textarea, select, form, dialog')) return false;
      return true;
    });
    hits.sort((a, b) => {
      const ra = a.getBoundingClientRect();
      const rb = b.getBoundingClientRect();
      const areaDiff = (ra.width * ra.height) - (rb.width * rb.height);
      if (areaDiff) return areaDiff;
      return compact(a.textContent).length - compact(b.textContent).length;
    });
    return hits[0] || null;
  }

  function topAction(label) {
    return shortControlMatch((text) => text.includes(label) && text.length < 80);
  }

  function lowestCommonAncestor(nodes) {
    const valid = nodes.filter(Boolean);
    if (!valid.length) return null;
    let current = valid[0];
    while (current && current !== document.body) {
      if (valid.every((node) => current.contains(node))) return current;
      current = current.parentElement;
    }
    return null;
  }

  function findToolbarHost() {
    const field = topAction(LABELS.field);
    const rebuild = topAction(LABELS.rebuild);
    const close = topAction(LABELS.close);
    if (!field || !rebuild || !close) return null;

    let host = lowestCommonAncestor([field, rebuild, close]);
    if (!host) return null;

    // The correct toolbar is a shallow strip, not the whole header/page shell.
    // If the common ancestor is too tall, walk down the field branch until the
    // smallest child still containing the other two controls is reached.
    let changed = true;
    while (changed) {
      changed = false;
      for (const child of Array.from(host.children)) {
        if (child.contains(field) && child.contains(rebuild) && child.contains(close)) {
          host = child;
          changed = true;
          break;
        }
      }
    }

    const r = host.getBoundingClientRect();
    if (r.height > 130 || r.width < 320) return null;
    return { host, field, rebuild, close };
  }

  function directChild(host, node) {
    let current = node;
    while (current && current.parentElement && current.parentElement !== host) current = current.parentElement;
    return current && current.parentElement === host ? current : null;
  }

  function shortcutRoot(node, kind) {
    if (!node) return null;
    let best = node;
    let current = node.parentElement;
    const predicate = kind === 'content'
      ? (text) => text.includes(LABELS.content) && !text.includes('yönetimi')
      : (text) => text.includes(LABELS.projects) && text.includes(LABELS.caseStudy) && !text.includes('yönetimi');

    for (let depth = 0; current && current !== document.body && depth < 3; depth += 1, current = current.parentElement) {
      const text = fold(current.textContent);
      const r = current.getBoundingClientRect();
      if (!predicate(text)) break;
      if (r.width > 280 || r.height > 140) break;
      if (current.querySelector('input, textarea, select, form, dialog')) break;
      best = current;
    }
    return best;
  }

  function findContentShortcut(host) {
    const node = shortControlMatch((text) => {
      return text.includes(LABELS.content) &&
        !text.includes('yönetimi') &&
        !text.includes('ana sayfa') &&
        text.length < 55;
    });
    if (!node || host.contains(node)) return null;
    return shortcutRoot(node, 'content');
  }

  function findProjectShortcut(host) {
    const node = shortControlMatch((text) => {
      return text.includes(LABELS.projects) &&
        text.includes(LABELS.caseStudy) &&
        !text.includes('yönetimi') &&
        !text.includes('bir proje seç') &&
        !text.includes('mevcut saha kayıt') &&
        text.length < 45;
    });
    if (!node || host.contains(node)) return null;
    return shortcutRoot(node, 'projects');
  }

  function markSecondary(root) {
    Array.from(root.querySelectorAll('*')).forEach((el) => {
      const text = fold(el.textContent);
      if (!text) return;
      if (text === LABELS.caseStudy || /^v?3\.1\.\d+(?:[-._a-z0-9]+)?$/i.test(compact(el.textContent))) {
        el.classList.add('bg-v3181-toolbar-secondary');
      }
    });
  }

  function moveShortcut(root, host, beforeNode, kind) {
    if (!root || !host || host.contains(root)) return false;
    root.classList.remove('bg-v3180-toolbar-item', 'bg-v3180-toolbar-content', 'bg-v3180-toolbar-projects');
    root.classList.add('bg-v3181-toolbar-shortcut', `bg-v3181-toolbar-${kind}`);
    root.setAttribute('data-bg-v3181-toolbar-shortcut', kind);
    markSecondary(root);
    if (beforeNode && beforeNode.parentElement === host) host.insertBefore(root, beforeNode);
    else host.appendChild(root);
    return true;
  }

  function apply() {
    const toolbar = findToolbarHost();
    if (!toolbar) return false;

    const beforeNode = directChild(toolbar.host, toolbar.field);
    if (!beforeNode) return false;

    const content = findContentShortcut(toolbar.host);
    const projects = findProjectShortcut(toolbar.host);
    if (!content || !projects) return false;

    const contentMoved = moveShortcut(content, toolbar.host, beforeNode, 'content');
    const projectsMoved = moveShortcut(projects, toolbar.host, beforeNode, 'projects');

    if (contentMoved || projectsMoved) {
      toolbar.host.setAttribute('data-bg-v3181-toolbar-host', '1');
      document.documentElement.dataset.bgV3181ToolbarDone = '1';
      return true;
    }
    return false;
  }

  function boot() {
    // Remove V3.1.80 runtime markers if the browser retained the old shell via cache.
    document.documentElement.removeAttribute('data-bg-v3180-toolbar-done');

    if (apply()) return;
    const observer = new MutationObserver(() => {
      if (apply()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 10000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
