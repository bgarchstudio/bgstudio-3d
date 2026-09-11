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

PANEL_VERSION = '3.1.58'
BACKUPS = BACKUPS_ROOT

# Tek kaynak: panel dropdown'u, API ve kayıt doğrulaması aynı kategori listesini kullanır.
CATEGORY_OPTIONS = (
    ('dekoratif-duvar', 'Dekoratif & Duvar'),
    ('aydinlatma', 'Aydınlatma'),
    ('ev-duzen', 'Ev & Düzen'),
    ('gaming-masaustu', 'Gaming & Masaüstü'),
    ('anahtarlik-aksesuar', 'Anahtarlık & Aksesuar'),
    ('hediye-kisiye-ozel', 'Hediye & Kişiye Özel'),
    ('pratik-fonksiyonel', 'Pratik & Fonksiyonel'),
    ('pet-urunleri', 'Pet Ürünleri'),
    ('taki-makyaj', 'Takı & Makyaj'),
    ('oyun-oyuncak', 'Oyun & Oyuncak'),
)
PRODUCT_CATEGORIES = {category_id for category_id, _ in CATEGORY_OPTIONS}
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
    'Pet', 'Kedi', 'Köpek', 'Mama', 'Mama Küreği', 'Su Kabı', 'Oyuncak', 'Petshop',
    'Takı', 'Makyaj', 'Takı Standı', 'Kolye', 'Bileklik', 'Oyun', 'Oyuncak', 'Stres Oyuncağı'
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


NFC_MEDIA_FIXED_PATHS = {
    'feedback_duo': 'assets/images/nfc/products/feedback-duo.webp',
    'restaurant_packages': 'assets/images/nfc/products/restaurant-packages.webp',
    'quick_stand': 'assets/images/nfc/products/quick-stand.webp',
}

NFC_MEDIA_DEFAULTS = {
    'feedback_duo': {'image': '', 'theme': 'dark'},
    'restaurant_packages': {'image': '', 'theme': 'light'},
    'quick_stand': {'image': '', 'theme': 'light'},
}

NFC_FAMILY_THEME_DEFAULTS = {
    'feedback_duo': 'dark',
    'restaurant_packages': 'light',
    'quick_stand': 'light',
}


def read_nfc_family_themes(seed_media=None, persist=True):
    raw = get_collection('nfc_family_themes', {})
    raw = raw if isinstance(raw, dict) else {}
    seed_media = seed_media if isinstance(seed_media, dict) else {}
    out = {}
    for key, default in NFC_FAMILY_THEME_DEFAULTS.items():
        seed_row = seed_media.get(key) if isinstance(seed_media.get(key), dict) else {}
        value = str(raw.get(key) or seed_row.get('theme') or default).strip().lower()
        out[key] = 'dark' if value == 'dark' else 'light'
    if persist and raw != out:
        set_collection('nfc_family_themes', out)
        try:
            export_to_repo()
        except Exception:
            pass
    return out


def write_nfc_family_themes(value):
    incoming = value if isinstance(value, dict) else {}
    current = read_nfc_family_themes(persist=False)
    out = {}
    for key, default in NFC_FAMILY_THEME_DEFAULTS.items():
        raw = str(incoming.get(key) or current.get(key) or default).strip().lower()
        out[key] = 'dark' if raw == 'dark' else 'light'
    set_collection('nfc_family_themes', out)
    return out


def overlay_nfc_family_themes(settings, persist=True):
    settings = dict(settings) if isinstance(settings, dict) else {}
    media = settings.get('nfc_media') if isinstance(settings.get('nfc_media'), dict) else {}
    themes = read_nfc_family_themes(media, persist=persist)
    merged = {}
    for key, default_row in NFC_MEDIA_DEFAULTS.items():
        row = media.get(key) if isinstance(media.get(key), dict) else {}
        merged[key] = {
            'image': str(row.get('image') or ''),
            'theme': themes.get(key, default_row.get('theme', 'light')),
        }
    settings['nfc_media'] = merged
    return settings


def _repair_nfc_media_from_files(settings, persist=False):
    """Self-heal NFC showcase image pointers from their fixed repo files.

    V3.1.48: if an older storage schema or restart loses only the nfc_media
    pointer, the uploaded WebP itself remains authoritative and is reattached.
    """
    settings = dict(settings) if isinstance(settings, dict) else {}
    media_in = settings.get('nfc_media') if isinstance(settings.get('nfc_media'), dict) else {}
    media = {}
    changed = False
    for key, rel in NFC_MEDIA_FIXED_PATHS.items():
        row = media_in.get(key) if isinstance(media_in.get(key), dict) else {}
        raw = str(row.get('image') or '').replace('\\', '/').lstrip('/')
        file_exists = (ROOT / rel).is_file()
        if file_exists:
            image = rel
        else:
            image = ''
        if raw != image:
            changed = True
        default_theme = str((NFC_MEDIA_DEFAULTS.get(key) or {}).get('theme') or 'light').lower()
        theme = 'dark' if str(row.get('theme') or default_theme).strip().lower() == 'dark' else 'light'
        if str((row or {}).get('theme') or '').strip().lower() != theme:
            changed = True
        media[key] = {'image': image, 'theme': theme}
    if media_in != media:
        changed = True
    settings['nfc_media'] = media
    if persist and changed:
        set_collection('site_settings', settings)
        try:
            export_to_repo()
        except Exception:
            pass
    return settings


FEEDBACK_DUO_2026_PRICES = {
    10: (14900, 4900), 15: (19900, 6900), 20: (24900, 8900),
    25: (29900, 9900), 30: (34900, 10900), 35: (39900, 11900),
    40: (44900, 12900), 45: (49900, 13900), 50: (54900, 14900),
    55: (59900, 15900), 60: (64900, 16900), 65: (68900, 17900),
    70: (72900, 18900), 75: (76900, 19900), 80: (80900, 20900),
    85: (84900, 21900), 90: (88900, 22900), 95: (92900, 23900),
    100: (96900, 24900), 110: (104900, 26900), 120: (112900, 28900),
}
FEEDBACK_DUO_CAPACITIES = tuple(FEEDBACK_DUO_2026_PRICES.keys())
SPECIAL_RESTAURANT_2026_PRICES = {
    25: (29900, 9900), 30: (34900, 10900), 35: (39900, 11900),
    40: (44900, 12900), 45: (49900, 13900), 50: (54900, 14900),
    55: (59900, 15900), 60: (64900, 16900), 65: (68900, 17900),
    70: (72900, 18900), 75: (76900, 19900), 80: (80900, 20900),
    85: (84900, 21900), 90: (88900, 22900), 95: (92900, 23900),
    100: (96900, 24900), 110: (104900, 26900), 120: (112900, 28900),
}
SPECIAL_RESTAURANT_CAPACITIES = tuple(SPECIAL_RESTAURANT_2026_PRICES.keys())


def _feedback_duo_default_rows(year):
    rows = {}
    for stands in FEEDBACK_DUO_CAPACITIES:
        price, renewal = FEEDBACK_DUO_2026_PRICES[stands]
        rows[str(stands)] = {
            'stands': stands,
            'nfc': stands * 2,
            'price': price if str(year) == '2026' else None,
            'renewal': renewal if str(year) == '2026' else None,
        }
    return rows


def _special_restaurant_default_rows(year):
    rows = {}
    for tables in SPECIAL_RESTAURANT_CAPACITIES:
        price, renewal = SPECIAL_RESTAURANT_2026_PRICES[tables]
        rows[str(tables)] = {
            'tables': tables,
            'nfc': tables * 3,
            'price': price if str(year) == '2026' else None,
            'renewal': renewal if str(year) == '2026' else None,
        }
    return rows


def default_site_settings():
    return {
        'announcement_bar': {
            'enabled': True,
            'speed': 'normal',
            'direction': 'rtl',
            'separator': '✦',
            'messages': [
                {'id':'ucretsiz-kargo','text':'1.000 TL üzeri ücretsiz kargo','url':'','enabled':True,'source_type':'manual','source_ref':''},
                {'id':'kusadasi-teslim','text':'Kuşadası elden teslim','url':'','enabled':True,'source_type':'manual','source_ref':''},
                {'id':'kisiye-ozel','text':'Kişiye özel 3D üretim','url':'/ozel-uretim/','enabled':True,'source_type':'manual','source_ref':''},
                {'id':'kurumsal','text':'Kurumsal toplu sipariş','url':'/kurumsal/','enabled':True,'source_type':'manual','source_ref':''},
                {'id':'nfc-qr','text':'NFC + QR işletme çözümleri','url':'/nfc-qr/','enabled':True,'source_type':'manual','source_ref':''},
            ],
            'integration': {'discounts_enabled': False, 'mode': 'manual'},
        },
        'nfc_site': {
            'active_year': '2026',
            'years': {
                '2026': {
                    'qr_unit': 150,
                    'menu_design': 2500,
                    'logo_design': 2500,
                    'packages': {
                        'baslangic': {'price': 13900, 'list_price': 15900, 'renewal': 4900},
                        'profesyonel': {'price': 19900, 'list_price': 21900, 'renewal': 6900},
                        'premium': {'price': 25900, 'list_price': 28900, 'renewal': 8900},
                        'hizli_stand': {'price': 2000, 'list_price': None, 'renewal': 990},
                        # Compatibility mirror of the 10-stand Feedback Duo tier.
                        'feedback_duo': {'price': 14900, 'list_price': None, 'renewal': 4900},
                    },
                    'feedback_duo_packages': _feedback_duo_default_rows('2026'),
                    'special_restaurant_packages': _special_restaurant_default_rows('2026'),
                },
                '2027': {
                    'qr_unit': 200,
                    'menu_design': 3000,
                    'logo_design': 3000,
                    'packages': {
                        'baslangic': {'price': None, 'list_price': None, 'renewal': None},
                        'profesyonel': {'price': None, 'list_price': None, 'renewal': None},
                        'premium': {'price': None, 'list_price': None, 'renewal': None},
                        'hizli_stand': {'price': None, 'list_price': None, 'renewal': None},
                        'feedback_duo': {'price': None, 'list_price': None, 'renewal': None},
                    },
                    'feedback_duo_packages': _feedback_duo_default_rows('2027'),
                    'special_restaurant_packages': _special_restaurant_default_rows('2027'),
                },
            },
        },
        'website_copy': {
            'catalog_intro': 'Dekoratif tasarımlardan gaming ve masaüstü ürünlerine, pet çözümlerinden takı & makyaj, oyun & oyuncak, aksesuar ve kişiye özel üretimlere uzanan atölye seçkimiz. Fiyatı belirtilmeyen ürünlerde ölçü, adet ve üretim detayına göre teklif hazırlanır.'
        },
        'nfc_media': {
            'feedback_duo': {'image': '', 'theme': 'dark'},
            'restaurant_packages': {'image': '', 'theme': 'light'},
            'quick_stand': {'image': '', 'theme': 'light'},
        },
    }

def migrate_nfc_pricing_schema(settings, persist=False):
    """V3.1.54: seed full 25–120 ready restaurant pricing plus current NFC structures safely."""
    settings = dict(settings) if isinstance(settings, dict) else default_site_settings()
    nfc = settings.get('nfc_site') if isinstance(settings.get('nfc_site'), dict) else default_site_settings()['nfc_site']
    nfc = dict(nfc)
    years = nfc.get('years') if isinstance(nfc.get('years'), dict) else {}
    years = dict(years)
    changed = False
    defaults = default_site_settings()['nfc_site']['years']
    for year in ('2026','2027'):
        row = years.get(year) if isinstance(years.get(year), dict) else {}
        row = dict(row)
        packages = row.get('packages') if isinstance(row.get('packages'), dict) else {}
        packages = {k: dict(v) if isinstance(v, dict) else {} for k,v in packages.items()}
        dyear = defaults[year]
        # Newly published Hızlı Stand annual renewal has no legacy equivalent.
        if year == '2026':
            quick = packages.get('hizli_stand') if isinstance(packages.get('hizli_stand'), dict) else {}
            quick = dict(quick)
            if quick.get('price') is None:
                quick['price'] = 2000; changed = True
            if quick.get('renewal') is None:
                quick['renewal'] = 990; changed = True
            packages['hizli_stand'] = quick
            duo_legacy = packages.get('feedback_duo') if isinstance(packages.get('feedback_duo'), dict) else {}
            duo_legacy = dict(duo_legacy)
            if duo_legacy.get('price') is None:
                duo_legacy['price'] = 14900; changed = True
            if duo_legacy.get('renewal') is None:
                duo_legacy['renewal'] = 4900; changed = True
            packages['feedback_duo'] = duo_legacy
        row['packages'] = packages
        if not isinstance(row.get('feedback_duo_packages'), dict) or not row.get('feedback_duo_packages'):
            row['feedback_duo_packages'] = _feedback_duo_default_rows(year); changed = True
        special_existing = row.get('special_restaurant_packages') if isinstance(row.get('special_restaurant_packages'), dict) else {}
        special_existing = dict(special_existing)
        special_defaults = _special_restaurant_default_rows(year)
        for cap in SPECIAL_RESTAURANT_CAPACITIES:
            key = str(cap)
            if not isinstance(special_existing.get(key), dict):
                special_existing[key] = dict(special_defaults[key]); changed = True
            else:
                existing = dict(special_existing[key])
                expected_nfc = cap * 3
                if existing.get('tables') != cap:
                    existing['tables'] = cap; changed = True
                if existing.get('nfc') != expected_nfc:
                    existing['nfc'] = expected_nfc; changed = True
                special_existing[key] = existing
        row['special_restaurant_packages'] = special_existing
        years[year] = row
    nfc['years'] = years
    settings['nfc_site'] = nfc
    if persist and changed:
        set_collection('site_settings', settings)
        try:
            export_to_repo()
        except Exception:
            pass
    return settings


NFC_PRICING_COLLECTION = 'nfc_site_pricing'


def _pricing_signature(value):
    return json.dumps(value if isinstance(value, dict) else {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def read_nfc_site_pricing(seed=None, persist=True):
    """Read the authoritative NFC website pricing collection.

    V3.1.57: pricing no longer relies on the larger site_settings document as
    its only persistence source.  The dedicated collection is authoritative,
    while site_settings.nfc_site stays as the public/build compatibility mirror.
    """
    seed = seed if isinstance(seed, dict) else default_site_settings()['nfc_site']
    raw = get_collection(NFC_PRICING_COLLECTION, {})
    raw = raw if isinstance(raw, dict) else {}
    source = raw if isinstance(raw.get('years'), dict) else seed
    clean = clean_nfc_site_settings(source, seed)
    if persist and _pricing_signature(raw) != _pricing_signature(clean):
        set_collection(NFC_PRICING_COLLECTION, clean)
        try:
            export_to_repo()
        except Exception:
            pass
    return clean


def write_nfc_site_pricing(value, current=None):
    current = current if isinstance(current, dict) else default_site_settings()['nfc_site']
    clean = clean_nfc_site_settings(value, current)
    set_collection(NFC_PRICING_COLLECTION, clean)
    raw = get_collection(NFC_PRICING_COLLECTION, {})
    raw = raw if isinstance(raw, dict) else {}
    verified = clean_nfc_site_settings(raw, clean) if isinstance(raw.get('years'), dict) else {}
    if _pricing_signature(verified) != _pricing_signature(clean):
        raise RuntimeError('NFC fiyatları kalıcı fiyat kasasına yazılamadı.')
    return clean


def read_site_settings():
    data = get_collection('site_settings', default_site_settings())
    if not isinstance(data, dict):
        data = default_site_settings()
    # V3.1.54: seed Hızlı renewal, Feedback Duo ladder and all 25–120 ready restaurant packages.
    data = migrate_nfc_pricing_schema(data, persist=True)
    # V3.1.57: dedicated pricing collection is authoritative after restart/F5.
    pricing = read_nfc_site_pricing(data.get('nfc_site'), persist=True)
    if _pricing_signature(data.get('nfc_site')) != _pricing_signature(pricing):
        data = dict(data)
        data['nfc_site'] = pricing
        set_collection('site_settings', data)
        try:
            export_to_repo()
        except Exception:
            pass
    # V3.1.48: uploaded NFC showcase images survive old-schema/restart pointer loss.
    data = _repair_nfc_media_from_files(data, persist=True)
    # V3.1.52: tone is authoritative in a separate collection.
    return overlay_nfc_family_themes(data, persist=True)


def _safe_campaign_url(value):
    url = str(value or '').strip()[:500]
    if not url:
        return ''
    low = url.lower()
    if low.startswith(('javascript:', 'data:', 'vbscript:')):
        raise ValueError('Kampanya bağlantısı güvenli değil.')
    if url.startswith(('/', '#')) or low.startswith(('https://', 'http://')):
        return url
    # Plain site-relative paths such as urunler/... are accepted and normalized.
    if re.fullmatch(r'[A-Za-z0-9_./?=&%+#-]+', url):
        return '/' + url.lstrip('/')
    raise ValueError('Kampanya bağlantısı http(s) adresi veya site içi / ile başlayan yol olmalı.')


def _clean_money(value, *, allow_none=True, minimum=0, maximum=10000000):
    if value in (None, '', 'null'):
        return None if allow_none else minimum
    raw = str(value).strip().replace('TL', '').replace('₺', '').replace(' ', '')
    if '.' in raw and ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    elif ',' in raw:
        raw = raw.replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
        raw = raw.replace('.', '')
    try:
        n = float(raw)
    except Exception:
        raise ValueError(f'Geçersiz fiyat değeri: {value}')
    if n < minimum or n > maximum:
        raise ValueError(f'Fiyat {minimum} ile {maximum} arasında olmalı.')
    return int(round(n))


def clean_nfc_site_settings(value, current=None):
    defaults = default_site_settings()['nfc_site']
    current = current if isinstance(current, dict) else defaults
    incoming = value if isinstance(value, dict) else {}
    active_year = str(incoming.get('active_year') or current.get('active_year') or '2026')
    if active_year not in ('2026', '2027'):
        active_year = '2026'
    out = {'active_year': active_year, 'years': {}}
    incoming_years = incoming.get('years') if isinstance(incoming.get('years'), dict) else {}
    current_years = current.get('years') if isinstance(current.get('years'), dict) else {}
    package_keys = ('baslangic', 'profesyonel', 'premium', 'hizli_stand', 'feedback_duo')

    for year in ('2026', '2027'):
        dyear = defaults['years'][year]
        cyear = current_years.get(year) if isinstance(current_years.get(year), dict) else dyear
        iyear = incoming_years.get(year) if isinstance(incoming_years.get(year), dict) else {}
        qr_unit = _clean_money(iyear.get('qr_unit', cyear.get('qr_unit', dyear['qr_unit'])), allow_none=False, minimum=0)
        menu_design = _clean_money(iyear.get('menu_design', cyear.get('menu_design', dyear['menu_design'])), allow_none=False, minimum=0)
        logo_design = _clean_money(iyear.get('logo_design', cyear.get('logo_design', dyear['logo_design'])), allow_none=False, minimum=0)

        ipack = iyear.get('packages') if isinstance(iyear.get('packages'), dict) else {}
        cpack = cyear.get('packages') if isinstance(cyear.get('packages'), dict) else {}
        packages = {}
        for key in package_keys:
            dp = dyear['packages'].get(key, {})
            cp = cpack.get(key) if isinstance(cpack.get(key), dict) else dp
            pp = ipack.get(key) if isinstance(ipack.get(key), dict) else {}
            packages[key] = {
                'price': _clean_money(pp.get('price', cp.get('price', dp.get('price'))), allow_none=True),
                'list_price': _clean_money(pp.get('list_price', cp.get('list_price', dp.get('list_price'))), allow_none=True),
                'renewal': _clean_money(pp.get('renewal', cp.get('renewal', dp.get('renewal'))), allow_none=True),
            }

        # Premium Feedback Duo capacity ladder.
        iduo = iyear.get('feedback_duo_packages') if isinstance(iyear.get('feedback_duo_packages'), dict) else {}
        cduo = cyear.get('feedback_duo_packages') if isinstance(cyear.get('feedback_duo_packages'), dict) else {}
        dduo = dyear.get('feedback_duo_packages') if isinstance(dyear.get('feedback_duo_packages'), dict) else _feedback_duo_default_rows(year)
        duo_rows = {}
        for stands in FEEDBACK_DUO_CAPACITIES:
            key = str(stands)
            dp = dduo.get(key) if isinstance(dduo.get(key), dict) else {'stands': stands, 'nfc': stands * 2, 'price': None, 'renewal': None}
            cp = cduo.get(key) if isinstance(cduo.get(key), dict) else dp
            pp = iduo.get(key) if isinstance(iduo.get(key), dict) else {}
            duo_rows[key] = {
                'stands': stands,
                'nfc': stands * 2,
                'price': _clean_money(pp.get('price', cp.get('price', dp.get('price'))), allow_none=True),
                'renewal': _clean_money(pp.get('renewal', cp.get('renewal', dp.get('renewal'))), allow_none=True),
            }

        # High-capacity ready restaurant packages. Currently 120 tables has a published ready price.
        ispecial = iyear.get('special_restaurant_packages') if isinstance(iyear.get('special_restaurant_packages'), dict) else {}
        cspecial = cyear.get('special_restaurant_packages') if isinstance(cyear.get('special_restaurant_packages'), dict) else {}
        dspecial = dyear.get('special_restaurant_packages') if isinstance(dyear.get('special_restaurant_packages'), dict) else _special_restaurant_default_rows(year)
        special_rows = {}
        for tables in SPECIAL_RESTAURANT_CAPACITIES:
            key = str(tables)
            dp = dspecial.get(key) if isinstance(dspecial.get(key), dict) else {'tables': tables, 'nfc': tables * 3, 'price': None, 'renewal': None}
            cp = cspecial.get(key) if isinstance(cspecial.get(key), dict) else dp
            pp = ispecial.get(key) if isinstance(ispecial.get(key), dict) else {}
            special_rows[key] = {
                'tables': tables,
                'nfc': tables * 3,
                'price': _clean_money(pp.get('price', cp.get('price', dp.get('price'))), allow_none=True),
                'renewal': _clean_money(pp.get('renewal', cp.get('renewal', dp.get('renewal'))), allow_none=True),
            }

        # Keep legacy/quote summary fields in sync with the first Feedback Duo tier.
        first_duo = duo_rows.get('10') or {}
        if first_duo.get('price') is not None:
            packages['feedback_duo']['price'] = first_duo.get('price')
        if first_duo.get('renewal') is not None:
            packages['feedback_duo']['renewal'] = first_duo.get('renewal')

        out['years'][year] = {
            'qr_unit': qr_unit,
            'menu_design': menu_design,
            'logo_design': logo_design,
            'packages': packages,
            'feedback_duo_packages': duo_rows,
            'special_restaurant_packages': special_rows,
        }

    # Do not allow a future year to become public with incomplete core pricing.
    ay = out['years'][active_year]
    required = [ay['qr_unit'], ay['menu_design'], ay['logo_design']]
    for key in ('baslangic', 'profesyonel', 'premium'):
        required.extend([ay['packages'][key]['price'], ay['packages'][key]['renewal']])
    required.extend([ay['packages']['hizli_stand']['price'], ay['packages']['hizli_stand']['renewal']])
    if any(v is None for v in required):
        raise ValueError(f'{active_year} aktif fiyat yılı yapılamaz; restoran paketleri, yenilemeler, Hızlı Stand fiyat/yenileme, QR, menü ve logo fiyatlarını doldur.')
    return out

def clean_website_copy(value, current=None):
    defaults = default_site_settings()['website_copy']
    current = current if isinstance(current, dict) else defaults
    incoming = value if isinstance(value, dict) else {}
    intro = re.sub(r'\s+', ' ', str(incoming.get('catalog_intro', current.get('catalog_intro', defaults['catalog_intro'])) or '')).strip()
    if not intro:
        intro = defaults['catalog_intro']
    return {'catalog_intro': intro[:520]}


def clean_nfc_media_settings(value, current=None):
    defaults = default_site_settings()['nfc_media']
    current = current if isinstance(current, dict) else defaults
    incoming = value if isinstance(value, dict) else {}
    fixed_paths = NFC_MEDIA_FIXED_PATHS
    out = {}
    for key, fixed in fixed_paths.items():
        current_row = current.get(key) if isinstance(current.get(key), dict) else {}
        incoming_row = incoming.get(key) if isinstance(incoming.get(key), dict) else current_row
        image = str(incoming_row.get('image') or '').replace('\\', '/').lstrip('/')
        theme_default = str((defaults.get(key) or {}).get('theme') or 'light').lower()
        theme = 'dark' if str(incoming_row.get('theme') or current_row.get('theme') or theme_default).strip().lower() == 'dark' else 'light'
        # NFC showcase images always live at fixed, repo-safe paths.
        out[key] = {'image': fixed if image == fixed else '', 'theme': theme}
    return out


def clean_site_settings(value):
    payload = value if isinstance(value, dict) else {}
    current = read_site_settings()
    current_bar = current.get('announcement_bar') if isinstance(current.get('announcement_bar'), dict) else {}
    incoming = payload.get('announcement_bar') if isinstance(payload.get('announcement_bar'), dict) else current_bar
    speed = str(incoming.get('speed') or current_bar.get('speed') or 'normal').strip().lower()
    if speed not in ('slow', 'normal', 'fast'):
        speed = 'normal'
    direction = str(incoming.get('direction') or current_bar.get('direction') or 'rtl').strip().lower()
    if direction not in ('rtl', 'ltr'):
        direction = 'rtl'
    rows = incoming.get('messages') if isinstance(incoming.get('messages'), list) else []
    messages = []
    used = set()
    for index, row in enumerate(rows[:30], 1):
        if not isinstance(row, dict):
            continue
        text = re.sub(r'\s+', ' ', str(row.get('text') or '')).strip()[:180]
        if not text:
            continue
        raw_id = slugify(row.get('id') or text) or f'mesaj-{index}'
        item_id = raw_id
        suffix = 2
        while item_id in used:
            item_id = f'{raw_id}-{suffix}'; suffix += 1
        used.add(item_id)
        source_type = str(row.get('source_type') or 'manual').strip().lower()
        if source_type not in ('manual', 'discount', 'campaign'):
            source_type = 'manual'
        messages.append({
            'id': item_id,
            'text': text,
            'url': _safe_campaign_url(row.get('url')),
            'enabled': bool(row.get('enabled', True)),
            'source_type': source_type,
            'source_ref': str(row.get('source_ref') or '').strip()[:120],
        })
    current_nfc = current.get('nfc_site') if isinstance(current.get('nfc_site'), dict) else default_site_settings()['nfc_site']
    current_copy = current.get('website_copy') if isinstance(current.get('website_copy'), dict) else default_site_settings()['website_copy']
    incoming_nfc = payload.get('nfc_site') if isinstance(payload.get('nfc_site'), dict) else current_nfc
    incoming_copy = payload.get('website_copy') if isinstance(payload.get('website_copy'), dict) else current_copy
    current_media = current.get('nfc_media') if isinstance(current.get('nfc_media'), dict) else default_site_settings()['nfc_media']
    incoming_media = payload.get('nfc_media') if isinstance(payload.get('nfc_media'), dict) else current_media
    settings = {
        'announcement_bar': {
            'enabled': bool(incoming.get('enabled', True)),
            'speed': speed,
            'direction': direction,
            'separator': '✦',
            'messages': messages,
            # Reserved bridge: future discount rules can inject generated messages
            # without changing the manual message schema.
            'integration': {
                'discounts_enabled': bool((incoming.get('integration') or {}).get('discounts_enabled', False)) if isinstance(incoming.get('integration'), dict) else False,
                'mode': str((incoming.get('integration') or {}).get('mode') or 'manual')[:40] if isinstance(incoming.get('integration'), dict) else 'manual',
            },
        },
        'nfc_site': clean_nfc_site_settings(incoming_nfc, current_nfc),
        'website_copy': clean_website_copy(incoming_copy, current_copy),
        'nfc_media': clean_nfc_media_settings(incoming_media, current_media),
    }
    # No active message means nothing can be displayed; keep data but hide the bar.
    if not any(x.get('enabled', True) and x.get('text') for x in messages):
        settings['announcement_bar']['enabled'] = False
    return settings


def write_site_settings(value):
    clean = clean_site_settings(value)
    # V3.1.57: write pricing to its own persistent collection first, then mirror it.
    clean['nfc_site'] = write_nfc_site_pricing(clean.get('nfc_site'), clean.get('nfc_site'))
    set_collection('site_settings', clean)
    media = clean.get('nfc_media') if isinstance(clean.get('nfc_media'), dict) else {}
    write_nfc_family_themes({key: (media.get(key) or {}).get('theme') for key in NFC_FAMILY_THEME_DEFAULTS})
    try:
        export_to_repo()
    except Exception:
        pass
    # Never report a successful write before the persistent store can read it back.
    stored = get_collection('site_settings', {})
    stored = stored if isinstance(stored, dict) else {}
    stored_pricing = read_nfc_site_pricing(clean.get('nfc_site'), persist=False)
    if _pricing_signature(stored_pricing) != _pricing_signature(clean.get('nfc_site')):
        raise RuntimeError('NFC fiyat kaydı doğrulanamadı; eski fiyatlara dönmemesi için işlem durduruldu.')
    if _pricing_signature((stored or {}).get('nfc_site')) != _pricing_signature(clean.get('nfc_site')):
        repaired = dict(stored) if stored else dict(clean)
        repaired['nfc_site'] = clean['nfc_site']
        set_collection('site_settings', repaired)
        try:
            export_to_repo()
        except Exception:
            pass
    return overlay_nfc_family_themes(clean, persist=False)



def _public_nfc_family_theme(key):
    path = ROOT / 'nfc-qr/index.html'
    if not path.is_file():
        return None
    html_text = path.read_text(encoding='utf-8')
    pattern = rf'<article[^>]*data-family-key="{re.escape(str(key))}"[^>]*>'
    found = re.search(pattern, html_text, flags=re.I | re.S)
    if not found:
        return None
    tag = found.group(0)
    theme = re.search(r'data-family-theme="(light|dark)"', tag, flags=re.I)
    return theme.group(1).lower() if theme else None


def save_nfc_family_theme(key, theme):
    key = str(key or '').strip()
    if key not in NFC_MEDIA_FIXED_PATHS:
        raise ValueError('Geçersiz NFC ürün ailesi.')
    theme = 'dark' if str(theme or '').strip().lower() == 'dark' else 'light'

    # 1) Save into a dedicated tone store first.
    themes = read_nfc_family_themes(persist=False)
    themes[key] = theme
    write_nfc_family_themes(themes)
    persisted_theme = read_nfc_family_themes(persist=False).get(key)
    if persisted_theme != theme:
        raise RuntimeError(f'Kart tonu kalıcı kayda yazılamadı ({persisted_theme or "boş"}).')

    # 2) Mirror into site_settings for backward compatibility.
    current = read_site_settings()
    settings = dict(current)
    current_media = current.get('nfc_media') if isinstance(current.get('nfc_media'), dict) else {}
    media = {k: dict(current_media.get(k) or {}) for k in NFC_MEDIA_FIXED_PATHS}
    row = media.get(key) or {}
    rel = NFC_MEDIA_FIXED_PATHS[key]
    image = rel if (ROOT / rel).is_file() else str(row.get('image') or '')
    media[key] = {'image': image, 'theme': theme}
    settings['nfc_media'] = media
    set_collection('site_settings', settings)
    export_to_repo()

    # 3) Force this build to use the just-saved tone; future rebuilds read the
    # same value from nfc_family_themes.
    result = build_site(nfc_family_theme_overrides={key: theme})
    verified = _public_nfc_family_theme(key)
    if verified != theme:
        raise RuntimeError(f'Kart tonu kaydedildi ancak site çıktısı {verified or "bulunamadı"} olarak üretildi.')

    repaired = read_site_settings()
    if ((repaired.get('nfc_media') or {}).get(key) or {}).get('theme') != theme:
        raise RuntimeError('Kart tonu build sonrası kalıcı ayarda doğrulanamadı.')
    return repaired, {**(result or {}), 'verified_theme': verified, 'verified_family': key}


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
    try:
        settings = read_site_settings()
        bar = settings.get('announcement_bar') if isinstance(settings, dict) else {}
        messages = [x for x in (bar.get('messages') or []) if isinstance(x, dict) and x.get('enabled', True) and str(x.get('text') or '').strip()] if isinstance(bar, dict) else []
        if bar.get('enabled'):
            checks.append({'status':'pass' if messages else 'fail','label':'Kampanya şeridi','detail':f'Şerit açık · {len(messages)} aktif mesaj · hız: {bar.get("speed") or "normal"} · yön: {bar.get("direction") or "rtl"}.' if messages else 'Şerit açık ama aktif mesaj yok.'})
        else:
            checks.append({'status':'pass','label':'Kampanya şeridi','detail':f'Şerit kapalı · {len(messages)} mesaj kayıtlı.'})
    except Exception as e:
        checks.append({'status':'warn','label':'Kampanya şeridi','detail':str(e)})

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




def normalize_price_input(value):
    """Normalize Turkish/English TL input to canonical decimal text."""
    raw = str(value or '').strip().upper().replace('TL', '').replace('₺', '')
    raw = re.sub(r'\s+', '', raw)
    if not raw or not re.fullmatch(r'[0-9.,]+', raw):
        return None
    if '.' in raw and ',' in raw:
        if raw.rfind(',') > raw.rfind('.'):
            raw = raw.replace('.', '').replace(',', '.')
        else:
            raw = raw.replace(',', '')
    elif '.' in raw:
        if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
            raw = raw.replace('.', '')
    elif ',' in raw:
        if re.fullmatch(r'\d{1,3}(?:,\d{3})+', raw):
            raw = raw.replace(',', '')
        else:
            raw = raw.replace(',', '.')
    if not re.fullmatch(r'\d+(?:\.\d+)?', raw):
        return None
    try:
        n = float(raw)
    except Exception:
        return None
    if not (n > 0):
        return None
    if n.is_integer():
        return str(int(n))
    return ('%.2f' % n).rstrip('0').rstrip('.')

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
        raw_price = normalize_price_input(item.get('price_value'))
        if qty < 1 or raw_price is None:
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
    raw_base = str(out.get('price_value') or '').strip()
    out['price_value'] = normalize_price_input(raw_base) if raw_base else None
    if raw_base and out['price_value'] is None:
        raise ValueError('Normal sayısal fiyat geçersiz.')
    raw_sale = str(out.get('sale_price_value') or '').strip()
    sale_raw = normalize_price_input(raw_sale) if raw_sale else None
    if raw_sale:
        if sale_raw is None:
            raise ValueError('İndirimli fiyat geçersiz.')
        if out['price_value'] is None:
            raise ValueError('İndirim için normal sayısal fiyat zorunlu.')
        if float(sale_raw) >= float(out['price_value']):
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
        row.update({
            'slug': slug,
            'source_kind': 'nfc',
            'source_slug': slug,
            # Corporate visibility belongs to the NFC source record. This keeps
            # the NFC page independent while the corporate mirror can be hidden.
            'show_in_corporate': bool(src.get('show_in_corporate', True)),
            # Linked mirror publication follows the NFC source itself. Corporate-only
            # hiding is handled by show_in_corporate, so homepage proof is unaffected.
            'active': bool(src.get('active', True)),
        })
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
        'tags': [str(x).strip() for x in (item.get('tags') or []) if str(x).strip()][:16],
        'active': bool(item.get('active', True)),
        'sort_order': int(item.get('sort_order') or 999),
    }
    if kind in ('prototype','nfc'): out['category'] = str(item.get('category') or ('Prototip / özel parça' if kind == 'prototype' else 'NFC / QR saha uygulaması')).strip()
    if kind == 'nfc':
        # Independent toggle: NFC stays published while its corporate mirror may be hidden.
        out['show_in_corporate'] = bool(item.get('show_in_corporate', True))
    if kind in ('nfc','corporate','prototype'):
        out['theme'] = 'dark' if str(item.get('theme') or '').lower() == 'dark' else 'light'
    if item.get('image'): out['image'] = str(item.get('image'))
    if kind in ('nfc','corporate') and item.get('profile_image'):
        out['profile_image'] = str(item.get('profile_image'))
    return out


def _public_theme_state(kind, slug):
    page_rel = {
        'nfc': 'nfc-qr/index.html',
        'corporate': 'kurumsal/index.html',
        'prototype': 'prototip-parca/index.html',
    }[kind]
    page = ROOT / page_rel
    text = page.read_text(encoding='utf-8') if page.exists() else ''
    ref = re.escape(slugify(slug))
    match = re.search(rf'<article\b[^>]*\bid="referans-{ref}"[^>]*>', text, flags=re.I)
    if not match:
        raise RuntimeError(f'{kind}: referans kartı build çıktısında bulunamadı.')
    tag = match.group(0)
    found = re.search(r'data-card-theme="(light|dark)"', tag, flags=re.I)
    return (found.group(1).lower() if found else '')


def _public_reference_present(kind, slug):
    page_rel = {
        'nfc': 'nfc-qr/index.html',
        'corporate': 'kurumsal/index.html',
        'prototype': 'prototip-parca/index.html',
    }[kind]
    page = ROOT / page_rel
    text = page.read_text(encoding='utf-8') if page.exists() else ''
    ref = re.escape(slugify(slug))
    return bool(re.search(rf'<article\b[^>]*\bid="referans-{ref}"[^>]*>', text, flags=re.I))


def save_nfc_corporate_visibility(slug, visible):
    """Toggle only the Corporate-page mirror of one NFC record."""
    slug = str(slug or '').strip()
    visible = bool(visible)
    nfc_items = read_content('nfc')
    row = next((x for x in nfc_items if str(x.get('slug') or '') == slug), None)
    if not row:
        raise ValueError('Kurumsal görünürlüğü değiştirilecek NFC kaydı bulunamadı.')
    row['show_in_corporate'] = visible
    write_content('nfc', nfc_items)
    write_content('corporate', sync_nfc_to_corporate(nfc_items, read_content('corporate')))
    result = build_site()
    expected_present = bool(row.get('active', True)) and visible
    public_present = _public_reference_present('corporate', slug)
    if public_present != expected_present:
        raise RuntimeError('Kurumsal görünürlük kaydedildi ancak sayfa çıktısı doğrulanamadı.')
    return row, {**result, 'corporate_visible': visible, 'corporate_card_present': public_present}


def save_all_nfc_corporate_visibility(visible):
    """Bulk show/hide every NFC-backed Corporate mirror without touching NFC publication."""
    visible = bool(visible)
    nfc_items = read_content('nfc')
    for row in nfc_items:
        row['show_in_corporate'] = visible
    write_content('nfc', nfc_items)
    write_content('corporate', sync_nfc_to_corporate(nfc_items, read_content('corporate')))
    result = build_site()
    expected = sum(1 for row in nfc_items if row.get('active', True) and visible)
    actual = sum(1 for row in nfc_items if _public_reference_present('corporate', row.get('slug'))) if visible else 0
    if visible and actual != expected:
        raise RuntimeError(f'NFC aynaları topluca açıldı ancak {expected} karttan {actual} tanesi doğrulandı.')
    if not visible and any(_public_reference_present('corporate', row.get('slug')) for row in nfc_items):
        raise RuntimeError('NFC aynaları topluca gizlendi ancak Kurumsal sayfada en az bir NFC kartı kaldı.')
    return nfc_items, {**result, 'corporate_visible': visible, 'affected': len(nfc_items)}


def save_content_theme(kind, slug, theme):
    """Persist a card tone and prove the exact public card received it."""
    kind = content_collection(kind)
    slug = str(slug or '').strip()
    theme = 'dark' if str(theme or '').strip().lower() == 'dark' else 'light'
    items = read_content(kind)
    row = next((x for x in items if str(x.get('slug') or '') == slug), None)
    if not row:
        raise ValueError('Kart tonu kaydedilecek referans bulunamadı.')
    row['theme'] = theme
    write_content(kind, items)

    if kind == 'nfc':
        # NFC public card keeps its own tone. Corporate linked cards keep their
        # independent corporate tone instead of overwriting the NFC choice.
        write_content('corporate', sync_nfc_to_corporate(items, read_content('corporate')))
    elif kind == 'corporate':
        write_content('corporate', sync_nfc_to_corporate(read_content('nfc'), items))

    result = build_site()
    persisted = next((x for x in read_content(kind) if str(x.get('slug') or '') == slug), None) or {}
    if str(persisted.get('theme') or '').lower() != theme:
        raise RuntimeError('Kart tonu kalıcı veriye yazılamadı.')
    public_theme = _public_theme_state(kind, slug)
    if public_theme != theme:
        raise RuntimeError(f'Kart tonu kaydedildi ancak canlı sayfa çıktısı {public_theme or "bulunamadı"} olarak üretildi.')
    return persisted, {**result, 'verified_theme': public_theme, 'verified_kind': kind, 'verified_slug': slug}

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
            categories = [{'id': category_id, 'label': label} for category_id, label in CATEGORY_OPTIONS]
            return self.send_json({'products': read_products(), 'colors': read_colors(), 'categories': categories, 'tag_presets': TAG_PRESETS, 'root': str(ROOT), 'storage': storage_status()})
        if u.path == '/api/colors':
            return self.send_json({'colors': read_colors(), 'root': str(ROOT), 'storage': storage_status()})
        if u.path == '/api/status':
            return self.send_json({'ok': True, 'root': str(ROOT), 'version': PANEL_VERSION, 'storage': storage_status()})
        if u.path == '/api/site-settings':
            return self.send_json({'ok': True, 'settings': read_site_settings(), 'root': str(ROOT), 'storage': storage_status()})
        if u.path == '/api/nfc-site-settings':
            settings = read_site_settings()
            return self.send_json({'ok': True, 'nfc_site': settings.get('nfc_site') or default_site_settings()['nfc_site'], 'website_copy': settings.get('website_copy') or default_site_settings()['website_copy'], 'nfc_media': settings.get('nfc_media') or default_site_settings()['nfc_media'], 'root': str(ROOT), 'storage': storage_status()})
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
            if self.path == '/api/site-settings/save':
                payload = self.read_json()
                full_backup('before-site-settings-save')
                settings = write_site_settings(payload.get('settings') or {})
                result = build_site()
                return self.send_json({'ok': True, 'message': 'Kampanya şeridi ayarları kaydedildi ve site güncellendi.', 'settings': settings, 'result': result})


            if self.path == '/api/nfc-family-theme/save':
                payload = self.read_json()
                full_backup('before-nfc-family-theme-save')
                settings, result = save_nfc_family_theme(payload.get('key'), payload.get('theme'))
                key = str(payload.get('key') or '')
                labels = {
                    'feedback_duo': 'Premium Feedback Duo',
                    'restaurant_packages': 'Standart Restoran Paketleri',
                    'quick_stand': 'Hızlı Bağlantı Standı',
                }
                tone = 'Koyu' if result.get('verified_theme') == 'dark' else 'Açık'
                return self.send_json({'ok': True, 'message': f'{labels.get(key, key)} · {tone} kart tonu kaydedildi ve build doğrulandı.', 'nfc_media': settings.get('nfc_media'), 'result': result})

            if self.path == '/api/nfc-site-settings/save':
                payload = self.read_json()
                full_backup('before-nfc-site-settings-save')
                current = read_site_settings()
                merged = dict(current)
                merged['nfc_site'] = payload.get('nfc_site') if isinstance(payload.get('nfc_site'), dict) else current.get('nfc_site')
                merged['website_copy'] = payload.get('website_copy') if isinstance(payload.get('website_copy'), dict) else current.get('website_copy')

                fixed_media = NFC_MEDIA_FIXED_PATHS
                current_media = current.get('nfc_media') if isinstance(current.get('nfc_media'), dict) else default_site_settings()['nfc_media']
                incoming_media = payload.get('nfc_media') if isinstance(payload.get('nfc_media'), dict) else {}
                media = {}
                uploads = payload.get('media_uploads') if isinstance(payload.get('media_uploads'), dict) else {}
                clears = set(payload.get('media_clear') or []) if isinstance(payload.get('media_clear'), list) else set()
                for key, rel in fixed_media.items():
                    current_row = current_media.get(key) if isinstance(current_media.get(key), dict) else {}
                    incoming_row = incoming_media.get(key) if isinstance(incoming_media.get(key), dict) else {}
                    default_theme = str((NFC_MEDIA_DEFAULTS.get(key) or {}).get('theme') or 'light').lower()
                    theme = 'dark' if str(incoming_row.get('theme') or current_row.get('theme') or default_theme).strip().lower() == 'dark' else 'light'
                    image_value = str(current_row.get('image') or '').replace('\\', '/').lstrip('/')
                    if key in clears:
                        remove_file(rel)
                        image_value = ''
                    image = uploads.get(key)
                    if isinstance(image, dict) and image.get('data'):
                        save_data_uri(image.get('data'), ROOT / rel)
                        image_value = rel
                    media[key] = {'image': image_value, 'theme': theme}
                merged['nfc_media'] = media

                settings = write_site_settings(merged)
                # V3.1.48: re-read actual fixed files and persist pointers before reporting success.
                settings = _repair_nfc_media_from_files(settings, persist=True)
                for key in uploads:
                    if key not in fixed_media:
                        continue
                    rel = fixed_media[key]
                    if not (ROOT / rel).is_file() or (settings.get('nfc_media') or {}).get(key, {}).get('image') != rel:
                        raise ValueError(f'{key} vitrin görseli diske kaydedilemedi; işlem başarılı sayılmadı.')
                expected_pricing = settings.get('nfc_site')
                result = build_site()
                # V3.1.57: build sonrası kalıcı kasayı yeniden oku. Eski fiyat geri geldiyse başarı dönme.
                verified = read_site_settings()
                if _pricing_signature(verified.get('nfc_site')) != _pricing_signature(expected_pricing):
                    repair = dict(verified)
                    repair['nfc_site'] = expected_pricing
                    repair['website_copy'] = settings.get('website_copy')
                    repair['nfc_media'] = settings.get('nfc_media')
                    write_site_settings(repair)
                    result = build_site()
                    verified = read_site_settings()
                if _pricing_signature(verified.get('nfc_site')) != _pricing_signature(expected_pricing):
                    raise RuntimeError('Fiyatlar build sonrasında kalıcı olarak doğrulanamadı; işlem başarılı sayılmadı.')
                return self.send_json({'ok': True, 'message': 'NFC website fiyatları kalıcı kasada doğrulandı ve site yeniden hazırlandı.', 'nfc_site': verified.get('nfc_site'), 'website_copy': verified.get('website_copy'), 'nfc_media': verified.get('nfc_media'), 'result': result, 'persistence_verified': True})

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

            if self.path == '/api/content/corporate-visibility/save':
                payload = self.read_json()
                slug = str(payload.get('slug') or '')
                visible = bool(payload.get('visible', True))
                full_backup('before-corporate-visibility-save')
                item, result = save_nfc_corporate_visibility(slug, visible)
                label = 'gösteriliyor' if visible else 'gizlendi'
                return self.send_json({'ok': True, 'message': f'NFC kaydı Kurumsal sayfada {label}.', 'item': item, 'result': result})

            if self.path == '/api/content/corporate-visibility/bulk':
                payload = self.read_json()
                visible = bool(payload.get('visible', True))
                full_backup('before-corporate-visibility-bulk')
                items, result = save_all_nfc_corporate_visibility(visible)
                label = 'gösteriliyor' if visible else 'gizlendi'
                return self.send_json({'ok': True, 'message': f'Tüm NFC aynaları Kurumsal sayfada {label}.', 'items': items, 'result': result})

            if self.path == '/api/content/theme/save':
                payload = self.read_json()
                kind = payload.get('kind')
                slug = str(payload.get('slug') or '')
                theme = str(payload.get('theme') or '')
                full_backup('before-content-theme-save')
                item, result = save_content_theme(kind, slug, theme)
                return self.send_json({'ok': True, 'message': f'Kart tonu {item.get("theme")} olarak kaydedildi ve build doğrulandı.', 'item': item, 'result': result})

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
