/* BG Studio 3D Product Manager · V3.1.80
   Move Site İçerikleri + Projeler into the existing top action row.
   The original nodes are moved, not cloned, so all existing listeners stay intact. */
(() => {
  'use strict';

  const compact = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const fold = (value) => compact(value).toLocaleLowerCase('tr-TR');

  const labels = {
    live: 'canlı site',
    publish: 'yayın kontrolü',
    colors: 'benim renklerim',
    campaign: 'kampanya şeridi',
    close: 'paneli kapat',
    field: 'saha / kurumsal / prototip & parça',
    content: 'site içerikleri',
    projects: 'projeler'
  };

  function textHas(el, value) {
    return !!el && fold(el.textContent).includes(value);
  }

  function candidates() {
    return Array.from(document.querySelectorAll(
      'button, a, [role="button"], [tabindex], .card, .quick-card, .shortcut, .action-card, .admin-card, .tool-card, .panel-card'
    ));
  }

  function smallestMatch(label, reject = []) {
    const hits = candidates().filter((el) => {
      const t = fold(el.textContent);
      return t.includes(label) && !reject.some((bad) => t.includes(bad));
    });
    if (!hits.length) return null;
    hits.sort((a, b) => {
      const ta = compact(a.textContent).length;
      const tb = compact(b.textContent).length;
      if (ta !== tb) return ta - tb;
      return a.childElementCount - b.childElementCount;
    });
    return hits[0];
  }

  function findToolbar(anchor) {
    if (!anchor) return null;
    let node = anchor.parentElement;
    let fallback = null;
    for (let depth = 0; node && node !== document.body && depth < 8; depth += 1, node = node.parentElement) {
      const t = fold(node.textContent);
      if (!fallback && t.includes(labels.publish) && t.includes(labels.close)) fallback = node;
      if (
        t.includes(labels.live) &&
        t.includes(labels.publish) &&
        t.includes(labels.colors) &&
        t.includes(labels.campaign) &&
        t.includes(labels.close)
      ) return node;
    }
    return fallback;
  }

  function cardRoot(node, label, secondaryLabel) {
    if (!node) return null;
    let best = node;
    let current = node;
    for (let depth = 0; current && current !== document.body && depth < 4; depth += 1, current = current.parentElement) {
      const t = fold(current.textContent);
      if (!t.includes(label)) break;
      const rect = current.getBoundingClientRect();
      if (rect.width > 60 && rect.width < 280 && rect.height > 28 && rect.height < 150) best = current;
      if (secondaryLabel && t.includes(secondaryLabel)) best = current;
    }
    return best;
  }

  function cleanupOldParent(parent) {
    if (!parent || parent === document.body) return;
    requestAnimationFrame(() => {
      const visibleChildren = Array.from(parent.children).filter((child) => {
        if (child.classList.contains('bg-v3180-toolbar-item')) return false;
        const style = getComputedStyle(child);
        return style.display !== 'none' && style.visibility !== 'hidden';
      });
      if (!visibleChildren.length && !compact(parent.textContent)) {
        parent.classList.add('bg-v3180-empty-source');
      }
    });
  }

  function moveIntoToolbar(node, toolbar, beforeNode, kind) {
    if (!node || !toolbar || toolbar.contains(node)) return false;
    const oldParent = node.parentElement;
    node.classList.add('bg-v3180-toolbar-item', `bg-v3180-toolbar-${kind}`);
    node.setAttribute('data-bg-v3180-toolbar-item', kind);

    // Secondary stacked metadata belongs to the old card presentation.
    Array.from(node.querySelectorAll('small, em, .eyebrow, .kicker, .meta, .subtitle, .sub, .version, .badge')).forEach((el) => {
      const t = fold(el.textContent);
      if (t.includes('case study') || /^v?3\.1\./.test(t)) el.classList.add('bg-v3180-toolbar-secondary');
    });

    if (beforeNode && beforeNode.parentElement === toolbar) toolbar.insertBefore(node, beforeNode);
    else toolbar.appendChild(node);
    cleanupOldParent(oldParent);
    return true;
  }

  function apply() {
    if (document.documentElement.dataset.bgV3180ToolbarDone === '1') return;

    const live = smallestMatch(labels.live);
    const toolbar = findToolbar(live);
    if (!toolbar) return;

    const fieldButton = smallestMatch(labels.field);
    const beforeNode = fieldButton && toolbar.contains(fieldButton)
      ? Array.from(toolbar.children).find((child) => child === fieldButton || child.contains(fieldButton)) || null
      : null;

    const contentHit = smallestMatch(labels.content);
    const projectsHit = smallestMatch(labels.projects, ['siteyi yeniden oluştur']);
    const contentCard = cardRoot(contentHit, labels.content, '3.1.');
    const projectsCard = cardRoot(projectsHit, labels.projects, 'case study');

    let changed = false;
    changed = moveIntoToolbar(contentCard, toolbar, beforeNode, 'content') || changed;
    changed = moveIntoToolbar(projectsCard, toolbar, beforeNode, 'projects') || changed;

    if (changed) {
      toolbar.classList.add('bg-v3180-toolbar-row');
      toolbar.setAttribute('data-bg-v3180-toolbar', '1');
      document.documentElement.dataset.bgV3180ToolbarDone = '1';
    }
  }

  const boot = () => {
    apply();
    if (document.documentElement.dataset.bgV3180ToolbarDone === '1') return;
    const observer = new MutationObserver(() => {
      apply();
      if (document.documentElement.dataset.bgV3180ToolbarDone === '1') observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => observer.disconnect(), 8000);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
