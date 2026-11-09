/* BG Studio 3D — Ürün 3D görüntüleyici (v3.3.58)
   "3D'de döndür" butonu ürünün gerçek baskı modelini (GLB) açar. three.js yalnızca
   butona basılınca yüklenir; model beyaz mat malzemeyle, koyu sahnede gösterilir. */
(() => {
  const btn = document.querySelector('[data-model3d]');
  if (!btn) return;
  const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/+esm';
  const GLTF_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/GLTFLoader.js/+esm';
  const ORBIT_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let lib = null, dialog = null, renderer = null, raf = 0, controls = null, camera = null, scene = null, loaded = false;

  const build = () => {
    dialog = document.createElement('div');
    dialog.className = 'model3d-dialog';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-label', `${btn.dataset.model3dName || 'Ürün'} 3D modeli`);
    dialog.innerHTML = `<div class="model3d-backdrop" data-model3d-close></div>
      <div class="model3d-card"><div class="model3d-head"><div><small>Gerçek baskı modeli</small><strong>${btn.dataset.model3dName || ''}</strong></div>
      <button type="button" class="model3d-close" data-model3d-close aria-label="Kapat">×</button></div>
      <div class="model3d-stage" data-model3d-stage><p class="model3d-loading" data-model3d-status>Model yükleniyor…</p></div>
      <p class="model3d-hint">Döndürmek için sürükle · yakınlaştırmak için kaydır ya da iki parmakla büyüt</p></div>`;
    document.body.appendChild(dialog);
    dialog.addEventListener('click', (e) => { if (e.target.closest('[data-model3d-close]')) close(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && dialog && !dialog.hidden) close(); });
  };

  const close = () => {
    dialog.hidden = true;
    document.body.classList.remove('model3d-open');
    cancelAnimationFrame(raf); raf = 0;
    btn.focus({ preventScroll: true });
  };

  const start = async () => {
    const stage = dialog.querySelector('[data-model3d-stage]');
    const status = dialog.querySelector('[data-model3d-status]');
    try {
      if (!lib) {
        const [THREE, gltf, orbit] = await Promise.all([import(THREE_URL), import(GLTF_URL), import(ORBIT_URL)]);
        lib = { THREE, GLTFLoader: gltf.GLTFLoader, OrbitControls: orbit.OrbitControls };
      }
      const { THREE } = lib;
      if (!renderer) {
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100000);
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        stage.appendChild(renderer.domElement);
        scene.add(new THREE.HemisphereLight(0xffffff, 0x2a231e, 1.15));
        const key = new THREE.DirectionalLight(0xffffff, 2.1); key.position.set(1.2, 1.6, 1.4); scene.add(key);
        const rim = new THREE.DirectionalLight(0xc8894a, 1.2); rim.position.set(-1.4, 0.8, -1.2); scene.add(rim);
        controls = new lib.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true; controls.dampingFactor = 0.08;
        controls.autoRotate = !reduce; controls.autoRotateSpeed = 1.4;
        controls.addEventListener('start', () => { controls.autoRotate = false; });
    controls.addEventListener('end', () => { if (!reduce) controls.autoRotate = true; });
        const resize = () => { const w = stage.clientWidth || 600, h = stage.clientHeight || 400; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); };
        if ('ResizeObserver' in window) new ResizeObserver(resize).observe(stage);
        resize();
      }
      if (!loaded) {
        const gltf = await new lib.GLTFLoader().loadAsync(btn.dataset.model3d);
        const model = gltf.scene;
        const mat = new THREE.MeshStandardMaterial({ color: 0xf2f2f2, roughness: 0.48, metalness: 0.02, side: THREE.DoubleSide });
        model.traverse((o) => { if (o.isMesh) { o.material = mat; o.geometry.computeVertexNormals(); } });
        const box = new THREE.Box3().setFromObject(model);
        const c = box.getCenter(new THREE.Vector3()); model.position.sub(c);
        const r = box.getSize(new THREE.Vector3()).length() / 2 || 1;
        scene.add(model);
        camera.near = r / 100; camera.far = r * 100; camera.updateProjectionMatrix();
        camera.position.set(r * 1.9, r * 1.1, r * 2.4);
        controls.target.set(0, 0, 0); controls.update();
        loaded = true;
        status.remove();
      }
      const loop = () => { raf = requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera); };
      if (!raf) loop();
    } catch (err) {
      console.warn('[3D]', err);
      status.textContent = 'Model şu an açılamadı. Görsellerden inceleyebilir ya da WhatsApp’tan sorabilirsin.';
    }
  };

  btn.addEventListener('click', () => {
    if (!dialog) build();
    dialog.hidden = false;
    document.body.classList.add('model3d-open');
    dialog.querySelector('.model3d-close').focus({ preventScroll: true });
    start();
  });
})();
