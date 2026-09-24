/* BG Studio 3D Product Manager · V3.1.82-R1
   Deterministic toolbar placement.
   Uses the real launcher IDs created by site-content-admin.js and project-admin.js. */
(() => {
  'use strict';

  const fold = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('tr-TR');

  function findHost() {
    return document.querySelector('.top-actions') ||
      document.querySelector('[data-top-actions]') ||
      Array.from(document.querySelectorAll('header div, header nav, header section')).find((el) => {
        const text = fold(el.textContent);
        return text.includes('canlı site') && text.includes('paneli kapat') && text.includes('siteyi yeniden oluştur');
      }) || null;
  }

  function directChild(host, node) {
    let current = node;
    while (current && current.parentElement && current.parentElement !== host) current = current.parentElement;
    return current && current.parentElement === host ? current : null;
  }

  function fieldAnchor(host) {
    const candidates = Array.from(host.querySelectorAll('button,a,[role="button"]'));
    const match = candidates.find((el) => {
      const text = fold(el.textContent);
      return text.includes('saha') && text.includes('kurumsal') && text.includes('prototip');
    });
    return match ? directChild(host, match) : null;
  }

  function styleShortcut(node, kind) {
    node.classList.remove('bg-v3180-toolbar-item','bg-v3180-toolbar-content','bg-v3180-toolbar-projects');
    node.classList.add('bg-v3181-toolbar-shortcut', `bg-v3181-toolbar-${kind}`);
    node.setAttribute('data-bg-v3181-toolbar-shortcut', kind);
    node.querySelectorAll('b,strong,small').forEach((child) => {
      const text = fold(child.textContent);
      if (kind === 'content' || text.includes('case study')) child.classList.add('bg-v3181-toolbar-secondary');
    });
  }

  function apply() {
    const host = findHost();
    const content = document.getElementById('bgSiteContentLauncher');
    const projects = document.getElementById('bgProjectAdminLauncher');
    if (!host || !content || !projects) return false;

    const anchor = fieldAnchor(host);
    styleShortcut(content, 'content');
    styleShortcut(projects, 'projects');

    // Move the real controls, preserving their original click handlers.
    if (anchor) {
      if (content.parentElement !== host || content.nextElementSibling !== projects) host.insertBefore(content, anchor);
      if (projects.parentElement !== host || projects.nextElementSibling !== anchor) host.insertBefore(projects, anchor);
    } else {
      if (content.parentElement !== host) host.appendChild(content);
      if (projects.parentElement !== host) host.appendChild(projects);
    }

    host.setAttribute('data-bg-v3181-toolbar-host', '1');
    document.documentElement.dataset.bgV3182ToolbarDone = '1';
    return true;
  }

  function boot() {
    document.documentElement.removeAttribute('data-bg-v3180-toolbar-done');
    document.documentElement.removeAttribute('data-bg-v3181-toolbar-done');
    if (apply()) return;

    const observer = new MutationObserver(() => {
      if (apply()) observer.disconnect();
    });
    observer.observe(document.body, {childList:true, subtree:true});
    window.setTimeout(() => observer.disconnect(), 30000);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
