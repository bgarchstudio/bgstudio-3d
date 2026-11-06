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
