from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime
import json, base64, re, webbrowser, threading, sys, shutil, traceback

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / 'static'
DATA = ROOT / 'data' / 'products.json'
BACKUPS = ROOT / 'data' / 'backups'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import build_site

MIME = {
    '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
    '.svg': 'image/svg+xml', '.json': 'application/json; charset=utf-8', '.ico': 'image/x-icon'
}


def slugify(text):
    tr = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')
    s = text.translate(tr).lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:80]


def read_products():
    return json.loads(DATA.read_text(encoding='utf-8'))


def write_products(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def backup():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    if DATA.exists():
        shutil.copy2(DATA, BACKUPS / f"products-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")


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


def clean_product(p):
    allowed = {
        'slug', 'name', 'category', 'price_text', 'price_value', 'card_description', 'description',
        'options', 'features', 'production_note', 'main_image', 'main_image_width', 'main_image_height',
        'poster_image', 'poster_image_width', 'poster_image_height', 'featured', 'active', 'sort_order',
        'seo_title', 'seo_description'
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
    out['featured'] = bool(out.get('featured'))
    out['active'] = bool(out.get('active', True))
    try:
        out['sort_order'] = int(out.get('sort_order') or 999)
    except Exception:
        out['sort_order'] = 999
    out['seo_title'] = str(out.get('seo_title') or f"{out['name']} | BG Studio 3D").strip()
    out['seo_description'] = str(out.get('seo_description') or f"{out['name']} — {out['description']}").strip()[:170]
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('[Panel]', fmt % args)

    def send_json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def read_json(self):
        n = int(self.headers.get('Content-Length', '0'))
        if n > 25 * 1024 * 1024:
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
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/api/products':
            return self.send_json({'products': read_products(), 'root': str(ROOT)})
        if u.path == '/api/status':
            return self.send_json({'ok': True, 'root': str(ROOT)})
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
                if idx is None and not main:
                    raise ValueError('Yeni üründe ana görsel zorunlu.')

                if main:
                    p['main_image'] = f"assets/images/products/{p['slug']}.webp"
                    p['main_image_width'] = int(main.get('width') or 1000)
                    p['main_image_height'] = int(main.get('height') or 760)
                    save_data_uri(main.get('data'), ROOT / p['main_image'])
                elif idx is not None:
                    old = products[idx]
                    for k in ('main_image', 'main_image_width', 'main_image_height'):
                        p[k] = old.get(k)

                if poster:
                    p['poster_image'] = f"assets/images/posters/{p['slug']}.webp"
                    p['poster_image_width'] = int(poster.get('width') or 1254)
                    p['poster_image_height'] = int(poster.get('height') or 1254)
                    save_data_uri(poster.get('data'), ROOT / p['poster_image'])
                elif idx is not None:
                    old = products[idx]
                    for k in ('poster_image', 'poster_image_width', 'poster_image_height'):
                        p[k] = old.get(k)

                backup()
                if idx is None:
                    products.append(p)
                else:
                    products[idx] = p
                write_products(products)
                result = build_site()
                return self.send_json({'ok': True, 'message': 'Ürün kaydedildi ve site dosyaları güncellendi.', 'result': result, 'product': p})

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
    print('\nBG Studio 3D Ürün Yöneticisi')
    print('Repo:', ROOT)
    print('Panel:', url)
    print('Kapatmak için paneldeki “Paneli kapat” düğmesini kullanabilir veya bu pencereyi kapatabilirsiniz.\n')
    threading.Timer(.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()
