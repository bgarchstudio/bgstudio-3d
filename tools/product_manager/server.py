from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote
from urllib.request import urlopen, Request
from datetime import datetime
import json, base64, re, webbrowser, threading, sys, shutil, traceback, time

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent / 'static'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage import (
    ensure_initialized, get_collection, set_collection, export_to_repo,
    save_media, remove_media, copy_media, media_path,
    create_db_backup, create_full_backup, list_backups as storage_list_backups,
    restore_backup as storage_restore_backup, status as storage_status,
    BACKUPS_ROOT
)
from build import build_site

PANEL_VERSION = '3.1.22'
BACKUPS = BACKUPS_ROOT

PRODUCT_CATEGORIES = {
    'dekoratif-duvar', 'aydinlatma', 'ev-duzen', 'gaming-masaustu',
    'anahtarlik-aksesuar', 'hediye-kisiye-ozel', 'pratik-fonksiyonel',
    'pet-urunleri'
}
CATEGORY_ALIASES = {
    'dekoratif': 'dekoratif-duvar',
    'aydinlatma': 'aydinlatma',
    'fonksiyonel': 'pratik-fonksiyonel',
    'kisiye-ozel': 'hediye-kisiye-ozel',
    'pet': 'pet-urunleri',
}
TAG_PRESETS = [
    'Kişiye Özel', 'Kurumsal', 'Adetli Üretim', 'Logolu', 'Hediye',
    'Gaming', 'PlayStation', 'Xbox', 'Masaüstü', 'Anahtarlık', 'Organizer',
    'Duvar Dekoru', 'Açacak', 'Telefon', 'Saat / Şarj', 'Futbol', 'Flexi', 'Kitap',
    'Pet', 'Kedi', 'Köpek', 'Mama', 'Mama Küreği', 'Su Kabı', 'Oyuncak', 'Petshop'
]
ensure_initialized()
export_to_repo()

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
    data = get_collection('products', [])
    return data if isinstance(data, list) else []


def write_products(data):
    set_collection('products', data)


def read_colors():
    data = get_collection('colors', [])
    if not isinstance(data, list):
        return []
    return sorted(data, key=lambda x: (int(x.get('sort_order') or 9999), str(x.get('name') or '').casefold()))

def normalize_hex(value):
    value = str(value or '').strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        return value.lower()
    return '#c7b9a6'


def clean_colors(items):
    out = []
    seen = set()
    for i, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get('name') or '').strip()
        if not name:
            continue
        color_id = slugify(item.get('id') or name)
        if not color_id or color_id in seen:
            continue
        seen.add(color_id)
        raw_qty = item.get('stock_qty')
        if raw_qty in ('', None):
            qty = None
        else:
            try:
                qty = max(0, int(raw_qty))
            except Exception:
                qty = None
        in_stock = bool(item.get('in_stock', True)) and (qty is None or qty > 0)
        out.append({
            'id': color_id,
            'name': name[:60],
            'hex': normalize_hex(item.get('hex')),
            'in_stock': in_stock,
            'stock_qty': qty,
            'sort_order': int(item.get('sort_order') or ((i + 1) * 10)),
        })
    return sorted(out, key=lambda x: (x['sort_order'], x['name'].casefold()))[:80]


def write_colors(items):
    clean = clean_colors(items)
    set_collection('colors', clean)
    return clean


def backup():
    return create_db_backup('products-auto')


def full_backup(reason='manual'):
    return create_full_backup(reason)


def list_backups():
    return storage_list_backups()


def restore_backup(name):
    storage_restore_backup(name)
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
    colors = read_colors()
    color_ids = {c.get('id') for c in colors}
    bad_color_refs = []
    for prod in products:
        for cid in (prod.get('color_ids') or []):
            if cid not in color_ids:
                bad_color_refs.append(f"{prod.get('name')}: {cid}")
    stocked = len([c for c in colors if c.get('in_stock')])
    checks.append({'status':'warn' if bad_color_refs else 'pass','label':'Renk stoğu','detail':('Eksik renk referansı: '+', '.join(bad_color_refs[:8])) if bad_color_refs else f'{len(colors)} renk tanımlı, {stocked} renk stokta.'})
    try:
        corp = read_content('corporate')
        nfc_slugs = {x.get('slug') for x in read_content('nfc')}
        broken_links = [x.get('source_slug') for x in corp if x.get('source_kind') == 'nfc' and x.get('source_slug') not in nfc_slugs]
        checks.append({'status':'warn' if broken_links else 'pass','label':'Kurumsal senkron','detail':('Bağlantısı kopuk: '+', '.join(broken_links[:8])) if broken_links else f'{len(corp)} kurumsal kart; NFC bağlantıları senkron.'})
    except Exception as e:
        checks.append({'status':'warn','label':'Kurumsal senkron','detail':str(e)})
    try:
        nfc_rows = [x for x in read_content('nfc') if x.get('active', True)]
        nfc_page = (ROOT / 'nfc-qr' / 'index.html').read_text(encoding='utf-8')
        rendered = len(re.findall(r'data-reference-id="[^"]+"', nfc_page))
        checks.append({
            'status':'pass' if rendered == len(nfc_rows) else 'fail',
            'label':'NFC sayfa senkronu',
            'detail':f'Panelde {len(nfc_rows)} aktif NFC referansı, sitede {rendered} kart render edildi.'
        })
    except Exception as e:
        checks.append({'status':'warn','label':'NFC sayfa senkronu','detail':str(e)})
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

    # Site-wide chrome and internal-link audit. This catches navigation drift before GitHub push.
    public_html = [p for p in ROOT.rglob('*.html') if 'tools\\product_manager' not in str(p) and 'tools/product_manager' not in p.as_posix()]
    nav_issues = []
    active_nav_issues = []
    title_map = {}
    h1_issues = []
    broken_links = []
    proto_label = 'Prototip &amp; Parça Üretim'
    expected_active = {
        'urunler/index.html': 'urunler/',
        'ozel-uretim/index.html': 'ozel-uretim/',
        'kurumsal/index.html': 'kurumsal/',
        'nfc-qr/index.html': 'nfc-qr/',
        'prototip-parca/index.html': 'prototip-parca/',
        'hakkimizda/index.html': 'hakkimizda/',
        'iletisim/index.html': 'iletisim/',
    }
    for page in public_html:
        try:
            html = page.read_text(encoding='utf-8')
        except Exception:
            continue
        rel_page = page.relative_to(ROOT).as_posix()
        nav_match = re.search(r'<nav\b[^>]*class="[^"]*main-nav[^"]*"[^>]*>(.*?)</nav>', html, re.S | re.I)
        if nav_match:
            nav_html = nav_match.group(1)
            if 'prototip-parca/' not in nav_html or proto_label not in nav_html:
                nav_issues.append(rel_page)
            expected_href = expected_active.get(rel_page)
            if expected_href:
                active_match = re.search(r'<a\b[^>]*(?:aria-current="page"|class="[^"]*is-active[^"]*")[^>]*href="([^"]+)"|<a\b[^>]*href="([^"]+)"[^>]*(?:aria-current="page"|class="[^"]*is-active[^"]*")', nav_html, re.I)
                active_href = next((g for g in (active_match.groups() if active_match else []) if g), '')
                if expected_href not in active_href:
                    active_nav_issues.append(rel_page)
        title_match = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
        if title_match:
            title_text = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            title_map.setdefault(title_text, []).append(rel_page)
        h1_count = len(re.findall(r'<h1\b', html, re.I))
        if h1_count != 1 and rel_page != '404.html':
            h1_issues.append(f'{rel_page} ({h1_count} h1)')
        for href in re.findall(r'href="([^"]+)"', html, re.I):
            href = href.strip()
            if not href or href.startswith(('#','http://','https://','mailto:','tel:','javascript:')):
                continue
            clean = href.split('#',1)[0].split('?',1)[0]
            if not clean:
                continue
            if clean.startswith('/'):
                target = ROOT / clean.lstrip('/')
            else:
                target = page.parent / clean
            if clean.endswith('/'):
                target = target / 'index.html'
            elif target.is_dir():
                target = target / 'index.html'
            if not target.exists():
                broken_links.append(f'{rel_page} → {href}')
    duplicate_titles = [f"{title}: {', '.join(pages[:3])}" for title,pages in title_map.items() if title and len(pages) > 1]
    checks.append({'status':'fail' if nav_issues else 'pass','label':'Ana menü tutarlılığı','detail':('Prototip sekmesi eksik/farklı: '+', '.join(nav_issues[:8])) if nav_issues else 'Tüm sayfalarda Prototip & Parça Üretim sekmesi aynı.'})
    checks.append({'status':'warn' if active_nav_issues else 'pass','label':'Aktif sekme durumu','detail':('Aktif menü yanlış/eksik: '+', '.join(active_nav_issues[:8])) if active_nav_issues else 'Ana hizmet sayfalarında aktif sekme doğru işaretleniyor.'})
    checks.append({'status':'warn' if h1_issues else 'pass','label':'Sayfa başlık yapısı','detail':('Kontrol et: '+', '.join(h1_issues[:8])) if h1_issues else 'Tüm ana sayfalarda tek H1 kullanılıyor.'})
    checks.append({'status':'warn' if duplicate_titles else 'pass','label':'SEO başlık benzersizliği','detail':('Tekrarlanan title: '+ ' | '.join(duplicate_titles[:4])) if duplicate_titles else 'HTML title alanları birbirinden ayrışıyor.'})
    checks.append({'status':'fail' if broken_links else 'pass','label':'İç bağlantılar','detail':('Kırık: '+', '.join(broken_links[:8])) if broken_links else f'{len(public_html)} HTML sayfada yerel bağlantılar sağlam.'})

    featured = len([p for p in active if p.get('featured')])
    checks.append({'status':'pass','label':'Öne çıkanlar','detail':f'{featured} ürün ana sayfada öne çıkıyor; sabit ürün limiti uygulanmıyor.'})
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
    try:
        rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
        save_media(rel, raw)
    except ValueError:
        pass


def remove_file(rel):
    if not rel:
        return
    rel = str(rel).replace('\\', '/').lstrip('/')
    p = (ROOT / rel).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError:
        return
    remove_media(rel)
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
        'slug', 'name', 'category', 'price_text', 'price_value', 'sale_price_value', 'card_description', 'description',
        'options', 'features', 'production_note', 'main_image', 'main_image_width', 'main_image_height',
        'poster_image', 'poster_image_width', 'poster_image_height', 'gallery_images', 'featured', 'active',
        'sort_order', 'seo_title', 'seo_description', 'pricing_tiers', 'color_ids', 'tags'
    }
    out = {k: p.get(k) for k in allowed if k in p}
    out['name'] = str(out.get('name') or '').strip()
    out['slug'] = slugify(str(out.get('slug') or out['name']))
    if not out['name'] or not out['slug']:
        raise ValueError('Ürün adı ve URL slug zorunlu.')
    category = str(out.get('category') or '').strip()
    category = CATEGORY_ALIASES.get(category, category)
    if category not in PRODUCT_CATEGORIES:
        raise ValueError('Kategori geçersiz.')
    out['category'] = category
    out['price_text'] = str(out.get('price_text') or 'Fiyat için iletişim').strip()
    pv = str(out.get('price_value') or '').strip().replace(',', '.')
    out['price_value'] = pv if re.fullmatch(r'\d+(?:\.\d+)?', pv) else None
    sale_raw = str(out.get('sale_price_value') or '').strip().replace(',', '.')
    if sale_raw:
        if not re.fullmatch(r'\d+(?:\.\d+)?', sale_raw):
            raise ValueError('İndirimli fiyat geçersiz.')
        if out['price_value'] is None:
            raise ValueError('İndirim için normal sayısal fiyat zorunlu.')
        if float(sale_raw) <= 0 or float(sale_raw) >= float(out['price_value']):
            raise ValueError('İndirimli fiyat normal fiyattan düşük olmalı.')
        out['sale_price_value'] = sale_raw
    else:
        out['sale_price_value'] = None
    out['card_description'] = str(out.get('card_description') or '').strip()
    out['description'] = str(out.get('description') or '').strip()
    out['production_note'] = str(out.get('production_note') or '').strip()
    out['options'] = [str(x).strip() for x in (out.get('options') or []) if str(x).strip()]
    valid_color_ids = {c.get('id') for c in read_colors()}
    out['color_ids'] = [str(x).strip() for x in (out.get('color_ids') or []) if str(x).strip() in valid_color_ids]
    out['features'] = [str(x).strip() for x in (out.get('features') or []) if str(x).strip()]
    clean_tags = []
    seen_tags = set()
    for value in (out.get('tags') or []):
        tag = re.sub(r'\s+', ' ', str(value or '')).strip()[:40]
        key = tag.casefold()
        if tag and key not in seen_tags:
            seen_tags.add(key)
            clean_tags.append(tag)
    out['tags'] = clean_tags[:16]
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
    return dst_rel if copy_media(src_rel, dst_rel) else None



def content_collection(kind):
    if kind == 'nfc': return 'nfc'
    if kind == 'prototype': return 'prototype'
    if kind == 'corporate': return 'corporate'
    raise ValueError('İçerik türü geçersiz.')


def read_content(kind):
    data = get_collection(content_collection(kind), [])
    return data if isinstance(data, list) else []


def write_content(kind, data):
    set_collection(content_collection(kind), data)


def resequence_content(items, preferred_slug='', desired_position=None):
    """Treat sort_order as a 1-based position and keep every value unique."""
    rows = [dict(x) for x in (items or []) if isinstance(x, dict)]
    preferred_slug = str(preferred_slug or '')
    preferred = next((x for x in rows if str(x.get('slug') or '') == preferred_slug), None) if preferred_slug else None
    others = [x for x in rows if x is not preferred]
    others.sort(key=lambda x: (int(x.get('sort_order') or 999999), str(x.get('name') or x.get('slug') or '').casefold()))
    if preferred is not None:
        try:
            pos = int(desired_position or preferred.get('sort_order') or len(rows))
        except Exception:
            pos = len(rows)
        pos = max(1, min(len(others) + 1, pos))
        others.insert(pos - 1, preferred)
    for i, row in enumerate(others, 1):
        row['sort_order'] = i
    return others


def sync_nfc_to_corporate(nfc_items=None, corporate_items=None):
    """All NFC & QR references are automatically represented on the corporate page."""
    nfc_items = resequence_content(nfc_items if nfc_items is not None else read_content('nfc'))
    corporate_items = list(corporate_items if corporate_items is not None else read_content('corporate'))
    nfc_slugs = {str(x.get('slug') or '') for x in nfc_items if x.get('slug')}
    existing_links = {}
    independent = []
    for row in corporate_items:
        if row.get('source_kind') == 'nfc' and row.get('source_slug'):
            slug = str(row.get('source_slug'))
            if slug in nfc_slugs and slug not in existing_links:
                existing_links[slug] = dict(row)
            continue
        slug = str(row.get('slug') or '')
        if slug in nfc_slugs and slug not in existing_links:
            existing_links[slug] = {
                'slug': slug, 'source_kind': 'nfc', 'source_slug': slug,
                'theme': 'dark' if str(row.get('theme') or '').lower() == 'dark' else 'light',
                'active': bool(row.get('active', True)), 'sort_order': int(row.get('sort_order') or 999)
            }
        else:
            independent.append(dict(row))
    linked = []
    for idx, src in enumerate(nfc_items, 1):
        slug = str(src.get('slug') or '')
        row = existing_links.get(slug) or {
            'slug': slug, 'source_kind': 'nfc', 'source_slug': slug,
            'theme': 'dark' if idx % 2 else 'light', 'active': bool(src.get('active', True)), 'sort_order': idx
        }
        row.update({'slug': slug, 'source_kind': 'nfc', 'source_slug': slug})
        linked.append(row)
    return resequence_content(linked + independent)

def clean_content_item(kind, item):
    if kind == 'corporate':
        source_slug = slugify(item.get('source_slug') or '')
        if source_slug:
            if not any(x.get('slug') == source_slug for x in read_content('nfc')):
                raise ValueError('Bağlı NFC saha kaydı bulunamadı.')
            return {
                'slug': source_slug, 'source_kind': 'nfc', 'source_slug': source_slug,
                'theme': 'dark' if str(item.get('theme') or '').lower() == 'dark' else 'light',
                'active': bool(item.get('active', True)),
                'sort_order': int(item.get('sort_order') or 999),
            }
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
    if kind in ('prototype','nfc'): out['category'] = str(item.get('category') or ('Prototip / özel parça' if kind == 'prototype' else 'NFC / QR saha uygulaması')).strip()
    if kind == 'corporate': out['theme'] = 'dark' if str(item.get('theme') or '').lower() == 'dark' else 'light'
    if item.get('image'): out['image'] = str(item.get('image'))
    if kind in ('nfc','corporate') and item.get('profile_image'):
        out['profile_image'] = str(item.get('profile_image'))
    return out


def save_content_item(kind, payload):
    items = read_content(kind)
    original = str(payload.get('original_slug') or '')
    raw_item = payload.get('item') or {}
    item = clean_content_item(kind, raw_item)
    if original and item['slug'] != original:
        raise ValueError('Mevcut kaydın URL slug alanını değiştirmeyin.')
    idx = next((i for i,x in enumerate(items) if x.get('slug') == original), None) if original else None
    if idx is None and any(x.get('slug') == item['slug'] for x in items):
        raise ValueError('Bu URL slug zaten kullanılıyor.')
    old = items[idx] if idx is not None else {}
    image = payload.get('image')
    if image:
        folder = 'prototypes' if kind == 'prototype' else 'references'
        rel = f'assets/images/{folder}/{item["slug"]}.webp'
        save_data_uri(image.get('data'), ROOT / rel)
        item['image'] = rel
    elif old.get('image'):
        item['image'] = old.get('image')

    if kind in ('nfc', 'corporate') and not (kind == 'corporate' and item.get('source_kind') == 'nfc'):
        profile = payload.get('profile_image')
        clear_profile = bool(payload.get('profile_image_clear'))
        if profile:
            rel = f'assets/images/references/{item["slug"]}-profile.webp'
            save_data_uri(profile.get('data'), ROOT / rel)
            item['profile_image'] = rel
        elif clear_profile:
            old_rel = str(old.get('profile_image') or '')
            if old_rel.startswith('assets/images/references/'):
                try:
                    remove_media(old_rel)
                    (ROOT / old_rel).unlink(missing_ok=True)
                except Exception:
                    pass
            item.pop('profile_image', None)
        elif old.get('profile_image'):
            item['profile_image'] = old.get('profile_image')

    requested_position = int(raw_item.get('sort_order') or (len(items) + 1))
    if idx is None:
        items.append(item)
    else:
        items[idx] = item
    items = resequence_content(items, item['slug'], requested_position)
    item = next(x for x in items if x.get('slug') == item['slug'])
    write_content(kind, items)

    if kind == 'nfc':
        # Every NFC & QR reference automatically appears in Corporate References.
        corporate = sync_nfc_to_corporate(items, read_content('corporate'))
        write_content('corporate', corporate)
    elif kind == 'corporate':
        # Preserve the automatic NFC coverage even after corporate-specific edits.
        corporate = sync_nfc_to_corporate(read_content('nfc'), items)
        write_content('corporate', corporate)
        item = next((x for x in corporate if x.get('slug') == item['slug']), item)

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
            categories = [
                {'id':'dekoratif-duvar','label':'Dekoratif & Duvar'},
                {'id':'aydinlatma','label':'Aydınlatma'},
                {'id':'ev-duzen','label':'Ev & Düzen'},
                {'id':'gaming-masaustu','label':'Gaming & Masaüstü'},
                {'id':'anahtarlik-aksesuar','label':'Anahtarlık & Aksesuar'},
                {'id':'hediye-kisiye-ozel','label':'Hediye & Kişiye Özel'},
                {'id':'pratik-fonksiyonel','label':'Pratik & Fonksiyonel'},
                {'id':'pet-urunleri','label':'Pet Ürünleri'},
            ]
            return self.send_json({'products': read_products(), 'colors': read_colors(), 'categories': categories, 'tag_presets': TAG_PRESETS, 'root': str(ROOT), 'storage': storage_status()})
        if u.path == '/api/colors':
            return self.send_json({'colors': read_colors(), 'root': str(ROOT), 'storage': storage_status()})
        if u.path == '/api/status':
            return self.send_json({'ok': True, 'root': str(ROOT), 'version': PANEL_VERSION, 'storage': storage_status()})
        if u.path == '/api/backups':
            return self.send_json({'ok': True, 'backups': list_backups()})
        if u.path == '/api/preflight':
            return self.send_json(preflight())
        if u.path == '/api/content':
            from urllib.parse import parse_qs
            kind = (parse_qs(u.query).get('kind') or [''])[0]
            return self.send_json({'items': read_content(kind), 'sources': read_content('nfc') if kind == 'corporate' else [], 'kind': kind, 'root': str(ROOT), 'storage': storage_status()})
        if u.path.startswith('/assets/') or u.path in ('/favicon.ico', '/apple-touch-icon.png'):
            return self.send_file(ROOT / unquote(u.path.lstrip('/')), ROOT)
        path = 'index.html' if u.path in ('/', '') else unquote(u.path.lstrip('/'))
        return self.send_file(STATIC / path, STATIC)

    def do_POST(self):
        try:
            if self.path == '/api/colors/save':
                payload = self.read_json()
                full_backup('before-colors-save')
                colors = write_colors(payload.get('colors') or [])
                result = build_site()
                return self.send_json({'ok': True, 'message': 'Renk stoğu kaydedildi ve site güncellendi.', 'colors': colors, 'result': result})

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
                p['sort_order'] = max([int(x.get('sort_order') or 0) for x in products] + [0]) + 1
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
                    p['sort_order'] = i
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
                
                if not (kind == 'corporate' and item.get('source_kind') == 'nfc'):
                    remove_file(item.get('image'))
                remaining = resequence_content([x for x in items if x.get('slug') != slug])
                write_content(kind, remaining)
                if kind == 'nfc':
                    write_content('corporate', sync_nfc_to_corporate(remaining, read_content('corporate')))
                elif kind == 'corporate':
                    write_content('corporate', sync_nfc_to_corporate(read_content('nfc'), remaining))
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


def _shutdown_stale_panel_servers():
    """Close older BG Studio panel processes before binding the current one.

    A previously-open CMD can keep 127.0.0.1:8765 alive after repository files
    are updated. The browser then loads the new static UI from disk through the
    old Python process, producing a version/schema mismatch and an empty panel.
    Only endpoints that identify themselves as BG Studio product-manager status
    responses are touched.
    """
    stopped = []
    for port in range(8765, 8780):
        try:
            with urlopen(f'http://127.0.0.1:{port}/api/status', timeout=0.18) as response:
                payload = json.loads(response.read().decode('utf-8', errors='replace') or '{}')
            if not isinstance(payload, dict) or 'version' not in payload or 'root' not in payload:
                continue
            request = Request(
                f'http://127.0.0.1:{port}/api/shutdown',
                data=b'{}',
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            try:
                with urlopen(request, timeout=0.35) as response:
                    response.read()
                stopped.append((port, str(payload.get('version') or '?')))
            except Exception:
                pass
        except Exception:
            continue
    if stopped:
        print('Eski panel oturumu kapatıldı:', ', '.join(f'{p} / v{v}' for p, v in stopped))
        time.sleep(0.65)


def run():
    _shutdown_stale_panel_servers()
    # Always regenerate public pages from the persistent AppData collections
    # before opening the manager. This prevents a correct panel record set from
    # coexisting with a stale nfc-qr/index.html from an earlier build.
    try:
        ensure_initialized()
        export_to_repo()
        result = build_site()
        print(f"Site başlangıçta senkronlandı: {result.get('nfc_references', 0)} NFC, {result.get('corporate_references', 0)} kurumsal referans.")
    except Exception as exc:
        print('Başlangıç site senkronu uyarısı:', exc)
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
    st = storage_status()
    print('Repo :', ROOT)
    print('Veri :', st['database'])
    print('Medya:', st['media'])
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
