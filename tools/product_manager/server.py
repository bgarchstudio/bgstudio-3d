from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime
import json, base64, re, webbrowser, threading, sys, shutil, traceback, zipfile

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / 'static'
DATA = ROOT / 'data' / 'products.json'
NFC_DATA = ROOT / 'data' / 'nfc_references.json'
PROTOTYPE_DATA = ROOT / 'data' / 'prototypes.json'
BACKUPS = ROOT / 'data' / 'backups'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import build_site

PANEL_VERSION = '2.5.3'

MIME = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
    '.svg': 'image/svg+xml', '.json': 'application/json; charset=utf-8', '.ico': 'image/x-icon'
}


def slugify(text):
    tr = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')
    s = str(text or '').translate(tr).lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:80]


def clip_seo_text(text, max_len=160):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(text) <= max_len:
        return text
    clipped = text[:max_len + 1]
    if ' ' in clipped:
        clipped = clipped.rsplit(' ', 1)[0]
    clipped = re.sub(r'[,:;.!?\-–—]+$', '', clipped).rstrip()
    return clipped + '.'


def make_seo(name, card_description='', description=''):
    name = str(name or '').strip()
    source = str(card_description or description or '').strip()
    if source and name:
        source = re.sub(r'^' + re.escape(name) + r'\s*[-—–:,.]*\s*', '', source, flags=re.I)
        source = re.sub(r'\s+', ' ', source).strip()
        source = re.sub(r'[.!?]+$', '', source).strip()
    title = f"{name} | Kuşadası 3D Baskı | BG Studio 3D" if name else ''
    suffix = '3D baskı ile üretilir. Kuşadası elden teslim ve Türkiye geneli kargo.'
    seo_description = f"{name}, {source}. {suffix}" if source else f"{name}, {suffix}"
    return title, clip_seo_text(seo_description, 160)


def read_products():
    return json.loads(DATA.read_text(encoding='utf-8'))


def write_products(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def backup():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    if DATA.exists():
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        path = BACKUPS / f"products-{stamp}.json"
        shutil.copy2(DATA, path)
        # Keep lightweight automatic JSON backups bounded.
        auto = sorted(BACKUPS.glob('products-*.json'), reverse=True)
        for old in auto[60:]:
            old.unlink(missing_ok=True)
        return path
    return None


def full_backup(reason='manual'):
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    safe_reason = re.sub(r'[^a-z0-9-]+', '-', str(reason).lower()).strip('-') or 'manual'
    path = BACKUPS / f"site-{stamp}-{safe_reason}.zip"
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        if DATA.exists(): z.write(DATA, DATA.relative_to(ROOT))
        for content_data in (NFC_DATA, PROTOTYPE_DATA):
            if content_data.exists(): z.write(content_data, content_data.relative_to(ROOT))
        for folder in (ROOT / 'assets/images/products', ROOT / 'assets/images/posters', ROOT / 'assets/images/references', ROOT / 'assets/images/prototypes'):
            if folder.exists():
                for file in folder.rglob('*'):
                    if file.is_file(): z.write(file, file.relative_to(ROOT))
    snaps = sorted(BACKUPS.glob('site-*.zip'), reverse=True)
    for old in snaps[15:]: old.unlink(missing_ok=True)
    return path


def list_backups():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    files = sorted([*BACKUPS.glob('site-*.zip'), *BACKUPS.glob('products-*.json')], key=lambda x: x.stat().st_mtime, reverse=True)
    out = []
    for file in files[:30]:
        out.append({
            'name': file.name,
            'type': 'full' if file.suffix.lower() == '.zip' else 'products',
            'size': file.stat().st_size,
            'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat(timespec='seconds')
        })
    return out


def restore_backup(name):
    file = (BACKUPS / Path(str(name)).name).resolve()
    if BACKUPS.resolve() not in file.parents or not file.exists():
        raise ValueError('Yedek bulunamadı.')
    full_backup('before-restore')
    if file.suffix.lower() == '.json':
        data = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(data, list): raise ValueError('Yedek ürün verisi geçersiz.')
        write_products(data)
    elif file.suffix.lower() == '.zip':
        with zipfile.ZipFile(file, 'r') as z:
            for member in z.infolist():
                target = (ROOT / member.filename).resolve()
                if ROOT.resolve() not in target.parents and target != ROOT.resolve():
                    raise ValueError('Yedek içeriği güvenli değil.')
            z.extractall(ROOT)
    else:
        raise ValueError('Desteklenmeyen yedek türü.')
    return build_site()


def preflight():
    checks = []
    try:
        products = read_products()
        checks.append({'status':'pass','label':'Ürün verisi','detail':f'{len(products)} ürün JSON dosyasından okunuyor.'})
    except Exception as e:
        return {'ok':False,'checks':[{'status':'fail','label':'Ürün verisi','detail':str(e)}]}
    active = [x for x in products if x.get('active', True)]
    slugs = [x.get('slug') for x in products]
    dupes = sorted({x for x in slugs if x and slugs.count(x) > 1})
    checks.append({'status':'fail' if dupes else 'pass','label':'URL slug','detail':('Tekrarlanan: '+', '.join(dupes)) if dupes else 'Tüm ürün URL slug alanları benzersiz.'})
    missing = []
    for prod in products:
        if prod.get('main_image') and not (ROOT / prod['main_image']).exists(): missing.append(f"{prod.get('name')}: ana görsel")
        if not (ROOT / 'urunler' / str(prod.get('slug')) / 'index.html').exists(): missing.append(f"{prod.get('name')}: ürün sayfası")
        for item in normalize_gallery(prod.get('gallery_images')):
            if not (ROOT / item['path']).exists(): missing.append(f"{prod.get('name')}: galeri")
    checks.append({'status':'fail' if missing else 'pass','label':'Ürün dosyaları','detail':('Eksik: '+', '.join(missing[:8])) if missing else 'Ürün sayfaları ve referans verilen görseller mevcut.'})
    pricing_bad = []
    for prod in products:
        seen = set()
        for tier in normalize_pricing_tiers(prod.get('pricing_tiers')):
            qty = tier.get('quantity')
            if qty in seen or not tier.get('price_value'):
                pricing_bad.append(prod.get('name'))
                break
            seen.add(qty)
    checks.append({'status':'warn' if pricing_bad else 'pass','label':'Set fiyatları','detail':('Kontrol et: '+', '.join(pricing_bad[:8])) if pricing_bad else 'Tanımlı set / adet fiyatları geçerli.'})
    seo_missing = [p.get('name') for p in active if not p.get('seo_title') or not p.get('seo_description')]
    checks.append({'status':'warn' if seo_missing else 'pass','label':'SEO alanları','detail':('Eksik: '+', '.join(seo_missing[:8])) if seo_missing else 'Yayındaki tüm ürünlerde SEO başlığı ve açıklaması var.'})
    cname = ROOT / 'CNAME'
    cname_ok = cname.exists() and cname.read_text(encoding='utf-8').strip() == '3d.bgstudio.com.tr'
    checks.append({'status':'fail' if not cname_ok else 'pass','label':'Canlı domain','detail':'CNAME = 3d.bgstudio.com.tr' if cname_ok else 'CNAME eksik veya beklenen domain farklı.'})
    sitemap = ROOT / 'sitemap.xml'
    expected = len(active) + 12
    locs = sitemap.read_text(encoding='utf-8').count('<loc>') if sitemap.exists() else 0
    checks.append({'status':'pass' if locs == expected else 'warn','label':'Sitemap','detail':f'{locs} URL bulundu; beklenen {expected}.'})
    featured = len([p for p in active if p.get('featured')])
    checks.append({'status':'warn' if featured > 8 else 'pass','label':'Öne çıkanlar','detail':f'{featured} ürün ana sayfada öne çıkıyor.'})
    failures = sum(c['status']=='fail' for c in checks)
    warnings = sum(c['status']=='warn' for c in checks)
    return {'ok': failures == 0, 'checks':checks, 'summary':{'products':len(products),'active':len(active),'failures':failures,'warnings':warnings}}


def save_data_uri(uri, path):
    if not uri:
        return
    m = re.match(r'^data:[^;]+;base64,(.+)$', uri, re.S)
    if not m:
        raise ValueError('Görsel verisi okunamadı.')
    raw = base64.b64decode(m.group(1))
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Görsel çok büyük.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def remove_file(rel):
    if not rel:
        return
    p = (ROOT / str(rel)).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError:
        return
    if p.exists() and p.is_file():
        p.unlink()


def normalize_gallery(value):
    out = []
    for item in value or []:
        if isinstance(item, str):
            out.append({'path': item, 'width': 1000, 'height': 1000, 'alt': ''})
        elif isinstance(item, dict) and item.get('path'):
            out.append({
                'path': str(item.get('path')),
                'width': int(item.get('width') or 1000),
                'height': int(item.get('height') or 1000),
                'alt': str(item.get('alt') or '')
            })
    return out[:12]


def normalize_pricing_tiers(items):
    out = []
    seen = set()
    for item in (items or []):
        if not isinstance(item, dict):
            continue
        try:
            qty = int(item.get('quantity') or 0)
        except Exception:
            qty = 0
        raw_price = str(item.get('price_value') or '').strip().replace(',', '.')
        if qty < 1 or not re.fullmatch(r'\d+(?:\.\d+)?', raw_price):
            continue
        if qty in seen:
            continue
        seen.add(qty)
        label = str(item.get('label') or '').strip() or (f"{qty}’li set" if qty > 1 else 'Tekli')
        note = str(item.get('note') or '').strip()
        out.append({'label': label[:60], 'quantity': qty, 'price_value': raw_price, 'note': note[:80]})
    return sorted(out, key=lambda x: x['quantity'])[:12]


def clean_product(p):
    allowed = {
        'slug', 'name', 'category', 'price_text', 'price_value', 'card_description', 'description',
        'options', 'features', 'production_note', 'main_image', 'main_image_width', 'main_image_height',
        'poster_image', 'poster_image_width', 'poster_image_height', 'gallery_images', 'featured', 'active',
        'sort_order', 'seo_title', 'seo_description', 'pricing_tiers'
    }
    out = {k: p.get(k) for k in allowed if k in p}
    out['name'] = str(out.get('name') or '').strip()
    out['slug'] = slugify(str(out.get('slug') or out['name']))
    if not out['name'] or not out['slug']:
        raise ValueError('Ürün adı ve URL slug zorunlu.')
    if out.get('category') not in ('dekoratif', 'aydinlatma', 'fonksiyonel', 'kisiye-ozel'):
        raise ValueError('Kategori geçersiz.')
    out['price_text'] = str(out.get('price_text') or 'Fiyat için iletişim').strip()
    pv = str(out.get('price_value') or '').strip().replace(',', '.')
    out['price_value'] = pv if re.fullmatch(r'\d+(?:\.\d+)?', pv) else None
    out['card_description'] = str(out.get('card_description') or '').strip()
    out['description'] = str(out.get('description') or '').strip()
    out['production_note'] = str(out.get('production_note') or '').strip()
    out['options'] = [str(x).strip() for x in (out.get('options') or []) if str(x).strip()]
    out['features'] = [str(x).strip() for x in (out.get('features') or []) if str(x).strip()]
    out['pricing_tiers'] = normalize_pricing_tiers(out.get('pricing_tiers'))
    out['gallery_images'] = normalize_gallery(out.get('gallery_images'))
    out['featured'] = bool(out.get('featured'))
    out['active'] = bool(out.get('active', True))
    try:
        out['sort_order'] = int(out.get('sort_order') or 999)
    except Exception:
        out['sort_order'] = 999
    default_title, default_description = make_seo(out['name'], out['card_description'], out['description'])
    out['seo_title'] = str(out.get('seo_title') or default_title).strip()
    out['seo_description'] = clip_seo_text(out.get('seo_description') or default_description, 160)
    return out


def unique_slug(products, base):
    existing = {p.get('slug') for p in products}
    candidate = slugify(base) or 'urun-kopya'
    if candidate not in existing:
        return candidate
    n = 2
    while f'{candidate}-{n}' in existing:
        n += 1
    return f'{candidate}-{n}'


def duplicate_asset(src_rel, dst_rel):
    if not src_rel:
        return None
    src = ROOT / src_rel
    dst = ROOT / dst_rel
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst_rel
    return None



def content_path(kind):
    if kind == 'nfc': return NFC_DATA
    if kind == 'prototype': return PROTOTYPE_DATA
    raise ValueError('İçerik türü geçersiz.')


def read_content(kind):
    path = content_path(kind)
    if not path.exists(): return []
    return json.loads(path.read_text(encoding='utf-8'))


def write_content(kind, data):
    content_path(kind).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def clean_content_item(kind, item):
    name = str(item.get('name') or '').strip()
    slug = slugify(item.get('slug') or name)
    if not name or not slug: raise ValueError('İsim zorunlu.')
    out = {
        'slug': slug, 'name': name,
        'headline': str(item.get('headline') or '').strip(),
        'description': str(item.get('description') or '').strip(),
        'tags': [str(x).strip() for x in (item.get('tags') or []) if str(x).strip()][:8],
        'active': bool(item.get('active', True)),
        'sort_order': int(item.get('sort_order') or 999),
    }
    if kind == 'prototype': out['category'] = str(item.get('category') or 'Prototip / özel parça').strip()
    if item.get('image'): out['image'] = str(item.get('image'))
    return out


def save_content_item(kind, payload):
    items = read_content(kind)
    original = str(payload.get('original_slug') or '')
    item = clean_content_item(kind, payload.get('item') or {})
    if original and item['slug'] != original: raise ValueError('Mevcut kaydın URL slug alanını değiştirmeyin.')
    idx = next((i for i,x in enumerate(items) if x.get('slug') == original), None) if original else None
    if idx is None and any(x.get('slug') == item['slug'] for x in items): raise ValueError('Bu URL slug zaten kullanılıyor.')
    old = items[idx] if idx is not None else {}
    image = payload.get('image')
    if image:
        folder = 'references' if kind == 'nfc' else 'prototypes'
        rel = f'assets/images/{folder}/{item["slug"]}.webp'
        save_data_uri(image.get('data'), ROOT / rel)
        item['image'] = rel
    elif old.get('image'):
        item['image'] = old.get('image')
    if idx is None: items.append(item)
    else: items[idx] = item
    write_content(kind, items)
    return item, build_site()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[Panel]', fmt % args)

    def send_json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.end_headers()
        self.wfile.write(b)

    def read_json(self):
        n = int(self.headers.get('Content-Length', '0'))
        if n > 60 * 1024 * 1024:
            raise ValueError('İstek çok büyük.')
        return json.loads(self.rfile.read(n).decode('utf-8'))

    def send_file(self, file, base):
        file = file.resolve()
        base = base.resolve()
        if base not in file.parents and file != base:
            self.send_error(403)
            return
        if not file.exists() or not file.is_file():
            self.send_error(404)
            return
        b = file.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', MIME.get(file.suffix.lower(), 'application/octet-stream'))
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/products':
            return self.send_json({'products': read_products(), 'root': str(ROOT)})
        if u.path == '/api/status':
            return self.send_json({'ok': True, 'root': str(ROOT), 'version': PANEL_VERSION})
        if u.path == '/api/backups':
            return self.send_json({'ok': True, 'backups': list_backups()})
        if u.path == '/api/preflight':
            return self.send_json(preflight())
        if u.path == '/api/content':
            from urllib.parse import parse_qs
            kind = (parse_qs(u.query).get('kind') or [''])[0]
            return self.send_json({'items': read_content(kind), 'kind': kind, 'root': str(ROOT)})
        if u.path.startswith('/assets/') or u.path in ('/favicon.ico', '/apple-touch-icon.png'):
            return self.send_file(ROOT / unquote(u.path.lstrip('/')), ROOT)
        path = 'index.html' if u.path in ('/', '') else unquote(u.path.lstrip('/'))
        return self.send_file(STATIC / path, STATIC)

    def do_POST(self):
        try:
            if self.path == '/api/save':
                payload = self.read_json()
                original = payload.get('original_slug') or ''
                p = clean_product(payload.get('product') or {})
                if original and p['slug'] != original:
                    raise ValueError('Mevcut ürünün URL slug alanını değiştirmeyin. SEO adresini koruyoruz.')
                products = read_products()
                idx = next((i for i, x in enumerate(products) if x['slug'] == original), None) if original else None
                if idx is None and any(x['slug'] == p['slug'] for x in products):
                    raise ValueError('Bu URL slug zaten kullanılıyor.')
                main = payload.get('main_image')
                poster = payload.get('poster_image')
                gallery = payload.get('gallery_images') or []
                replace_gallery = bool(payload.get('replace_gallery'))
                if idx is None and not main:
                    raise ValueError('Yeni üründe ana görsel zorunlu.')

                old = products[idx] if idx is not None else {}
                if main:
                    p['main_image'] = f"assets/images/products/{p['slug']}.webp"
                    p['main_image_width'] = int(main.get('width') or 1000)
                    p['main_image_height'] = int(main.get('height') or 760)
                    save_data_uri(main.get('data'), ROOT / p['main_image'])
                elif idx is not None:
                    for k in ('main_image', 'main_image_width', 'main_image_height'):
                        p[k] = old.get(k)

                if poster:
                    p['poster_image'] = f"assets/images/posters/{p['slug']}.webp"
                    p['poster_image_width'] = int(poster.get('width') or 1254)
                    p['poster_image_height'] = int(poster.get('height') or 1254)
                    save_data_uri(poster.get('data'), ROOT / p['poster_image'])
                elif idx is not None:
                    for k in ('poster_image', 'poster_image_width', 'poster_image_height'):
                        p[k] = old.get(k)

                if replace_gallery:
                    for item in normalize_gallery(old.get('gallery_images')):
                        remove_file(item.get('path'))
                    saved_gallery = []
                    for n, image in enumerate(gallery[:12], 1):
                        rel = f"assets/images/products/{p['slug']}-gallery-{n:02d}.webp"
                        save_data_uri(image.get('data'), ROOT / rel)
                        saved_gallery.append({
                            'path': rel,
                            'width': int(image.get('width') or 1000),
                            'height': int(image.get('height') or 1000),
                            'alt': f"{p['name']} galeri görseli {n}"
                        })
                    p['gallery_images'] = saved_gallery
                elif idx is not None:
                    p['gallery_images'] = normalize_gallery(old.get('gallery_images'))

                backup()
                if idx is None:
                    products.append(p)
                else:
                    products[idx] = p
                write_products(products)
                result = build_site()
                return self.send_json({'ok': True, 'message': 'Ürün kaydedildi ve site dosyaları güncellendi.', 'result': result, 'product': p})

            if self.path == '/api/duplicate':
                payload = self.read_json()
                slug = payload.get('slug')
                products = read_products()
                src = next((x for x in products if x.get('slug') == slug), None)
                if not src:
                    raise ValueError('Kopyalanacak ürün bulunamadı.')
                backup()
                p = json.loads(json.dumps(src, ensure_ascii=False))
                p['name'] = f"{src.get('name', 'Ürün')} Kopya"
                p['slug'] = unique_slug(products, f"{src.get('slug', 'urun')}-kopya")
                p['active'] = False
                p['featured'] = False
                p['sort_order'] = max([int(x.get('sort_order') or 0) for x in products] + [0]) + 10
                p['seo_title'], p['seo_description'] = make_seo(p['name'], p.get('card_description'), p.get('description'))
                main = f"assets/images/products/{p['slug']}.webp"
                if duplicate_asset(src.get('main_image'), main):
                    p['main_image'] = main
                if src.get('poster_image'):
                    poster = f"assets/images/posters/{p['slug']}.webp"
                    if duplicate_asset(src.get('poster_image'), poster):
                        p['poster_image'] = poster
                new_gallery = []
                for n, item in enumerate(normalize_gallery(src.get('gallery_images')), 1):
                    rel = f"assets/images/products/{p['slug']}-gallery-{n:02d}.webp"
                    if duplicate_asset(item.get('path'), rel):
                        new_gallery.append({**item, 'path': rel, 'alt': f"{p['name']} galeri görseli {n}"})
                p['gallery_images'] = new_gallery
                products.append(p)
                write_products(products)
                build_site()
                return self.send_json({'ok': True, 'message': 'Ürün kopyalandı. Güvenlik için arşivde oluşturuldu.', 'product': p})

            if self.path == '/api/archive':
                payload = self.read_json()
                slug = payload.get('slug')
                products = read_products()
                p = next((x for x in products if x.get('slug') == slug), None)
                if not p:
                    raise ValueError('Ürün bulunamadı.')
                backup()
                new_active = bool(payload.get('active', False))
                p['active'] = new_active
                if not new_active:
                    p['featured'] = False
                write_products(products)
                build_site()
                return self.send_json({'ok': True, 'message': 'Ürün yayına alındı.' if new_active else 'Ürün arşivlendi.', 'product': p})

            if self.path == '/api/feature':
                payload = self.read_json()
                slug = payload.get('slug')
                products = read_products()
                p = next((x for x in products if x.get('slug') == slug), None)
                if not p:
                    raise ValueError('Ürün bulunamadı.')
                backup()
                p['featured'] = not bool(p.get('featured'))
                if p['featured']:
                    p['active'] = True
                write_products(products)
                build_site()
                return self.send_json({'ok': True, 'message': 'Öne çıkan durumu güncellendi.', 'product': p})

            if self.path == '/api/reorder':
                payload = self.read_json()
                order = payload.get('order') or []
                products = read_products()
                by_slug = {p.get('slug'): p for p in products}
                ordered = []
                seen = set()
                for slug in order:
                    if slug in by_slug and slug not in seen:
                        ordered.append(by_slug[slug]); seen.add(slug)
                ordered += [p for p in sorted(products, key=lambda x: int(x.get('sort_order') or 9999)) if p.get('slug') not in seen]
                backup()
                for i, p in enumerate(ordered, 1):
                    p['sort_order'] = i * 10
                write_products(products)
                build_site()
                return self.send_json({'ok': True, 'message': 'Katalog sırası güncellendi.', 'products': products})

            if self.path == '/api/delete':
                payload = self.read_json()
                slug = payload.get('slug')
                products = read_products()
                p = next((x for x in products if x.get('slug') == slug), None)
                if not p:
                    raise ValueError('Ürün bulunamadı.')
                backup()
                full_backup('before-delete')
                products = [x for x in products if x.get('slug') != slug]
                write_products(products)
                remove_file(p.get('main_image'))
                remove_file(p.get('poster_image'))
                for item in normalize_gallery(p.get('gallery_images')):
                    remove_file(item.get('path'))
                folder = ROOT / 'urunler' / slug
                if folder.exists() and folder.is_dir():
                    shutil.rmtree(folder)
                build_site()
                return self.send_json({'ok': True, 'message': 'Ürün kalıcı olarak silindi.'})

            if self.path == '/api/content/save':
                payload = self.read_json()
                kind = payload.get('kind')
                full_backup('before-content-save')
                item, result = save_content_item(kind, payload)
                return self.send_json({'ok': True, 'message': 'İçerik kaydedildi ve site güncellendi.', 'item': item, 'result': result})

            if self.path == '/api/content/delete':
                payload = self.read_json()
                kind = payload.get('kind')
                slug = str(payload.get('slug') or '')
                items = read_content(kind)
                item = next((x for x in items if x.get('slug') == slug), None)
                if not item: raise ValueError('Kayıt bulunamadı.')
                full_backup('before-content-delete')
                remove_file(item.get('image'))
                write_content(kind, [x for x in items if x.get('slug') != slug])
                result = build_site()
                return self.send_json({'ok': True, 'message': 'Kayıt silindi.', 'result': result})

            if self.path == '/api/backup':
                path = full_backup('manual')
                return self.send_json({'ok': True, 'message': 'Tam site yedeği oluşturuldu.', 'backup': path.name, 'backups': list_backups()})

            if self.path == '/api/restore':
                payload = self.read_json()
                result = restore_backup(payload.get('name') or '')
                return self.send_json({'ok': True, 'message': 'Yedek geri yüklendi ve site yeniden oluşturuldu.', 'result': result})

            if self.path == '/api/rebuild':
                return self.send_json({'ok': True, 'result': build_site(), 'message': 'Site yeniden oluşturuldu.'})

            if self.path == '/api/shutdown':
                self.send_json({'ok': True, 'message': 'Panel kapatılıyor.'})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return

            self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            self.send_json({'ok': False, 'error': str(e)}, 400)


def run():
    server = None
    port = None
    for p in range(8765, 8780):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', p), Handler)
            port = p
            break
        except OSError:
            continue
    if not server:
        print('Uygun port bulunamadı.')
        input('Enter...')
        return
    url = f'http://127.0.0.1:{port}/'
    print('\nBG Studio 3D Ürün Yöneticisi PRO')
    print('Panel:', url)
    print('Repo :', ROOT)
    print('Kapatmak için paneldeki "Paneli kapat" butonunu kullan.\n')
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    run()
