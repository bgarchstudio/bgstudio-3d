/* BG Studio 3D — STL Stüdyo (v3.3.57)
   Müşteri STL dosyasını bırakır; model tarayıcıda 3D açılır, ölçü / hacim / tahmini gram
   ve baskı süresi hesaplanır, WhatsApp teklif mesajı hazırlanır. Dosya cihazdan çıkmaz.
   three.js yalnızca dosya seçilince CDN'den yüklenir (sayfa hızını etkilemez). */
(() => {
  const root = document.querySelector('[data-stl-studio]');
  if (!root) return;

  const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/+esm';
  const STL_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/STLLoader.js/+esm';
  const TMF_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/3MFLoader.js/+esm';
  const ORBIT_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm';
  const WA_NUMBER = '905302466903';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const MAX_MB = 60;
  const DENSITY = { PLA: 1.24, PETG: 1.27 };
  // Kabuk + %15 dolgu varsayımı: katı hacmin kabaca %35–%55'i kadar malzeme harcanır.
  const FILL_MIN = 0.35, FILL_MAX = 0.55;
  // Tahmini baskı hızı (g/saat), standart kalite.
  const RATE_FAST = 22, RATE_SLOW = 12;

  const $ = (sel) => root.querySelector(sel);
  const drop = $('[data-stl-drop]');
  const input = $('[data-stl-input]');
  const viewer = $('[data-stl-viewer]');
  const result = $('[data-stl-result]');
  const status = $('[data-stl-status]');
  const fileName = $('[data-stl-name]');
  const out = {
    size: $('[data-stl-size]'), volume: $('[data-stl-volume]'), weight: $('[data-stl-weight]'),
    time: $('[data-stl-time]'), fit: $('[data-stl-fit]')
  };
  const qty = $('[data-stl-qty]');
  const unitSel = $('[data-stl-unit]');
  const materialBtns = [...root.querySelectorAll('[data-stl-material]')];
  const waLink = $('[data-stl-whatsapp]');
  const resetBtn = $('[data-stl-reset]');

  let lib = null;
  let scene, camera, renderer, controls, mesh, raf = 0;
  let current = null; // { name, volMm3, size:[x,y,z] }
  let material = 'PLA';

  const setStatus = (text, isError = false) => {
    status.textContent = text;
    status.classList.toggle('is-error', isError);
  };
  const fmt = (n, d = 0) => Number(n).toLocaleString('tr-TR', { maximumFractionDigits: d, minimumFractionDigits: d });

  const loadLib = async () => {
    if (lib) return lib;
    const [THREE, stl, orbit] = await Promise.all([import(THREE_URL), import(STL_URL), import(ORBIT_URL)]);
    lib = { THREE, STLLoader: stl.STLLoader, OrbitControls: orbit.OrbitControls };
    return lib;
  };
  const load3MF = async () => {
    if (!lib.ThreeMFLoader) lib.ThreeMFLoader = (await import(TMF_URL)).ThreeMFLoader;
    return lib.ThreeMFLoader;
  };
  // 3MF: tüm parçaları dünya dönüşümleriyle tek bir geometriye birleştir.
  const mergeGroup = (group) => {
    const { THREE } = lib;
    group.updateMatrixWorld(true);
    const chunks = []; let total = 0;
    group.traverse((o) => {
      if (!o.isMesh || !o.geometry?.attributes?.position) return;
      let g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
      g.applyMatrix4(o.matrixWorld);
      const a = g.attributes.position.array; chunks.push(a); total += a.length;
    });
    const merged = new Float32Array(total); let off = 0;
    chunks.forEach((a) => { merged.set(a, off); off += a.length; });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(merged, 3));
    return geo;
  };

  const ensureScene = () => {
    const { THREE, OrbitControls } = lib;
    if (renderer) return;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100000);
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    viewer.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xfff4e6, 0x1a1410, 1.1));
    const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(1, 1.4, 1.2); scene.add(key);
    const rim = new THREE.DirectionalLight(0xc8894a, 1.1); rim.position.set(-1.2, 0.6, -1); scene.add(rim);
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.autoRotate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    controls.autoRotateSpeed = 1.1;
    controls.addEventListener('start', () => { controls.autoRotate = false; });
    controls.addEventListener('end', () => { if (!reduce) controls.autoRotate = true; });
    const resize = () => {
      const w = viewer.clientWidth || 400, h = viewer.clientHeight || 300;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    };
    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(viewer);
    resize();
    const loop = () => { raf = requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera); };
    loop();
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { cancelAnimationFrame(raf); raf = 0; } else if (!raf) loop();
    });
  };

  const signedVolume = (pos) => {
    let v = 0;
    for (let i = 0; i < pos.length; i += 9) {
      const ax = pos[i], ay = pos[i + 1], az = pos[i + 2];
      const bx = pos[i + 3], by = pos[i + 4], bz = pos[i + 5];
      const cx = pos[i + 6], cy = pos[i + 7], cz = pos[i + 8];
      v += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx);
    }
    return Math.abs(v / 6);
  };

  const unitFactor = () => Number(unitSel?.value || 1);

  const render = () => {
    if (!current) return;
    const f = unitFactor();
    const [sx, sy, sz] = current.size.map((s) => s * f);
    const volCm3 = current.volMm3 * f * f * f / 1000;
    const n = Math.max(1, Math.min(9999, parseInt(qty?.value || '1', 10) || 1));
    const d = DENSITY[material];
    const gMin = volCm3 * d * FILL_MIN, gMax = volCm3 * d * FILL_MAX;
    const hMin = (gMin / RATE_FAST) * n, hMax = (gMax / RATE_SLOW) * n;
    out.size.textContent = `${fmt(sx, 1)} × ${fmt(sy, 1)} × ${fmt(sz, 1)} mm`;
    out.volume.textContent = `${fmt(volCm3, 1)} cm³`;
    out.weight.textContent = `${fmt(gMin * n)}–${fmt(gMax * n)} g`;
    const hText = (h) => (h < 1 ? `${fmt(Math.max(5, h * 60))} dk` : `${fmt(h, h < 10 ? 1 : 0)} saat`);
    out.time.textContent = `${hText(hMin)} – ${hText(hMax)}`;
    const longest = Math.max(sx, sy, sz);
    out.fit.textContent = longest > 250 ? 'Parça büyük: bölünerek basılabilir, birlikte değerlendirelim.' : (longest < 5 ? 'Çok küçük görünüyor: birim cm veya inç olabilir, yukarıdan değiştir.' : 'Tek parça basılabilir boyutta.');
    out.fit.classList.toggle('is-warn', longest > 250 || longest < 5);
    const msg = [
      'Merhaba BG Studio 3D, sitenizdeki STL Stüdyo’da dosyamı inceledim.',
      `Dosya: ${current.name}`,
      `Ölçü: ${fmt(sx, 1)} × ${fmt(sy, 1)} × ${fmt(sz, 1)} mm`,
      `Malzeme: ${material} · Adet: ${n}`,
      `Tahmini: ${fmt(gMin * n)}–${fmt(gMax * n)} g, ${hText(hMin)} – ${hText(hMax)}`,
      'Dosyayı bu sohbete gönderiyorum, fiyat teklifi alabilir miyim?'
    ].join('\n');
    waLink.href = `https://wa.me/${WA_NUMBER}?text=${encodeURIComponent(msg)}`;
  };

  const showModel = (geometry) => {
    const { THREE } = lib;
    ensureScene();
    if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); }
    geometry.computeBoundingBox();
    const box = geometry.boundingBox;
    const center = new THREE.Vector3(); box.getCenter(center);
    geometry.translate(-center.x, -center.y, -center.z);
    geometry.rotateX(-Math.PI / 2); // STL Z-yukarı → sahne Y-yukarı
    geometry.computeVertexNormals();
    mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xf3f0eb, roughness: 0.5, metalness: 0.02 }));
    scene.add(mesh);
    const size = new THREE.Vector3(); box.getSize(size);
    const r = Math.max(size.x, size.y, size.z) || 1;
    camera.near = r / 100; camera.far = r * 100; camera.updateProjectionMatrix();
    camera.position.set(r * 1.6, r * 1.1, r * 1.8);
    controls.target.set(0, 0, 0); controls.update();
  };

  const handleFile = async (file) => {
    if (!file) return;
    if (!/\.(stl|3mf)$/i.test(file.name)) { setStatus('STL veya 3MF dosyası açabiliyoruz. STEP veya OBJ için dosyanı WhatsApp’tan gönder.', true); return; }
    if (file.size > MAX_MB * 1024 * 1024) { setStatus(`Dosya ${MAX_MB} MB’tan büyük. WhatsApp’tan gönderirsen birlikte bakalım.`, true); return; }
    root.classList.add('is-loading');
    setStatus('Model açılıyor…');
    try {
      await loadLib();
      const buf = await file.arrayBuffer();
      const geometry = /\.3mf$/i.test(file.name) ? mergeGroup(new (await load3MF())().parse(buf)) : new lib.STLLoader().parse(buf);
      const pos = geometry.attributes.position.array;
      if (!pos.length) throw new Error('empty');
      geometry.computeBoundingBox();
      const s = geometry.boundingBox.getSize(new lib.THREE.Vector3());
      current = { name: file.name, volMm3: signedVolume(pos), size: [s.x, s.y, s.z] };
      fileName.textContent = file.name;
      showModel(geometry);
      root.classList.add('has-model');
      result.hidden = false;
      setStatus('Model hazır. Döndürmek için sürükle, yakınlaştırmak için kaydır.');
      render();
    } catch (err) {
      console.warn('[STL Stüdyo]', err);
      setStatus('Dosya okunamadı. Bozuk olabilir; WhatsApp’tan gönderirsen biz açalım.', true);
    } finally {
      root.classList.remove('is-loading');
    }
  };

  drop.addEventListener('click', () => input.click());
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
  input.addEventListener('change', () => handleFile(input.files?.[0]));
  ['dragenter', 'dragover'].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add('is-over'); }));
  ['dragleave', 'drop'].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove('is-over'); }));
  drop.addEventListener('drop', (e) => handleFile(e.dataTransfer?.files?.[0]));
  qty?.addEventListener('input', render);
  unitSel?.addEventListener('change', render);
  materialBtns.forEach((b) => b.addEventListener('click', () => {
    material = b.dataset.stlMaterial;
    materialBtns.forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    render();
  }));
  resetBtn?.addEventListener('click', () => {
    current = null; input.value = '';
    if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); mesh = null; }
    root.classList.remove('has-model'); result.hidden = true; setStatus('');
  });
})();
