from pathlib import Path
import json, re, html, sys
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data' / 'products.json'
NFC_DATA = ROOT / 'data' / 'nfc_references.json'
PROTOTYPE_DATA = ROOT / 'data' / 'prototypes.json'
CORPORATE_DATA = ROOT / 'data' / 'corporate_references.json'
COLORS_DATA = ROOT / 'data' / 'colors.json'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage import ensure_initialized, get_collection, set_collection, export_to_repo
ensure_initialized()
BASE_URL = 'https://3d.bgstudio.com.tr'
CATEGORY_LABELS = {
    'dekoratif-duvar': 'Dekoratif & Duvar',
    'aydinlatma': 'Aydınlatma',
    'ev-duzen': 'Ev & Düzen',
    'gaming-masaustu': 'Gaming & Masaüstü',
    'anahtarlik-aksesuar': 'Anahtarlık & Aksesuar',
    'hediye-kisiye-ozel': 'Hediye & Kişiye Özel',
    'pratik-fonksiyonel': 'Pratik & Fonksiyonel',
    'pet-urunleri': 'Pet Ürünleri',
    'taki-makyaj': 'Takı & Makyaj',
    'oyun-oyuncak': 'Oyun & Oyuncak',
    # Legacy values are kept readable for old backups.
    'dekoratif': 'Dekoratif & Duvar',
    'fonksiyonel': 'Pratik & Fonksiyonel',
    'kisiye-ozel': 'Hediye & Kişiye Özel',
    'pet': 'Pet Ürünleri',
}
CATEGORY_ORDER = [
    'dekoratif-duvar', 'aydinlatma', 'ev-duzen', 'gaming-masaustu',
    'anahtarlik-aksesuar', 'hediye-kisiye-ozel', 'pratik-fonksiyonel',
    'pet-urunleri', 'taki-makyaj', 'oyun-oyuncak'
]
FAQ = [
    ('Renk seçebilir miyim?', 'Mevcut filament seçenekleri ürüne göre değişir. Sipariş öncesinde uygun renkleri WhatsApp üzerinden birlikte netleştiriyoruz.'),
    ('Üretim ve teslim süresi ne kadar?', 'Süre; ürün, adet ve atölye yoğunluğuna göre değişebilir. Güncel üretim ve teslim bilgisini sipariş öncesinde paylaşıyoruz.'),
    ('3D baskı katman izleri normal mi?', 'Evet. Katman dokusu 3D baskı üretim yönteminin doğal karakteridir. Ürünler doğrudan baskı kalitesini koruyacak şekilde hazırlanır.'),
]


def esc(v):
    return html.escape(str(v or ''), quote=True)

def parse_price_number(value):
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
    try:
        return float(raw)
    except Exception:
        return None

def canonical_price_value(value):
    n = parse_price_number(value)
    if n is None or n <= 0:
        return None
    if n.is_integer():
        return str(int(n))
    return ('%.2f' % n).rstrip('0').rstrip('.')

def format_try(value):
    n = parse_price_number(value)
    if n is None:
        return ''
    if n.is_integer():
        text = f"{int(n):,}".replace(',', '.')
    else:
        text = f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        text = text.rstrip('0').rstrip(',')
    return text + ' TL'



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


def default_nfc_site_settings():
    return {
        'active_year': '2026',
        'years': {
            '2026': {
                'qr_unit': 150, 'menu_design': 2500, 'logo_design': 2500,
                'packages': {
                    'baslangic': {'price': 13900, 'list_price': 15900, 'renewal': 4900},
                    'profesyonel': {'price': 19900, 'list_price': 21900, 'renewal': 6900},
                    'premium': {'price': 25900, 'list_price': 28900, 'renewal': 8900},
                    'hizli_stand': {'price': 2000, 'list_price': None, 'renewal': 990},
                    'feedback_duo': {'price': 14900, 'list_price': None, 'renewal': 4900},
                },
                'feedback_duo_packages': _feedback_duo_default_rows('2026'),
                'special_restaurant_packages': _special_restaurant_default_rows('2026'),
            },
            '2027': {
                'qr_unit': 200, 'menu_design': 3000, 'logo_design': 3000,
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
    }

def default_website_copy():
    return {
        'catalog_intro': 'Dekoratif tasarımlardan gaming ve masaüstü ürünlerine, pet çözümlerinden takı & makyaj, oyun & oyuncak, aksesuar ve kişiye özel üretimlere uzanan atölye seçkimiz. Fiyatı belirtilmeyen ürünlerde ölçü, adet ve üretim detayına göre teklif hazırlanır.'
    }


NFC_PRICING_COLLECTION = 'nfc_site_pricing'


def load_site_settings():
    data = get_collection('site_settings', {})
    data = dict(data) if isinstance(data, dict) else {}
    # V3.1.57: build always prefers the dedicated persistent pricing source.
    pricing = get_collection(NFC_PRICING_COLLECTION, {})
    if isinstance(pricing, dict) and isinstance(pricing.get('years'), dict):
        data['nfc_site'] = pricing
    return data


def active_nfc_pricing():
    settings = load_site_settings()
    nfc = settings.get('nfc_site') if isinstance(settings.get('nfc_site'), dict) else default_nfc_site_settings()
    defaults = default_nfc_site_settings()
    year = str(nfc.get('active_year') or defaults['active_year'])
    if year not in ('2026', '2027'):
        year = '2026'
    years = nfc.get('years') if isinstance(nfc.get('years'), dict) else {}
    incoming = years.get(year) if isinstance(years.get(year), dict) else {}
    base = defaults['years'][year]

    packages_in = incoming.get('packages') if isinstance(incoming.get('packages'), dict) else {}
    packages = {}
    for key, base_pack in base['packages'].items():
        row = packages_in.get(key) if isinstance(packages_in.get(key), dict) else {}
        def pick(field):
            value = row.get(field) if field in row else base_pack.get(field)
            if value is None and base_pack.get(field) is not None:
                return base_pack.get(field)
            return value
        packages[key] = {
            'price': pick('price'),
            'list_price': pick('list_price'),
            'renewal': pick('renewal'),
        }

    def merge_capacity_rows(field, default_rows, multiplier, count_name):
        incoming_rows = incoming.get(field) if isinstance(incoming.get(field), dict) else {}
        rows = {}
        for key, base_row in default_rows.items():
            source = incoming_rows.get(key) if isinstance(incoming_rows.get(key), dict) else {}
            count = int(base_row.get(count_name) or key)
            rows[str(key)] = {
                count_name: count,
                'nfc': count * multiplier,
                'price': source.get('price', base_row.get('price')),
                'renewal': source.get('renewal', base_row.get('renewal')),
            }
        return rows

    duo_rows = merge_capacity_rows('feedback_duo_packages', base.get('feedback_duo_packages') or _feedback_duo_default_rows(year), 2, 'stands')
    special_rows = merge_capacity_rows('special_restaurant_packages', base.get('special_restaurant_packages') or _special_restaurant_default_rows(year), 3, 'tables')
    first_duo = duo_rows.get('10') or {}
    if first_duo.get('price') is not None:
        packages['feedback_duo']['price'] = first_duo.get('price')
    if first_duo.get('renewal') is not None:
        packages['feedback_duo']['renewal'] = first_duo.get('renewal')

    return {
        'year': year,
        'qr_unit': incoming.get('qr_unit', base['qr_unit']),
        'menu_design': incoming.get('menu_design', base['menu_design']),
        'logo_design': incoming.get('logo_design', base['logo_design']),
        'packages': packages,
        'feedback_duo_packages': duo_rows,
        'special_restaurant_packages': special_rows,
    }

def website_copy_settings():
    settings = load_site_settings()
    copy = settings.get('website_copy') if isinstance(settings.get('website_copy'), dict) else {}
    default = default_website_copy()
    intro = re.sub(r'\s+', ' ', str(copy.get('catalog_intro') or default['catalog_intro'])).strip()
    return {'catalog_intro': intro[:520]}


def default_nfc_media_settings():
    return {
        'feedback_duo': {'image': '', 'theme': 'dark'},
        'restaurant_packages': {'image': '', 'theme': 'light'},
        'quick_stand': {'image': '', 'theme': 'light'},
        'premium_plus': {'image': '', 'theme': 'dark'},
    }


def default_nfc_family_themes():
    return {
        'feedback_duo': 'dark',
        'restaurant_packages': 'light',
        'quick_stand': 'light',
        'premium_plus': 'dark',
    }


def nfc_family_theme_settings():
    # V3.1.52: tone is stored independently from media self-heal.
    defaults = default_nfc_family_themes()
    raw = get_collection('nfc_family_themes', {})
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for key, default in defaults.items():
        value = str(raw.get(key) or default).strip().lower()
        out[key] = 'dark' if value == 'dark' else 'light'
    return out


def nfc_media_settings():
    settings = load_site_settings()
    incoming = settings.get('nfc_media') if isinstance(settings.get('nfc_media'), dict) else {}
    fixed_paths = {
        'feedback_duo': 'assets/images/nfc/products/feedback-duo.webp',
        'restaurant_packages': 'assets/images/nfc/products/restaurant-packages.webp',
        'quick_stand': 'assets/images/nfc/products/quick-stand.webp',
    }
    out = {}
    for key, default_row in default_nfc_media_settings().items():
        row = incoming.get(key) if isinstance(incoming.get(key), dict) else {}
        image = ''
        fixed = fixed_paths.get(key)
        if fixed:
            raw = str(row.get('image') or '').replace('\\', '/').lstrip('/')
            if (ROOT / fixed).is_file():
                image = fixed
            elif raw and (ROOT / raw).is_file():
                image = raw
        default_theme = str(default_row.get('theme') or 'light').lower()
        theme = 'dark' if str(row.get('theme') or default_theme).strip().lower() == 'dark' else 'light'
        out[key] = {'image': image, 'theme': theme}
    return out


def render_nfc_family_media(key, label, alt):
    media = nfc_media_settings().get(key) or {}
    image = str(media.get('image') or '')
    if image:
        aria = esc(f'{alt} görselini büyüt')
        return f'<div class="nfc-family-media has-image zoomable-media" role="button" tabindex="0" aria-label="{aria}"><img src="../{esc(image)}" alt="{esc(alt)}" loading="lazy" decoding="async"></div>'
    return f'<div class="nfc-family-media"><span>{esc(label)}</span></div>'


def clip_seo_text(text, max_len=160):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(text) <= max_len:
        return text
    clipped = text[:max_len + 1]
    if ' ' in clipped:
        clipped = clipped.rsplit(' ', 1)[0]
    clipped = re.sub(r'[,:;.!?\-–—]+$', '', clipped).rstrip()
    return clipped + '.'


def make_seo(p):
    name = str(p.get('name') or '').strip()
    source = str(p.get('card_description') or p.get('description') or '').strip()
    if source and name:
        source = re.sub(r'^' + re.escape(name) + r'\s*[-—–:,.]*\s*', '', source, flags=re.I)
        source = re.sub(r'\s+', ' ', source).strip()
        source = re.sub(r'[.!?]+$', '', source).strip()
    title = f"{name} | Kuşadası 3D Baskı | BG Studio 3D" if name else ''
    suffix = '3D baskı ile üretilir. Kuşadası elden teslim ve Türkiye geneli kargo.'
    description = f"{name}, {source}. {suffix}" if source else f"{name}, {suffix}"
    return title, clip_seo_text(description, 160)


def load_products():
    data = get_collection('products', [])
    if not isinstance(data, list):
        data = []
    return sorted(data, key=lambda p: (int(p.get('sort_order') or 9999), p.get('name', '').casefold()))


def load_colors():
    data = get_collection('colors', [])
    if not isinstance(data, list):
        return []
    return sorted(data, key=lambda c: (int(c.get('sort_order') or 9999), str(c.get('name') or '').casefold()))


def load_materials():
    data = get_collection('materials', [])
    if not isinstance(data, list) or not data:
        data = [
            {'id':'pla','name':'PLA','sort_order':10},
            {'id':'pla-plus','name':'PLA+','sort_order':20},
            {'id':'pla-hd','name':'PLA HD','sort_order':30},
            {'id':'petg','name':'PETG','sort_order':40},
            {'id':'tpu','name':'TPU','sort_order':50},
            {'id':'asa','name':'ASA','sort_order':60},
            {'id':'abs','name':'ABS','sort_order':70},
        ]
    return sorted(data, key=lambda m: (int(m.get('sort_order') or 9999), str(m.get('name') or '').casefold()))


def color_is_available(color):
    qty = color.get('stock_qty')
    return bool(color.get('in_stock', True)) and (qty is None or int(qty or 0) > 0)


def product_color_entries(p):
    colors = load_colors()
    by_id = {str(c.get('id')): c for c in colors}
    explicit = [str(x) for x in (p.get('color_ids') or []) if str(x) in by_id]
    if explicit:
        return [by_id[cid] for cid in explicit if color_is_available(by_id[cid])]
    # Legacy compatibility: old products stored colors in `options` as plain names.
    names = {str(c.get('name') or '').strip().casefold(): c for c in colors}
    found = []
    for option in (p.get('options') or []):
        c = names.get(str(option).strip().casefold())
        if c and color_is_available(c) and c not in found:
            found.append(c)
    return found


def legacy_order_options(p):
    options = [str(x).strip() for x in (p.get('options') or []) if str(x).strip()]
    colors = load_colors()
    color_names = {str(c.get('name') or '').strip().casefold() for c in colors}
    if p.get('color_ids'):
        return options
    # When legacy options are recognized as palette colors, do not duplicate them as a generic select.
    return [x for x in options if x.casefold() not in color_names]


def ensure_explicit_reference_themes():
    """Persist one explicit light/dark value for every managed reference.

    Older NFC/prototype records could rely on odd/even fallback styling. Preserve
    that current appearance once, then remove all runtime alternation so the
    panel selection is the only source of truth for every public reference page.
    """
    changed = {}
    for kind in ('nfc', 'corporate', 'prototype'):
        rows = get_collection(kind, [])
        if not isinstance(rows, list):
            continue
        next_rows = []
        dirty = False
        for idx, raw in enumerate(rows, 1):
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            theme = str(row.get('theme') or '').strip().lower()
            if theme not in ('light', 'dark'):
                if kind in ('nfc', 'prototype'):
                    try:
                        order = int(row.get('sort_order') or idx)
                    except Exception:
                        order = idx
                    theme = 'dark' if order % 2 == 1 else 'light'
                else:
                    theme = 'light'
                row['theme'] = theme
                dirty = True
            next_rows.append(row)
        if dirty:
            set_collection(kind, next_rows)
            changed[kind] = True
    return changed


def load_managed_content(path):
    mapping = {
        NFC_DATA: 'nfc',
        PROTOTYPE_DATA: 'prototype',
        CORPORATE_DATA: 'corporate',
    }
    data = get_collection(mapping.get(path, ''), []) if path in mapping else []
    if not isinstance(data, list):
        return []
    return sorted(data, key=lambda x: (int(x.get('sort_order') or 9999), str(x.get('name') or '').casefold()))


def resolve_nfc_items():
    """Canonical NFC list used by the public NFC & QR page.

    Storage repair runs before this, so the manager list and generated page
    always read the same persistent collection.
    """
    return [x for x in load_managed_content(NFC_DATA) if x.get('active', True)]


def case_media(item, prefix, name):
    image = item.get('image')
    if not image:
        return '', ''
    src = prefix + str(image)
    return f'<div class="case-media"><img alt="{name}" decoding="async" loading="lazy" src="{esc(src)}"/></div>', ' has-media'


def case_profile(item, prefix, name, label='Profil fotoğrafı'):
    profile = str(item.get('profile_image') or '').strip()
    src = prefix + profile if profile else prefix + 'assets/brand/bgstudio3d-monogram.png'
    fallback = ' is-fallback' if not profile else ''
    alt = f'{name} {label}' if name else label
    return f'<span class="case-profile{fallback}"><img alt="{esc(alt)}" decoding="async" loading="lazy" src="{esc(src)}"/></span>'

def case_anchor(item, slug_override=None):
    """Stable deep-link id for a managed reference card."""
    raw = str(slug_override or item.get('slug') or item.get('source_slug') or item.get('name') or 'referans').strip().lower()
    raw = raw.replace('_', '-')
    safe = re.sub(r'[^a-z0-9-]+', '-', raw).strip('-')
    safe = re.sub(r'-{2,}', '-', safe) or 'referans'
    return 'referans-' + safe


def reference_identity(item, slug_override=None):
    """Canonical identity shared by homepage links and every destination card.

    NFC-backed corporate cards prefer source_slug so copies of the same business
    resolve to the same stable identity across pages.
    """
    raw = str(slug_override or item.get('source_slug') or item.get('slug') or item.get('name') or 'referans').strip().lower()
    raw = raw.replace('_', '-')
    safe = re.sub(r'[^a-z0-9-]+', '-', raw).strip('-')
    return re.sub(r'-{2,}', '-', safe) or 'referans'


def reference_attrs(item, slug_override=None):
    ref_id = reference_identity(item, slug_override)
    name = str(item.get('name') or '').strip()
    return f'data-reference-id="{esc(ref_id)}" data-reference-name="{esc(name)}"'


def home_case_link(item):
    """Point homepage “İşi incele” links to the exact managed card, not page top."""
    link = str(item.get('home_link') or ('nfc-qr/' if item.get('source_kind') == 'nfc' else 'kurumsal/')).strip()
    if link.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        return link
    # Remove stale hashes from older data. The canonical reference identity below
    # is authoritative and is rebuilt every time the site is generated.
    link = link.split('#', 1)[0]
    normalized = link.lstrip('/')
    target_slug = item.get('source_slug') if normalized.startswith('nfc-qr') and item.get('source_kind') == 'nfc' else item.get('slug')
    target_id = reference_identity(item, target_slug)
    return link.rstrip('/') + '/#referans-' + target_id


def managed_case_theme(item, legacy_alternate=False):
    """Return one explicit card theme for every managed reference.

    New saves always persist light/dark. Legacy rows without a stored value keep
    the old alternating appearance until the user makes a choice.
    """
    raw = str(item.get('theme') or '').strip().lower()
    if raw in ('dark', 'light'):
        return raw
    if legacy_alternate and int(item.get('sort_order') or 0) % 2 == 1:
        return 'dark'
    return 'light'


def managed_case_is_dark(item, legacy_alternate=False):
    return managed_case_theme(item, legacy_alternate=legacy_alternate) == 'dark'


def managed_case_class(theme, media_class=''):
    theme = 'dark' if str(theme).lower() == 'dark' else 'light'
    dark = ' dark' if theme == 'dark' else ''
    return f'case-card{dark} theme-{theme}{media_class}'


def render_managed_case(item, prefix='../'):
    """Prototype/default managed card with per-card light/dark tone."""
    name = esc(item.get('name'))
    headline = esc(item.get('headline') or item.get('name'))
    desc = esc(item.get('description'))
    tags = ''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or []))
    kicker = esc(item.get('category') or item.get('name'))
    media, media_class = case_media(item, prefix, name)
    theme = managed_case_theme(item, legacy_alternate=False)
    klass = managed_case_class(theme, media_class)
    project_link = f'<a class="case-project-link" href="{esc(project_public_url(item, prefix))}">Proje detayını gör ↗</a>'
    body = f'<div class="case-body"><span class="case-type">{kicker}</span><h3>{headline}</h3><p>{desc}</p><div class="case-meta">{tags}</div>{project_link}</div>'
    return f'<article class="{klass}" id="referans-{reference_identity(item)}" data-reference-key="referans-{reference_identity(item)}" {reference_attrs(item)} data-card-theme="{theme}">{media}{body}</article>'

def render_nfc_case(item, prefix='../'):
    """NFC field card: business identity is primary and tone is managed per card."""
    name = esc(item.get('name'))
    raw_name = str(item.get('name') or '')
    desc = esc(item.get('description') or item.get('headline'))
    tags = ''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or []))
    kicker = esc(item.get('category') or 'NFC / QR saha uygulaması')
    media, media_class = case_media(item, prefix, name)
    profile = case_profile(item, prefix, raw_name, 'profil fotoğrafı')
    theme = managed_case_theme(item, legacy_alternate=False)
    klass = managed_case_class(theme, media_class)
    identity = f'<div class="case-identity">{profile}<span class="case-type">{kicker}</span></div>'
    project_link = f'<a class="case-project-link" href="{esc(project_public_url(item, prefix))}">Proje detayını gör ↗</a>'
    body = f'<div class="case-body">{identity}<h3>{name}</h3><p>{desc}</p><div class="case-meta">{tags}</div>{project_link}</div>'
    return f'<article class="{klass}" id="referans-{reference_identity(item)}" data-reference-key="referans-{reference_identity(item)}" {reference_attrs(item)} data-card-theme="{theme}">{media}{body}</article>'

def resolve_corporate_items():
    nfc_items = load_managed_content(NFC_DATA)
    nfc = {str(x.get('slug')): x for x in nfc_items}
    resolved = []
    seen_nfc = set()
    for raw in load_managed_content(CORPORATE_DATA):
        item = dict(raw)
        if item.get('source_kind') == 'nfc' and item.get('source_slug'):
            source_slug = str(item.get('source_slug'))
            src = nfc.get(source_slug)
            if not src:
                continue
            seen_nfc.add(source_slug)
            item = {**src, **{k:v for k,v in raw.items() if k in ('slug','source_kind','source_slug','theme','sort_order','home_link')}}
            item['active'] = bool(src.get('active', True))
        resolved.append(item)

    # Safety net: an NFC record can never disappear from Corporate even if an
    # older database is missing its linked corporate row.
    for idx, src in enumerate(nfc_items, 1):
        slug = str(src.get('slug') or '')
        if not slug or slug in seen_nfc:
            continue
        resolved.append({
            **src,
            'slug': slug,
            'source_kind': 'nfc',
            'source_slug': slug,
            'theme': 'dark' if idx % 2 else 'light',
            'active': bool(src.get('active', True)),
            'sort_order': idx,
        })

    return sorted(resolved, key=lambda x:(int(x.get('sort_order') or 9999), str(x.get('name') or '').casefold()))

def ensure_corporate_markers(text):
    if '<!-- CONTENT_MANAGER:CORPORATE_START -->' in text and '<!-- CONTENT_MANAGER:CORPORATE_END -->' in text:
        return text
    pattern = re.compile(r'<div class="case-grid">.*?</div></div></section>', re.S)
    replacement = '<div class="case-grid"><!-- CONTENT_MANAGER:CORPORATE_START -->\n<!-- CONTENT_MANAGER:CORPORATE_END --></div></div></section>'
    if not pattern.search(text):
        raise RuntimeError('Kurumsal referans alanı bulunamadı.')
    return pattern.sub(replacement, text, count=1)


def render_corporate_case(item, prefix='../'):
    name = esc(item.get('name'))
    raw_name = str(item.get('name') or '')
    headline = esc(item.get('headline') or item.get('name'))
    desc = esc(item.get('description'))
    tags = ''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or []))
    media, media_class = case_media(item, prefix, name)
    profile = case_profile(item, prefix, raw_name, 'profil fotoğrafı')
    theme = managed_case_theme(item, legacy_alternate=False)
    klass = managed_case_class(theme, media_class)
    # Corporate layout deliberately uses business name as kicker and project headline as title.
    identity = f'<div class="case-identity">{profile}<span class="case-type">{name}</span></div>'
    project_link = f'<a class="case-project-link" href="{esc(project_public_url(item, prefix))}">Proje detayını gör ↗</a>'
    body = f'<div class="case-body">{identity}<h3>{headline}</h3><p>{desc}</p><div class="case-meta">{tags}</div>{project_link}</div>'
    return f'<article class="{klass}" id="referans-{reference_identity(item)}" data-reference-key="referans-{reference_identity(item)}" {reference_attrs(item)} data-card-theme="{theme}">{media}{body}</article>'


def render_home_field_case(item, index, prefix=''):
    name = esc(item.get('name'))
    raw_name = str(item.get('name') or '')
    headline = esc(item.get('headline') or item.get('name'))
    desc = esc(item.get('description'))
    tags = ''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or [])[:3])
    profile = case_profile(item, prefix, raw_name, 'profil görseli')
    card_theme = managed_case_theme(item, legacy_alternate=False)
    theme = ' dark theme-dark' if card_theme == 'dark' else ' theme-light'
    category = esc(item.get('category') or ('NFC / QR saha uygulaması' if item.get('source_kind') == 'nfc' else 'Kurumsal üretim'))
    link = project_public_url(item, '')
    target_key = link.split('#', 1)[1] if '#' in link else 'referans-' + reference_identity(item)
    ref_id = reference_identity(item, item.get('source_slug') if item.get('source_kind') == 'nfc' else item.get('slug'))
    return f'<article class="field-work-card{theme}" data-card-theme="{card_theme}" data-reference-target="{esc(target_key)}" data-reference-id="{esc(ref_id)}" data-reference-name="{esc(raw_name)}"><div class="field-work-top">{profile}<div><span class="field-work-no">{index:02d}</span><span class="field-work-type">{category}</span></div></div><h3>{headline}</h3><p>{desc}</p><div class="field-work-meta">{tags}</div><a class="field-work-link" href="{esc(link)}">İşi incele ↗</a></article>'


SITE_CONTENT_V3175_COLLECTION = 'site_content_v3175'

SITE_CONTENT_V3175_DEFAULTS = {
    'home': {
        'hero_eyebrow': 'BG STUDIO 3D',
        'hero_title': 'Fikirden fiziksel ürüne.',
        'hero_lead': '3D baskı ürünleri, özel üretim, prototip ve işletmelere özel fiziksel + dijital sistemler.',
        'hero_primary_label': 'Ürünleri İncele', 'hero_primary_url': 'urunler/',
        'hero_secondary_label': 'Özel Üretim', 'hero_secondary_url': 'ozel-uretim/',
        'hero_product_slugs': [],
        'showcase_product_slugs': [],
        'production_product_slug': '',
        'production_eyebrow': 'ÖZEL ÜRETİM', 'production_title': 'Aklındaki parçayı üretelim.',
        'production_lead': 'Fotoğraf, eskiz, ölçü veya fikirle başlayabiliriz. Tasarımı üretilebilir hale getirip baskı sürecine taşıyoruz.',
        'production_cta_label': 'Teklif Al ↗', 'production_cta_url': 'teklif/?tur=ozel-uretim',
        'why_eyebrow': 'NEDEN BG STUDIO', 'why_title': 'Tasarım ile|üretim aynı|masada.',
        'final_eyebrow': 'BİR FİKRİN Mİ VAR?', 'final_title': 'Birlikte üretelim.',
        'final_lead': 'Ürün, prototip, işletme çözümü veya özel üretim talebini gönder. Uygun üretim yolunu birlikte netleştirelim.',
        'final_primary_label': 'Teklif Al ↗', 'final_primary_url': 'teklif/',
    },
    'corporate': {
        'hero_eyebrow': 'KURUMSAL ÜRETİM',
        'hero_title': 'İşletmenin ihtiyacına göre tasarla, üret, teslim et.',
        'hero_lead': 'Tek bir sektöre bağlı kalmadan; işletmeye özel fiziksel ürün, promosyon, masaüstü çözüm ve saha uygulamalarını tasarımdan üretime tek süreçte yürütüyoruz.',
        'primary_label': 'Kurumsal teklif al ↗', 'primary_url': '../teklif/?tur=kurumsal',
        'secondary_label': 'Projeleri incele ↗', 'secondary_url': '../projeler/',
    },
    'prototype': {
        'hero_eyebrow': 'PROTOTİP + PARÇA ÜRETİM',
        'hero_title': 'Sorundan çalışan parçaya.',
        'hero_lead': 'Kırılan, bulunamayan veya geliştirilmesi gereken parçaları ölçü, model ve üretim gereksinimine göre ele alıyoruz. Dekoratif üründen farklı olarak burada odak; uyum, işlev ve tekrar üretilebilirlik.',
        'primary_label': 'Parçan için teklif al ↗', 'primary_url': '../teklif/?tur=prototip',
        'secondary_label': 'Teknik projeleri incele ↗', 'secondary_url': '../projeler/',
    },
    'about': {
        'hero_eyebrow': 'BG STUDIO 3D', 'hero_title': 'Fikirden fiziksel ürüne.',
        'hero_lead': 'BG Studio 3D; ürün, özel üretim, prototip, kurumsal işler ve işletmelere yönelik NFC + QR sistemlerini aynı tasarım ve üretim yaklaşımında buluşturan Kuşadası merkezli bir stüdyodur.',
        'primary_label': 'Ürünleri gör ↗', 'primary_url': '../urunler/',
        'secondary_label': 'Birlikte üretelim ↗', 'secondary_url': '../teklif/',
    },
    'contact': {
        'hero_eyebrow': 'İLETİŞİM', 'hero_title': 'Ne üretmek istediğini anlat.',
        'hero_lead': 'Ürün siparişi, özel üretim, kurumsal çalışma, prototip veya NFC + QR sistemi için en uygun kanaldan bize ulaş.',
    },
}


def _site_content_safe_url(value, fallback=''):
    value = str(value or '').strip()
    if not value:
        return fallback
    low = value.casefold()
    if low.startswith(('javascript:', 'data:', 'vbscript:')):
        return fallback
    if re.match(r'^(?:https?://|/|\.\.?/|[a-z0-9][a-z0-9._~!$&\'()*+,;=:@%/-]*(?:\?[a-z0-9._~!$&\'()*+,;=:@%/?-]*)?(?:#[^\s]*)?)$', value, flags=re.I):
        return value
    return fallback


def clean_site_content_v3175(value):
    raw = value if isinstance(value, dict) else {}
    out = {}
    url_keys = {key for section in SITE_CONTENT_V3175_DEFAULTS.values() for key in section if key.endswith('_url')}
    for section, defaults in SITE_CONTENT_V3175_DEFAULTS.items():
        supplied = raw.get(section) if isinstance(raw.get(section), dict) else {}
        row = {}
        for key, default in defaults.items():
            if key in ('hero_product_slugs', 'showcase_product_slugs'):
                items = supplied.get(key, default)
                if not isinstance(items, list): items = []
                slot_count = 3 if key == 'hero_product_slugs' else 6
                cleaned = []
                for item in items[:slot_count]:
                    token = str(item or '').strip().casefold()
                    if key == 'showcase_product_slugs' and token == '__hide__':
                        cleaned.append('__hide__')
                    else:
                        cleaned.append(re.sub(r'[^a-z0-9-]', '', token)[:100])
                cleaned.extend([''] * max(0, slot_count - len(cleaned)))
                row[key] = cleaned[:slot_count]
                continue
            if key == 'production_product_slug':
                token = str(supplied.get(key, default) or '').strip().casefold()
                row[key] = re.sub(r'[^a-z0-9-]', '', token)[:100]
                continue
            text = str(supplied.get(key, default) or '').strip()
            if not text:
                text = str(default)
            if key in url_keys:
                text = _site_content_safe_url(text, str(default))
            limit = 900 if key.endswith('_lead') else 220
            row[key] = text[:limit]
        out[section] = row
    return out


def read_site_content_v3175():
    return clean_site_content_v3175(get_collection(SITE_CONTENT_V3175_COLLECTION, {}))


def write_site_content_v3175(value):
    clean = clean_site_content_v3175(value)
    set_collection(SITE_CONTENT_V3175_COLLECTION, clean)
    export_to_repo()
    return clean


def _site_text(section, key):
    return read_site_content_v3175().get(section, {}).get(key, SITE_CONTENT_V3175_DEFAULTS.get(section, {}).get(key, ''))


def _site_why_title_html(value):
    parts = [part.strip() for part in re.split(r'[|\n]+', str(value or '')) if part.strip()][:3]
    if not parts: parts = ['Tasarım ile', 'üretim aynı', 'masada.']
    return ''.join(f'<span>{esc(part)}</span>' for part in parts)


def _homepage_product_pool(active, featured):
    """Deterministic fallback pool. Manual placements are handled separately."""
    picked = []
    seen = set()
    for product in list(featured or []) + list(active or []):
        slug = str(product.get('slug') or '').strip()
        if not slug or slug in seen:
            continue
        seen.add(slug)
        picked.append(product)
    return picked


def _homepage_slot_products(active, featured, configured, slot_count, allow_hide=False):
    """Resolve exact panel slots while keeping an automatic fallback for empty slots."""
    by_slug = {str(product.get('slug') or '').strip(): product for product in (active or [])}
    pool = _homepage_product_pool(active, featured)
    tokens = list(configured or [])[:slot_count]
    tokens.extend([''] * max(0, slot_count - len(tokens)))
    resolved = []
    used = set()

    def next_auto():
        for product in pool:
            slug = str(product.get('slug') or '').strip()
            if slug and slug not in used:
                used.add(slug)
                return product
        return None

    for token in tokens[:slot_count]:
        token = str(token or '').strip()
        if allow_hide and token == '__hide__':
            resolved.append(None)
            continue
        product = by_slug.get(token) if token else None
        if product:
            slug = str(product.get('slug') or '').strip()
            if slug in used:
                product = next_auto()
            else:
                used.add(slug)
        else:
            product = next_auto()
        resolved.append(product)
    return resolved


def _homepage_single_product(active, featured, configured_slug='', fallback_index=0):
    by_slug = {str(product.get('slug') or '').strip(): product for product in (active or [])}
    configured_slug = str(configured_slug or '').strip()
    if configured_slug in by_slug:
        return by_slug[configured_slug]
    pool = _homepage_product_pool(active, featured)
    if not pool:
        return None
    return pool[min(max(int(fallback_index or 0), 0), len(pool)-1)]


def _picture_sources_for_product(product, prefix=''):
    # Use AVIF/WebP only when the matching optimized file really exists.
    raw = str(product.get('main_image') or '').strip()
    if not raw:
        return {'fallback': '', 'avif': '', 'webp': ''}
    rel = Path(raw)
    absolute = ROOT / rel
    candidates = {'fallback': prefix + raw, 'avif': '', 'webp': ''}
    for suffix, key in (('.avif', 'avif'), ('.webp', 'webp')):
        candidate = absolute.with_suffix(suffix)
        if candidate.exists():
            candidates[key] = prefix + candidate.relative_to(ROOT).as_posix()
    return candidates


def render_home_product_picture(product, prefix='', eager=False, css_class=''):
    name = esc(product.get('name') or 'BG Studio 3D ürünü')
    sources = _picture_sources_for_product(product, prefix)
    fallback = sources.get('fallback') or prefix + 'assets/brand/bgstudio3d-monogram.png'
    width = int(product.get('main_image_width') or 1000)
    height = int(product.get('main_image_height') or 760)
    source_html = ''
    if sources.get('avif'):
        source_html += f'<source srcset="{esc(sources["avif"])}" type="image/avif"/>'
    if sources.get('webp') and sources.get('webp') != fallback:
        source_html += f'<source srcset="{esc(sources["webp"])}" type="image/webp"/>'
    loading = 'eager' if eager else 'lazy'
    priority = ' fetchpriority="high"' if eager else ''
    klass = f' class="{esc(css_class)}"' if css_class else ''
    return f'<picture{klass}>{source_html}<img alt="{name}" decoding="async" height="{height}" loading="{loading}" src="{esc(fallback)}" width="{width}"{priority}/></picture>'


def render_home_showcase_product(product, index=0):
    name = esc(product.get('name') or '')
    href = esc('urunler/' + str(product.get('slug') or '').strip('/') + '/')
    label = esc(category_label(product))
    price_html = card_price_html(product)
    picture = render_home_product_picture(product, '', eager=False, css_class='home-showcase-picture')
    lead_class = ' is-lead' if index == 0 else ''
    return (
        f'<article class="home-showcase-card home-motion{lead_class}" data-home-motion>'
        f'<a class="home-showcase-media" href="{href}">{picture}</a>'
        f'<div class="home-showcase-body"><div class="home-showcase-top"><span>{label}</span>{price_html}</div>'
        f'<h3><a href="{href}">{name}</a></h3>'
        f'<a class="home-showcase-link" href="{href}">Ürünü incele ↗</a></div></article>'
    )


def render_home_project_feature(item, index, prefix=''):
    raw_name = str(item.get('name') or '').strip()
    name = esc(raw_name)
    headline = esc(item.get('headline') or raw_name)
    desc = esc(item.get('description') or '')
    category = esc(item.get('category') or ('NFC / QR saha uygulaması' if item.get('source_kind') == 'nfc' else 'Kurumsal üretim'))
    tags = ''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or [])[:3])
    link = esc(project_public_url(item, ''))
    media_path = str(item.get('image') or item.get('profile_image') or '').strip()
    if media_path:
        media = f'<div class="home-project-media"><img alt="{name}" decoding="async" loading="lazy" src="{esc(prefix + media_path)}"/></div>'
    else:
        media = f'<div class="home-project-media home-project-media-fallback"><span>{index:02d}</span><strong>{name or "BG Studio"}</strong></div>'
    ref_id = reference_identity(item, item.get('source_slug') if item.get('source_kind') == 'nfc' else item.get('slug'))
    return (
        f'<article class="home-project-card home-motion" data-home-motion data-reference-id="{esc(ref_id)}" data-reference-name="{name}">'
        f'{media}<div class="home-project-body"><div class="home-project-kicker"><span>{index:02d}</span><small>{category}</small></div>'
        f'<h3>{headline}</h3><p>{desc}</p><div class="home-project-tags">{tags}</div>'
        f'<a class="home-project-link" href="{link}">Projeyi incele ↗</a></div></article>'
    )


def _home_visual_product(product, position='main', eager=False):
    if not product:
        return f'<div class="home-hero-visual-fallback home-hero-visual-{esc(position)}"><span>BG</span><small>STUDIO 3D</small></div>'
    picture = render_home_product_picture(product, '', eager=eager, css_class='home-hero-picture')
    name = esc(product.get('name') or 'BG Studio 3D')
    price = esc(active_price_text(product))
    return (
        f'<figure class="home-hero-visual home-hero-visual-{esc(position)}">{picture}'
        f'<figcaption><span>{name}</span><small>{price}</small></figcaption></figure>'
    )


def render_homepage_v3163(active, featured, field_items):
    # V3.1.76: editorial copy and every homepage product placement can be managed without touching code.
    home_copy = read_site_content_v3175()['home']
    hero_products = _homepage_slot_products(active, featured, home_copy.get('hero_product_slugs'), 3)
    hero_main = hero_products[0] if hero_products else None
    hero_side_1 = hero_products[1] if len(hero_products) > 1 else hero_main
    hero_side_2 = hero_products[2] if len(hero_products) > 2 else hero_side_1
    showcase_slots = _homepage_slot_products(active, featured, home_copy.get('showcase_product_slugs'), 6, allow_hide=True)
    product_cards = '\n'.join(render_home_showcase_product(product, i) for i, product in enumerate(showcase_slots) if product)
    project_cards = '\n'.join(render_home_project_feature(x, i + 1, '') for i, x in enumerate((field_items or [])[:4]))
    production_product = _homepage_single_product(active, featured, home_copy.get('production_product_slug'), fallback_index=1)
    production_visual = _home_visual_product(production_product, 'production', eager=False)

    return f'''<main class="home-v3163" id="main-content">
<section class="home-hero-v3163 bg-section-compact" aria-labelledby="home-hero-title">
  <div class="shell home-hero-grid-v3163">
    <div class="home-hero-copy-v3163 home-motion" data-home-motion>
      <p class="eyebrow">{esc(home_copy["hero_eyebrow"])}</p>
      <h1 id="home-hero-title">{esc(home_copy["hero_title"])}</h1>
      <p class="home-hero-lead">{esc(home_copy["hero_lead"])}</p>
      <div class="hero-actions home-hero-actions-v3163"><a class="primary-cta" href="{esc(home_copy["hero_primary_url"])}">{esc(home_copy["hero_primary_label"])}</a><a class="secondary-cta" href="{esc(home_copy["hero_secondary_url"])}">{esc(home_copy["hero_secondary_label"])}</a></div>
      <div class="home-hero-proof"><span>Kuşadası merkezli üretim</span><span>Tek adet + toplu üretim</span><span>Türkiye geneli kargo</span></div>
    </div>
    <div class="home-hero-stage-v3163" data-home-parallax="0.16" aria-label="BG Studio 3D ürün seçkisi">
      {_home_visual_product(hero_main, 'main', eager=True)}
      {_home_visual_product(hero_side_1, 'side-one', eager=False)}
      {_home_visual_product(hero_side_2, 'side-two', eager=False)}
      <div class="home-hero-stage-label"><span>BG STUDIO 3D</span><strong>Tasarım → Üretim</strong></div>
    </div>
  </div>
</section>

<section class="home-products-v3163 bg-section" aria-labelledby="home-products-title">
  <div class="shell">
    <div class="home-section-head home-motion" data-home-motion><div><p class="eyebrow">ÜRÜNLER</p><h2 id="home-products-title">Tasarlandı. Basıldı. Kullanıma hazır.</h2></div><a class="text-cta" href="urunler/">Ürünleri Gör ↗</a></div>
    <div class="home-showcase-grid">
<!-- PRODUCT_MANAGER:FEATURED_START -->
{product_cards}
<!-- PRODUCT_MANAGER:FEATURED_END -->
    </div>
  </div>
</section>

<section class="home-production-v3163 bg-section" aria-labelledby="home-production-title">
  <div class="shell home-split-panel home-split-production">
    <div class="home-split-copy home-motion" data-home-motion><p class="eyebrow">{esc(home_copy["production_eyebrow"])}</p><h2 id="home-production-title">{esc(home_copy["production_title"])}</h2><p>{esc(home_copy["production_lead"])}</p><a class="primary-cta" href="{esc(home_copy["production_cta_url"])}">{esc(home_copy["production_cta_label"])}</a></div>
    <div class="home-production-stage home-motion" data-home-motion>{production_visual}<div class="home-production-steps"><span><b>01</b>Fikir</span><span><b>02</b>Model</span><span><b>03</b>Baskı</span></div></div>
  </div>
</section>

<section class="home-business-v3163 bg-section" aria-labelledby="home-business-title">
  <div class="shell home-split-panel home-split-business">
    <figure class="home-business-visual home-motion zoomable-media" data-home-motion tabindex="0" role="button" aria-label="BG Studio NFC stand sistemini büyüt"><img alt="BG Studio NFC restoran stand şeması" decoding="async" height="1254" loading="lazy" src="assets/images/nfc-stand-semasi.webp" width="1254"/></figure>
    <div class="home-split-copy home-motion" data-home-motion><p class="eyebrow">İŞLETME ÇÖZÜMLERİ</p><h2 id="home-business-title">Fiziksel ürünün ötesinde.</h2><p>İşletmeye özel 3D standı NFC, QR, dijital menü, değerlendirme ve yönetim altyapısıyla tek deneyimde birleştiriyoruz.</p><div class="home-business-points"><span>İşletmeye özel fiziksel stand</span><span>NFC + QR erişimi</span><span>Dijital işletme altyapısı</span></div><a class="secondary-cta" href="nfc-qr/">NFC Sistemlerini İncele ↗</a></div>
  </div>
</section>

<section class="home-projects-v3163 bg-section" id="sahadan-isler" aria-labelledby="home-projects-title">
  <div class="shell">
    <div class="home-section-head home-motion" data-home-motion><div><p class="eyebrow">SAHADAN İŞLER</p><h2 id="home-projects-title">Gerçek ihtiyaçlar. Gerçek teslimler.</h2></div><p>Tamamlanan işletme ve üretim projelerinden seçilen uygulamalar.</p></div>
    <div class="home-project-grid">
<!-- CONTENT_MANAGER:HOME_FIELD_START -->
{project_cards}
<!-- CONTENT_MANAGER:HOME_FIELD_END -->
    </div>
    <div class="home-project-actions"><a class="secondary-cta" href="kurumsal/">Kurumsal işleri gör ↗</a><a class="ghost-cta" href="nfc-qr/">NFC saha çözümleri ↗</a></div>
  </div>
</section>

<section class="home-why-v3163 bg-section" aria-labelledby="home-why-title">
  <div class="shell home-why-shell">
    <div class="home-why-heading home-motion" data-home-motion><div class="home-why-kicker"><p class="eyebrow">{esc(home_copy["why_eyebrow"])}</p></div><h2 id="home-why-title">{_site_why_title_html(home_copy["why_title"])}</h2></div>
    <div class="home-why-grid">
      <article class="home-motion" data-home-motion><span>01</span><h3>Üretilebilir fikirler</h3><p>Görsel fikri baskı süresi, malzeme ve kullanım senaryosuyla birlikte değerlendiriyoruz.</p></article>
      <article class="home-motion" data-home-motion><span>02</span><h3>Gerçek kullanım</h3><p>Dekoratif ürün kadar fonksiyonel parça, stand, aparat ve işletme ihtiyaçlarına odaklanıyoruz.</p></article>
      <article class="home-motion" data-home-motion><span>03</span><h3>Tek üretim altyapısı</h3><p>Tek üründen toplu üretime ve NFC + QR sistemlerine uzanan aynı tasarım yaklaşımı.</p></article>
    </div>
    <a class="home-architecture-branch home-motion" data-home-motion href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>BG Studio'nun diğer iş kolu</span><strong>Architecture ↗</strong></a>
  </div>
</section>

<section class="home-final-v3163 bg-section-compact" aria-labelledby="home-final-title">
  <div class="shell home-final-shell home-motion" data-home-motion><div><p class="eyebrow">{esc(home_copy["final_eyebrow"])}</p><h2 id="home-final-title">{esc(home_copy["final_title"])}</h2><p>{esc(home_copy["final_lead"])}</p></div><div class="home-final-actions"><a class="primary-cta" href="{esc(home_copy["final_primary_url"])}">{esc(home_copy["final_primary_label"])}</a><a class="secondary-cta" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp'tan Yaz ↗</a></div></div>
</section>
</main>'''


def rebuild_homepage_v3163(text, active, featured, field_items):
    # Replace only <main>; head, announcement, canonical header and footer stay intact.
    main_html = render_homepage_v3163(active, featured, field_items)
    pattern = re.compile(r'<main\b[^>]*>.*?</main>', flags=re.I | re.S)
    if not pattern.search(text):
        raise RuntimeError('V3.1.63 ana sayfa <main> alanı bulunamadı.')
    updated = pattern.sub(lambda _m: main_html, text, count=1)

    home_copy = read_site_content_v3175().get('home', {})
    selected = _homepage_slot_products(active, featured, home_copy.get('hero_product_slugs'), 3)
    hero_first = selected[0] if selected else None
    if hero_first:
        hero_src = str(hero_first.get('main_image') or '').strip()
        if hero_src:
            preload = f'<!-- BGSTUDIO:HOME_HERO_PRELOAD --><link rel="preload" as="image" href="{esc(hero_src)}" fetchpriority="high"/>'
            if '<!-- BGSTUDIO:HOME_HERO_PRELOAD -->' in updated:
                updated = re.sub(r'<!-- BGSTUDIO:HOME_HERO_PRELOAD -->\s*<link\b[^>]*>', preload, updated, count=1, flags=re.I)
            elif '</head>' in updated:
                updated = updated.replace('</head>', preload + '</head>', 1)
    return updated


CATALOG_MATERIAL_PATTERNS = (
    ('pla-plus', 'PLA+', (r'\bpla\s*\+', r'\bpla\s*plus\b')),
    ('pla-hd', 'PLA HD', (r'\bpla\s*hd\b',)),
    ('petg', 'PETG', (r'\bpetg\b',)),
    ('tpu', 'TPU', (r'\btpu\b',)),
    ('asa', 'ASA', (r'\basa\b',)),
    ('abs', 'ABS', (r'\babs\b',)),
    ('pla', 'PLA', (r'\bpla\b',)),
)

def _catalog_product_text(p):
    parts = [
        p.get('name'), p.get('card_description'), p.get('description'),
        p.get('production_note'), ' '.join(str(x) for x in (p.get('tags') or [])),
        ' '.join(str(x) for x in (p.get('features') or [])),
    ]
    return re.sub(r'\s+', ' ', ' '.join(str(x or '') for x in parts)).strip()

def catalog_materials(p):
    """Use explicit panel material selection; legacy products keep text fallback until edited."""
    material_rows = load_materials()
    by_id = {str(item.get('id') or ''): str(item.get('name') or item.get('id') or '') for item in material_rows}
    if 'material_ids' in p:
        found = []
        seen = set()
        for material_id in (p.get('material_ids') or []):
            key = str(material_id or '').strip()
            if key and key in by_id and key not in seen:
                seen.add(key)
                found.append((key, by_id[key]))
        return found

    # Legacy compatibility only. Once a product is saved with material_ids,
    # catalog filtering becomes fully panel-controlled.
    source = _catalog_product_text(p).casefold()
    found = []
    matched_keys = set()
    for key, label, patterns in CATALOG_MATERIAL_PATTERNS:
        if key == 'pla' and ('pla-plus' in matched_keys or 'pla-hd' in matched_keys):
            continue
        if key not in by_id:
            continue
        if any(re.search(pattern, source, flags=re.I) for pattern in patterns):
            found.append((key, by_id.get(key) or label))
            matched_keys.add(key)
    return found


def catalog_personalizable(p):
    # Explicit admin switch only. Category/title/tag text never forces this flag.
    return bool(p.get('personalizable'))


PRODUCTION_STATUS = {
    'active': ('Üretime açık', 'status-active'),
    'busy': ('Yoğunluk yüksek', 'status-busy'),
    'preorder': ('Ön sipariş', 'status-preorder'),
    'paused': ('Geçici olarak üretimde değil', 'status-paused'),
}

def product_production_status(p):
    key = str(p.get('production_status') or '').strip().lower()
    return key if key in PRODUCTION_STATUS else ''

def product_schema_availability(p):
    key = product_production_status(p)
    if key == 'preorder':
        return 'https://schema.org/PreOrder'
    if key == 'paused':
        return 'https://schema.org/OutOfStock'
    return 'https://schema.org/InStock'

def product_og_media(p):
    source = str(p.get('og_image_source') or 'main').strip().lower()
    if source == 'poster' and p.get('poster_image'):
        return (p.get('poster_image'), int(p.get('poster_image_width') or 1254), int(p.get('poster_image_height') or 1254))
    if source == 'gallery':
        for item in (p.get('gallery_images') or []):
            if isinstance(item, str) and item:
                return (item, 1000, 1000)
            if isinstance(item, dict) and item.get('path'):
                return (item.get('path'), int(item.get('width') or 1000), int(item.get('height') or 1000))
    return (p.get('main_image'), int(p.get('main_image_width') or 1000), int(p.get('main_image_height') or 760))

def _detail_lines(value):
    return [line.strip() for line in str(value or '').splitlines() if line.strip()]

def render_product_technical(p):
    rows = []
    materials = [label for _, label in catalog_materials(p)]
    if materials:
        rows.append(('Malzeme', ', '.join(materials)))
    for label, key in (
        ('Ölçüler', 'dimensions'), ('Ağırlık', 'weight'), ('Baskı yöntemi', 'print_method'),
        ('Baskı / üretim süresi', 'production_time'), ('Tahmini hazırlık', 'estimated_production_time'),
    ):
        value = str(p.get(key) or '').strip()
        if value:
            rows.append((label, value))
    box = _detail_lines(p.get('box_contents'))
    tech = _detail_lines(p.get('technical_info'))
    usage = _detail_lines(p.get('usage_info'))
    personalization = _detail_lines(p.get('personalization_info'))
    if not rows and not box and not tech and not usage and not personalization:
        return ''
    facts = ''.join(f'<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>' for label, value in rows)
    blocks = []
    for title, values in (('Kutu içeriği', box), ('Teknik notlar', tech), ('Kullanım', usage), ('Kişiselleştirme', personalization)):
        if values:
            blocks.append(f'<div class="product-tech-list"><h3>{esc(title)}</h3><ul>' + ''.join(f'<li>{esc(v)}</li>' for v in values) + '</ul></div>')
    return '<details class="product-tech-accordion"><summary><span>Teknik &amp; üretim bilgileri</span><small>Detayları göster</small></summary><div class="product-tech-body">' + (f'<dl class="product-tech-grid">{facts}</dl>' if facts else '') + ''.join(blocks) + '</div></details>'


def category_label(p):
    return CATEGORY_LABELS.get(p.get('category'), p.get('category', '').replace('-', ' ').title())


def sale_price_info(p):
    base = parse_price_number(p.get('price_value'))
    sale = parse_price_number(p.get('sale_price_value'))
    if base is None or sale is None or base <= 0 or sale <= 0 or sale >= base:
        return None
    percent = max(1, round((1 - sale / base) * 100))
    return {'base': base, 'sale': sale, 'percent': percent}


def active_price_value(p):
    info = sale_price_info(p)
    return canonical_price_value(p.get('sale_price_value')) if info else canonical_price_value(p.get('price_value'))


def active_price_text(p):
    info = sale_price_info(p)
    if info:
        return format_try(p.get('sale_price_value')) or str(p.get('sale_price_value'))
    return p.get('price_text') or 'Fiyat için iletişim'


def card_price_html(p):
    info = sale_price_info(p)
    if not info:
        return f'<strong>{esc(p.get("price_text") or "Fiyat için iletişim")}</strong>'
    old = esc(p.get('price_text') or format_try(p.get('price_value')) or '')
    sale = esc(format_try(p.get('sale_price_value')) or '')
    return f'<span class="sale-price"><del>{old}</del><strong>{sale}</strong><em>%{info["percent"]}</em></span>'


def render_card(p, prefix='', catalog=False, catalog_index=0):
    raw_name = str(p['name'])
    raw_label = category_label(p)
    raw_price = active_price_text(p)
    raw_desc = p.get('card_description') or p.get('description') or ''
    name = esc(raw_name)
    label = esc(raw_label)
    price = esc(raw_price)
    price_markup = card_price_html(p)
    desc = esc(raw_desc)
    img = esc(prefix + p['main_image'])
    href = esc(prefix + 'urunler/' + p['slug'] + '/')
    if prefix == '../':
        href = esc('../urunler/' + p['slug'] + '/')
    search = ' '.join([
        raw_label, raw_price, raw_name, str(raw_desc),
        ' '.join(str(x) for x in (p.get('tags') or [])),
        ' '.join(str(x) for x in (p.get('features') or [])),
        ' '.join(label for _key, label in catalog_materials(p)),
        'Ürünü incele'
    ]).casefold()
    w = int(p.get('main_image_width') or 1000)
    h = int(p.get('main_image_height') or 760)

    if catalog:
        price_value = active_price_value(p) or ''
        try:
            order_value = int(p.get('sort_order') or 9999)
        except Exception:
            order_value = 9999
        materials = catalog_materials(p)
        material_keys = '|'.join(key for key, _label in materials)
        personalizable = catalog_personalizable(p)
        badges = []
        if p.get('featured'):
            badges.append('<span class="catalog-card-badge">Öne çıkan</span>')
        if personalizable:
            badges.append('<span class="catalog-card-badge catalog-card-badge-soft">Kişiye özel</span>')
        if sale_price_info(p):
            badges.append('<span class="catalog-card-badge catalog-card-badge-sale">İndirim</span>')
        badge_markup = f'<span class="catalog-card-badges">{"".join(badges[:2])}</span>' if badges else ''
        return (
            f'<article class="product-card catalog-product-card" '
            f'data-category="{esc(p.get("category"))}" data-search="{esc(search)}" '
            f'data-price="{esc(price_value)}" data-order="{order_value}" data-added-rank="{int(catalog_index or 0)}" '
            f'data-featured="{"1" if p.get("featured") else "0"}" '
            f'data-personalizable="{"1" if personalizable else "0"}" '
            f'data-materials="{esc(material_keys)}" aria-hidden="false">\n'
            f'<a class="product-image" href="{href}">{badge_markup}<img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{img}" width="{w}"/></a>\n'
            f'<div class="product-card-body"><span class="catalog-card-category">{label}</span>'
            f'<h3><a href="{href}">{name}</a></h3>'
            f'<div class="catalog-card-footer"><span class="catalog-card-price">{price_markup}</span>'
            f'<a class="product-link" href="{href}" aria-label="{name} ürününü incele">İncele ↗</a></div>'
            f'</div>\n</article>'
        )

    return (
        f'<article class="product-card" data-category="{esc(p.get("category"))}" data-search="{esc(search)}">\n'
        f'<a class="product-image" href="{href}"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{img}" width="{w}"/></a>\n'
        f'<div class="product-card-body"><div class="product-topline"><span>{label}</span>{price_markup}</div>\n'
        f'<h3><a href="{href}">{name}</a></h3><p>{desc}</p>\n'
        f'<a class="product-link" href="{href}">Ürünü incele ↗</a>\n</div>\n</article>'
    )


def replace_between(text, start_marker, end_marker, content):
    pattern = re.compile(re.escape(start_marker) + r'.*?' + re.escape(end_marker), re.S)
    replacement = start_marker + '\n' + content + '\n' + end_marker
    if not pattern.search(text):
        raise RuntimeError(f'İşaret bulunamadı: {start_marker}')
    return pattern.sub(lambda _m: replacement, text, count=1)




def effective_pricing_tiers(p):
    """Return storefront pricing tiers with base price as authoritative Tekli price.

    A multi-buy price must never replace the product's normal catalog price. If
    price_value exists, quantity=1 is always generated from that base value and
    any conflicting quantity=1 tier is ignored.
    """
    source = [dict(t) for t in (p.get('pricing_tiers') or []) if isinstance(t, dict)]
    tiers = []
    base = active_price_value(p)
    if base not in (None, ''):
        tiers.append({
            'label': 'Tekli',
            'quantity': 1,
            'price_value': str(base),
            'note': 'Tekli fiyat',
            '_auto': True,
        })
        source = [t for t in source if int(t.get('quantity') or 1) > 1]
    for t in source:
        try:
            qty = int(t.get('quantity') or 1)
        except Exception:
            qty = 1
        if qty < 1 or t.get('price_value') in (None, ''):
            continue
        tiers.append({
            'label': str(t.get('label') or (f"{qty}’li set" if qty > 1 else 'Tekli')),
            'quantity': qty,
            'price_value': canonical_price_value(t.get('price_value')),
            'note': str(t.get('note') or ''),
            '_auto': bool(t.get('_auto')),
        })
    # Deduplicate by quantity, preferring the authoritative base tier.
    dedup = {}
    for t in tiers:
        q = int(t.get('quantity') or 1)
        if q not in dedup or t.get('_auto'):
            dedup[q] = t
    return [dedup[q] for q in sorted(dedup)]

def render_schema(p):
    obj = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': p['name'],
        'description': p.get('description', ''),
        'brand': {'@type': 'Brand', 'name': 'BG Studio 3D'},
        'url': f"{BASE_URL}/urunler/{p['slug']}/",
        'image': f"{BASE_URL}/{p['main_image']}",
    }
    tiers = effective_pricing_tiers(p)
    if p.get('tags'):
        obj['keywords'] = ', '.join(str(x) for x in p.get('tags') or [])
    if tiers:
        obj['offers'] = [
            {
                '@type': 'Offer',
                'name': str(t.get('label') or f"{t.get('quantity', 1)} adet"),
                'priceCurrency': 'TRY',
                'price': str(t.get('price_value')),
                'availability': product_schema_availability(p),
                'eligibleQuantity': {'@type': 'QuantitativeValue', 'value': int(t.get('quantity') or 1), 'unitText': 'adet'},
            }
            for t in tiers if t.get('price_value') not in (None, '')
        ]
    elif active_price_value(p) not in (None, ''):
        obj['offers'] = {
            '@type': 'Offer',
            'priceCurrency': 'TRY',
            'price': str(active_price_value(p)),
            'availability': product_schema_availability(p),
        }
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def choose_related(products, p):
    active = [x for x in products if x.get('active', True) and x['slug'] != p['slug']]
    same = [x for x in active if x.get('category') == p.get('category')]
    other = [x for x in active if x.get('category') != p.get('category')]
    return (same + other)[:3]


def render_product_page(p, related):
    name = esc(p['name'])
    label = esc(category_label(p))
    price = esc(active_price_text(p))
    sale_info = sale_price_info(p)
    desc = esc(p.get('description') or '')
    card_desc = esc(p.get('card_description') or p.get('description') or '')
    default_title, default_description = make_seo(p)
    title = esc(p.get('seo_title') or default_title)
    seo_desc = esc(clip_seo_text(p.get('seo_description') or default_description, 160))
    canonical = f"{BASE_URL}/urunler/{esc(p['slug'])}/"
    main_rel = '../../' + p['main_image']
    main_abs = f"{BASE_URL}/{p['main_image']}"
    w = int(p.get('main_image_width') or 1000)
    h = int(p.get('main_image_height') or 760)
    og_path, og_w, og_h = product_og_media(p)
    og_abs = f"{BASE_URL}/{og_path}" if og_path else main_abs

    poster_thumb = ''
    if p.get('poster_image'):
        poster_rel = '../../' + p['poster_image']
        pw = int(p.get('poster_image_width') or 1254)
        ph = int(p.get('poster_image_height') or 1254)
        poster_thumb = (
            f'<button aria-label="Afiş görselini göster" aria-pressed="false" class="gallery-thumb" '
            f'data-gallery-alt="{name} ürün afişi" data-gallery-src="{esc(poster_rel)}" type="button">'
            f'<img alt="{name} ürün afişi" decoding="async" height="{ph}" loading="lazy" src="{esc(poster_rel)}" width="{pw}"/>'
            f'<span>Afiş</span></button>'
        )
    gallery_thumbs = ''
    for i, item in enumerate(p.get('gallery_images') or [], 1):
        if isinstance(item, str):
            item = {'path': item, 'width': 1000, 'height': 1000, 'alt': ''}
        path = item.get('path') if isinstance(item, dict) else None
        if not path:
            continue
        rel = '../../' + path
        gw = int(item.get('width') or 1000)
        gh = int(item.get('height') or 1000)
        galt = esc(item.get('alt') or f"{p['name']} galeri görseli {i}")
        gallery_thumbs += (
            f'<button aria-label="Galeri görseli {i} göster" aria-pressed="false" class="gallery-thumb" '
            f'data-gallery-alt="{galt}" data-gallery-src="{esc(rel)}" type="button">'
            f'<img alt="{galt}" decoding="async" height="{gh}" loading="lazy" src="{esc(rel)}" width="{gw}"/>'
            f'<span>{i + 2}. Görsel</span></button>'
        )

    color_entries = product_color_entries(p)
    legacy_options = legacy_order_options(p)
    options_html = ''.join(f'<option value="{esc(o)}">{esc(o)}</option>' for o in legacy_options)
    option_field_html = ''
    if legacy_options:
        option_field_html = f'<label class="order-field"><span>Seçenek</span><select aria-label="Ürün seçeneği" data-order-option="">{options_html}</select></label>'

    color_public = [
        {'id': str(c.get('id') or ''), 'name': str(c.get('name') or ''), 'hex': str(c.get('hex') or '#c7b9a6')}
        for c in color_entries
    ]
    color_json = json.dumps(color_public, ensure_ascii=False, separators=(',', ':')).replace('<', '\u003c')
    color_data_html = f'<script type="application/json" data-product-colors>{color_json}</script>' if color_public else ''
    color_picker_html = ''
    if color_public:
        color_picker_html = '<div class="order-color-section"><div class="order-color-head"><span>Renk seçimi</span><small>Setteki her ürünün rengini ayrı ayrı seçebilirsin.</small></div><div class="order-color-slots" data-order-color-slots></div></div>'

    color_tags = ''.join(
        f'<span class="color-public-chip"><i style="--swatch:{esc(c.get("hex") or "#c7b9a6")}"></i><b>{esc(c.get("name"))}</b></span>'
        for c in color_entries
    )
    legacy_tags = ''.join(f'<span>{esc(o)}</span>' for o in legacy_options)
    tags = color_tags + legacy_tags
    product_tags = ''.join(f'<span class="product-meta-tag">{esc(t)}</span>' for t in (p.get('tags') or [])[:16])
    product_tag_section = (
        '<div class="detail-section product-tag-section"><h2>Ürün etiketleri</h2>'
        f'<div class="option-tags product-meta-tags">{product_tags}</div></div>'
    ) if product_tags else ''

    pricing_tiers = effective_pricing_tiers(p)
    tier_options_html = ''
    tier_cards_html = ''
    # The normal product price is authoritative on first paint. Set prices only
    # replace it after the customer chooses another package.
    selected_display_price = esc(active_price_text(p))
    active_base_value = active_price_value(p)
    if active_base_value not in (None, ''):
        selected_display_price = esc(format_try(active_base_value) or active_price_text(p))
    price_list_html = ''
    discount_badge_html = ''
    if sale_info:
        price_list_html = f'<del class="price-list" data-discount-list-price>{esc(p.get("price_text") or format_try(p.get("price_value")) or "")}</del>'
        discount_badge_html = f'<span class="discount-badge" data-discount-badge>%{sale_info["percent"]} İNDİRİM</span>'
    if pricing_tiers:
        tier_options = []
        tier_cards = []
        for i, tier in enumerate(pricing_tiers):
            label_text = str(tier.get('label') or (f"{tier.get('quantity', 1)}’li set" if int(tier.get('quantity') or 1) > 1 else 'Tekli'))
            qty_value = int(tier.get('quantity') or 1)
            price_value = str(tier.get('price_value') or '')
            price_label = format_try(price_value)
            note_text = str(tier.get('note') or '')
            tier_options.append(
                f'<option value="{i}" data-tier-label="{esc(label_text)}" data-tier-qty="{qty_value}" data-tier-price="{esc(price_value)}" data-tier-price-label="{esc(price_label)}">{esc(label_text)} • {esc(price_label)}</option>'
            )
            tier_cards.append(
                f'<button aria-pressed="{"true" if i == 0 else "false"}" class="set-price-choice{" selected" if i == 0 else ""}" data-order-tier-choice="{i}" type="button"><span>{esc(label_text)}</span><strong>{esc(price_label)}</strong>{f'<small>{esc(note_text)}</small>' if note_text else ""}</button>'
            )
        tier_options_html = ''.join(tier_options)
        tier_cards_html = '<div class="set-pricing-panel"><div class="set-pricing-head"><span>Set / adet seçenekleri</span><small>Paketi seçtiğinde sipariş özeti ve fiyat otomatik güncellenir.</small></div><div class="set-pricing-grid">' + ''.join(tier_cards) + '</div></div>'
    tier_field_html = f'<label class="order-field"><span>Paket / set</span><select aria-label="Paket veya set seçeneği" data-order-tier="">{tier_options_html}</select></label>' if pricing_tiers else ''
    initial_choice = legacy_options[0] if legacy_options else (color_public[0]['name'] if color_public else 'Standart')
    initial_summary = f"{initial_choice} • {'1 set' if pricing_tiers else '1 adet'}"
    detail_options_heading = 'Renk seçenekleri' if color_public else 'Seçenekler'
    feats = ''.join(f'<li>{esc(x)}</li>' for x in (p.get('features') or ['3D baskı üretim', 'Sipariş öncesi detaylandırma']))
    related_html = ''.join(
        f'<a class="related-card" href="../{esc(r["slug"])}/">'
        f'<img alt="{esc(r["name"])}" decoding="async" height="{int(r.get("main_image_height") or 760)}" loading="lazy" '
        f'src="../../{esc(r["main_image"])}" width="{int(r.get("main_image_width") or 1000)}"/>'
        f'<div><h3>{esc(r["name"])}</h3><span class="related-price">{card_price_html(r)}</span></div></a>'
        for r in related
    )
    breadcrumb = json.dumps({
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Ana Sayfa', 'item': BASE_URL + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Ürünler', 'item': BASE_URL + '/urunler/'},
            {'@type': 'ListItem', 'position': 3, 'name': p['name'], 'item': canonical},
        ]
    }, ensure_ascii=False)
    faq = json.dumps({
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
            for q, a in FAQ
        ]
    }, ensure_ascii=False)
    faq_html = ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in FAQ)
    robots = 'index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1' if p.get('active', True) else 'noindex,follow'
    notice = '' if p.get('active', True) else '<div class="shell"><div class="catalog-empty" style="display:block;margin-top:24px"><strong>Bu ürün şu anda katalogda yayında değil.</strong></div></div>'
    production = esc(p.get('production_note') or '3D baskı ürünlerde katman dokusu üretim yönteminin doğal bir parçasıdır. Renk, adet ve kişiselleştirme seçenekleri sipariş öncesi netleştirilir.')
    status_key = product_production_status(p)
    status_badge_html = ''
    if status_key:
        status_label, status_class = PRODUCTION_STATUS[status_key]
        status_badge_html = f'<div class="production-status {status_class}"><span></span><strong>{esc(status_label)}</strong>{f"<small>{esc(p.get('estimated_production_time'))}</small>" if p.get('estimated_production_time') else ""}</div>'
    technical_html = render_product_technical(p)

    return f'''<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8"/><meta content="width=device-width, initial-scale=1" name="viewport"/><meta content="#f5ede2" name="theme-color"/>
<title>{title}</title><meta content="{seo_desc}" name="description"/>
<link href="{canonical}" rel="canonical"/>
<meta content="product" property="og:type"/><meta content="tr_TR" property="og:locale"/><meta content="BG Studio 3D" property="og:site_name"/>
<meta content="{title}" property="og:title"/><meta content="{card_desc}" property="og:description"/><meta content="{canonical}" property="og:url"/><meta content="{og_abs}" property="og:image"/><meta content="{name} | BG Studio 3D" property="og:image:alt"/>
<meta content="summary_large_image" name="twitter:card"/><meta content="{title}" name="twitter:title"/><meta content="{card_desc}" name="twitter:description"/><meta content="{og_abs}" name="twitter:image"/>
<link href="../../favicon.ico" rel="icon" sizes="any"/><link href="../../assets/brand/favicon-32x32.png" rel="icon" sizes="32x32" type="image/png"/><link href="../../assets/brand/favicon-16x16.png" rel="icon" sizes="16x16" type="image/png"/><link href="../../apple-touch-icon.png" rel="apple-touch-icon" sizes="180x180"/><link href="../../site.webmanifest" rel="manifest"/>
<link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"/><link href="../../assets/css/styles.css?v=3.1.52" rel="stylesheet"/>
<script type="application/ld+json">{render_schema(p)}</script><script data-schema="breadcrumb" type="application/ld+json">{breadcrumb}</script><script data-schema="faq" type="application/ld+json">{faq}</script>
<meta content="{robots}" name="robots"/><meta content="strict-origin-when-cross-origin" name="referrer"/><meta content="{og_w}" property="og:image:width"/><meta content="{og_h}" property="og:image:height"/><meta content="light" name="color-scheme"/>

</head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>
{render_site_header('../../', 'products')}
{notice}
<main id="main-content"><section class="product-detail shell"><div class="breadcrumb"><a href="../../">Ana Sayfa</a><span>/</span><a href="../">Ürünler</a><span>/</span><span>{name}</span></div><div class="product-detail-grid"><div class="product-gallery"><div aria-label="Seçili ürün görselini büyüt" class="gallery-stage zoomable-media" data-gallery-stage="" role="button" tabindex="0"><img alt="{name}" data-gallery-main="" decoding="async" fetchpriority="high" height="{h}" src="{esc(main_rel)}" width="{w}"/></div><div aria-label="Ürün görselleri" class="gallery-thumbs"><button aria-label="Ürün görselini göster" aria-pressed="true" class="gallery-thumb active" data-gallery-alt="{name}" data-gallery-src="{esc(main_rel)}" type="button"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{esc(main_rel)}" width="{w}"/><span>Ürün</span></button>{poster_thumb}{gallery_thumbs}</div><p class="gallery-hint">Görseli büyütmek için ana görsele tıkla.</p></div>
<div class="product-info"><p class="eyebrow">{label.upper()}</p><h1>{name}</h1><p class="product-lead">{desc}</p>{status_badge_html}<div class="price-block{' has-discount' if sale_info else ''}"><small>Fiyat</small><div class="price-display-row">{price_list_html}<strong data-product-price-display="">{selected_display_price}</strong>{discount_badge_html}</div></div>{tier_cards_html}<div class="order-configurator" data-order-config="" data-product-name="{name}" data-product-price="{price}" data-product-base-price-value="{esc(active_base_value or '')}"><div class="order-config-head"><strong>Siparişini hazırla</strong><span>Seçimini yap, mesajı hazır gönder.</span></div><div class="order-controls{' has-tier' if pricing_tiers else ''}{' color-mode' if color_public else ''}">{option_field_html}{tier_field_html}<div class="order-field order-qty-field"><span>{'Set adedi' if pricing_tiers else 'Adet'}</span><div class="qty-stepper"><button aria-label="Adedi azalt" data-qty-minus="" type="button">−</button><input aria-label="Adet" data-order-qty="" max="12" min="1" type="number" value="1"/><button aria-label="Adedi artır" data-qty-plus="" type="button">+</button></div></div></div>{color_picker_html}{color_data_html}<label class="order-field order-note-field"><span>Not (isteğe bağlı)</span><input data-order-note="" maxlength="160" placeholder="Örn. hediye olacak, teslim notu…" type="text"/></label><div class="order-summary"><span>Seçim:</span><strong data-order-summary="">{esc(initial_summary)}</strong></div><a class="primary-cta wide-cta smart-order-whatsapp" data-order-whatsapp="" href="#" rel="noopener" target="_blank">Seçimi WhatsApp’tan gönder ↗</a><p class="order-local-note">Seçimin site üzerinde kaydedilmez; yalnızca WhatsApp mesajını hazırlamak için kullanılır.</p></div><div class="product-action-row share-only-row"><button class="secondary-cta share-product" data-share-title="{name}" type="button">Ürün linkini paylaş</button></div><div class="detail-note">📍 Kuşadası elden teslim   •   📦 Türkiye geneli kargo</div><div class="product-facts"><div><small>Üretim</small><strong>3D baskı</strong></div><div><small>Teslim</small><strong>Kuşadası / kargo</strong></div><div><small>Seçenek</small><strong>Ürüne göre</strong></div><div><small>Sipariş</small><strong>WhatsApp</strong></div></div>{technical_html}<div class="detail-section"><h2>Öne çıkan özellikler</h2><ul>{feats}</ul></div><div class="detail-section"><h2>{detail_options_heading}</h2><div class="option-tags">{tags or '<span>WhatsApp üzerinden netleştirilir.</span>'}</div></div>{product_tag_section}<div class="detail-section"><h2>Üretim notu</h2><p>{production}</p></div></div></div><div class="assurance-strip"><div><strong>Kuşadası</strong><span>Elden teslim</span></div><div><strong>Türkiye</strong><span>Kargo seçeneği</span></div><div><strong>Atölye</strong><span>3D baskı üretim</span></div><div><strong>Sipariş</strong><span>WhatsApp üzerinden</span></div></div></section>
<section class="order-process shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ SÜRECİ</p><h2>Nasıl ilerliyoruz?</h2></div></div><div class="order-steps"><article class="order-step"><span>01</span><h3>Ürünü seç</h3><p>Renk, adet ve varsa kişiselleştirme isteğini bize ilet.</p></article><article class="order-step"><span>02</span><h3>Detayları netleştir</h3><p>Üretim seçeneği ve teslim/kargo detaylarını sipariş öncesi netleştir.</p></article><article class="order-step"><span>03</span><h3>Üretim</h3><p>Ürün atölyede 3D baskı ile hazırlanır ve kontrol edilir.</p></article><article class="order-step"><span>04</span><h3>Teslim</h3><p>Kuşadası elden teslim veya uygun kargo seçeneğiyle gönderim.</p></article></div></section>
<section class="product-faq shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ ÖNCESİ</p><h2>Bilmen gerekenler.</h2></div></div><div class="faq">{faq_html}</div></section>
<section class="related-products shell"><div class="section-title"><div><p class="eyebrow">BUNLAR DA İLGİNİ ÇEKEBİLİR</p><h2>Atölyeden başka seçenekler.</h2></div></div><div class="related-grid">{related_html}</div></section><section class="detail-back shell"><a class="text-cta" href="../">← Tüm ürünlere dön</a></section></main>
<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı ve özel üretim.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a aria-label="BG Studio 3D Instagram" class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>bgstudio.3dtr</span></a><a aria-label="BG Studio 3D Facebook" class="footer-social icon-facebook" href="https://www.facebook.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>Facebook · BG Studio 3D</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../prototip-parca/">Prototip &amp; Parça Üretim</a><a href="../../kusadasi-3d-baski/">Kuşadası 3D Baskı</a><a href="../../iletisim/">İletişim</a><a href="../../gizlilik/">Gizlilik</a><a href="../../siparis-bilgilendirme/">Sipariş Bilgilendirme</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır. | 3D baskı, özel üretim ve kurumsal çözümler.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>
<script defer="" src="../../assets/js/consent.js"></script><script defer="" src="../../assets/js/main.js?v=3.1.4"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div><div class="mobile-product-cta"><div><strong>{name}</strong><span class="mobile-price-wrap">{price_list_html}<b data-mobile-price="">{selected_display_price}</b></span></div><a data-mobile-order-whatsapp="" href="#" rel="noopener" target="_blank">Siparişi hazırla</a></div></body></html>'''



SITE_ASSET_VERSION = '3.1.76'


def _relative_prefix_for_html(html_path):
    rel = html_path.relative_to(ROOT)
    depth = max(0, len(rel.parts) - 1)
    return '../' * depth


def _nav_active_key(html_path):
    rel = html_path.relative_to(ROOT).as_posix().lower()
    if rel == 'urunler/index.html' or rel.startswith('urunler/'):
        return 'products'
    if rel.startswith('ozel-uretim/'):
        return 'custom-production'
    if rel.startswith('prototip-parca/'):
        return 'prototype'
    if rel.startswith('kurumsal/'):
        return 'corporate'
    if rel.startswith('nfc-qr/'):
        return 'nfc'
    if rel.startswith('projeler/'):
        return 'projects'
    if rel.startswith('hakkimizda/'):
        return 'about'
    if rel.startswith('iletisim/'):
        return 'contact'
    return ''


def render_site_header(prefix='', active_key=''):
    def direct_active(key):
        return ' aria-current="page" class="nav-link is-active"' if active_key == key else ' class="nav-link"'

    def group_class(*keys):
        return 'nav-group is-active' if active_key in keys else 'nav-group'

    def child_active(key):
        return ' aria-current="page" class="is-active"' if active_key == key else ''

    # Keep route URLs relative so the static site works locally, on GitHub Pages
    # and on the production custom domain without a router dependency.
    return (
        '<header class="site-header" id="top" data-bg-nav="v3.1.72"><div class="shell nav-shell">'
        f'<a aria-label="BG Studio 3D ana sayfa" class="brand" href="{prefix}"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a>'
        '<button aria-controls="primary-navigation" aria-expanded="false" aria-label="Menüyü aç" class="menu-toggle" type="button"><span></span><span></span></button>'
        '<nav aria-label="Ana menü" class="main-nav" id="primary-navigation">'
        f'<a{direct_active("products")} href="{prefix}urunler/">Ürünler</a>'
        f'<div class="{group_class("custom-production", "prototype")}"><button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-production">Üretim</button><div class="nav-submenu" id="nav-production"><a{child_active("custom-production")} href="{prefix}ozel-uretim/">Özel Üretim</a><a{child_active("prototype")} href="{prefix}prototip-parca/">Prototip &amp; Parça Üretim</a></div></div>'
        f'<div class="{group_class("corporate", "nfc")}"><button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-business">İşletmeler</button><div class="nav-submenu" id="nav-business"><a{child_active("corporate")} href="{prefix}kurumsal/">Kurumsal</a><a{child_active("nfc")} href="{prefix}nfc-qr/">NFC &amp; QR Sistemleri</a></div></div>'
        f'<a{direct_active("projects")} href="{prefix}projeler/">Projeler</a>'
        f'<div class="{group_class("about", "contact")}"><button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-studio">BG Studio</button><div class="nav-submenu" id="nav-studio"><a{child_active("about")} href="{prefix}hakkimizda/">Hakkımızda</a><a{child_active("contact")} href="{prefix}iletisim/">İletişim</a><a class="arch-link" href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture ↗</a></div></div>'
        '<div class="nav-actions"><a class="nav-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a></div>'
        '</nav></div></header>'
    )


def sync_site_header_navigation():
    """Give every public page one canonical V3.1.72 header without touching page data."""
    header_pattern = re.compile(r'<header\b[^>]*class="[^"]*\bsite-header\b[^"]*"[^>]*>.*?</header>', flags=re.I | re.S)
    scanned = 0
    changed = 0
    missing_header = []
    for html_path in ROOT.rglob('*.html'):
        rel_parts = html_path.relative_to(ROOT).parts
        if 'tools' in rel_parts:
            continue
        scanned += 1
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if not header_pattern.search(text):
            # Legal/special fragments may intentionally omit a site header; record only.
            missing_header.append(html_path.relative_to(ROOT).as_posix())
            continue
        prefix = _relative_prefix_for_html(html_path)
        updated = header_pattern.sub(render_site_header(prefix, _nav_active_key(html_path)), text, count=1)
        # Make the existing homepage field-work section a stable project target.
        if html_path == ROOT / 'index.html' and 'id="sahadan-isler"' not in updated:
            updated = re.sub(r'<section\b([^>]*class="[^"]*\bfield-work\b[^"]*"[^>]*)>', r'<section id="sahadan-isler"\1>', updated, count=1, flags=re.I)
        if updated != text:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed, 'missing_header': missing_header}


def sync_site_asset_versions():
    """Bump shared assets and install the separate navigation module on every public page."""
    changed = 0
    scanned = 0
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        scanned += 1
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        prefix = _relative_prefix_for_html(html_path)
        updated = re.sub(r'((?:\.\./)*assets/css/styles\.css\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', text)
        updated = re.sub(r'((?:\.\./)*assets/js/main\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/navigation\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/homepage\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/catalog\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/nfc-hub\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/projects\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/quote-center\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        # Every page receiving the global footer must be able to reopen cookie preferences.
        if 'footer-consent-button' in updated and 'assets/js/consent.js' not in updated:
            consent_tag = f'<script defer="" src="{prefix}assets/js/consent.js"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js(?:\?v=[^"]+)?"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.start()] + consent_tag + updated[main_match.start():]
            else:
                updated = updated.replace('</body>', consent_tag + '</body>', 1)
        if 'assets/js/navigation.js' not in updated:
            nav_tag = f'<script defer="" src="{prefix}assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.start()] + nav_tag + updated[main_match.start():]
            else:
                updated = updated.replace('</body>', nav_tag + '</body>', 1)
        if html_path == ROOT / 'index.html' and 'assets/js/homepage.js' not in updated:
            home_tag = f'<script defer="" src="assets/js/homepage.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.start()] + home_tag + updated[main_match.start():]
            else:
                updated = updated.replace('</body>', home_tag + '</body>', 1)
        if html_path == ROOT / 'urunler' / 'index.html' and 'assets/js/catalog.js' not in updated:
            catalog_tag = f'<script defer="" src="../assets/js/catalog.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.start()] + catalog_tag + updated[main_match.start():]
            else:
                updated = updated.replace('</body>', catalog_tag + '</body>', 1)
        if html_path.relative_to(ROOT).as_posix().startswith('nfc-qr/') and 'assets/js/nfc-hub.js' not in updated:
            nfc_tag = f'<script defer="" src="{prefix}assets/js/nfc-hub.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.end()] + nfc_tag + updated[main_match.end():]
            else:
                updated = updated.replace('</body>', nfc_tag + '</body>', 1)
        if html_path.relative_to(ROOT).as_posix().startswith('projeler/') and 'assets/js/projects.js' not in updated:
            projects_tag = f'<script defer="" src="{prefix}assets/js/projects.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.end()] + projects_tag + updated[main_match.end():]
            else:
                updated = updated.replace('</body>', projects_tag + '</body>', 1)
        if html_path == ROOT / 'teklif' / 'index.html' and 'assets/js/quote-center.js' not in updated:
            quote_tag = f'<script defer="" src="../assets/js/quote-center.js?v={SITE_ASSET_VERSION}"></script>'
            main_match = re.search(r'<script\b[^>]*src="(?:\.\./)*assets/js/main\.js\?v=[^"]+"[^>]*></script>', updated, flags=re.I)
            if main_match:
                updated = updated[:main_match.end()] + quote_tag + updated[main_match.end():]
            else:
                updated = updated.replace('</body>', quote_tag + '</body>', 1)
        build_meta = f'<meta name="bgstudio-build" content="{SITE_ASSET_VERSION}"/>'
        if 'name="bgstudio-build"' in updated:
            updated = re.sub(r'<meta\s+name="bgstudio-build"\s+content="[^"]*"\s*/?>', build_meta, updated, count=1, flags=re.I)
        elif '</head>' in updated:
            updated = updated.replace('</head>', build_meta + '</head>', 1)
        if updated != text:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed}

def render_nfc_platform_sections(theme_overrides=None):
    """Canonical NFC + QR product, package and pricing presentation.

    V3.1.53 separates the three product families correctly:
    Standard Restaurant Systems, Hızlı Bağlantı Standı and Premium Feedback Duo.
    High-capacity restaurant ready packages remain part of the restaurant system.
    """
    pricing = active_nfc_pricing()
    year = str(pricing.get('year') or '2026')
    qr_unit = int(pricing.get('qr_unit') or 0)
    menu_design = int(pricing.get('menu_design') or 0)
    logo_design = int(pricing.get('logo_design') or 0)
    packages = pricing.get('packages') or {}
    duo_rows = pricing.get('feedback_duo_packages') if isinstance(pricing.get('feedback_duo_packages'), dict) else {}
    special_rows = pricing.get('special_restaurant_packages') if isinstance(pricing.get('special_restaurant_packages'), dict) else {}

    all_settings = load_site_settings()
    nfc_all = all_settings.get('nfc_site') if isinstance(all_settings.get('nfc_site'), dict) else default_nfc_site_settings()
    years_all = nfc_all.get('years') if isinstance(nfc_all.get('years'), dict) else {}
    y2027 = years_all.get('2027') if isinstance(years_all.get('2027'), dict) else default_nfc_site_settings()['years']['2027']
    qr_2027 = int(y2027.get('qr_unit') or 200)
    logo_2027 = int(y2027.get('logo_design') or 3000)

    def pack(key):
        return packages.get(key) if isinstance(packages.get(key), dict) else {}

    def money(value, fallback='Özel teklif'):
        return format_try(value) or fallback

    def normal_and_renewal(key):
        row = pack(key)
        bits = []
        if row.get('list_price'):
            bits.append(f"Normal fiyat: {money(row.get('list_price'))}")
        if row.get('renewal'):
            bits.append(f"Yıllık yenileme: {money(row.get('renewal'))}")
        return ' · '.join(bits) if bits else 'Proje kapsamına göre'

    start_qr_cost = qr_unit * 30
    pro_qr_cost = qr_unit * 45
    premium_qr_cost = qr_unit * 60
    quick_qr_cost = qr_unit * 3
    quick_price = pack('hizli_stand').get('price')
    quick_renewal = pack('hizli_stand').get('renewal')
    quick_with_qr = (quick_price + quick_qr_cost) if quick_price is not None else None
    quick_with_logo = (quick_price + logo_design) if quick_price is not None else None
    quick_full = (quick_price + quick_qr_cost + logo_design) if quick_price is not None else None

    published_duo = []
    for key, row in sorted(duo_rows.items(), key=lambda kv: int(kv[0])):
        if not isinstance(row, dict):
            continue
        stands = int(row.get('stands') or key)
        published_duo.append({
            'stands': stands,
            'nfc': stands * 2,
            'price': row.get('price'),
            'renewal': row.get('renewal'),
        })
    first_duo = next((row for row in published_duo if row.get('price') is not None), published_duo[0] if published_duo else {'stands':10,'nfc':20,'price':None,'renewal':None})
    duo_start_price = first_duo.get('price')
    duo_start_renewal = first_duo.get('renewal')
    duo_table_rows = ''.join(
        f'<tr><td>{row["stands"]} stand</td><td>{row["nfc"]} NFC</td><td>{money(row.get("price"))}</td><td>{money(row.get("renewal"))}</td></tr>'
        for row in published_duo
    )
    duo_mobile_cards = ''.join(
        f'<article class="duo-price-mini"><div><strong>{row["stands"]} stand</strong><span>{row["nfc"]} NFC</span></div><div><small>Kurulum / Satış</small><b>{money(row.get("price"))}</b></div><div><small>Yıllık Yenileme</small><b>{money(row.get("renewal"))}</b></div></article>'
        for row in published_duo
    )

    capacities = ['25','30','35','40','45','50','55','60','65','70','75','80','85','90','95','100','110','120']
    special_default_key = capacities[0]
    special_default = special_rows.get(special_default_key) if isinstance(special_rows.get(special_default_key), dict) else {
        'tables': int(special_default_key), 'nfc': int(special_default_key) * 3, 'price': None, 'renewal': None
    }
    special_qr_count = int(special_default_key) * 3
    special_qr_cost = special_qr_count * qr_unit

    def data_number(value):
        try:
            return str(int(value))
        except Exception:
            return ''

    capacity_chips = ''.join(
        (
            f'<button class="nfc-capacity-choice{" is-selected" if x == special_default_key else ""}" type="button" '
            f'data-special-capacity="{x}" data-special-nfc="{int(x) * 3}" '
            f'data-special-price="{data_number((special_rows.get(x) or {}).get("price"))}" '
            f'data-special-renewal="{data_number((special_rows.get(x) or {}).get("renewal"))}" '
            f'aria-pressed="{"true" if x == special_default_key else "false"}">'
            f'<span>{x} masa</span><small>{money((special_rows.get(x) or {}).get("price"))}</small></button>'
        )
        for x in capacities
    )

    menu_scope_copy = (
        'Türkçe + İngilizce görsel menü · 8 ek dilde dijital metin menü · '
        'ürün içerikleri · 14 alerjen bilgi katmanı · yaklaşık kalori bilgileri'
    )

    def restaurant_option_picker(code, label, tables, qr_count, cta_class='secondary-cta'):
        row = pack(code)
        base_price = row.get('price')
        qr_cost = int(qr_count) * qr_unit
        return (
            f'<div class="nfc-package-configurator" data-nfc-package-calculator '
            f'data-package-code="{code}" data-package-label="{esc(label)}" data-tables="{tables}" '
            f'data-base-price="{data_number(base_price)}" data-qr-count="{qr_count}" '
            f'data-qr-unit="{qr_unit}" data-menu-price="{menu_design}" data-logo-price="{logo_design}">'
            f'<div class="nfc-config-head"><strong>Paketi kendine göre hesapla</strong>'
            f'<small>Ek hizmete tıkla. Seçili toplam anında yenilenir.</small></div>'
            f'<div class="nfc-config-options">'
            f'<button type="button" data-package-option="qr" aria-pressed="false"><span>QR sistemi</span>'
            f'<b>+{money(qr_cost)}</b><small>{qr_count} QR · {money(qr_unit)} / QR</small></button>'
            f'<button type="button" data-package-option="menu" aria-pressed="false"><span>Menü Tasarımı</span>'
            f'<b>+{money(menu_design)}</b><small>{esc(menu_scope_copy)}</small></button>'
            f'<button type="button" data-package-option="logo" aria-pressed="false"><span>Logo Tasarımı</span>'
            f'<b>+{money(logo_design)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button>'
            f'</div>'
            f'<div class="nfc-config-total"><span>Seçili toplam</span>'
            f'<strong data-package-total>{money(base_price)}</strong>'
            f'<small data-package-breakdown>NFC paket bedeli dahil · Ek hizmet seçilmedi</small></div>'
            f'<a class="{cta_class}" data-package-offer href="../teklif/?tur=nfc&amp;paket={code}">{esc(label)} için teklif al</a>'
            f'</div>'
        )

    media_settings = nfc_media_settings()
    saved_themes = nfc_family_theme_settings()
    theme_overrides = theme_overrides if isinstance(theme_overrides, dict) else {}

    def family_theme(key, fallback='light'):
        base = 'dark' if str(fallback).lower() == 'dark' else 'light'
        override = str(theme_overrides.get(key) or '').strip().lower()
        if override in ('light', 'dark'):
            return override
        saved = str(saved_themes.get(key) or '').strip().lower()
        if saved in ('light', 'dark'):
            return saved
        row = media_settings.get(key) if isinstance(media_settings.get(key), dict) else {}
        return 'dark' if str(row.get('theme') or base).strip().lower() == 'dark' else 'light'

    def family_card_attrs(key, fallback='light'):
        return 'nfc-family-card', family_theme(key, fallback)

    restaurant_media = render_nfc_family_media('restaurant_packages', 'Restoran paket görseli', 'BG Studio NFC standart restoran sistemleri')
    quick_media = render_nfc_family_media('quick_stand', 'Hızlı stand görseli', 'BG Studio NFC Hızlı Bağlantı Standı')
    feedback_media = render_nfc_family_media('feedback_duo', 'Premium Feedback Duo görseli', 'BG Studio NFC Premium Feedback Duo müşteri deneyimi sistemi')
    restaurant_class, restaurant_theme = family_card_attrs('restaurant_packages', 'light')
    quick_class, quick_theme = family_card_attrs('quick_stand', 'light')
    feedback_class, feedback_theme = family_card_attrs('feedback_duo', 'dark')

    channels = ''.join(f'<span>{esc(x)}</span>' for x in [
        'Google Yorum','Tripadvisor','Instagram','Facebook','WhatsApp','TikTok','X','YouTube','LinkedIn','Pinterest','Threads','Telegram','Snapchat','Web sitesi','Diğer bağlantılar'
    ])
    feedback_topics = ''.join(f'<span>{x}</span>' for x in ['Yemek','Servis','Ekip','İçecek / Bar','Tavsiye'])

    return f'''<!-- NFC_PLATFORM_V161_START -->
<section class="page-hero nfc-platform-hero"><div class="shell page-hero-grid reveal"><div><p class="eyebrow">BG STUDIO NFC İŞLETME PLATFORMU</p><h1>Bir etiketten fazlası. İşletmen için dijital altyapı.</h1><p class="lead">BG Studio NFC; işletmeye özel fiziksel standları, NFC ve isteğe bağlı QR erişimini, müşteri etkileşimlerini, dijital menüyü, değerlendirme akışını, analitikleri ve yönetim panelini tek altyapıda birleştirir.</p><div class="hero-actions"><a class="primary-cta" href="../teklif/?tur=nfc">İşletmen için teklif al ↗</a><a class="secondary-cta" href="#urun-aileleri">Çözümleri incele ↓</a></div></div><aside class="info-panel info-panel-dark nfc-platform-metrics"><p class="eyebrow">TEK SİSTEMDE</p><div class="metric-grid"><div class="metric"><strong>Fiziksel</strong><span>İşletmeye özel 3D stand</span></div><div class="metric"><strong>Dijital</strong><span>Menü, feedback ve bağlantılar</span></div><div class="metric"><strong>Panel</strong><span>İşletme müşteri paneli</span></div><div class="metric"><strong>Analitik</strong><span>Stand / masa bazlı performans</span></div></div></aside></div></section>
<!-- NFC_REFERENCE_SLOT -->
<section class="section-pad-sm nfc-stand-schema" id="stand-semasi" data-nfc-stand-schema data-nfc-stand-schema-version="3.1.61"><div class="shell"><div class="split-title nfc-stand-schema-heading"><div><p class="eyebrow">STAND YAPISI</p><h2>Tek stand üzerinde tüm erişim noktaları.</h2></div><p>Logo, QR alanları, uygulama ikonları ve NFC temas bölgeleri işletmenize özel tasarlanır. Restoran sistemlerinde arka yüz her masa için numaralandırılabilir.</p></div><figure class="nfc-stand-schema-figure zoomable-media" tabindex="0" role="button" aria-label="BG Studio NFC stand şemasını büyüt"><img src="../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC restoran stand şeması; işletmeye özel logo, menü, Google ve sosyal medya QR alanları, NFC temas bölgeleri ve arka yüzde masa numarası gösterimi" width="1254" height="1254" loading="lazy" decoding="async"><figcaption><span>Büyütmek için görsele dokun veya tıkla</span></figcaption></figure><div class="nfc-stand-schema-points"><article><span>01</span><div><strong>İşletmeye özel kimlik</strong><p>Logo ve fiziksel stand görünümü işletmeye göre hazırlanır.</p></div></article><article><span>02</span><div><strong>QR erişim alanları</strong><p>Menü, Google ve sosyal medya hedefleri QR ile de erişilebilir.</p></div></article><article><span>03</span><div><strong>NFC temas noktaları</strong><p>Telefonu temas alanına yaklaştıran misafir ilgili dijital hedefe geçer.</p></div></article><article><span>04</span><div><strong>Masa numaralı arka yüz</strong><p>Restoran kurulumunda her standın arka yüzü masa numarasına göre ayrıştırılabilir.</p></div></article></div><div class="nfc-stand-schema-actions"><a class="secondary-cta" href="#restoran-sistemleri">Paketleri incele ↓</a><a class="primary-cta" href="../teklif/?tur=nfc">İşletmen için teklif al ↗</a></div></div></section>
<section class="tech-stage nfc-system-chain"><div class="shell reveal"><div class="split-title"><h2>Fiziksel temas noktasından işletme verisine.</h2><p>NFC veya QR yalnızca erişim katmanıdır. Hedef yönetimi, müşteri akışları, geri bildirim, analitik ve raporlama BG Studio NFC altyapısında devam eder.</p></div><div class="flow"><article class="flow-card"><span>01</span><h3>Özel 3D stand</h3><p>Logo, renk ve kullanım senaryosuna göre tasarlanır ve üretilir.</p></article><article class="flow-card"><span>02</span><h3>NFC / QR erişimi</h3><p>Bağımsız hedeflere veya işletme uygulamasına hızlı erişim sağlar.</p></article><article class="flow-card"><span>03</span><h3>Panel <span class="plain-amp">&amp;</span> otomasyon</h3><p>Menü, feedback, bildirim, bağlantı ve müşteri akışları yönetilir.</p></article><article class="flow-card"><span>04</span><h3>Analitik <span class="plain-amp">&amp;</span> rapor</h3><p>Kullanım ve performans verileri işletme bazında izlenir.</p></article></div></div></section>
<section class="section-pad-sm shell reveal nfc-product-families" id="urun-aileleri"><div class="split-title nfc-family-heading"><div><p class="eyebrow">3 ANA İŞLETME ÇÖZÜMÜ</p><h2>İhtiyaca göre ayrı ürün sistemleri.</h2></div><p>Standart Restoran Sistemleri, Hızlı Bağlantı Standı ve Premium Feedback Duo birbirinin alt paketi değildir. Her biri farklı işletme ihtiyacına göre konumlanır.</p></div><div class="nfc-family-grid">
<article class="{restaurant_class}" data-family-theme="{restaurant_theme}">{restaurant_media}<div class="nfc-family-copy"><p class="eyebrow">01 · STANDART RESTORAN SİSTEMLERİ</p><h3>Restoran altyapısı</h3><p>Başlangıç, Profesyonel, Premium ve yüksek kapasiteli Özel Restoran Hazır Paketleri. Her masada 3 NFC; Akıllı Menü, panel, analitik ve işletme otomasyonu aynı sistem çekirdeğinde çalışır.</p><div class="nfc-family-tags"><span>3 NFC / masa</span><span>Başlangıç · Profesyonel · Premium</span><span>Özel Restoran Hazır Paketleri</span><span>QR opsiyonel</span></div><div class="nfc-family-price"><small>{year} başlangıç</small><strong>{money(pack('baslangic').get('price'))}</strong></div><a class="secondary-cta" href="#restoran-sistemleri">Restoran paketlerini incele</a></div></article>
<article class="{quick_class}" data-family-theme="{quick_theme}">{quick_media}<div class="nfc-family-copy"><p class="eyebrow">02 · HIZLI BAĞLANTI STANDI</p><h3>3 bağımsız NFC hedefi</h3><p>Menü altyapısına ihtiyaç duymayan işletmeler için üç farklı bağlantıyı tek, işletmeye özel stand üzerinde birleştirir.</p><div class="nfc-family-tags"><span>3 NFC / stand</span><span>QR opsiyonel</span><span>Logo tasarımı opsiyonel</span><span>Menü sistemi yok</span></div><div class="nfc-family-price"><small>{year} başlangıç</small><strong>{money(quick_price)}</strong></div><a class="secondary-cta" href="#hizli-stand">Hızlı Standı incele</a></div></article>
<article class="{feedback_class}" data-family-theme="{feedback_theme}">{feedback_media}<div class="nfc-family-copy"><p class="eyebrow">03 · PREMIUM FEEDBACK DUO</p><h3>Müşteri deneyimi sistemi</h3><p>5 sorulu işletme içi feedback, Google değerlendirme devam akışı ve seçilebilir sosyal / iletişim hedefini aynı fiziksel standda birleştirir.</p><div class="nfc-family-tags"><span>2 NFC / stand</span><span>5 sorulu feedback</span><span>Google devam akışı</span><span>10–120 stand hazır kapasite</span></div><div class="nfc-family-price"><small>{year} başlayan kurulum</small><strong>{money(duo_start_price)}</strong></div><a class="secondary-cta" href="#premium-feedback-duo">Premium Feedback Duo'yu incele</a></div></article>
</div></section>

<section class="section-pad-sm shell reveal nfc-packages" id="restoran-sistemleri"><div class="split-title nfc-package-heading"><div><p class="eyebrow">01 · STANDART RESTORAN SİSTEMLERİ</p><h2>Aynı restoran altyapısı. Farklı kapasite.</h2></div><p>Başlangıç, Profesyonel ve Premium aynı BG Studio NFC sistemini kullanır. Ana fark masa / stand ve NFC kapasitesidir. QR, Menü Tasarımı ve Logo Tasarımı isteğe bağlıdır.</p></div>
<div class="package-grid package-grid-detailed nfc-capacity-packages">
<article class="package package-detailed"><div class="package-head"><span class="package-kicker">10 MASA · 30 NFC</span><span class="package-badge">Başlangıç</span></div><h3>Başlangıç</h3><p>10 masaya kadar restoranlar için BG Studio NFC işletme altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('baslangic').get('price'))}</strong><span>{normal_and_renewal('baslangic')}</span></div><div class="package-capacity"><span><b>10</b>Masa</span><span><b>30</b>NFC</span><span><b>30</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>10 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Masa bazlı kullanım analitiği</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Garson Çağır + Hesap İste seçeneği</li><li>Bildirim / push altyapısı</li><li>Uzaktan sistem yönetimi</li></ul>{restaurant_option_picker('baslangic','Başlangıç',10,30,'secondary-cta')}</article>
<article class="package package-detailed featured"><div class="package-head"><span class="package-kicker">15 MASA · 45 NFC</span><span class="package-badge">Öne çıkan</span></div><h3>Profesyonel</h3><p>15 masalık restoranlar için 45 NFC erişim noktası, dijital menü, panel ve analitik altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('profesyonel').get('price'))}</strong><span>{normal_and_renewal('profesyonel')}</span></div><div class="package-capacity"><span><b>15</b>Masa</span><span><b>45</b>NFC</span><span><b>45</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>15 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Masa bazlı kullanım analitiği</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Garson Çağır + Hesap İste seçeneği</li><li>Bildirim / push altyapısı</li><li>Uzaktan sistem yönetimi</li></ul>{restaurant_option_picker('profesyonel','Profesyonel',15,45,'primary-cta')}</article>
<article class="package package-detailed"><div class="package-head"><span class="package-kicker">20 MASA · 60 NFC</span><span class="package-badge">Premium</span></div><h3>Premium</h3><p>20 masalık restoranlar için 60 NFC erişim noktası ve BG Studio NFC platformunun tam restoran altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('premium').get('price'))}</strong><span>{normal_and_renewal('premium')}</span></div><div class="package-capacity"><span><b>20</b>Masa</span><span><b>60</b>NFC</span><span><b>60</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>20 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Detaylı masa bazlı analitik</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Garson Çağır + Hesap İste seçeneği</li><li>Bildirim / push altyapısı</li><li>Uzaktan sistem yönetimi</li></ul>{restaurant_option_picker('premium','Premium',20,60,'secondary-cta')}</article>
</div>
<div class="nfc-package-rule"><strong>QR sistemi restoran paketlerine zorunlu dahil değildir.</strong><span>Her masa 3 NFC erişim noktasıyla gelir. QR tercih edilirse masa başına 3 QR eklenir. Menü Tasarımı ve Logo Tasarımı da ayrı opsiyonel kalemlerdir.</span></div>

<div class="restaurant-common-platform"><div class="restaurant-common-head"><div><p class="eyebrow">TÜM STANDART RESTORAN PAKETLERİNDE MEVCUT</p><h3>Mevcut restoran altyapısı tüm kapasitelerde devam eder.</h3></div><p>Başlangıç, Profesyonel, Premium ve 25–120 masa Özel Restoran Hazır Paketleri aynı sistem çekirdeğini kullanır. Premium Plus bu kapsamın yerine geçmez.</p></div><div class="restaurant-common-grid"><article><h4>Akıllı Menü</h4><ul><li>Akıllı Menü ve çoklu dil altyapısı</li><li>Türkçe + İngilizce görsel menü</li><li>8 ek dilde dijital metin menü</li><li>Ürün içerikleri</li><li>14 alerjen bilgi katmanı</li><li>Yaklaşık kalori bilgileri</li></ul></article><article><h4>Değerlendirme & Google</h4><ul><li>Müşteri değerlendirme sistemi</li><li>Google değerlendirme devam akışı</li><li>Google puan ve yorum performansı</li><li>Sosyal medya / iletişim yönlendirmeleri</li></ul></article><article><h4>Panel & Analitik</h4><ul><li>İşletme müşteri paneli</li><li>Masa ve alan bazlı kullanım analitikleri</li><li>Bildirim / push altyapısı</li><li>Uzaktan sistem yönetimi</li></ul></article><article class="restaurant-common-accent"><h4>Servis Talepleri</h4><ul><li>Garson Çağır</li><li>Hesap İste</li><li>Talebin masa / alan bilgisiyle panele düşmesi</li><li>İşletme bazında aktif / pasif yönetim</li></ul><p>Garson Çağır + Hesap İste, Premium Plus avantajı değildir. Tüm Standart Restoran paketlerinin mevcut ortak özelliğidir.</p></article></div></div>

<div class="special-ready-card"><div class="special-ready-copy"><p class="eyebrow">ÖZEL RESTORAN HAZIR PAKETLERİ</p><h3>Yüksek kapasitede restoran altyapısı.</h3><p>20 masanın üzerindeki restoranlarda aynı Standart Restoran altyapısı işletmenin kapasitesine göre ölçeklenir. Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ve Garson Çağır + Hesap İste mevcut kapsamda devam eder. Masa sayını seç; NFC paket bedeli, QR hesabı ve ek tasarım hizmetleri sağdaki kartta anında hesaplansın.</p><div class="special-ready-tags"><span>Akıllı Menü + çoklu dil</span><span>14 alerjen + yaklaşık kalori</span><span>Google performansı + değerlendirme</span><span>Garson Çağır + Hesap İste</span></div><div class="nfc-capacity-selector-head"><strong>Masa sayını seç</strong><span>Aşağıdaki kartlardan birine tıkla. Sağdaki hesap anında yenilenir.</span></div><div class="nfc-capacity-chips" role="group" aria-label="Özel Restoran hazır masa kapasitesi">{capacity_chips}</div></div><div class="special-ready-highlight" data-special-package-calculator data-qr-unit="{qr_unit}" data-menu-price="{menu_design}" data-logo-price="{logo_design}"><span class="package-kicker" data-special-title>GÜNCEL {special_default_key} MASA HAZIR PAKETİ</span><div class="special-ready-metrics"><span><b data-special-tables>{special_default_key}</b>Masa</span><span><b data-special-nfc>{special_qr_count}</b>NFC</span></div><div class="special-ready-price"><small data-special-price-year>{year} NFC hazır paket bedeli</small><strong data-special-base-price>{money(special_default.get('price'))}</strong><span data-special-renewal>Yıllık yenileme: {money(special_default.get('renewal'))}</span></div><div class="special-ready-options"><button type="button" data-special-option="qr" aria-pressed="false"><span>QR sistemi</span><b data-special-qr-cost>+{money(special_qr_cost)}</b><small data-special-qr-copy>{special_qr_count} QR × {money(qr_unit)} / QR</small></button><button type="button" data-special-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b data-special-menu-cost>+{money(menu_design)}</b><small>{esc(menu_scope_copy)}</small></button><button type="button" data-special-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b data-special-logo-cost>+{money(logo_design)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button></div><div class="special-ready-breakdown"><div><span>NFC hazır paket</span><b data-special-line-base>{money(special_default.get('price'))}</b></div><div><span>QR sistemi</span><b data-special-line-qr>Seçilmedi</b></div><div><span>Menü Tasarımı</span><b data-special-line-menu>Seçilmedi</b></div><div><span>Logo Tasarımı</span><b data-special-line-logo>Seçilmedi</b></div></div><div class="special-ready-total"><span>Seçili toplam</span><strong data-special-total>{money(special_default.get('price'))}</strong><small>NFC paket bedeli + seçtiğin ek hizmetler</small></div><a class="secondary-cta" data-special-offer href="../teklif/?tur=nfc&amp;paket=ozel-kapasite&amp;masa={special_default_key}">{special_default_key} masa için teklifi al</a></div></div>
</section>

<section class="section-pad-sm shell premium-plus-teaser" id="premium-plus" data-premium-plus-roadmap="3.1.61" aria-labelledby="premium-plus-title"><div class="premium-plus-shell"><div class="premium-plus-head"><div class="premium-plus-copy"><p class="eyebrow">YAKINDA</p><h2 id="premium-plus-title">Premium Plus</h2><p>Mevcut Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ile Garson Çağır + Hesap İste özellikleri tüm Standart Restoran paketlerinde devam eder.</p><p>Premium Plus bunların üzerine doğrudan masa siparişi, Akıllı Misafir Profili ve CRM, sadakat sistemi, rezervasyon / masa yönetimi ve AI destekli müşteri deneyimi araçlarını ekleyen gelişmiş üst katman olarak konumlandırılacaktır.</p></div><div class="premium-plus-state" aria-label="Premium Plus ürün durumu"><span class="premium-plus-badge">YAKINDA</span><span class="premium-plus-progress">Geliştiriliyor</span><small>Henüz satışta değil</small></div></div><div class="premium-plus-roadmap-head"><div><p class="eyebrow">YAKINDA GELECEK ÖZELLİKLER</p><h3>Restoran deneyiminin bir sonraki katmanı.</h3></div><p>Özellik başlığına tıklayarak planlanan kapsamın ayrıntısını görebilirsin.</p></div><div class="premium-plus-grid">
<details class="premium-plus-feature"><summary><span class="premium-plus-no">01</span><div><h4>NFC dijital menüden masaya doğrudan sipariş oluşturma</h4><p>Müşteri, Akıllı Menü üzerinden seçimini doğrudan bulunduğu masadan iletebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Müşteri Akıllı Menü içerisinden ürünlerini seçerek siparişi doğrudan bulunduğu masadan işletmeye iletebilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">02</span><div><h4>Soğansız gibi müşteri notlarını masa siparişine ekleme</h4><p>Siparişe ürün tercihi ve özel talepler eklenebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Müşteri siparişine:</p><ul><li>Soğansız</li><li>Acısız</li><li>Buzsuz</li><li>Ekstra sos</li><li>Pişirme tercihi</li><li>veya özel not</li></ul><p>gibi talepler ekleyebilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">03</span><div><h4>Akıllı Misafir Profili ve CRM</h4><p>İzinli müşteri ilişkileri tek misafir profili altyapısında yönetilebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>İşletmenin izinli müşteri ilişkilerini tek noktada yönetebilmesini sağlayacak gelişmiş misafir profili altyapısı.</p><p>Sistem ileride ziyaret geçmişi, müşteri tercihleri ve işletmeyle olan etkileşimleri kullanarak daha kişiselleştirilmiş müşteri deneyimi sunabilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">04</span><div><h4>Sadakat, puan ve ziyaret ödülleri</h4><p>İşletme kendi sadakat ve ziyaret ödülü kurgusunu yönetebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>İşletmeler kendi sadakat sistemlerini oluşturabilecek.</p><p>Örnek kullanım:</p><ul><li>5 ziyaret sonrası ödül</li><li>10 ziyaret sonrası özel avantaj</li><li>Puan biriktirme</li><li>Ziyaret bazlı ödül</li><li>İşletmeye özel kampanya veya ayrıcalık</li></ul></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">05</span><div><h4>VIP ve tekrar gelen misafir tanıma</h4><p>İzinli kullanıcılar üzerinden tekrar gelen misafirler ayrıştırılabilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Sistem izinli kullanıcılar üzerinden tekrar gelen misafirleri tanıyabilecek.</p><p>Örnek segmentler:</p><ul><li>İlk kez gelen</li><li>Tekrar gelen</li><li>Sadık misafir</li><li>VIP misafir</li></ul></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">06</span><div><h4>Otomatik segmentler ve geri kazanım</h4><p>Davranışlara göre müşteri segmentleri ve geri kazanım grupları tanımlanabilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>İşletme müşterileri davranışlarına göre segmentleyebilecek.</p><p>Örnekler:</p><ul><li>30 gündür ziyaret etmeyen müşteriler</li><li>3 veya daha fazla kez gelen müşteriler</li><li>VIP müşteriler</li><li>Yüksek memnuniyet bırakan müşteriler</li><li>Geri kazanılması hedeflenen müşteriler</li></ul><p>Bu segmentler gelecekte işletmeye özel kampanya ve müşteri geri kazanım akışlarında kullanılabilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">07</span><div><h4>Rezervasyon, bekleme listesi ve masa yönetimi</h4><p>Ön salon ve masa operasyonları tek akışta yönetilebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Premium Plus kapsamında gelecekte:</p><ul><li>Online rezervasyon</li><li>Walk-in müşteri kaydı</li><li>Dijital bekleme listesi</li><li>Rezervasyon durumu</li><li>Masa hazır bilgisi</li><li>Müşterinin masaya alınması</li><li>Rezervasyon tamamlandı / gelmedi durumu</li></ul><p>gibi ön salon ve masa operasyon araçları geliştirilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">08</span><div><h4>AI ürün eşleştirme ve akıllı upsell</h4><p>Akıllı Menü seçilen ürüne göre tamamlayıcı öneriler sunabilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Akıllı Menü müşterinin seçtiği ürüne göre tamamlayıcı ürünler önerebilecek.</p><p>Örnek:</p><ul><li>“Bu ürünle birlikte en çok tercih edilenler”</li><li>“Şefin önerisi”</li><li>“Menünü tamamla”</li><li>“Ana yemeğinin yanında bunu da deneyebilirsin”</li></ul><p>İşletme gerektiğinde öneri ilişkilerini manuel olarak da yönetebilecek.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">09</span><div><h4>AI günlük yönetici özeti</h4><p>İşletme verileri sade günlük özet ve kısa aksiyon önerilerine dönüşebilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Sistem işletme verilerini sade bir günlük özet halinde yöneticinin önüne getirebilecek.</p><p>Örnek:</p><ul><li>Bugünkü NFC etkileşimleri</li><li>Yeni müşteri değerlendirmeleri</li><li>Google performansındaki değişimler</li><li>Memnuniyet kategorilerindeki yükseliş / düşüşler</li><li>Yoğun etkileşim alanları</li><li>Tekrar gelen misafirler</li><li>Dikkat edilmesi gereken müşteri deneyimi sinyalleri</li></ul><p>ve bunlara göre kısa aksiyon önerileri.</p></div></details>
<details class="premium-plus-feature"><summary><span class="premium-plus-no">10</span><div><h4>Gelişmiş modüllerde öncelikli erişim</h4><p>Yeni CRM, sadakat, rezervasyon ve AI modüllerinde öncelikli kapsama alınabilecek.</p></div><span class="premium-plus-toggle" aria-hidden="true"></span></summary><div class="premium-plus-feature-body"><p>Premium Plus kullanıcıları gelecekte geliştirilecek ileri seviye CRM, sadakat, rezervasyon, müşteri deneyimi ve AI modüllerinde öncelikli kapsama alınabilecek.</p></div></details>
</div><div class="premium-plus-note-group"><p class="premium-plus-note"><strong>Premium Plus mevcut paket özelliklerini yeniden paketlemez.</strong> Garson Çağır + Hesap İste zaten tüm Standart Restoran paketlerinin mevcut kapsamındadır. Premium Plus; NFC menüden doğrudan sipariş, müşteri sipariş notları, Akıllı Misafir Profili ve CRM, sadakat ve ziyaret ödülleri, VIP / tekrar gelen misafir tanıma, otomatik müşteri segmentleri, geri kazanım kampanyaları, rezervasyon ve dijital bekleme listesi, AI ürün önerileri ve AI yönetici özetleri için geliştirilen ayrı bir üst katmandır.</p><p class="premium-plus-release-note">Çıkış tarihi, kesin özellik kapsamı ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="premium-plus-footer"><span class="premium-plus-follow">Premium Plus gelişmelerini takip et</span><span class="premium-plus-coming">YAKINDA</span></div></div></section>

<section class="section-pad-sm shell reveal solution-detail solution-quick" id="hizli-stand"><div class="solution-heading"><div><p class="eyebrow">02 · BAĞIMSIZ İŞLETME ÇÖZÜMÜ</p><h2>Hızlı Bağlantı Standı</h2><p>Menü altyapısına ihtiyaç duymayan işletmeler için üç bağımsız NFC hedefini tek, işletmeye özel tasarım stand üzerinde birleştiren hızlı bağlantı çözümü.</p></div><div class="solution-price-stack"><small>{year} başlangıç fiyatı</small><strong>{money(quick_price)}</strong><span>{money(quick_renewal)} yıllık yenileme</span><em>3 NFC / stand</em></div></div>
<div class="solution-two-col"><div class="solution-panel"><h3>Tek stand, üç bağımsız hedef.</h3><p>Her NFC alanı ayrı bir bağlantıya yönlendirilebilir ve hedefler uzaktan değiştirilebilir.</p><div class="channel-cloud">{channels}</div><div class="solution-feature-list"><span>1 özel tasarım fiziksel stand</span><span>Stand başına 3 NFC</span><span>İşletme müşteri paneli</span><span>NFC / QR okutma analitiği</span><span>Google performans takibi</span><span>Uzaktan hedef yönetimi</span></div></div><div class="solution-panel solution-panel-accent"><h3>Opsiyonlar ve liste hesabı</h3><div class="quick-option-summary"><div><span>QR sistemi</span><strong>3 QR · +{money(quick_qr_cost)}</strong><small>{year}: 3 × {money(qr_unit)}</small></div><div><span>Logo Tasarımı</span><strong>+{money(logo_design)}</strong><small>{year} liste bedeli</small></div><div class="disabled-option"><span>Menü Tasarımı</span><strong>Bulunmaz</strong><small>Hızlı Stand menü sistemi içermez.</small></div></div><details class="solution-details"><summary>{year} örnek liste hesaplarını gör</summary><div class="quick-price-examples"><div><span>Sadece Hızlı Stand</span><b>{money(quick_price)}</b></div><div><span>Hızlı Stand + QR</span><b>{money(quick_with_qr)}</b></div><div><span>Hızlı Stand + Logo Tasarımı</span><b>{money(quick_with_logo)}</b></div><div><span>Hızlı Stand + QR + Logo Tasarımı</span><b>{money(quick_full)}</b></div></div><p>Bunlar liste fiyatlarıdır. İşletmeye özel teklif uygulanabilir.</p></details><div class="future-rate"><span>2027 QR opsiyonu: 3 × {money(qr_2027)} = <b>+{money(qr_2027*3)}</b></span><span>2027 Logo Tasarımı: <b>{money(logo_2027)}</b></span></div></div></div>
<div class="solution-actions"><a class="primary-cta" href="../teklif/?tur=nfc&amp;paket=hizli-stand">Hızlı Stand için teklif al ↗</a><a class="text-cta" href="#referans-koala-petshop">Koala Petshop saha referansını gör ↓</a></div></section>

<section class="section-pad-sm shell reveal solution-detail solution-feedback" id="premium-feedback-duo"><div class="solution-heading"><div><p class="eyebrow">03 · BAĞIMSIZ İŞLETME ÇÖZÜMÜ</p><h2>Premium Feedback Duo</h2><p>Müşteri geri bildirimini, Google değerlendirme devam akışını ve işletmenin seçtiği sosyal / iletişim bağlantısını aynı fiziksel stand üzerinde birleştiren gelişmiş müşteri deneyimi sistemi.</p></div><div class="solution-price-stack dark"><small>{year} başlayan kurulum</small><strong>{money(duo_start_price)}</strong><span>{money(duo_start_renewal)}'den başlayan yıllık yenileme</span><em>2 NFC / stand · 10–120 stand</em></div></div>
<div class="feedback-duo-flow"><article><span class="flow-no">NFC 1</span><h3>5 sorulu işletme içi değerlendirme</h3><p>Müşteri önce BG Studio feedback akışına alınır. Serbest görüşünü de bırakabilir; sonuç işletmenin müşteri paneline düşer ve ardından Google değerlendirme adımına devam edebilir.</p><div class="feedback-topic-chips">{feedback_topics}</div></article><article><span class="flow-no">NFC 2</span><h3>Seçilebilir sosyal / iletişim hedefi</h3><p>İkinci NFC Instagram'a sabit değildir. İşletmenin ihtiyacına göre sosyal medya, iletişim veya web hedeflerinden biri seçilir ve uzaktan yönetilebilir.</p><div class="channel-cloud compact">{channels}</div></article></div>
<div class="feedback-feature-grid"><article><h4>Müşteri deneyimi</h4><ul><li>İşletmeye özel fiziksel standlar</li><li>5 sorulu Feedback sistemi</li><li>Serbest müşteri görüşü</li><li>Google değerlendirme devam akışı</li><li>Seçilebilir sosyal / iletişim bağlantısı</li></ul></article><article><h4>Panel ve analitik</h4><ul><li>İşletme müşteri paneli</li><li>Stand bazlı NFC okutma analitiği</li><li>Feedback performans analitiği</li><li>Google puanı ve yorum performansı</li></ul></article><article><h4>Bildirim ve rapor</h4><ul><li>Bildirim Merkezi</li><li>Push bildirim altyapısı</li><li>Haftalık performans raporu</li><li>Genel işletme raporları</li></ul></article><article><h4>Yıllık haklar</h4><ul><li>2 sosyal / iletişim bağlantısı güncellemesi</li><li>1 işletme değerlendirme bağlantısı güncellemesi</li><li>Uzaktan bağlantı yönetimi</li><li>BG Studio yönetim altyapısı</li></ul></article></div>
<div class="feedback-price-summary"><div><span><b>2 NFC</b> / stand</span><span><b>{first_duo.get('stands',10)} stand / {first_duo.get('nfc',20)} NFC</b>'den başlayan hazır çözümler</span><span><b>{money(duo_start_price)}</b>'den başlayan kurulum</span><span><b>{money(duo_start_renewal)}</b>'den başlayan yıllık yenileme</span><span><b>10–120 stand</b> hazır kapasite</span></div></div>
<details class="feedback-pricing-details" id="feedback-fiyatlari"><summary><span>Tüm kapasite ve fiyatları gör</span><b>21 hazır kapasite</b></summary><div class="feedback-pricing-body"><div class="feedback-price-table-wrap"><table class="feedback-price-table"><thead><tr><th>Stand</th><th>NFC</th><th>Kurulum / Satış</th><th>Yıllık Yenileme</th></tr></thead><tbody>{duo_table_rows}</tbody></table></div><div class="feedback-price-mobile">{duo_mobile_cards}</div><p class="feedback-price-note">Hazır kapasiteler dışında işletmeye özel adet ve anlaşmalı fiyatlandırma yapılabilir.</p></div></details>
<p class="renewal-explain">Yıllık yenileme; müşteri paneli, feedback sistemi, analizler, bildirim / push altyapısı, raporlama ve sistem hizmetlerinin devam bedelidir.</p><div class="solution-actions"><a class="primary-cta" href="../teklif/?tur=nfc&amp;paket=feedback-duo&amp;masa={first_duo.get('stands',10)}">Premium Feedback Duo için teklif al ↗</a></div></section>

<section class="section-pad-sm shell reveal solution-compare"><div class="split-title"><div><p class="eyebrow">HANGİ ÇÖZÜM?</p><h2>Hızlı Stand mı, Premium Feedback Duo mu?</h2></div><p>İkisi de bağımsız işletme çözümüdür. Seçim, doğrudan bağlantı mı yoksa gelişmiş müşteri feedback ve raporlama akışı mı gerektiğine göre yapılır.</p></div><div class="compare-grid"><article><p class="eyebrow">HIZLI BAĞLANTI STANDI</p><h3>Doğrudan bağlantı</h3><div class="compare-metrics"><span><b>3 NFC</b>/ stand</span><span><b>{money(quick_price)}</b>başlangıç</span><span><b>{money(quick_renewal)}</b>yenileme</span></div><ul><li>3 bağımsız bağlantı hedefi</li><li>Menü sistemi yok</li><li>QR opsiyonel</li><li>Logo Tasarımı opsiyonel</li><li>İşletme paneli ve okutma analitiği</li></ul></article><article class="dark"><p class="eyebrow">PREMIUM FEEDBACK DUO</p><h3>Feedback + Google + raporlama</h3><div class="compare-metrics"><span><b>2 NFC</b>/ stand</span><span><b>{money(duo_start_price)}</b>başlangıç</span><span><b>{money(duo_start_renewal)}</b>'den yenileme</span></div><ul><li>NFC 1: 5 sorulu feedback + Google devamı</li><li>NFC 2: seçilebilir sosyal / iletişim hedefi</li><li>Feedback analitiği ve Google performansı</li><li>Bildirim / push altyapısı</li><li>Haftalık raporlama · 10–120 stand</li></ul></article></div></section>

<section class="section-pad-sm shell reveal nfc-platform-block-wrap"><div class="nfc-platform-block"><div class="nfc-platform-title"><div><p class="eyebrow">BG STUDIO NFC YÖNETİM ALTYAPISI</p><h3>Fiziksel ürünün arkasında çalışan sistem.</h3></div><p>Çözüme göre özellik seti değişse de işletme paneli, uzaktan hedef yönetimi, analitik ve BG Studio yönetim altyapısı fiziksel standları dijital sisteme bağlar.</p></div><div class="nfc-infra-grid"><article class="nfc-infra-card"><span>01</span><h4>İşletme paneli</h4><p>Kullanım verileri, bildirimler, paket ve sistem durumları tek merkezde takip edilir.</p></article><article class="nfc-infra-card"><span>02</span><h4>Analitik</h4><p>Masa veya stand bazlı NFC / QR etkileşimleri çözüm tipine göre raporlanır.</p></article><article class="nfc-infra-card"><span>03</span><h4>Uzaktan hedef yönetimi</h4><p>Bağlantılar ve dijital hedefler fiziksel ürünü yeniden üretmeden yönetilebilir.</p></article><article class="nfc-infra-card"><span>04</span><h4>Özel tasarım ve üretim</h4><p>Standlar hazır pleksi üstüne etiket yapıştırılan ürünler değildir; tasarım ve 3D üretim işletmeye göre hazırlanır.</p></article></div></div>
<div class="nfc-options"><div class="nfc-options-copy"><p class="eyebrow">OPSİYONEL HİZMETLER</p><h3>Çözümüne göre ekle.</h3><p>QR, Menü Tasarımı ve Logo Tasarımı paket hesabına ayrı eklenir. Restoran kartlarında seçimini yapıp toplamı anında görebilirsin.</p></div><div class="nfc-option-list nfc-option-list-three"><div><span>QR sistemi</span><strong>{money(qr_unit)} / QR</strong><small>Restoranlarda masa başına 3 QR · Hızlı Standda 3 QR</small></div><div><span>Menü Tasarımı</span><strong>{money(menu_design)}</strong><small>Türkçe + İngilizce görsel menü · 8 ek dilde dijital metin menü · ürün içerikleri · 14 alerjen bilgi katmanı · yaklaşık kalori</small></div><div><span>Logo Tasarımı</span><strong>{money(logo_design)}</strong><small>İşletmeye özel logo · fiziksel stand ve dijital menü kullanımına uyumlu</small></div></div></div></section>
<p class="package-footnote shell">Fiyatlar {year} dönemindeki güncel website fiyat yapısını gösterir. İşletme kapsamı, adet ve özel anlaşmalara göre teklif ayrıca netleştirilebilir.</p>
<!-- NFC_PLATFORM_V161_END -->'''

def rebuild_nfc_platform_sections(html_text, theme_overrides=None):
    """Replace public NFC platform/package copy without touching field references."""
    rendered = render_nfc_platform_sections(theme_overrides=theme_overrides)
    marker_pattern = re.compile(
        r'<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156|159|160|161)_START\s*-->.*?<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156|159|160|161)_END\s*-->',
        flags=re.I | re.S,
    )
    if marker_pattern.search(html_text):
        html_text = marker_pattern.sub(rendered, html_text, count=1)
    else:
        start = re.search(r'<section\b[^>]*class="[^"]*page-hero[^"]*"[^>]*>', html_text, flags=re.I)
        ref = re.search(r'<section\b[^>]*class="[^"]*custom-band[^"]*"[^>]*>.*?<h2>\s*Sahada çalışan örnekler\.\s*</h2>', html_text, flags=re.I | re.S)
        if not start or not ref or ref.start() <= start.start():
            raise RuntimeError('NFC platform bölümü güvenli biçimde bulunamadı; referans alanına dokunulmadı.')
        html_text = html_text[:start.start()] + rendered + '\n' + html_text[ref.start():]

    desc = ('BG Studio NFC; Standart Restoran Sistemleri, Hızlı Bağlantı Standı ve Premium Feedback Duo ile '
            'özel 3D stand, NFC/QR, işletme paneli, analitik, feedback ve dijital müşteri akışlarını birleştirir.')
    html_text = re.sub(r'(<meta\s+content=")[^"]*("\s+name="description"\s*/?>)', lambda m: m.group(1)+desc+m.group(2), html_text, count=1, flags=re.I)
    html_text = re.sub(r'(<meta\s+content=")[^"]*("\s+property="og:description"\s*/?>)', lambda m: m.group(1)+desc+m.group(2), html_text, count=1, flags=re.I)
    html_text = re.sub(r'(<meta\s+content=")[^"]*("\s+name="twitter:description"\s*/?>)', lambda m: m.group(1)+desc+m.group(2), html_text, count=1, flags=re.I)
    return html_text


def render_nfc_reference_section(cards_html):
    """Return the entire NFC field-reference section from canonical panel data.

    V3.1.42 intentionally does not trust the cards already present in
    nfc-qr/index.html. A static page patch must never be able to erase newer
    AppData references such as Naz Balık or Yusuf Şef again.
    """
    return (
        '<section class="section-pad custom-band nfc-reference-first" id="sahadan-isler"><div class="shell reveal">'
        '<div class="split-title"><h2>Sahada çalışan örnekler.</h2>'
        '<p>Kurulan her sistem işletmenin masa sayısı, hedef kanalları ve kullanım senaryosuna göre farklılaşır. '
        'Aşağıdaki örnekler sahada uygulanan kurulumlardan seçildi.</p></div>'
        '<div class="case-grid case-grid-managed"><!-- CONTENT_MANAGER:NFC_START -->\n'
        + cards_html +
        '\n<!-- CONTENT_MANAGER:NFC_END --></div></div></section>'
    )


def rebuild_nfc_reference_section(html_text, cards_html):
    """Rebuild public NFC field references as the first content block of the NFC page.

    V3.1.61 keeps the hero first, proof-of-work second and Stand Şeması third on the NFC page. The platform renderer
    recreates a dedicated slot on every build, so stale pages cannot push the
    managed reference cards back to the bottom.
    """
    section = render_nfc_reference_section(cards_html)

    managed_pattern = re.compile(
        r'<section\b[^>]*class="[^"]*custom-band[^"]*"[^>]*>.*?'
        r'<!--\s*CONTENT_MANAGER:NFC_START\s*-->.*?'
        r'<!--\s*CONTENT_MANAGER:NFC_END\s*-->.*?</section>',
        flags=re.I | re.S,
    )
    html_text = managed_pattern.sub('', html_text, count=1)

    heading_pattern = re.compile(
        r'<section\b[^>]*>.*?<h2>\s*Sahada çalışan örnekler\.\s*</h2>.*?</section>',
        flags=re.I | re.S,
    )
    html_text = heading_pattern.sub('', html_text, count=1)

    slot = '<!-- NFC_REFERENCE_SLOT -->'
    if slot in html_text:
        return html_text.replace(slot, section, 1)

    hero_section = re.search(
        r'<section\b[^>]*class="[^"]*page-hero[^"]*nfc-platform-hero[^"]*"[^>]*>.*?</section>',
        html_text,
        flags=re.I | re.S,
    )
    if not hero_section:
        hero_section = re.search(r'<section\b[^>]*class="[^"]*page-hero[^"]*"[^>]*>.*?</section>', html_text, flags=re.I | re.S)
    if hero_section:
        return html_text[:hero_section.end()] + '\n' + section + html_text[hero_section.end():]

    faq_anchor = re.search(r'<section\b[^>]*class="[^"]*nfc-faq[^"]*"', html_text, flags=re.I)
    if faq_anchor:
        return html_text[:faq_anchor.start()] + section + '\n' + html_text[faq_anchor.start():]
    raise RuntimeError('NFC & QR referans bölümü sayfada güvenli konuma yerleştirilemedi.')


def validate_nfc_reference_output(html_text, items):
    """Prove that every active panel record appears once in the NFC section."""
    start = html_text.find('<!-- CONTENT_MANAGER:NFC_START -->')
    end = html_text.find('<!-- CONTENT_MANAGER:NFC_END -->')
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError('NFC & QR: referans build işaretleri bulunamadı.')
    section = html_text[start:end]
    rendered_ids = re.findall(r'data-reference-id="([^"]+)"', section, flags=re.I)
    expected_ids = [reference_identity(item) for item in items]
    if len(rendered_ids) != len(expected_ids):
        raise RuntimeError(
            f'NFC & QR: panelde {len(expected_ids)} aktif kayıt var ancak sayfada {len(rendered_ids)} kart üretildi.'
        )
    if set(rendered_ids) != set(expected_ids):
        missing = [x for x in expected_ids if x not in rendered_ids]
        extra = [x for x in rendered_ids if x not in expected_ids]
        raise RuntimeError(f'NFC & QR: referans eşleşmesi bozuk. Eksik={missing}, fazla={extra}')
    if len(rendered_ids) != len(set(rendered_ids)):
        raise RuntimeError('NFC & QR: aynı referans kartı birden fazla kez üretildi.')


def validate_reference_theme_output(html_text, items, label):
    """Fail the build if a persisted card tone did not reach the generated HTML."""
    for item in items:
        ref_id = reference_identity(item)
        expected = managed_case_theme(item, legacy_alternate=False)
        match = re.search(rf'<article\b[^>]*\bid="referans-{re.escape(ref_id)}"[^>]*>', html_text, flags=re.I)
        if not match:
            raise RuntimeError(f'{label}: {ref_id} kartı build çıktısında bulunamadı.')
        tag = match.group(0)
        if f'data-card-theme="{expected}"' not in tag or f'theme-{expected}' not in tag:
            raise RuntimeError(f'{label}: {ref_id} kart tonu build çıktısına uygulanamadı ({expected}).')



def sync_nfc_offer_schema(html_text, pricing):
    year = str(pricing.get('year') or '2026')
    packages = pricing.get('packages') or {}
    offers = []

    core = [
        ('baslangic', 'Standart Restoran · Başlangıç'),
        ('profesyonel', 'Standart Restoran · Profesyonel'),
        ('premium', 'Standart Restoran · Premium'),
        ('hizli_stand', 'Hızlı Bağlantı Standı'),
    ]
    for key, name in core:
        row = packages.get(key) if isinstance(packages.get(key), dict) else {}
        price = row.get('price')
        if price in (None, ''):
            continue
        offers.append({'@type': 'Offer', 'name': name, 'price': str(int(price)), 'priceCurrency': 'TRY'})

    duo = pricing.get('feedback_duo_packages') if isinstance(pricing.get('feedback_duo_packages'), dict) else {}
    duo10 = duo.get('10') if isinstance(duo.get('10'), dict) else {}
    if duo10.get('price') not in (None, ''):
        offers.append({'@type': 'Offer', 'name': 'Premium Feedback Duo · 10 Stand / 20 NFC', 'price': str(int(duo10['price'])), 'priceCurrency': 'TRY'})

    special = pricing.get('special_restaurant_packages') if isinstance(pricing.get('special_restaurant_packages'), dict) else {}
    ready120 = special.get('120') if isinstance(special.get('120'), dict) else {}
    if ready120.get('price') not in (None, ''):
        offers.append({'@type': 'Offer', 'name': 'Özel Restoran Hazır Paketi · 120 Masa / 360 NFC', 'price': str(int(ready120['price'])), 'priceCurrency': 'TRY'})

    schema = {
        '@context': 'https://schema.org',
        '@type': 'Service',
        'name': 'BG Studio NFC & QR İşletme Sistemleri',
        'provider': {'@type': 'LocalBusiness', 'name': 'BG Studio 3D', 'url': 'https://3d.bgstudio.com.tr/'},
        'areaServed': 'Türkiye',
        'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': f'{year} NFC & QR İşletme Çözümleri', 'itemListElement': offers},
    }
    script = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(',', ':')) + '</script>'
    pattern = re.compile(r'<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"Service","name":"BG Studio NFC.*?</script>', flags=re.S)
    if pattern.search(html_text):
        return pattern.sub(script, html_text, count=1)
    return html_text


def verify_v3164_public_shell(include_home=True, include_catalog=True):
    """Fail loudly if a public page misses the V3.1.72 public shell."""
    failures = []
    checked = 0
    for html_path in ROOT.rglob('*.html'):
        rel_parts = html_path.relative_to(ROOT).parts
        if 'tools' in rel_parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'site-header' not in text:
            continue
        checked += 1
        rel = html_path.relative_to(ROOT).as_posix()
        required = (
            'data-bg-nav="v3.1.72"',
            '>Üretim</button>',
            '>İşletmeler</button>',
            '>Projeler</a>',
            '>BG Studio</button>',
            f'assets/js/navigation.js?v={SITE_ASSET_VERSION}',
        )
        missing = [token for token in required if token not in text]
        if include_home and html_path == ROOT / 'index.html':
            home_required = (
                'class="home-v3163"',
                'Fikirden fiziksel ürüne.',
                'id="sahadan-isler"',
                f'assets/js/homepage.js?v={SITE_ASSET_VERSION}',
            )
            missing.extend(token for token in home_required if token not in text)
        if include_catalog and html_path == ROOT / 'urunler' / 'index.html':
            catalog_required = (
                'data-catalog-v3164',
                'id="catalog-sort"',
                'data-catalog-flag="featured"',
                'data-catalog-flag="personalizable"',
                f'assets/js/catalog.js?v={SITE_ASSET_VERSION}',
            )
            missing.extend(token for token in catalog_required if token not in text)
        if rel.startswith('nfc-qr/'):
            nfc_required = (f'assets/js/nfc-hub.js?v={SITE_ASSET_VERSION}',)
            if rel in ('nfc-qr/restoran/index.html','nfc-qr/hizli-baglanti/index.html','nfc-qr/feedback/index.html','nfc-qr/premium-plus/index.html'):
                nfc_required += ('data-nfc-hub-v3167="subpage"',)
            missing.extend(token for token in nfc_required if token not in text)
        if rel.startswith('projeler/'):
            project_required = (f'assets/js/projects.js?v={SITE_ASSET_VERSION}', 'data-projects-v3168')
            missing.extend(token for token in project_required if token not in text)
        if rel == 'teklif/index.html':
            quote_required = ('data-quote-form', f'assets/js/quote-center.js?v={SITE_ASSET_VERSION}', 'Ne için teklif istiyorsunuz?')
            missing.extend(token for token in quote_required if token not in text)
        if missing:
            failures.append({'page': rel, 'missing': missing})
    if failures:
        sample = '; '.join(f"{item['page']}: {', '.join(item['missing'])}" for item in failures[:8])
        raise RuntimeError('V3.1.72 public shell doğrulaması başarısız. Eski navigasyon kalan sayfalar var: ' + sample)
    return {'checked': checked, 'ok': True}


verify_v3163_public_shell = verify_v3164_public_shell


# ==============================================================
# V3.1.66 + V3.1.67 COMBINED NFC EXPERIENCE
# NFC hub + SEO subpages + capacity stepper + software showcase.
# Existing pricing/reference sources stay authoritative.
# ==============================================================

def _nfc_money(value, fallback='Özel teklif'):
    return format_try(value) or fallback


def _nfc_v3167_footer(prefix='../../'):
    return f'''<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="{prefix}"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı, özel üretim ve işletme sistemleri.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a aria-label="BG Studio 3D Instagram" class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>bgstudio.3dtr</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20NFC%20ve%20QR%20sistemleri%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="{prefix}urunler/">Ürünler</a><a href="{prefix}ozel-uretim/">Özel Üretim</a><a href="{prefix}kurumsal/">Kurumsal</a><a href="{prefix}nfc-qr/">NFC &amp; QR</a><a href="{prefix}prototip-parca/">Prototip &amp; Parça Üretim</a><a href="{prefix}iletisim/">İletişim</a><a href="{prefix}gizlilik/">Gizlilik</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>'''


def _nfc_v3167_page(title, description, route, body_html):
    prefix = '../../'
    canonical = f'{BASE_URL}/nfc-qr/{route}/'
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(clip_seo_text(description, 160))}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(clip_seo_text(description, 160))}"><meta property="og:url" content="{canonical}"><link rel="icon" href="{prefix}favicon.ico" sizes="any"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="{prefix}assets/css/styles.css?v={SITE_ASSET_VERSION}"><meta name="robots" content="index,follow"><meta name="color-scheme" content="light"></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header(prefix, 'nfc')}<main id="main-content" class="nfc-v3167-subpage" data-nfc-hub-v3167="subpage">{body_html}</main>{_nfc_v3167_footer(prefix)}<script defer src="{prefix}assets/js/consent.js"></script><script defer src="{prefix}assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="{prefix}assets/js/main.js?v={SITE_ASSET_VERSION}"></script><script defer src="{prefix}assets/js/nfc-hub.js?v={SITE_ASSET_VERSION}"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20NFC%20ve%20QR%20sistemleri%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div></body></html>'''


def _nfc_v3167_media(key, alt, prefix='../../'):
    row = nfc_media_settings().get(key) or {}
    image = str(row.get('image') or '').replace('\\', '/').lstrip('/')
    if image:
        return f'<div class="nfc-v3167-media zoomable-media" role="button" tabindex="0" aria-label="{esc(alt)} görselini büyüt"><img src="{prefix}{esc(image)}" alt="{esc(alt)}" loading="lazy" decoding="async"></div>'
    if key == 'restaurant_packages':
        return f'<div class="nfc-v3167-media nfc-v3167-media-fallback"><img src="{prefix}assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC restoran stand şeması" loading="lazy" decoding="async"></div>'
    return '<div class="nfc-v3167-media nfc-v3167-media-fallback"><span>BG Studio NFC + QR</span><small>İşletmeye özel fiziksel + dijital sistem</small></div>'


def _nfc_v3167_browser_frame(title='İşletme paneli'):
    modules = ['NFC taramaları','Menü etkileşimleri','Feedback','Google yönlendirme','Sosyal medya','Çoklu dil','Alerjen','Kalori','Bildirimler']
    module_html = ''.join(f'<span>{esc(x)}</span>' for x in modules)
    return f'''<div class="nfc-browser-frame" aria-label="BG Studio NFC yazılım arayüzü sunumu"><div class="nfc-browser-top"><span></span><span></span><span></span><b>{esc(title)}</b></div><div class="nfc-browser-body"><aside><strong>BG NFC</strong><i>Panel</i><i>Analitik</i><i>Menü</i><i>Feedback</i><i>Ayarlar</i></aside><div class="nfc-browser-content"><div class="nfc-browser-title"><div><small>YÖNETİM ALTYAPISI</small><strong>Fiziksel standın arkasındaki dijital sistem</strong></div><span>Canlı sistem yapısı</span></div><div class="nfc-browser-module-grid">{module_html}</div><div class="nfc-browser-panels"><div><small>ETKİLEŞİM AKIŞI</small><strong>NFC / QR → dijital hedef → panel</strong></div><div><small>YÖNETİM</small><strong>Uzaktan hedef ve içerik yönetimi</strong></div></div></div></div></div>'''


def _nfc_v3167_flow():
    return '''<div class="nfc-digital-flow" aria-label="BG Studio NFC sistem akışı"><span><b>01</b>Stand</span><i>→</i><span><b>02</b>Telefon</span><i>→</i><span><b>03</b>Dijital deneyim</span><i>→</i><span><b>04</b>İşletme paneli</span></div>'''


def _nfc_v3167_option_calculator(code, label, tables, qr_count, base_price, qr_unit, menu_price, logo_price, offer_prefix='../../'):
    def num(v):
        try: return str(int(v))
        except Exception: return ''
    qr_cost = int(qr_count) * int(qr_unit)
    menu_scope = 'TR + EN görsel menü · 8 ek dijital dil · ürün içerikleri · 14 alerjen · yaklaşık kalori'
    return f'''<div class="nfc-package-configurator" data-nfc-package-calculator data-offer-base="{offer_prefix}teklif/" data-package-code="{esc(code)}" data-package-label="{esc(label)}" data-tables="{int(tables)}" data-base-price="{num(base_price)}" data-qr-count="{int(qr_count)}" data-qr-unit="{int(qr_unit)}" data-menu-price="{int(menu_price)}" data-logo-price="{int(logo_price)}"><div class="nfc-config-head"><strong>Ek hizmetlerini seç</strong><small>Toplam satış anında güncellenir.</small></div><div class="nfc-config-options"><button type="button" data-package-option="qr" aria-pressed="false"><span>QR sistemi</span><b>+{_nfc_money(qr_cost)}</b><small>{int(qr_count)} QR · {_nfc_money(qr_unit)} / QR</small></button><button type="button" data-package-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b>+{_nfc_money(menu_price)}</b><small>{esc(menu_scope)}</small></button><button type="button" data-package-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b>+{_nfc_money(logo_price)}</b><small>İşletmeye özel logo · fiziksel ve dijital kullanıma uyumlu</small></button></div><div class="nfc-config-total"><span>Toplam satış</span><strong data-package-total>{_nfc_money(base_price)}</strong><small data-package-breakdown>Paket plan bedeli dahil · Ek hizmet seçilmedi</small></div><a class="primary-cta" data-package-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket={esc(code)}">{esc(label)} için teklif al ↗</a></div>'''


def _nfc_v3167_capacity_calculator(pricing, offer_prefix='../../'):
    year = str(pricing.get('year') or '2026')
    qr_unit = int(pricing.get('qr_unit') or 0)
    menu_price = int(pricing.get('menu_design') or 0)
    logo_price = int(pricing.get('logo_design') or 0)
    rows = pricing.get('special_restaurant_packages') if isinstance(pricing.get('special_restaurant_packages'), dict) else {}
    capacities = [25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,110,120]
    first = capacities[0]
    first_row = rows.get(str(first)) or {'price': None, 'renewal': None}
    first_nfc = first * 3
    def num(v):
        try: return str(int(v))
        except Exception: return ''
    buttons = ''.join(
        f'<button type="button" data-special-capacity="{tables}" data-special-nfc="{tables*3}" data-special-price="{num((rows.get(str(tables)) or {}).get("price"))}" data-special-renewal="{num((rows.get(str(tables)) or {}).get("renewal"))}" aria-pressed="{"true" if tables == first else "false"}"><span>{tables} masa</span><small>{_nfc_money((rows.get(str(tables)) or {}).get("price"))}</small></button>'
        for tables in capacities
    )
    table_rows = ''.join(
        f'<tr><td>{tables} masa</td><td>{tables*3} NFC</td><td>{_nfc_money((rows.get(str(tables)) or {}).get("price"))}</td><td>{_nfc_money((rows.get(str(tables)) or {}).get("renewal"))}</td></tr>'
        for tables in capacities
    )
    return f'''<div class="nfc-capacity-lab" data-capacity-stepper-root><div class="nfc-capacity-lab-copy"><p class="eyebrow">25–120 MASA</p><h3>Masa sayını seç. Toplamı anında gör.</h3><p>Uzun fiyat listesini taramak yerine kapasiteyi slider veya + / − kontrolleriyle değiştir. Mevcut fiyat motoru aynı değerleri hesaplamaya devam eder.</p><div class="nfc-capacity-stepper"><button type="button" data-capacity-prev aria-label="Önceki kapasite">−</button><div><small>Masa sayısı</small><strong data-capacity-display>{first}</strong><span data-capacity-nfc-display>{first_nfc} NFC</span></div><button type="button" data-capacity-next aria-label="Sonraki kapasite">+</button></div><input class="nfc-capacity-range" data-capacity-range type="range" min="0" max="{len(capacities)-1}" step="1" value="0" aria-label="Masa kapasitesi"><div class="nfc-capacity-range-labels"><span>25</span><span>60</span><span>120 masa</span></div><div class="nfc-capacity-data" hidden>{buttons}</div><details class="nfc-all-prices"><summary>Tüm fiyatları göster <span>{len(capacities)} hazır kapasite</span></summary><div class="nfc-all-prices-table"><table><thead><tr><th>Kapasite</th><th>NFC</th><th>Paket plan bedeli</th><th>Yıllık yenileme</th></tr></thead><tbody>{table_rows}</tbody></table></div></details></div><div class="special-ready-highlight nfc-capacity-live-card" data-special-package-calculator data-offer-base="{offer_prefix}teklif/" data-qr-unit="{qr_unit}" data-menu-price="{menu_price}" data-logo-price="{logo_price}"><span class="package-kicker" data-special-title>GÜNCEL {first} MASA HAZIR PAKETİ</span><div class="special-ready-metrics"><span><b data-special-tables>{first}</b>Masa</span><span><b data-special-nfc>{first_nfc}</b>NFC</span></div><div class="special-ready-price"><small data-special-price-year>{year} paket plan bedeli</small><strong data-special-base-price>{_nfc_money(first_row.get('price'))}</strong><span data-special-renewal>Yıllık yenileme: {_nfc_money(first_row.get('renewal'))}</span></div><div class="special-ready-options"><button type="button" data-special-option="qr" aria-pressed="false"><span>QR sistemi</span><b data-special-qr-cost>+{_nfc_money(first_nfc*qr_unit)}</b><small data-special-qr-copy>{first_nfc} QR × {_nfc_money(qr_unit)} / QR</small></button><button type="button" data-special-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b data-special-menu-cost>+{_nfc_money(menu_price)}</b><small>TR + EN görsel menü · 8 ek dijital dil · ürün içerikleri · 14 alerjen · yaklaşık kalori</small></button><button type="button" data-special-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b data-special-logo-cost>+{_nfc_money(logo_price)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button></div><div class="special-ready-breakdown"><div><span>Paket plan bedeli</span><b data-special-line-base>{_nfc_money(first_row.get('price'))}</b></div><div><span>QR</span><b data-special-line-qr>Seçilmedi</b></div><div><span>Menü Tasarımı</span><b data-special-line-menu>Seçilmedi</b></div><div><span>Logo Tasarımı</span><b data-special-line-logo>Seçilmedi</b></div></div><div class="special-ready-total"><span>Toplam satış</span><strong data-special-total>{_nfc_money(first_row.get('price'))}</strong><small>Seçilen kapasite + ek hizmetler</small></div><a class="primary-cta" data-special-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket=ozel-kapasite&amp;masa={first}">{first} masa için teklif al</a></div></div>'''



def _nfc_v3167_quick_calculator(pricing, offer_prefix='../../'):
    packages = pricing.get('packages') if isinstance(pricing.get('packages'), dict) else {}
    row = packages.get('hizli_stand') if isinstance(packages.get('hizli_stand'), dict) else {}
    qr_unit = int(pricing.get('qr_unit') or 0)
    logo_price = int(pricing.get('logo_design') or 0)
    base = row.get('price')
    renewal = row.get('renewal')
    qr_count = 3
    return f'''<div class="nfc-quick-live"><div class="nfc-quick-live-head"><div><p class="eyebrow">CANLI HESAP</p><h3>Hızlı Stand kapsamını seç.</h3></div><span>Yıllık yenileme: {_nfc_money(renewal)}</span></div><div class="nfc-package-configurator" data-nfc-package-calculator data-offer-base="{offer_prefix}teklif/" data-package-code="hizli-stand" data-package-label="Hızlı Bağlantı Standı" data-tables="1" data-base-price="{int(base) if base is not None else ''}" data-qr-count="{qr_count}" data-qr-unit="{qr_unit}" data-menu-price="0" data-logo-price="{logo_price}"><div class="nfc-config-options nfc-config-options-two"><button type="button" data-package-option="qr" aria-pressed="false"><span>3 QR ekle</span><b>+{_nfc_money(qr_count*qr_unit)}</b><small>{qr_count} × {_nfc_money(qr_unit)} / QR</small></button><button type="button" data-package-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b>+{_nfc_money(logo_price)}</b><small>İşletmeye özel logo tasarımı</small></button></div><div class="nfc-config-total"><span>Toplam satış</span><strong data-package-total>{_nfc_money(base)}</strong><small data-package-breakdown>Paket plan bedeli dahil · Ek hizmet seçilmedi</small></div><a class="primary-cta" data-package-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket=hizli-stand">Bu kapsamla teklif al ↗</a></div></div>'''


def _nfc_v3167_duo_calculator(pricing, offer_prefix='../../'):
    rows = pricing.get('feedback_duo_packages') if isinstance(pricing.get('feedback_duo_packages'), dict) else {}
    qr_unit = int(pricing.get('qr_unit') or 0)
    ordered = sorted((row for row in rows.values() if isinstance(row, dict)), key=lambda row: int(row.get('stands') or 0))
    if not ordered:
        return ''
    def num(value):
        try: return str(int(value))
        except Exception: return ''
    buttons=[]
    for index,row in enumerate(ordered):
        stands=int(row.get('stands') or 0); nfc=int(row.get('nfc') or stands*2)
        buttons.append(f'<button type="button" data-duo-capacity data-duo-stands="{stands}" data-duo-nfc="{nfc}" data-duo-price="{num(row.get("price"))}" data-duo-renewal="{num(row.get("renewal"))}" aria-pressed="{"true" if index == 0 else "false"}">{stands}</button>')
    first=ordered[0]; stands=int(first.get('stands') or 0); nfc=int(first.get('nfc') or stands*2)
    return f'''<div class="nfc-duo-calculator" data-duo-calculator data-qr-unit="{qr_unit}" data-offer-base="{offer_prefix}teklif/"><div class="nfc-duo-selector"><div><p class="eyebrow">DUO CANLI HESAP</p><h3>Stand sayısını seç.</h3><p>Paket plan bedeli paneldeki güncel Duo tarifesinden gelir. QR açılırsa stand başına 2 QR ayrıca hesaplanır.</p></div><div class="nfc-capacity-stepper"><button type="button" data-duo-prev aria-label="Önceki Duo kapasitesi">−</button><div><small>Stand sayısı</small><strong data-duo-stands-display>{stands}</strong><span data-duo-nfc-display>{nfc} NFC</span></div><button type="button" data-duo-next aria-label="Sonraki Duo kapasitesi">+</button></div><input class="nfc-capacity-range" data-duo-range type="range" min="0" max="{len(ordered)-1}" step="1" value="0" aria-label="Duo stand kapasitesi"><div class="nfc-duo-data" hidden>{''.join(buttons)}</div></div><div class="nfc-duo-live-card"><span class="package-kicker">PREMIUM FEEDBACK DUO</span><div class="special-ready-metrics"><span><b data-duo-live-stands>{stands}</b>Stand</span><span><b data-duo-live-nfc>{nfc}</b>NFC</span><span data-duo-live-qr-metric hidden><b data-duo-live-qr>{nfc}</b>QR</span></div><div class="special-ready-price"><small>Paket plan bedeli</small><strong data-duo-base>{_nfc_money(first.get('price'))}</strong><span data-duo-renewal>Yıllık yenileme: {_nfc_money(first.get('renewal'))}</span></div><button class="nfc-duo-qr-toggle" type="button" data-duo-qr-toggle aria-pressed="false"><span>QR sistemini ekle</span><b data-duo-qr-price>+{_nfc_money(nfc*qr_unit)}</b><small data-duo-qr-copy>{nfc} QR × {_nfc_money(qr_unit)}</small></button><div class="special-ready-breakdown"><div><span>Paket plan bedeli</span><b data-duo-line-base>{_nfc_money(first.get('price'))}</b></div><div data-duo-qr-line hidden><span>QR sistemi</span><b data-duo-line-qr>+{_nfc_money(nfc*qr_unit)}</b></div></div><div class="special-ready-total"><span>Toplam satış</span><strong data-duo-total>{_nfc_money(first.get('price'))}</strong><small>QR seçimi değiştikçe toplam güncellenir.</small></div><a class="primary-cta" data-duo-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket=feedback-duo&amp;masa={stands}">{stands} stand için teklif al ↗</a></div></div>'''

def _nfc_v3167_software_showcase():
    return f'''<section class="section-pad shell nfc-software-showcase" id="yazilim"><div class="split-title"><div><p class="eyebrow">YAZILIM + FİZİKSEL ÜRÜN</p><h2>Standın arkasında çalışan işletme altyapısı.</h2></div><p>BG Studio NFC yalnızca fiziksel bir stand değildir. NFC ve QR erişimleri dijital deneyim, analitik, feedback ve yönetim araçlarıyla aynı sistemde buluşur.</p></div>{_nfc_v3167_flow()}<div class="nfc-software-grid"><div class="nfc-software-copy"><article><span>01</span><h3>İşletme paneli</h3><p>NFC taramaları, menü etkileşimleri, feedback, yönlendirmeler ve sistem durumu tek merkezden takip edilir.</p></article><article><span>02</span><h3>Müşteri deneyimi</h3><p>Akıllı Menü, çoklu dil, içerik, alerjen ve yaklaşık kalori katmanları fiziksel erişim noktalarına bağlanır.</p></article><article><span>03</span><h3>Analitik ve bildirim</h3><p>Çözüm tipine göre masa veya stand etkileşimleri, feedback ve yönlendirme performansı izlenebilir.</p></article><article><span>04</span><h3>Uzaktan yönetim</h3><p>Dijital hedefler fiziksel ürünü yeniden basmadan güncellenebilir. Bildirim ve yönetim altyapısı sistemin devamlılığını destekler.</p></article></div>{_nfc_v3167_browser_frame()}</div></section>'''


def render_nfc_platform_sections(theme_overrides=None):
    """V3.1.66/67 compact NFC product hub. Detailed content lives on SEO subpages."""
    pricing = active_nfc_pricing()
    year = str(pricing.get('year') or '2026')
    packages = pricing.get('packages') if isinstance(pricing.get('packages'), dict) else {}
    restaurant = packages.get('baslangic') or {}
    quick = packages.get('hizli_stand') or {}
    duo = packages.get('feedback_duo') or {}
    restaurant_media = render_nfc_family_media('restaurant_packages', 'Restoran sistemleri', 'BG Studio NFC restoran sistemleri')
    quick_media = render_nfc_family_media('quick_stand', 'Hızlı Bağlantı Standı', 'BG Studio NFC Hızlı Bağlantı Standı')
    feedback_media = render_nfc_family_media('feedback_duo', 'Premium Feedback', 'BG Studio NFC Premium Feedback Duo ve Trio')
    saved_themes = nfc_family_theme_settings()
    theme_overrides = theme_overrides if isinstance(theme_overrides, dict) else {}
    def family_theme(key, fallback='light'):
        value = str(theme_overrides.get(key) or saved_themes.get(key) or fallback).strip().lower()
        return 'dark' if value == 'dark' else 'light'
    restaurant_theme = family_theme('restaurant_packages', 'light')
    quick_theme = family_theme('quick_stand', 'light')
    feedback_theme = family_theme('feedback_duo', 'dark')
    premium_plus_theme = family_theme('premium_plus', 'dark')
    capacity_preview = _nfc_v3167_capacity_calculator(pricing, offer_prefix='../')
    return f'''<!-- NFC_PLATFORM_V167_START -->
<section class="page-hero nfc-platform-hero nfc-hub-hero" data-nfc-hub-v3167="main"><div class="shell nfc-hub-hero-grid"><div class="nfc-hub-hero-copy"><p class="eyebrow">BG STUDIO NFC + QR</p><h1>Fiziksel temas. Dijital deneyim. Tek sistem.</h1><p class="lead">İşletmeler için fiziksel + dijital müşteri etkileşim sistemi. Özel tasarım 3D standları NFC, QR, Akıllı Menü, feedback, analitik ve yönetim altyapısıyla birleştiriyoruz.</p><div class="hero-actions"><a class="primary-cta" href="#sistemler">Sistemleri İncele ↓</a><a class="secondary-cta" href="../teklif/?tur=nfc">Teklif Al ↗</a></div><div class="nfc-hub-proof"><span>İşletmeye özel 3D üretim</span><span>NFC + QR</span><span>Panel + analitik</span><span>Kuşadası merkezli</span></div></div><div class="nfc-hub-hero-visual"><img src="../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC ve QR restoran stand sistemi" width="1254" height="1254" fetchpriority="high" decoding="async"><div class="nfc-hub-hero-badge"><strong>Fiziksel + Dijital</strong><span>Stand → Telefon → Sistem</span></div></div></div></section>
<section class="section-pad shell nfc-solution-hub" id="sistemler"><div class="split-title"><div><p class="eyebrow">ÇÖZÜM MERKEZİ</p><h2>İşletmene uygun sistemi seç.</h2></div><p>Ana sayfada kısa karşılaştır, ayrıntı için çözüm sayfasına geç. Fiyat ve paket motorları mevcut panel verilerinden beslenmeye devam eder.</p></div><div class="nfc-solution-grid"><article class="nfc-solution-card nfc-solution-card-large {'dark' if restaurant_theme=='dark' else ''}" id="restoran-sistemleri" data-family-key="restaurant_packages" data-family-theme="{restaurant_theme}">{restaurant_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>RESTORAN SİSTEMLERİ</span><b>{year} · {_nfc_money(restaurant.get('price'))}'den</b></div><h3>Masadan dijital deneyime.</h3><p>Akıllı Menü, çoklu dil, 14 alerjen, yaklaşık kalori, feedback, analitik ve Garson Çağır + Hesap İste altyapısı.</p><ul><li>Stand başına 3 NFC</li><li>QR opsiyonel</li><li>10–120 masa ölçeklenebilir</li></ul><a class="primary-cta" href="restoran/">Restoran Sistemlerini İncele ↗</a></div></article><article class="nfc-solution-card {'dark' if quick_theme=='dark' else ''}" data-family-key="quick_stand" data-family-theme="{quick_theme}">{quick_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>HIZLI BAĞLANTI</span><b>{_nfc_money(quick.get('price'))}</b></div><h3>Tek stand, üç bağlantı.</h3><p>Instagram, Google, WhatsApp, web veya işletmenin seçtiği farklı hedefleri tek fiziksel noktada birleştir.</p><ul><li>3 NFC / stand</li><li>QR opsiyonel</li><li>Uzaktan hedef yönetimi</li></ul><a class="secondary-cta" href="hizli-baglanti/">Hızlı Standı İncele ↗</a></div></article><article class="nfc-solution-card {'dark' if feedback_theme=='dark' else ''}" data-family-key="feedback_duo" data-family-theme="{feedback_theme}">{feedback_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>PREMIUM FEEDBACK</span><b>{_nfc_money(duo.get('price'))}'den</b></div><h3>Duo + Trio müşteri deneyimi.</h3><p>Feedback, Google devam akışı, sosyal / iletişim hedefleri ve raporlama odaklı gelişmiş işletme çözümü.</p><ul><li>Duo: 2 NFC / stand</li><li>Trio: 3 NFC / stand</li><li>QR paket dışında opsiyonel</li></ul><a class="secondary-cta" href="feedback/">Duo / Trio Detayları ↗</a></div></article><article class="nfc-solution-card nfc-solution-premium-plus {'dark' if premium_plus_theme=='dark' else 'light'}" data-family-key="premium_plus" data-family-theme="{premium_plus_theme}"><div class="nfc-premium-plus-visual"><span>YAKINDA</span><strong>Premium<br>Plus</strong><small>Geliştiriliyor</small></div><div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>ÜST KATMAN</span><b>Henüz satışta değil</b></div><h3>CRM, sadakat, rezervasyon ve AI.</h3><p>Doğrudan masa siparişi, misafir profili, sadakat, segmentasyon, rezervasyon ve AI araçları için geliştirilen ayrı üst katman.</p><ul><li>Doğrudan masa siparişi</li><li>Misafir CRM + sadakat</li><li>Rezervasyon + AI araçları</li></ul><a class="ghost-cta" href="premium-plus/">Premium Plus Yol Haritası ↗</a></div></article></div></section>
{_nfc_v3167_software_showcase()}
<section class="section-pad shell nfc-main-price-preview" id="fiyat-hesap"><div class="split-title"><div><p class="eyebrow">CANLI FİYAT HESABI</p><h2>25–120 masa için tek kontrol.</h2></div><p>Hazır kapasite listesini slider ve stepper ile sadeleştirdik. QR, Menü Tasarımı ve Logo Tasarımı seçimleri toplam satışa ayrı eklenir.</p></div>{capacity_preview}</section>
<section class="section-pad shell nfc-hub-final"><div class="nfc-final-panel"><div><p class="eyebrow">BG STUDIO NFC + QR</p><h2>İşletmenin ihtiyacını seç, sistemi birlikte netleştirelim.</h2><p>Restoran, hızlı bağlantı, feedback veya özel kapsam için mevcut sistemi ve fiyat yapısını bozmadan teklif hazırlayalım.</p></div><div class="hero-actions"><a class="primary-cta" href="../teklif/?tur=nfc">Teklif Al ↗</a><a class="secondary-cta" href="#sistemler">Sistemlere dön ↑</a></div></div></section>
<!-- NFC_PLATFORM_V167_END -->'''


def rebuild_nfc_platform_sections(html_text, theme_overrides=None):
    rendered = render_nfc_platform_sections(theme_overrides=theme_overrides)
    marker_pattern = re.compile(r'<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156|159|160|161|167)_START\s*-->.*?<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156|159|160|161|167)_END\s*-->', flags=re.I | re.S)
    if marker_pattern.search(html_text):
        html_text = marker_pattern.sub(rendered, html_text, count=1)
    else:
        start = re.search(r'<section\b[^>]*class="[^"]*page-hero[^"]*"[^>]*>', html_text, flags=re.I)
        ref = re.search(r'<section\b[^>]*class="[^"]*custom-band[^"]*"[^>]*>.*?<h2>\s*Sahada çalışan örnekler\.\s*</h2>', html_text, flags=re.I | re.S)
        if not start or not ref:
            raise RuntimeError('NFC ana ürün merkezi güvenli biçimde bulunamadı; saha referanslarına dokunulmadı.')
        html_text = html_text[:start.start()] + rendered + '\n' + html_text[ref.start():]
    desc = 'BG Studio NFC + QR; restoran sistemleri, Hızlı Bağlantı, Premium Feedback Duo / Trio ve geliştirilen Premium Plus ile fiziksel ve dijital işletme deneyimini birleştirir.'
    html_text = re.sub(r'(<meta\s+content=")[^"]*("\s+name="description"\s*/?>)', lambda m: m.group(1)+desc+m.group(2), html_text, count=1, flags=re.I)
    html_text = re.sub(r'(<title>).*?(</title>)', lambda m: m.group(1)+'BG Studio NFC + QR | İşletme Sistemleri'+m.group(2), html_text, count=1, flags=re.I|re.S)
    return html_text


def _nfc_v3167_standard_package_cards(pricing):
    year = str(pricing.get('year') or '2026')
    qr_unit = int(pricing.get('qr_unit') or 0)
    menu_price = int(pricing.get('menu_design') or 0)
    logo_price = int(pricing.get('logo_design') or 0)
    packages = pricing.get('packages') or {}
    specs = [('baslangic','Başlangıç',10,30),('profesyonel','Profesyonel',15,45),('premium','Premium',20,60)]
    cards=[]
    for code,label,tables,nfc in specs:
        row = packages.get(code) or {}
        normal = _nfc_money(row.get('list_price')) if row.get('list_price') else ''
        renewal = _nfc_money(row.get('renewal')) if row.get('renewal') else 'Özel teklif'
        cards.append(f'''<article class="nfc-v3167-package-card{' featured' if code == 'profesyonel' else ''}"><div class="package-head"><span class="package-kicker">{tables} MASA · {nfc} NFC</span><span class="package-badge">{esc(label)}</span></div><h3>{esc(label)}</h3><div class="package-price"><small>{year} paket plan bedeli</small><strong>{_nfc_money(row.get('price'))}</strong><span>{('Normal fiyat: ' + normal + ' · ') if normal else ''}Yıllık yenileme: {renewal}</span></div><ul><li>Stand başına 3 NFC</li><li>Akıllı Menü + çoklu dil</li><li>Feedback + Google devam akışı</li><li>Analitik + işletme paneli</li><li>Garson Çağır + Hesap İste</li></ul>{_nfc_v3167_option_calculator(code,label,tables,nfc,row.get('price'),qr_unit,menu_price,logo_price)}</article>''')
    return ''.join(cards)


def _nfc_v3167_restaurant_page(nfc_items):
    pricing = active_nfc_pricing()
    refs = ''.join(render_nfc_case(item, '../../') for item in nfc_items[:4])
    content = f'''<section class="nfc-sub-hero"><div class="shell nfc-sub-hero-grid"><div><nav class="nfc-breadcrumb"><a href="../../nfc-qr/">NFC + QR</a><span>/</span><b>Restoran Sistemleri</b></nav><p class="eyebrow">BG STUDIO NFC RESTORAN</p><h1>Masanın üzerindeki standdan işletme paneline.</h1><p class="lead">Restoranlar için NFC + QR erişimi, Akıllı Menü, değerlendirme, analitik ve servis taleplerini tek işletme altyapısında birleştiren sistem.</p><div class="hero-actions"><a class="primary-cta" href="#paketler">Paketleri İncele ↓</a><a class="secondary-cta" href="../../teklif/?tur=nfc&amp;paket=baslangic">Teklif Al ↗</a></div></div>{_nfc_v3167_media('restaurant_packages','BG Studio NFC restoran sistemi')}</div></section><nav class="shell nfc-section-nav" aria-label="Restoran sistemi bölümleri"><a href="#nasil-calisir">Nasıl çalışır</a><a href="#stand">Stand</a><a href="#yazilim">Yazılım</a><a href="#paketler">Paketler</a><a href="#kapasite">25–120 masa</a><a href="#saha">Saha</a><a href="#sss">SSS</a></nav><section class="section-pad shell" id="nasil-calisir"><div class="split-title"><div><p class="eyebrow">SİSTEM NEDİR?</p><h2>Fiziksel ürün ve dijital işletme sistemi birlikte çalışır.</h2></div><p>Her stand işletmenin kullanım senaryosuna göre NFC erişim noktaları taşır. QR opsiyonu aynı hedeflere alternatif erişim sunar. Dijital hedefler panel üzerinden yönetilir.</p></div>{_nfc_v3167_flow()}<div class="nfc-feature-matrix"><article><span>NFC</span><h3>Temassız erişim</h3><p>Misafir telefonu ilgili NFC alanına yaklaştırarak menü, değerlendirme veya seçilen hedefe geçer.</p></article><article><span>QR</span><h3>İsteğe bağlı alternatif</h3><p>QR seçilirse restoran sistemlerinde masa başına 3 QR eklenir ve ayrı fiyatlandırılır.</p></article><article><span>MENÜ</span><h3>Akıllı Menü</h3><p>Çoklu dil, ürün içerikleri, 14 alerjen bilgi katmanı ve yaklaşık kalori bilgileri desteklenir.</p></article><article><span>FEEDBACK</span><h3>Müşteri değerlendirmesi</h3><p>İşletme içi değerlendirme akışı, Google devam adımı ve müşteri deneyimi takibi aynı sistemde buluşur.</p></article></div></section><section class="section-pad-sm shell" id="stand"><div class="split-title"><div><p class="eyebrow">STAND</p><h2>İşletmeye özel tasarlanır ve 3D üretilir.</h2></div><p>Logo, QR alanları, uygulama ikonları, NFC temas bölgeleri ve restoran kurulumlarında arka yüz masa numarası işletmeye göre hazırlanır.</p></div><figure class="nfc-v3167-schema zoomable-media" role="button" tabindex="0"><img src="../../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC restoran stand şeması" loading="lazy" decoding="async"><figcaption>Görseli büyütmek için tıkla veya dokun</figcaption></figure></section>{_nfc_v3167_software_showcase()}<section class="section-pad shell" id="paketler"><div class="split-title"><div><p class="eyebrow">STANDART RESTORAN PAKETLERİ</p><h2>Başlangıçtan Premium'a.</h2></div><p>Garson Çağır + Hesap İste tüm Standart Restoran paketlerinde mevcut ortak özelliktir. QR, Menü Tasarımı ve Logo Tasarımı seçimleri ayrı kalemlerdir.</p></div><div class="nfc-v3167-package-grid">{_nfc_v3167_standard_package_cards(pricing)}</div></section><section class="section-pad shell" id="kapasite"><div class="split-title"><div><p class="eyebrow">ÖZEL RESTORAN HAZIR PAKETLERİ</p><h2>25–120 masa için canlı kapasite hesabı.</h2></div><p>Aynı restoran altyapısı kapasiteye göre ölçeklenir. Slider ile masa sayısını değiştir; sağ kartta paket plan bedeli ve seçilen ek hizmetlerle toplam satış güncellensin.</p></div>{_nfc_v3167_capacity_calculator(pricing)}</section><section class="section-pad shell" id="saha"><div class="split-title"><div><p class="eyebrow">SAHADAN</p><h2>Çalışan sistem örnekleri.</h2></div><p>BG Studio NFC sistemlerinin farklı işletmelerdeki fiziksel ve dijital kurulumlarından seçilen örnekler.</p></div><div class="reference-grid">{refs}</div><div class="section-actions"><a class="secondary-cta" href="../../nfc-qr/#sahadan-isler">Tüm NFC saha işlerini gör ↗</a></div></section><section class="section-pad shell" id="sss"><div class="split-title"><div><p class="eyebrow">SSS</p><h2>Restoran sistemi hakkında kısa cevaplar.</h2></div></div><div class="faq"><details><summary>QR zorunlu mu?</summary><p>Hayır. QR opsiyoneldir. Seçilirse masa başına 3 QR eklenir ve QR bedeli paket plan bedelinden ayrı hesaplanır.</p></details><details><summary>Garson Çağır + Hesap İste hangi pakette?</summary><p>Başlangıç, Profesyonel, Premium ve 25–120 masa Özel Restoran Hazır Paketlerinde mevcut ortak sistem özelliğidir.</p></details><details><summary>Menü Tasarımı neleri kapsar?</summary><p>Güncel kapsam; Türkçe ve İngilizce görsel menü, 8 ek dilde dijital metin menü, ürün içerikleri, 14 alerjen bilgi katmanı ve yaklaşık kalori bilgileridir.</p></details><details><summary>Stand yeniden basılmadan bağlantı değişebilir mi?</summary><p>Dijital hedefler sistem yapısına göre uzaktan yönetilebilir. Fiziksel ürünün yeniden üretilmesi her bağlantı değişikliğinde gerekmez.</p></details></div><div class="nfc-page-cta"><h3>Restoranın masa sayısını biliyorsan hesabı hazırla.</h3><a class="primary-cta" href="../../teklif/?tur=nfc&amp;paket=baslangic">Restoran için teklif al ↗</a></div></section>'''
    return _nfc_v3167_page('NFC + QR Restoran Sistemleri | BG Studio 3D', 'Restoranlar için NFC + QR, Akıllı Menü, feedback, analitik, Garson Çağır + Hesap İste ve 10–120 masa ölçeklenebilir BG Studio sistemi.', 'restoran', content)


def _nfc_v3167_quick_page():
    pricing = active_nfc_pricing(); year=str(pricing.get('year') or '2026'); qr=int(pricing.get('qr_unit') or 0); logo=int(pricing.get('logo_design') or 0); row=(pricing.get('packages') or {}).get('hizli_stand') or {}; base=row.get('price'); renew=row.get('renewal'); full=(base + qr*3 + logo) if base is not None else None
    content=f'''<section class="nfc-sub-hero"><div class="shell nfc-sub-hero-grid"><div><nav class="nfc-breadcrumb"><a href="../../nfc-qr/">NFC + QR</a><span>/</span><b>Hızlı Bağlantı</b></nav><p class="eyebrow">HIZLI BAĞLANTI STANDI</p><h1>Tek fiziksel noktadan üç dijital hedef.</h1><p class="lead">Instagram, Google, WhatsApp, web sitesi veya işletmenin seçtiği farklı bağlantıları 3 NFC ile tek stand üzerinde birleştiren kompakt işletme çözümü.</p><div class="hero-actions"><a class="primary-cta" href="../../teklif/?tur=nfc&amp;paket=hizli-stand">Teklif Al ↗</a><a class="secondary-cta" href="#fiyat">Fiyatı Gör ↓</a></div></div>{_nfc_v3167_media('quick_stand','BG Studio NFC Hızlı Bağlantı Standı')}</div></section><section class="section-pad shell"><div class="nfc-feature-matrix"><article><span>01</span><h3>3 NFC / stand</h3><p>Üç bağımsız erişim noktası işletmenin seçtiği dijital hedeflere bağlanır.</p></article><article><span>02</span><h3>QR opsiyonu</h3><p>İstenirse standa 3 QR eklenir. QR bedeli paket plan bedelinden ayrı hesaplanır.</p></article><article><span>03</span><h3>Uzaktan yönetim</h3><p>Uygun hedef bağlantıları fiziksel ürünü yeniden üretmeden güncellenebilir.</p></article><article><span>04</span><h3>İşletmeye özel üretim</h3><p>Stand 3D olarak tasarlanır ve üretilir. Hazır pleksi üzerine etiket uygulaması değildir.</p></article></div></section><section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">KULLANIM</p><h2>Bağlantılarını işletmenin akışına göre seç.</h2></div></div><div class="nfc-channel-grid"><span>Instagram</span><span>Google</span><span>WhatsApp</span><span>Web sitesi</span><span>Facebook</span><span>TikTok</span><span>Menü / özel URL</span><span>Diğer bağlantılar</span></div></section><section class="section-pad shell" id="fiyat"><div class="split-title"><div><p class="eyebrow">{year} FİYAT YAPISI</p><h2>Hızlı Stand hesabı.</h2></div><p>Menü Tasarımı Hızlı Bağlantı Standı kapsamında bulunmaz. QR ve Logo Tasarımı opsiyoneldir.</p></div><div class="nfc-quick-price-grid"><article><small>Paket plan bedeli</small><strong>{_nfc_money(base)}</strong><span>Yıllık yenileme: {_nfc_money(renew)}</span></article><article><small>QR sistemi</small><strong>+{_nfc_money(qr*3)}</strong><span>3 × {_nfc_money(qr)} / QR</span></article><article><small>Logo Tasarımı</small><strong>+{_nfc_money(logo)}</strong><span>İşletmeye özel tasarım</span></article><article class="dark"><small>Tümü seçilirse liste hesabı</small><strong>{_nfc_money(full)}</strong><span>Stand + 3 QR + Logo Tasarımı</span></article></div>{_nfc_v3167_quick_calculator(pricing)}<div class="nfc-page-cta"><h3>Hızlı Standı işletmene göre netleştirelim.</h3><a class="primary-cta" href="../../teklif/?tur=nfc&amp;paket=hizli-stand">Hızlı Stand için teklif al ↗</a></div></section>'''
    return _nfc_v3167_page('Hızlı Bağlantı Standı | NFC + QR | BG Studio 3D', '3 NFC bağlantısı, opsiyonel QR, Instagram, Google, WhatsApp, web ve uzaktan hedef yönetimi için BG Studio Hızlı Bağlantı Standı.', 'hizli-baglanti', content)


def _nfc_v3167_feedback_page():
    pricing=active_nfc_pricing(); rows=pricing.get('feedback_duo_packages') if isinstance(pricing.get('feedback_duo_packages'),dict) else {}; year=str(pricing.get('year') or '2026'); qr=int(pricing.get('qr_unit') or 0)
    ordered=[]
    for key,row in sorted(rows.items(), key=lambda kv:int(kv[0])):
        if isinstance(row,dict): ordered.append((int(row.get('stands') or key),row))
    first=ordered[0][1] if ordered else {}; first_stands=ordered[0][0] if ordered else 10
    table=''.join(f'<tr><td>{s} stand</td><td>{s*2} NFC</td><td>{_nfc_money(r.get("price"))}</td><td>{_nfc_money(r.get("renewal"))}</td></tr>' for s,r in ordered)
    content=f'''<section class="nfc-sub-hero nfc-sub-hero-dark"><div class="shell nfc-sub-hero-grid"><div><nav class="nfc-breadcrumb"><a href="../../nfc-qr/">NFC + QR</a><span>/</span><b>Premium Feedback</b></nav><p class="eyebrow">PREMIUM FEEDBACK</p><h1>Duo ve Trio. Müşteri deneyimine iki farklı seviye.</h1><p class="lead">Feedback, Google devam akışı, sosyal / iletişim hedefleri, analitik ve işletme panelini fiziksel standla birleştiren müşteri deneyimi sistemi.</p><div class="hero-actions"><a class="primary-cta" href="#duo-trio">Duo / Trio Karşılaştır ↓</a><a class="secondary-cta" href="../../teklif/?tur=nfc&amp;paket=feedback-duo">Teklif Al ↗</a></div></div>{_nfc_v3167_media('feedback_duo','BG Studio Premium Feedback Duo ve Trio')}</div></section><section class="section-pad shell" id="duo-trio"><div class="nfc-feedback-compare"><article><p class="eyebrow">DUO</p><h2>2 NFC / stand</h2><ul><li>NFC 1: işletme içi feedback + Google devam akışı</li><li>NFC 2: seçilebilir sosyal / iletişim hedefi</li><li>Feedback analitiği ve işletme paneli</li><li>QR opsiyonel ve paket dışında</li></ul><div class="nfc-feedback-price"><small>{year} başlayan paket plan bedeli</small><strong>{_nfc_money(first.get('price'))}</strong><span>{first_stands} standdan başlayan hazır kapasite</span></div><a class="primary-cta" href="../../teklif/?tur=nfc&amp;paket=feedback-duo&amp;masa={first_stands}">Duo için teklif al ↗</a></article><article class="dark"><p class="eyebrow">TRIO</p><h2>3 NFC / stand</h2><ul><li>Duo'daki feedback + sosyal / iletişim yapısı</li><li>3. NFC: Dijital Menü, web veya özel URL</li><li>İşletme senaryosuna göre üçüncü hedef</li><li>QR opsiyonel ve ayrı kalem</li></ul><div class="nfc-feedback-price"><small>Trio hazır tarifeleri</small><strong>Teklif kapsamında</strong><span>Güncel kapsam işletme ihtiyacına göre netleştirilir.</span></div><a class="secondary-cta" href="../../teklif/?tur=nfc">Trio için teklif al ↗</a></article></div></section><section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">QR OPSİYONU</p><h2>Paket plan bedelinden ayrı.</h2></div><p>QR kapalıysa QR kalemi ve QR kapasitesi hesaptan çıkar. Açılırsa fiziksel kurulum adedine göre ayrıca hesaplanır. Güncel QR birim fiyatı: <strong>{_nfc_money(qr)} / QR</strong>.</p></div></section><section class="section-pad shell">{_nfc_v3167_duo_calculator(pricing)}</section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">DUO HAZIR KAPASİTELERİ</p><h2>Tüm fiyatlar tek tabloda.</h2></div></div><details class="nfc-all-prices" open><summary>Tüm Duo fiyatlarını göster <span>{len(ordered)} kapasite</span></summary><div class="nfc-all-prices-table"><table><thead><tr><th>Stand</th><th>NFC</th><th>Paket plan bedeli</th><th>Yıllık yenileme</th></tr></thead><tbody>{table}</tbody></table></div></details></section>{_nfc_v3167_software_showcase()}'''
    return _nfc_v3167_page('Premium Feedback Duo & Trio | BG Studio NFC', 'Premium Feedback Duo ve Trio; işletme içi feedback, Google devam akışı, seçilebilir dijital hedefler, analitik ve opsiyonel QR sistemi.', 'feedback', content)


def _nfc_v3167_premium_plus_page():
    premium_plus_theme = nfc_family_theme_settings().get('premium_plus', 'dark')
    premium_plus_theme = 'dark' if str(premium_plus_theme).lower() == 'dark' else 'light'
    features=[
        ('01','Doğrudan masa siparişi','Müşteri Akıllı Menü üzerinden ürünlerini seçerek siparişi bulunduğu masadan işletmeye iletebilecek.'),
        ('02','Sipariş notları','Soğansız, acısız, buzsuz, ekstra sos, pişirme tercihi veya özel not gibi talepler siparişe eklenebilecek.'),
        ('03','Akıllı Misafir Profili ve CRM','İzinli ziyaret geçmişi, tercihler ve işletme etkileşimleri tek misafir profili altyapısında yönetilebilecek.'),
        ('04','Sadakat, puan ve ziyaret ödülleri','Ziyaret bazlı ödüller, puan sistemi ve işletmeye özel ayrıcalık kurguları desteklenecek.'),
        ('05','VIP ve tekrar gelen misafir','İlk kez gelen, tekrar gelen, sadık ve VIP misafir segmentleri izinli kullanıcılar üzerinden ayrıştırılabilecek.'),
        ('06','Otomatik segmentler ve geri kazanım','Davranışlara göre müşteri grupları ve geri kazanım kampanyası akışları geliştirilecek.'),
        ('07','Rezervasyon ve bekleme listesi','Online rezervasyon, walk-in kaydı, dijital bekleme listesi ve masa durumu araçları planlanıyor.'),
        ('08','AI ürün eşleştirme ve upsell','Akıllı Menü seçilen ürüne göre tamamlayıcı ürün ve menü önerileri sunabilecek.'),
        ('09','AI günlük yönetici özeti','NFC etkileşimleri, feedback, Google performansı ve müşteri deneyimi sinyalleri sade yönetici özetlerine dönüşebilecek.'),
        ('10','Gelişmiş modüllerde öncelik','Gelecekteki CRM, sadakat, rezervasyon ve AI modüllerinde Premium Plus kapsamına öncelik verilebilecek.'),
    ]
    cards=''.join(f'<article><span>{n}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></article>' for n,t,d in features)
    content=f'''<section class="nfc-sub-hero nfc-premium-plus-page-hero theme-{premium_plus_theme}" data-family-key="premium_plus" data-family-theme="{premium_plus_theme}"><div class="shell"><div class="premium-plus-state"><span class="premium-plus-badge">YAKINDA</span><span class="premium-plus-progress">Geliştiriliyor</span><small>Henüz satışta değil</small></div><p class="eyebrow">PREMIUM PLUS</p><h1>Restoran deneyiminin bir sonraki üst katmanı.</h1><p class="lead">Mevcut Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ve Garson Çağır + Hesap İste Standart Restoran paketlerinde devam eder. Premium Plus bunların üzerine yeni CRM, sadakat, rezervasyon ve AI araçları eklemek için geliştiriliyor.</p><div class="hero-actions"><a class="secondary-cta" href="../../nfc-qr/restoran/">Mevcut Restoran Sistemleri ↗</a><span class="primary-cta is-disabled" aria-disabled="true">Premium Plus · Yakında</span></div></div></section><section class="section-pad shell nfc-premium-plus-roadmap theme-{premium_plus_theme}"><div class="split-title"><div><p class="eyebrow">YOL HARİTASI</p><h2>Planlanan Premium Plus modülleri.</h2></div><p>Bu özellikler geliştirme yol haritasıdır. Çıkış tarihi, kesin kapsam ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="nfc-premium-roadmap-grid">{cards}</div><div class="premium-plus-note-group"><p class="premium-plus-note"><strong>Premium Plus mevcut paket özelliklerini yeniden paketlemez.</strong> Garson Çağır + Hesap İste tüm Standart Restoran paketlerinin mevcut kapsamındadır. Premium Plus'ın farkı doğrudan masa siparişi, sipariş notları, Misafir CRM, sadakat, VIP tanıma, segmentasyon, rezervasyon / bekleme listesi, AI upsell ve AI yönetici zekâsıdır.</p><p class="premium-plus-release-note">Çıkış tarihi, kesin özellik kapsamı ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="nfc-page-cta"><h3>Premium Plus gelişmelerini takip et.</h3><a class="secondary-cta" href="../../nfc-qr/">NFC + QR ana sayfasına dön ↗</a></div></section>'''
    return _nfc_v3167_page('Premium Plus · Yakında | BG Studio NFC', 'Premium Plus; doğrudan masa siparişi, Misafir CRM, sadakat, VIP tanıma, rezervasyon ve AI araçları için geliştirilen BG Studio NFC üst katmanıdır.', 'premium-plus', content)



def render_nfc_v3167_stand_schema_main():
    """Canonical main-page Stand Şeması. Kept separate so references stay second and schema stays third."""
    return '''<section class="section-pad-sm nfc-stand-schema" id="stand-semasi" data-nfc-stand-schema data-nfc-stand-schema-version="3.1.67"><div class="shell"><div class="split-title nfc-stand-schema-heading"><div><p class="eyebrow">STAND YAPISI</p><h2>Tek stand üzerinde tüm erişim noktaları.</h2></div><p>Logo, QR alanları, uygulama ikonları ve NFC temas bölgeleri işletmenize özel tasarlanır. Restoran kurulumunda arka yüz her masa için numaralandırılabilir.</p></div><figure class="nfc-stand-schema-figure zoomable-media" tabindex="0" role="button" aria-label="BG Studio NFC stand şemasını büyüt"><img src="../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC restoran stand şeması; işletmeye özel logo, menü, Google ve sosyal medya QR alanları, NFC temas bölgeleri ve arka yüzde masa numarası gösterimi" width="1254" height="1254" loading="lazy" decoding="async"><figcaption><span>Büyütmek için görsele dokun veya tıkla</span></figcaption></figure><div class="nfc-stand-schema-points"><article><span>01</span><div><strong>İşletmeye özel kimlik</strong><p>Logo ve fiziksel stand görünümü işletmeye göre hazırlanır.</p></div></article><article><span>02</span><div><strong>QR erişim alanları</strong><p>Menü, Google ve sosyal medya hedefleri QR ile de erişilebilir.</p></div></article><article><span>03</span><div><strong>NFC temas noktaları</strong><p>Telefonu temas alanına yaklaştıran misafir ilgili dijital hedefe geçer.</p></div></article><article><span>04</span><div><strong>Masa numaralı arka yüz</strong><p>Restoran kurulumunda her standın arka yüzü masa numarasına göre ayrıştırılabilir.</p></div></article></div><div class="nfc-stand-schema-actions"><a class="secondary-cta" href="#sistemler">Sistemleri incele ↓</a><a class="primary-cta" href="../teklif/?tur=nfc">İşletmen için teklif al ↗</a></div></div></section>'''


def ensure_nfc_v3167_stand_schema_after_references(html_text):
    """Keep the main NFC storytelling order: hero, field proof, stand schema, solutions."""
    schema = render_nfc_v3167_stand_schema_main()
    html_text = re.sub(
        r'<section\b[^>]*class="[^"]*\bnfc-stand-schema\b[^"]*"[^>]*>.*?</section>',
        '',
        html_text,
        count=1,
        flags=re.I | re.S,
    )
    reference = re.search(
        r'<section\b[^>]*id="sahadan-isler"[^>]*>.*?<!--\s*CONTENT_MANAGER:NFC_END\s*-->.*?</section>',
        html_text,
        flags=re.I | re.S,
    )
    if not reference:
        raise RuntimeError('V3.1.67: Stand Şeması için Sahada çalışan örnekler bölümü bulunamadı.')
    return html_text[:reference.end()] + '\n' + schema + html_text[reference.end():]

def build_nfc_v3167_subpages(nfc_items):
    pages={
        'restoran': _nfc_v3167_restaurant_page(nfc_items),
        'hizli-baglanti': _nfc_v3167_quick_page(),
        'feedback': _nfc_v3167_feedback_page(),
        'premium-plus': _nfc_v3167_premium_plus_page(),
    }
    written=[]
    for slug,html_text in pages.items():
        folder=ROOT/'nfc-qr'/slug; folder.mkdir(parents=True,exist_ok=True); path=folder/'index.html'; path.write_text(html_text,encoding='utf-8'); written.append(path.relative_to(ROOT).as_posix())
    return written

# ==============================================================
# V3.1.68 SAHADAN İŞLER + PROJELER
# Data-driven project index and case-study pages. No fabricated metrics.
# ==============================================================

def _project_kind(item):
    kind = str(item.get('_project_kind') or item.get('source_kind') or '').strip().lower()
    if kind == 'nfc':
        return 'nfc'
    if kind == 'prototype':
        return 'prototype'
    return 'corporate'


def _project_kind_label(item):
    return {
        'nfc': 'NFC + QR',
        'prototype': 'Prototip + Parça',
        'corporate': 'Kurumsal Üretim',
    }.get(_project_kind(item), 'BG Studio Projesi')


def _project_slug(item, force_kind_prefix=False):
    raw = str(item.get('_project_slug') or item.get('source_slug') or item.get('slug') or item.get('name') or 'proje').strip().lower().replace('_','-')
    safe = re.sub(r'[^a-z0-9-]+', '-', raw).strip('-')
    safe = re.sub(r'-{2,}', '-', safe) or 'proje'
    kind = _project_kind(item)
    # Prototype records keep an explicit prefix so links rendered on the
    # existing Prototip page can never collide with a corporate/NFC project.
    if kind == 'prototype' and not safe.startswith('prototip-'):
        safe = 'prototip-' + safe
    if force_kind_prefix and not safe.startswith(kind + '-'):
        return f'{kind}-{safe}'
    return safe


def collect_project_items(corporate_items, prototype_items):
    """Create one canonical project stream from existing panel-managed content."""
    rows = []
    seen = set()
    for raw in list(corporate_items or []) + [{**x, '_project_kind':'prototype'} for x in (prototype_items or [])]:
        if not isinstance(raw, dict) or not raw.get('active', True):
            continue
        item = dict(raw)
        kind = _project_kind(item)
        item['_project_kind'] = kind
        slug = _project_slug(item)
        if slug in seen:
            slug = _project_slug(item, True)
        if slug in seen:
            base = slug
            i = 2
            while f'{base}-{i}' in seen:
                i += 1
            slug = f'{base}-{i}'
        item['_project_slug'] = slug
        seen.add(slug)
        rows.append(item)
    return rows


def project_public_url(item, prefix=''):
    return f'{prefix}projeler/{_project_slug(item)}/'


def _project_media(item, prefix='../', css_class=''):
    image = str(item.get('image') or '').strip()
    name = esc(item.get('name') or item.get('headline') or 'BG Studio projesi')
    klass = f' {css_class}' if css_class else ''
    if image:
        return f'<div class="project-media{klass}"><img src="{esc(prefix + image)}" alt="{name}" loading="lazy" decoding="async"></div>'
    return f'<div class="project-media project-media-fallback{klass}"><span>BG</span><strong>{name}</strong></div>'


def _project_sector(item):
    return str(item.get('sector') or item.get('category') or _project_kind_label(item)).strip()


def _project_optional(item, *keys):
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, (dict,list)):
            continue
        text = str(value).strip()
        if text:
            return text
    return ''


def _project_quantity(item):
    return _project_optional(item, 'quantity', 'delivered_quantity', 'produced_quantity', 'stand_count')


def _project_metrics(item):
    raw = item.get('metrics') if isinstance(item.get('metrics'), dict) else {}
    aliases = [
        ('NFC taraması', ('nfc_scans','nfc_scan','scans')),
        ('Menü açılışı', ('menu_opens','menu_views','menu_clicks')),
        ('Feedback', ('feedback_count','feedbacks','reviews')),
        ('Google yönlendirmesi', ('google_redirects','google_clicks','google_transfers')),
    ]
    out=[]
    for label, keys in aliases:
        value = None
        for key in keys:
            if key in raw and raw.get(key) not in (None,''):
                value = raw.get(key); break
            if key in item and item.get(key) not in (None,''):
                value = item.get(key); break
        if value in (None,''):
            continue
        try:
            if float(value) < 0:
                continue
        except Exception:
            pass
        out.append((label, str(value)))
    return out


def _project_footer(prefix='../'):
    return f'''<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="{prefix}"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı, özel üretim ve işletme sistemleri.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>bgstudio.3dtr</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20projeleriniz%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="{prefix}urunler/">Ürünler</a><a href="{prefix}ozel-uretim/">Özel Üretim</a><a href="{prefix}kurumsal/">Kurumsal</a><a href="{prefix}nfc-qr/">NFC &amp; QR</a><a href="{prefix}prototip-parca/">Prototip &amp; Parça</a><a href="{prefix}projeler/">Projeler</a><a href="{prefix}iletisim/">İletişim</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>'''


def _project_page_shell(title, description, canonical_path, body_html, prefix='../'):
    canonical = BASE_URL + canonical_path
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(clip_seo_text(description,160))}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(clip_seo_text(description,160))}"><meta property="og:url" content="{canonical}"><link rel="icon" href="{prefix}favicon.ico" sizes="any"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="{prefix}assets/css/styles.css?v={SITE_ASSET_VERSION}"><meta name="robots" content="index,follow"><meta name="color-scheme" content="light"></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header(prefix,'projects')}<main id="main-content" data-projects-v3168>{body_html}</main>{_project_footer(prefix)}<script defer src="{prefix}assets/js/consent.js"></script><script defer src="{prefix}assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="{prefix}assets/js/main.js?v={SITE_ASSET_VERSION}"></script><script defer src="{prefix}assets/js/projects.js?v={SITE_ASSET_VERSION}"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20bir%20proje%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div></body></html>'''


def render_project_index(project_items):
    cards=[]
    counts={'all':len(project_items),'nfc':0,'corporate':0,'prototype':0}
    for idx,item in enumerate(project_items,1):
        kind=_project_kind(item); counts[kind]=counts.get(kind,0)+1
        name=esc(item.get('name') or 'BG Studio')
        headline=esc(item.get('headline') or item.get('name') or 'Proje')
        desc=esc(item.get('description') or '')
        sector=esc(_project_sector(item))
        tags=''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or [])[:4])
        media=_project_media(item,'../','project-index-media')
        cards.append(f'''<article class="project-index-card" data-project-card data-project-kind="{kind}" data-project-motion><a class="project-index-media-link" href="{esc(_project_slug(item))}/" aria-label="{name} projesini incele">{media}</a><div class="project-index-body"><div class="project-index-meta"><span>{idx:02d}</span><small>{esc(_project_kind_label(item))} · {sector}</small></div><h2>{headline}</h2><p>{desc}</p><div class="project-index-tags">{tags}</div><a class="project-index-link" href="{esc(_project_slug(item))}/">Projeyi incele ↗</a></div></article>''')
    filters=[]
    labels=[('all','Tümü'),('nfc','NFC + QR'),('corporate','Kurumsal'),('prototype','Prototip + Parça')]
    for key,label in labels:
        if key!='all' and not counts.get(key): continue
        active=' is-active' if key=='all' else ''
        filters.append(f'<button class="project-filter{active}" type="button" data-project-filter="{key}" aria-pressed="{str(key=="all").lower()}">{label}<span>{counts.get(key,0)}</span></button>')
    body=f'''<section class="project-index-hero"><div class="shell project-index-hero-grid"><div><p class="eyebrow">SAHADAN İŞLER</p><h1>Gerçek ihtiyaçlar.<br>Gerçek teslimler.</h1><p class="lead">Restoranlardan kurumsal üretime, NFC sistemlerinden teknik parçalara kadar tamamlanan BG Studio işlerini tek proje arşivinde incele.</p></div><div class="project-index-stat"><span>Aktif proje kaydı</span><strong>{len(project_items)}</strong><small>Panel ve veri tabanlı saha kayıtlarından üretilir.</small></div></div></section><section class="section-pad shell"><div class="project-filterbar" aria-label="Proje filtreleri">{''.join(filters)}<div class="project-result-count"><strong data-project-count>{len(project_items)}</strong> proje gösteriliyor</div></div><div class="project-index-grid" data-project-grid>{''.join(cards)}</div><div class="project-empty" data-project-empty hidden>Bu filtrede yayınlanmış proje bulunmuyor.</div></section><section class="project-index-cta"><div class="shell"><div><p class="eyebrow">SIRADAKİ PROJE</p><h2>Senin işletmen veya parçan olabilir.</h2><p>Kurumsal üretim, özel parça, prototip veya NFC + QR sistemi için kapsamı gönder.</p></div><a class="primary-cta" href="../teklif/">Teklif Al ↗</a></div></section>'''
    return _project_page_shell('Projeler | BG Studio 3D','BG Studio 3D sahadan işler, kurumsal üretim, NFC + QR ve prototip proje arşivi.','/projeler/',body,'../')


def render_project_detail(item, project_items):
    slug=_project_slug(item)
    name=str(item.get('name') or 'BG Studio')
    headline=str(item.get('headline') or name)
    description=str(item.get('description') or headline)
    sector=_project_sector(item)
    kind_label=_project_kind_label(item)
    quantity=_project_quantity(item)
    need=_project_optional(item,'need','project_need','ihtiyac')
    solution=_project_optional(item,'solution','project_solution','cozum')
    system=_project_optional(item,'system','project_system','sistem')
    delivery=_project_optional(item,'delivery','project_delivery','teslim')
    result=_project_optional(item,'result','project_result','sonuc')
    facts=[('Müşteri',name),('Sektör',sector)]
    if quantity: facts.append(('Üretilen adet',quantity))
    if system: facts.append(('Sistem',system))
    if delivery: facts.append(('Teslim',delivery))
    facts_html=''.join(f'<article><span>{esc(k)}</span><strong>{esc(v)}</strong></article>' for k,v in facts if v)
    tags=''.join(f'<span>{esc(t)}</span>' for t in (item.get('tags') or []))
    story=[]
    if need: story.append(('01','İhtiyaç',need))
    if solution: story.append(('02' if story else '01','BG Studio çözümü',solution))
    if result: story.append((f'{len(story)+1:02d}','Sonuç',result))
    if not story:
        story.append(('01','Proje özeti',description))
    story_html=''.join(f'<article class="project-story-card"><span>{num}</span><h2>{esc(title)}</h2><p>{esc(text)}</p></article>' for num,title,text in story)
    metrics=_project_metrics(item)
    metrics_html=''
    if metrics:
        metrics_html='<section class="section-pad-sm shell"><div class="project-metrics"><div><p class="eyebrow">GERÇEK SİSTEM VERİSİ</p><h2>Kayıtlı proje metrikleri.</h2><p>Yalnızca veri kaydında bulunan değerler gösterilir.</p></div><div class="project-metric-grid">'+''.join(f'<article><strong>{esc(v)}</strong><span>{esc(k)}</span></article>' for k,v in metrics)+'</div></div></section>'
    media=_project_media(item,'../../','project-detail-media')
    kind=_project_kind(item)
    service={'nfc':'../../nfc-qr/','prototype':'../../prototip-parca/','corporate':'../../kurumsal/'}.get(kind,'../../kurumsal/')
    offer={'nfc':'../../teklif/?tur=nfc','prototype':'../../teklif/?tur=prototip','corporate':'../../teklif/?tur=kurumsal'}.get(kind,'../../teklif/')
    related=[x for x in project_items if _project_slug(x)!=slug][:3]
    related_html=''.join(f'<a class="project-related-card" href="../{esc(_project_slug(x))}/">{_project_media(x,"../../","project-related-media")}<span>{esc(_project_kind_label(x))}</span><strong>{esc(x.get("name") or x.get("headline") or "Proje")}</strong></a>' for x in related)
    schema={'@context':'https://schema.org','@type':'CreativeWork','name':headline,'description':description,'creator':{'@type':'Organization','name':'BG Studio 3D','url':BASE_URL},'url':BASE_URL+'/projeler/'+slug+'/'}
    if item.get('image'): schema['image']=BASE_URL+'/'+str(item.get('image')).lstrip('/')
    schema_json=json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json">{schema_json}</script><section class="project-detail-hero"><div class="shell project-detail-grid"><div class="project-detail-copy"><nav class="project-breadcrumb"><a href="../../projeler/">Projeler</a><span>/</span><b>{esc(name)}</b></nav><p class="eyebrow">{esc(kind_label)} · {esc(sector)}</p><h1>{esc(headline)}</h1><p class="lead">{esc(description)}</p><div class="hero-actions"><a class="primary-cta" href="{offer}">Benzer proje için teklif al ↗</a><a class="secondary-cta" href="{service}">İlgili hizmeti incele ↗</a></div></div>{media}</div></section><section class="project-facts-wrap"><div class="shell project-facts">{facts_html}</div></section><section class="section-pad shell"><div class="project-story-grid">{story_html}</div>{('<div class="project-scope"><p class="eyebrow">UYGULAMA KAPSAMI</p><div class="project-scope-tags">'+tags+'</div></div>') if tags else ''}</section>{metrics_html}<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">DİĞER PROJELER</p><h2>Sahadan başka işler.</h2></div><a class="ghost-cta" href="../../projeler/">Tüm projeler ↗</a></div><div class="project-related-grid">{related_html}</div></section><section class="project-detail-cta"><div class="shell"><div><p class="eyebrow">BENZER BİR İHTİYAÇ MI VAR?</p><h2>Kapsamı gönder, üretim yolunu netleştirelim.</h2></div><a class="primary-cta" href="{offer}">Teklif Al ↗</a></div></section>'''
    return _project_page_shell(f'{headline} | BG Studio 3D Proje',description,f'/projeler/{slug}/',body,'../../')


def build_project_pages(project_items):
    root=ROOT/'projeler'
    root.mkdir(parents=True,exist_ok=True)
    (root/'index.html').write_text(render_project_index(project_items),encoding='utf-8')
    keep={'index.html'}
    for item in project_items:
        slug=_project_slug(item)
        folder=root/slug
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(render_project_detail(item,project_items),encoding='utf-8')
        keep.add(slug)
    for child in root.iterdir():
        if not child.is_dir() or child.name in keep:
            continue
        page=child/'index.html'
        if page.exists():
            try:
                text=page.read_text(encoding='utf-8')
            except Exception:
                text=''
            if 'data-projects-v3168' in text:
                import shutil
                shutil.rmtree(child,ignore_errors=True)
    return {'projects':len(project_items),'detail_pages':len(project_items)}


# ==============================================================
# V3.1.69 · CORPORATE / PROTOTYPE / ABOUT / CONTACT
# ==============================================================

def _editorial_page_shell(title, description, canonical_path, body_html, active_key, prefix='../'):
    canonical = BASE_URL + canonical_path
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(clip_seo_text(description,160))}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(clip_seo_text(description,160))}"><meta property="og:url" content="{canonical}"><link rel="icon" href="{prefix}favicon.ico" sizes="any"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="{prefix}assets/css/styles.css?v={SITE_ASSET_VERSION}"><meta name="robots" content="index,follow"><meta name="color-scheme" content="light"></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header(prefix,active_key)}<main id="main-content" class="v3169-page" data-v3169-page="{esc(active_key)}">{body_html}</main>{_project_footer(prefix)}<script defer src="{prefix}assets/js/consent.js"></script><script defer src="{prefix}assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="{prefix}assets/js/main.js?v={SITE_ASSET_VERSION}"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div></body></html>'''


def _corporate_sector(item):
    source = ' '.join(str(item.get(k) or '') for k in ('name','category','headline','description')) + ' ' + ' '.join(str(x) for x in (item.get('tags') or []))
    text = source.casefold()
    checks = [
        ('Restoran', ('restoran','restaurant','kafe','cafe')),
        ('Petshop', ('petshop','pet shop','veteriner')),
        ('Asansör', ('asansör','elevator')),
        ('Otel', ('otel','hotel','konaklama')),
        ('Promosyon', ('promosyon','anahtarlık','kurumsal hediye')),
        ('Teknik üretim', ('teknik','parça','prototip','yedek')),
    ]
    for label, keys in checks:
        if any(key in text for key in keys):
            return label
    return 'Kurumsal'


def render_corporate_page_v3169(items):
    page_copy = read_site_content_v3175()['corporate']
    sectors=[]
    for item in items:
        sector=_corporate_sector(item)
        if sector not in sectors:
            sectors.append(sector)
    sector_html=''.join(f'<span>{esc(x)}</span>' for x in sectors[:8]) or '<span>Kurumsal üretim</span>'
    cards=''.join(render_corporate_case(item, '../') for item in items)
    body=f'''<section class="v3169-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-sector-cloud"><small>ÇALIŞTIĞIMIZ İHTİYAÇ TİPLERİ</small>{sector_html}</div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">SÜREÇ</p><h2>İhtiyaçtan teslimata.</h2></div><p>Kurumsal işlerde ürün biçimi hazır kalıba göre değil, kullanım senaryosuna göre netleşir.</p></div><div class="v3169-process"><article><span>01</span><h3>İhtiyaç</h3><p>Adet, kullanım noktası, ölçü ve marka gereksinimini netleştiririz.</p></article><article><span>02</span><h3>Tasarım</h3><p>Ürünü marka kimliği ve üretim koşullarına göre geliştiririz.</p></article><article><span>03</span><h3>Üretim</h3><p>Onaylanan modeli 3D baskı üretim akışına alırız.</p></article><article><span>04</span><h3>Teslim</h3><p>Kontrol, paketleme ve teslim / kargo adımıyla işi tamamlarız.</p></article></div></section><section class="section-pad shell v3169-reference-section"><div class="split-title"><div><p class="eyebrow">SAHADAN KURUMSAL İŞLER</p><h2>Farklı sektörler. Tek üretim disiplini.</h2></div><p>Yayınlanan kartlar panel ve saha kayıtlarından gelir. Ayrıntısı bulunan işler proje sayfasına bağlanır.</p></div><div class="case-grid">{cards}</div></section><section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">TOPLU ÜRETİM</p><h2>Adedi ve ihtiyacı gönder.</h2><p>Kurumsal anahtarlık, masaüstü ürün, stand veya işletmeye özel parça için kapsamı birlikte netleştirelim.</p></div><a class="primary-cta" href="../teklif/?tur=kurumsal">Toplu sipariş için teklif al ↗</a></div></section>'''
    return _editorial_page_shell('Kurumsal 3D Üretim | BG Studio 3D','İşletmelere özel kurumsal 3D baskı, promosyon, masaüstü ürün ve saha üretimleri. Kuşadası BG Studio 3D.','/kurumsal/',body,'corporate')


def render_prototype_page_v3169(items):
    page_copy = read_site_content_v3175()['prototype']
    cards=''.join(render_managed_case(item, '../') for item in items)
    body=f'''<section class="v3169-hero v3169-tech-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-tech-flow"><span>SORUN</span><i>↓</i><span>MODEL / CAD</span><i>↓</i><span>3D BASKI</span><i>↓</i><span>ÇALIŞAN PARÇA</span></div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">TEKNİK AKIŞ</p><h2>Ölçü. Model. Test. Üretim.</h2></div><p>Parçanın görevi, temas ettiği yüzeyler ve tolerans ihtiyacı üretim kararını belirler.</p></div><div class="v3169-process"><article><span>01</span><h3>İnceleme</h3><p>Mevcut parça, ölçü, fotoğraf veya teknik dosya üzerinden ihtiyaç belirlenir.</p></article><article><span>02</span><h3>Model</h3><p>Gerekirse model revize edilir veya üretime uygun geometri hazırlanır.</p></article><article><span>03</span><h3>3D Baskı</h3><p>Parçanın kullanımına uygun baskı yönü, malzeme ve üretim ayarları seçilir.</p></article><article><span>04</span><h3>Kontrol</h3><p>Uyum ve kullanım amacı kontrol edilerek teslim edilir.</p></article></div></section><section class="section-pad shell v3169-reference-section"><div class="split-title"><div><p class="eyebrow">TEKNİK ÖRNEKLER</p><h2>Çalışan çözümler.</h2></div><p>Panelde yayınlanan prototip ve parça işleri burada otomatik listelenir.</p></div><div class="case-grid">{cards}</div></section><section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">DOSYAN HAZIR MI?</p><h2>STL, 3MF, STEP, PDF veya görselle başlayabiliriz.</h2><p>Ölçü ve kullanım bilgisini ekle. Üretim yolunu birlikte netleştirelim.</p></div><a class="primary-cta" href="../teklif/?tur=prototip">Teknik üretim teklifi al ↗</a></div></section>'''
    return _editorial_page_shell('Prototip ve Parça Üretimi | BG Studio 3D','Prototip, yedek parça ve teknik 3D baskı üretimi. Model, ölçü ve kullanım ihtiyacına göre Kuşadası BG Studio 3D.','/prototip-parca/',body,'prototype')


def render_about_page_v3169():
    page_copy = read_site_content_v3175()['about']
    body='''<section class="v3169-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-brand-panel"><span>TASARIM</span><span>3D ÜRETİM</span><span>PROTOTİP</span><span>İŞLETME SİSTEMLERİ</span></div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">YAKLAŞIM</p><h2>Önce kullanım. Sonra biçim.</h2></div><p>Ürünün nasıl görüneceği kadar nerede, kim tarafından ve hangi üretim koşullarında kullanılacağı da tasarım kararının parçasıdır.</p></div><div class="v3169-about-grid"><article><span>01</span><h3>BG Studio nedir?</h3><p>Fiziksel ürün ve işletme çözümlerini tasarım, 3D üretim ve dijital sistemlerle bir araya getiren bağımsız üretim markası.</p></article><article><span>02</span><h3>Tasarım yaklaşımı</h3><p>Gereksiz form yerine işlev, temiz detay, üretilebilirlik ve marka bütünlüğüne odaklanırız.</p></article><article><span>03</span><h3>Üretim süreci</h3><p>Model, baskı hazırlığı, üretim, kontrol, paketleme ve teslim adımlarını tek akışta yürütürüz.</p></article><article><span>04</span><h3>Atölye mantığı</h3><p>Tek seferlik özel işten tekrar üretilecek kurumsal parçaya kadar ölçeklenebilen çalışma biçimi.</p></article></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">ÜRETİM HATTI</p><h2>Modelden teslimata.</h2></div></div><div class="v3169-process"><article><span>01</span><h3>Model</h3><p>Ürün veya parçanın dijital modeli hazırlanır ya da mevcut dosya kontrol edilir.</p></article><article><span>02</span><h3>Baskı hazırlığı</h3><p>Yön, destek, malzeme, renk ve üretim parametreleri belirlenir.</p></article><article><span>03</span><h3>Üretim</h3><p>3D yazıcıda üretim alınır ve parça kontrol edilir.</p></article><article><span>04</span><h3>Paketleme & teslim</h3><p>Kuşadası elden teslim veya Türkiye geneli kargo akışına geçilir.</p></article></div></section><section class="v3169-architecture"><div class="shell"><div><p class="eyebrow">DİĞER İŞ KOLU</p><h2>BG Studio Architecture</h2><p>Mimarlık, 3D görselleştirme ve proje çalışmalarımız ayrı marka kolunda devam eder.</p></div><a class="secondary-cta" href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture sitesine geç ↗</a></div></section>'''
    return _editorial_page_shell('Hakkımızda | BG Studio 3D','BG Studio 3D; Kuşadası merkezli 3D baskı, özel üretim, prototip, kurumsal ürün ve NFC + QR işletme sistemleri stüdyosu.','/hakkimizda/',body,'about')


def render_contact_page_v3169():
    page_copy = read_site_content_v3175()['contact']
    body='''<section class="v3169-hero v3169-contact-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p></div><div class="v3169-contact-primary"><a href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><small>EN HIZLI İLETİŞİM</small><strong>WhatsApp</strong><span>Mesaj gönder ↗</span></a><a href="https://instagram.com/bgstudio.3dtr" rel="noopener" target="_blank"><small>SOSYAL MEDYA</small><strong>@bgstudio.3dtr</strong><span>Instagram'a git ↗</span></a></div></div></section><section class="section-pad shell"><div class="v3169-contact-grid"><article><span>01</span><h2>Kuşadası</h2><p>BG Studio 3D üretim ve elden teslim süreci Kuşadası merkezlidir.</p></article><article><span>02</span><h2>Elden teslim</h2><p>Uygun siparişlerde Kuşadası elden teslim seçeneği bulunur.</p></article><article><span>03</span><h2>Türkiye geneli kargo</h2><p>Gönderime uygun ürün ve üretimler Türkiye geneline kargolanır.</p></article><article><span>04</span><h2>Teklif</h2><p>Özel üretim ve işletme projelerinde kapsamı form üzerinden düzenli şekilde iletebilirsin.</p><a class="text-cta" href="../teklif/">Teklif formuna geç ↗</a></article></div></section><section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">İLK MESAJDA</p><h2>İşi hızlı netleştirelim.</h2><p>Ürün / parça türü, adet, yaklaşık ölçü, renk ve varsa görsel veya dosya bilgisini paylaşman teklif sürecini hızlandırır.</p></div><a class="primary-cta" href="../teklif/">Teklif talebi gönder ↗</a></div></section>'''
    return _editorial_page_shell('İletişim | BG Studio 3D','BG Studio 3D iletişim. Kuşadası elden teslim, Türkiye geneli kargo, WhatsApp ve Instagram üzerinden 3D baskı ve özel üretim talepleri.','/iletisim/',body,'contact')

# ==============================================================
# V3.1.70 + V3.1.72 COMBINED FINAL EXPERIENCE
# Scenario quote center + SEO/performance/mobile/a11y/footer/legal pass.
# ==============================================================

def render_global_footer(prefix=''):
    return f'''<footer class="footer footer-dark footer-v3171"><div class="shell footer-inner"><div class="footer-brand-row"><a class="brand footer-brand" href="{prefix}"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p>Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı, özel üretim ve işletme sistemleri.</p></div><div class="footer-mega" aria-label="Alt site haritası"><nav aria-label="Ürünler"><strong>ÜRÜNLER</strong><a href="{prefix}urunler/">Tüm Ürünler</a><a href="{prefix}urunler/?sirala=newest">Yeni Ürünler</a><a href="{prefix}urunler/?one-cikan=1">Öne Çıkanlar</a></nav><nav aria-label="Üretim"><strong>ÜRETİM</strong><a href="{prefix}ozel-uretim/">Özel Üretim</a><a href="{prefix}prototip-parca/">Prototip &amp; Parça</a><a href="{prefix}kurumsal/">Kurumsal</a></nav><nav aria-label="İşletmeler"><strong>İŞLETMELER</strong><a href="{prefix}nfc-qr/">NFC &amp; QR</a><a href="{prefix}nfc-qr/restoran/">Restoran</a><a href="{prefix}nfc-qr/hizli-baglanti/">Hızlı Stand</a><a href="{prefix}nfc-qr/feedback/">Feedback</a></nav><nav aria-label="BG Studio"><strong>BG STUDIO</strong><a href="{prefix}hakkimizda/">Hakkımızda</a><a href="{prefix}projeler/">Projeler</a><a href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture ↗</a><a href="{prefix}iletisim/">İletişim</a></nav><nav aria-label="Destek"><strong>DESTEK</strong><a href="{prefix}siparis-bilgilendirme/">Sipariş Bilgilendirme</a><a href="{prefix}gizlilik/">Gizlilik</a><a href="{prefix}kvkk/">KVKK</a><a href="{prefix}teslimat-iade/">Teslimat / İade</a></nav></div><div class="footer-bottom"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır.</p><div class="footer-bottom-links"><a href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank">Instagram</a><a href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D" rel="noopener" target="_blank">WhatsApp</a><button class="footer-consent-button" type="button">Çerez tercihleri</button><span>Kuşadası, Aydın</span></div></div></div></footer>'''


def sync_global_footer():
    pattern = re.compile(r'<footer\b[^>]*class="[^"]*\bfooter\b[^"]*"[^>]*>.*?</footer>', flags=re.I | re.S)
    scanned = changed = 0
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if not pattern.search(text):
            continue
        scanned += 1
        updated = pattern.sub(render_global_footer(_relative_prefix_for_html(html_path)), text, count=1)
        if updated != text:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed}


def _quote_package_options(pricing):
    year = str(pricing.get('year') or '2026')
    rows = pricing.get('special_restaurant_packages') or {}
    opts = [
        '<option value="">Çözüm seç</option>',
        '<option value="baslangic">Başlangıç · 10 masa</option>',
        '<option value="profesyonel">Profesyonel · 15 masa</option>',
        '<option value="premium">Premium · 20 masa</option>',
    ]
    for qty in SPECIAL_RESTAURANT_CAPACITIES:
        if str(qty) in rows:
            opts.append(f'<option value="ozel-kapasite-{qty}">Özel Restoran · {qty} masa</option>')
    opts += [
        '<option value="hizli-stand">Hızlı Bağlantı Standı</option>',
        '<option value="feedback-duo">Premium Feedback Duo</option>',
        '<option value="ozel-kapasite-custom">Farklı kapasite · özel teklif</option>',
    ]
    duo_opts = ''.join(f'<option value="{qty}">{qty} stand · {qty*2} NFC</option>' for qty in FEEDBACK_DUO_CAPACITIES)
    return ''.join(opts), duo_opts, year


def render_quote_center_v3170():
    pricing = active_nfc_pricing()
    package_options, duo_options, year = _quote_package_options(pricing)
    qr = _nfc_money(pricing.get('qr_unit'))
    menu = _nfc_money(pricing.get('menu_design'))
    logo = _nfc_money(pricing.get('logo_design'))
    desc = 'Özel üretim, kurumsal çalışma, prototip ve NFC + QR sistemleri için senaryoya göre değişen BG Studio 3D teklif formu.'
    canonical = BASE_URL + '/teklif/'
    body = f'''<section class="quote-hero"><div class="shell quote-hero-grid"><div><p class="eyebrow">TEKLİF MERKEZİ</p><h1>İhtiyacını seç.<br>Doğru detayları gönder.</h1><p class="lead">Form, seçtiğin çalışma tipine göre yalnız gereken alanları gösterir. Gönderim sonunda düzenli bir WhatsApp özeti hazırlanır.</p></div><div class="quote-hero-note"><strong>Hızlı başlangıç</strong><span>01 · Çalışma tipini seç</span><span>02 · Detayları doldur</span><span>03 · Özeti WhatsApp'tan gönder</span></div></div></section><section class="section-pad shell quote-center" aria-labelledby="quote-type-title"><div class="quote-section-head"><p class="eyebrow">01 · ÇALIŞMA TİPİ</p><h2 id="quote-type-title">Ne için teklif istiyorsunuz?</h2></div><form class="quote-form quote-form-v3170" data-quote-form novalidate><select class="sr-only" name="talep_turu" aria-label="Talep türü" required><option value="kisiye-ozel">Özel Üretim</option><option value="kurumsal">Kurumsal</option><option value="prototip">Prototip / Parça</option><option value="nfc">NFC &amp; QR</option><option value="diger">Diğer</option></select><div class="quote-type-grid" role="group" aria-label="Teklif türü"><button class="quote-type-card" type="button" data-quote-type="kisiye-ozel" aria-pressed="false"><span>01</span><strong>Özel Üretim</strong><small>Fikir, görsel, ölçü veya mevcut üründen üretim.</small></button><button class="quote-type-card" type="button" data-quote-type="kurumsal" aria-pressed="false"><span>02</span><strong>Kurumsal</strong><small>Toplu üretim, markalama ve işletmeye özel ürün.</small></button><button class="quote-type-card" type="button" data-quote-type="prototip" aria-pressed="false"><span>03</span><strong>Prototip / Parça</strong><small>STL, 3MF, STEP, PDF veya ölçüyle teknik üretim.</small></button><button class="quote-type-card" type="button" data-quote-type="nfc" aria-pressed="false"><span>04</span><strong>NFC &amp; QR</strong><small>Restoran, hızlı stand ve feedback çözümleri.</small></button><button class="quote-type-card" type="button" data-quote-type="diger" aria-pressed="false"><span>05</span><strong>Diğer</strong><small>Kapsamı farklı olan talepler.</small></button></div><div class="quote-dynamic" data-quote-dynamic><div class="quote-section-head compact"><p class="eyebrow">02 · DETAYLAR</p><h2>Teklif için gereken bilgiler.</h2></div><div class="quote-form-grid"><div class="field"><label for="quote-name">Ad / Soyad</label><input id="quote-name" name="ad" autocomplete="name" required maxlength="100" placeholder="Adınız"></div><div class="field"><label for="quote-business">İşletme / Marka</label><input id="quote-business" name="isletme" autocomplete="organization" maxlength="120" placeholder="Varsa işletme veya marka adı"></div><div class="field"><label for="quote-city">Şehir</label><input id="quote-city" name="sehir" autocomplete="address-level2" maxlength="80" placeholder="Örn. Kuşadası"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal prototip nfc"><label for="quote-qty">Adet</label><input id="quote-qty" name="adet" inputmode="numeric" min="1" type="number" placeholder="Örn. 50"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal prototip"><label for="quote-size">Yaklaşık ölçü / ebat</label><input id="quote-size" name="olcu" maxlength="100" placeholder="Örn. 120 × 80 × 30 mm"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal prototip nfc"><label for="quote-color">Renk / malzeme tercihi</label><input id="quote-color" name="renk" maxlength="120" placeholder="Örn. Siyah PETG / fark etmez"></div><div class="field field-wide" data-quote-scope="kisiye-ozel"><label for="quote-product-type">Ürün tipi</label><input id="quote-product-type" name="urun_tipi" maxlength="140" placeholder="Örn. masaüstü stand, dekor, aparat, kişiye özel ürün"></div><div class="field" data-quote-scope="kurumsal"><label for="quote-corporate-use">Kullanım / sektör</label><input id="quote-corporate-use" name="kurumsal_kullanim" maxlength="140" placeholder="Örn. promosyon, mağaza, restoran, teknik kullanım"></div><div class="field" data-quote-scope="kurumsal"><label for="quote-branding">Logo / markalama</label><input id="quote-branding" name="kurumsal_markalama" maxlength="140" placeholder="Logo, isim, renk veya ambalaj talebi"></div><div class="field" data-quote-scope="prototip"><label for="quote-prototype-job">Parçanın görevi</label><input id="quote-prototype-job" name="prototip_gorev" maxlength="180" placeholder="Nereye bağlanıyor, ne işe yarıyor?"></div><div class="field" data-quote-scope="prototip"><label for="quote-prototype-material">Tercih edilen malzeme</label><input id="quote-prototype-material" name="prototip_malzeme" maxlength="120" placeholder="PETG, PLA, TPU veya kararsızım"></div></div><section class="quote-nfc-config" data-nfc-quote-config hidden data-quote-scope="nfc"><div class="quote-nfc-head"><div><p class="eyebrow">NFC + QR SİSTEMİ</p><h3>Paket ve kapsam seçimi</h3></div><small>{year} web fiyat yapısı</small></div><div class="quote-form-grid"><div class="field field-wide"><label for="quote-nfc-package">Sistem / paket</label><select id="quote-nfc-package" name="nfc_paket" required>{package_options}</select></div><div class="field" data-feedback-capacity-wrap hidden><label for="quote-feedback-capacity">Feedback Duo kapasitesi</label><select id="quote-feedback-capacity" name="feedback_duo_capacity">{duo_options}</select></div></div><div class="quote-package-summary" data-nfc-package-summary hidden><div><small>SEÇİLİ ÇÖZÜM</small><strong data-nfc-package-title>Çözüm seç</strong><span data-nfc-package-capacity></span></div><div><small data-nfc-price-year>{year} BAŞLANGIÇ</small><strong data-nfc-package-price>Özel teklif</strong><span data-nfc-package-renewal></span></div></div><div class="quote-options"><label><input type="checkbox" name="nfc_qr" data-nfc-option><span><strong>QR sistemi</strong><small data-nfc-qr-copy>{qr} / QR</small></span></label><label><input type="checkbox" name="nfc_menu_design" data-nfc-option><span><strong>Menü Tasarımı</strong><small data-nfc-menu-price-copy>+{menu}</small></span></label><label><input type="checkbox" name="nfc_logo_design" data-nfc-option><span><strong>Logo Tasarımı</strong><small data-nfc-logo-price-copy>+{logo}</small></span></label></div><div class="quote-total" data-nfc-quote-total hidden><span>Seçili toplam</span><strong data-nfc-total-value></strong></div></section><section class="quote-files" data-quote-scope="kisiye-ozel kurumsal"><div><p class="eyebrow">DOSYA / GÖRSEL</p><h3>Referans ekle</h3><p>PNG, JPG, WEBP veya PDF. Her dosya en fazla 15 MB.</p></div><label class="quote-file-drop"><input type="file" data-quote-files accept=".png,.jpg,.jpeg,.webp,.pdf" multiple><span>Görsel veya PDF seç</span><small>Dosya adları teklife eklenir.</small></label></section><section class="quote-files" data-quote-scope="prototip"><div><p class="eyebrow">TEKNİK DOSYA</p><h3>Dosyan varsa ekle</h3><p>STL, 3MF, STEP, STP, PDF veya görsel. Her dosya en fazla 15 MB.</p></div><label class="quote-file-drop"><input type="file" data-quote-files accept=".stl,.3mf,.step,.stp,.pdf,.png,.jpg,.jpeg,.webp" multiple><span>Teknik dosya seç</span><small>Dosyalar web sunucusuna yüklenmez.</small></label></section><input type="hidden" name="dosya_ozeti"><ul class="quote-file-list" data-quote-file-list hidden></ul><p class="quote-security-note">🔒 Dosyalar bu sayfadan sunucuya gönderilmez. WhatsApp açıldığında seçtiğin dosyaları sohbete ayrıca ekle.</p><div class="field field-wide quote-detail-field"><label for="quote-detail">Talebini anlat</label><textarea id="quote-detail" name="detay" rows="6" required maxlength="1800" placeholder="Kullanım amacı, ölçü, adet ve önemli detayları yazın…"></textarea></div><div class="quote-status" role="status" aria-live="polite" data-quote-status></div><button class="primary-cta quote-submit" type="submit" data-quote-submit>Teklif özetini WhatsApp'ta aç ↗</button></div></form></section><section class="quote-trust"><div class="shell"><article><strong>Kuşadası</strong><span>Elden teslim</span></article><article><strong>Türkiye geneli</strong><span>Kargo</span></article><article><strong>Özel üretim</strong><span>İhtiyaca göre teklif</span></article><article><strong>NFC + QR</strong><span>Paket seçimine bağlı canlı hesap</span></article></div></section>'''
    org = {'@context':'https://schema.org','@type':'Service','name':'BG Studio 3D Teklif Merkezi','provider':{'@type':'Organization','name':'BG Studio 3D','url':BASE_URL},'areaServed':'Türkiye','url':canonical}
    schema = json.dumps(org,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Teklif Al | BG Studio 3D</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="Teklif Al | BG Studio 3D"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><meta name="robots" content="index,follow"><meta name="theme-color" content="#f5ede2"><link rel="icon" href="../favicon.ico" sizes="any"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="../assets/css/styles.css?v={SITE_ASSET_VERSION}"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header('../','')}<main id="main-content" class="quote-page-v3170">{body}</main>{render_global_footer('../')}<script defer src="../assets/js/consent.js"></script><script defer src="../assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/main.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/quote-center.js?v={SITE_ASSET_VERSION}"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D" rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div></body></html>'''


def render_legal_page_v3171(slug, title, intro, sections, indexable=True):
    canonical = f'{BASE_URL}/{slug}/'
    blocks = ''.join(f'<article><h2>{esc(head)}</h2><p>{esc(text)}</p></article>' for head,text in sections)
    robots = 'index,follow' if indexable else 'noindex,follow'
    body = f'''<section class="legal-hero"><div class="shell"><p class="eyebrow">BİLGİLENDİRME</p><h1>{esc(title)}</h1><p class="lead">{esc(intro)}</p></div></section><section class="section-pad shell legal-layout"><div class="legal-content">{blocks}</div><aside class="legal-aside"><strong>BG Studio 3D</strong><p>Kuşadası merkezli 3D baskı ve özel üretim.</p><a class="text-cta" href="../iletisim/">İletişime geç ↗</a></aside></section>'''
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | BG Studio 3D</title><meta name="description" content="{esc(clip_seo_text(intro,160))}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="{esc(title)} | BG Studio 3D"><meta property="og:description" content="{esc(clip_seo_text(intro,160))}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><meta name="robots" content="{robots}"><link rel="stylesheet" href="../assets/css/styles.css?v={SITE_ASSET_VERSION}"></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header('../','')}<main id="main-content" class="legal-page-v3171">{body}</main>{render_global_footer('../')}<script defer src="../assets/js/consent.js"></script><script defer src="../assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/main.js?v={SITE_ASSET_VERSION}"></script></body></html>'''


def build_legal_pages_v3171():
    pages = {
        'kvkk': ('KVKK Aydınlatma', 'Web sitesi ve teklif iletişimi kapsamında paylaşılan kişisel verilerin hangi amaçlarla işlendiğine ilişkin temel bilgilendirme.', [
            ('Toplanan bilgiler', 'İletişim veya teklif talebi sırasında ad, iletişim bilgisi, işletme bilgisi ve talebin kapsamı paylaşılabilir. Kart bilgisi bu web sitesinde tutulmaz.'),
            ('İşleme amacı', 'Paylaşılan bilgiler talebi yanıtlamak, üretim veya hizmet kapsamını netleştirmek, teslim ve iletişim sürecini yürütmek amacıyla değerlendirilir.'),
            ('Veri minimizasyonu', 'BG Studio 3D teklif ve sipariş süreci için gerekli olmayan kişisel bilgileri istememeyi hedefler. Web sitesinde çevrimiçi ödeme altyapısı devrede değildir.'),
            ('Başvuru ve iletişim', 'Kişisel verilerle ilgili talepler için BG Studio 3D iletişim kanalları üzerinden başvuru yapılabilir. Yasal saklama yükümlülükleri bulunan kayıtlar ayrı değerlendirilir.'),
        ]),
        'teslimat-iade': ('Teslimat / İade', '3D baskı, özel üretim ve kişiselleştirilen ürünlerde teslim ve iade süreci ürünün niteliğine göre değerlendirilir.', [
            ('Teslim seçenekleri', 'Uygun siparişlerde Kuşadası elden teslim ve Türkiye geneli kargo seçenekleri bulunur. Kesin teslim yöntemi sipariş öncesinde netleştirilir.'),
            ('Üretim süresi', '3D baskı üretim süresi ürün, adet, malzeme ve atölye yoğunluğuna göre değişir. Tahmini süre sipariş onayından önce paylaşılır.'),
            ('Kişiye özel üretimler', 'İsim, logo, ölçü veya müşteriye özgü başka bir detayla üretilen ürünler standart stok ürünü gibi değerlendirilemeyebilir. Üretim öncesi kapsamın doğru onaylanması önemlidir.'),
            ('Hasarlı kargo', 'Kargo kaynaklı hasar görülmesi halinde paket ve ürün görselleriyle mümkün olan en kısa sürede iletişime geçilmesi değerlendirme sürecini hızlandırır.'),
        ]),
        'kisiye-ozel-urun-kosullari': ('Kişiye Özel Ürün Koşulları', 'İsim, logo, ölçü, renk veya işletmeye özgü tasarımla hazırlanan işlerde onaylanan üretim kapsamı esas alınır.', [
            ('Onay', 'Üretim öncesinde isim, logo, ölçü, renk, adet ve diğer kişiselleştirme detaylarının doğru iletilmesi müşterinin sorumluluğundadır.'),
            ('3D baskı yüzeyi', 'Katman izleri 3D baskı üretim yönteminin doğal bir parçasıdır. Ürünün malzeme ve yüzey karakteri sipariş öncesinde değerlendirilebilir.'),
            ('Revizyon', 'Üretim başladıktan sonra tasarım, ölçü veya kişiselleştirme değişiklikleri yeniden üretim gerektirebilir ve ayrıca fiyatlandırılabilir.'),
        ]),
        'mesafeli-satis': ('Mesafeli Satış Altyapısı', 'BG Studio 3D web sitesinde çevrimiçi ödeme ve tamamlanmış checkout akışı henüz devrede değildir.', [('Durum', 'Bu sayfa gelecekte çevrimiçi satış altyapısı etkinleştirildiğinde sözleşme akışına bağlanmak üzere ayrılmıştır. Bugün sahte bir ödeme veya onay akışı gösterilmez.')]),
        'on-bilgilendirme': ('Ön Bilgilendirme Altyapısı', 'Çevrimiçi checkout devreye alınmadan önce ürün, fiyat, teslimat ve cayma koşullarının sipariş öncesi gösterileceği alan için teknik altyapı ayrılmıştır.', [('Durum', 'Mevcut sipariş ve teklif akışı WhatsApp üzerinden netleştirilir. Bu sayfa ödeme sistemi etkinleşene kadar bilgilendirme altyapısı olarak noindex durumundadır.')]),
    }
    built=[]
    for slug,(title,intro,sections) in pages.items():
        folder=ROOT/slug; folder.mkdir(parents=True,exist_ok=True)
        indexable=slug not in ('mesafeli-satis','on-bilgilendirme')
        (folder/'index.html').write_text(render_legal_page_v3171(slug,title,intro,sections,indexable=indexable),encoding='utf-8')
        built.append(slug)
    return built


def _route_from_html_path(html_path):
    rel = html_path.relative_to(ROOT).as_posix()
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-10]
    return '/' + rel


def _schema_script(data, marker):
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'<script type="application/ld+json" data-schema="{marker}">{payload}</script>'


def sync_seo_accessibility_performance_v3171():
    scanned=changed=0
    heading_warnings=[]
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try: text=html_path.read_text(encoding='utf-8')
        except Exception: continue
        scanned += 1
        updated=text
        route=_route_from_html_path(html_path)
        canonical=BASE_URL + (route if route == '/' else route.rstrip('/') + '/')
        title_match=re.search(r'<title>(.*?)</title>',updated,re.I|re.S)
        title=re.sub(r'<[^>]+>','',title_match.group(1)).strip() if title_match else 'BG Studio 3D'
        desc_match=re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',updated,re.I)
        if not desc_match:
            desc_match=re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',updated,re.I)
        desc=(desc_match.group(1).strip() if desc_match else 'BG Studio 3D · 3D baskı, özel üretim, prototip, kurumsal ve NFC + QR çözümleri.')
        if 'rel="canonical"' not in updated and "rel='canonical'" not in updated:
            updated=updated.replace('</title>',f'</title><link rel="canonical" href="{esc(canonical)}">',1)
        if 'name="robots"' not in updated:
            updated=updated.replace('</head>','<meta name="robots" content="index,follow"></head>',1)
        if 'name="theme-color"' not in updated:
            updated=updated.replace('</head>','<meta name="theme-color" content="#f5ede2"></head>',1)
        if 'name="twitter:card"' not in updated:
            card='summary_large_image' if 'property="og:image"' in updated else 'summary'
            og_image_match=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',updated,re.I)
            if not og_image_match:
                og_image_match=re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',updated,re.I)
            twitter=f'<meta name="twitter:card" content="{card}"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(clip_seo_text(desc,160))}">'
            if og_image_match:
                twitter += f'<meta name="twitter:image" content="{esc(og_image_match.group(1))}">'
            updated=updated.replace('</head>',twitter+'</head>',1)
        if 'data-schema="organization"' not in updated:
            org={'@context':'https://schema.org','@type':'Organization','name':'BG Studio 3D','url':BASE_URL,'sameAs':['https://instagram.com/bgstudio.3dtr','https://www.facebook.com/bgstudio.3dtr']}
            updated=updated.replace('</head>',_schema_script(org,'organization')+'</head>',1)
        if html_path == ROOT/'index.html' and 'data-schema="website"' not in updated:
            website={'@context':'https://schema.org','@type':'WebSite','name':'BG Studio 3D','url':BASE_URL}
            local={'@context':'https://schema.org','@type':'LocalBusiness','name':'BG Studio 3D','url':BASE_URL,'telephone':'+90 530 246 69 03','address':{'@type':'PostalAddress','addressLocality':'Kuşadası','addressRegion':'Aydın','addressCountry':'TR'}}
            updated=updated.replace('</head>',_schema_script(website,'website')+_schema_script(local,'local-business')+'</head>',1)
        if route != '/' and 'data-schema="breadcrumb"' not in updated:
            label_map={'urunler':'Ürünler','ozel-uretim':'Özel Üretim','kurumsal':'Kurumsal','nfc-qr':'NFC & QR','restoran':'Restoran Sistemleri','hizli-baglanti':'Hızlı Bağlantı','feedback':'Premium Feedback','premium-plus':'Premium Plus','prototip-parca':'Prototip & Parça','projeler':'Projeler','hakkimizda':'Hakkımızda','iletisim':'İletişim','teklif':'Teklif','gizlilik':'Gizlilik','kvkk':'KVKK','teslimat-iade':'Teslimat / İade','kisiye-ozel-urun-kosullari':'Kişiye Özel Ürün Koşulları'}
            parts=[part for part in route.strip('/').split('/') if part]
            items=[{'@type':'ListItem','position':1,'name':'Ana Sayfa','item':BASE_URL+'/'}]
            current=''
            for pos,part in enumerate(parts,2):
                current += '/' + part
                label=label_map.get(part) or (title.split('|')[0].strip() if part == parts[-1] else part.replace('-',' ').title())
                items.append({'@type':'ListItem','position':pos,'name':label,'item':BASE_URL+current+'/'})
            breadcrumb={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':items}
            updated=updated.replace('</head>',_schema_script(breadcrumb,'breadcrumb')+'</head>',1)
        if '<main' in updated and 'id="main-content"' not in updated:
            updated=re.sub(r'<main\b', '<main id="main-content"', updated, count=1, flags=re.I)
        if '<main' in updated and 'class="skip-link"' not in updated:
            body_match=re.search(r'<body[^>]*>',updated,re.I)
            if body_match:
                pos=body_match.end(); updated=updated[:pos]+'<a class="skip-link" href="#main-content">İçeriğe geç</a>'+updated[pos:]
        img_index=0
        def tune_img(match):
            nonlocal img_index
            tag=match.group(0); img_index += 1
            def add_attr(raw, attr):
                if raw.endswith('/>'):
                    return raw[:-2].rstrip() + ' ' + attr + '/>'
                return raw[:-1].rstrip() + ' ' + attr + '>'
            if 'decoding=' not in tag: tag=add_attr(tag, 'decoding="async"')
            priority=('fetchpriority="high"' in tag or 'loading="eager"' in tag or img_index==1)
            if not priority and 'loading=' not in tag: tag=add_attr(tag, 'loading="lazy"')
            return tag
        updated=re.sub(r'<img\b[^>]*>',tune_img,updated,flags=re.I)
        h1_count=len(re.findall(r'<h1\b',updated,re.I))
        if h1_count != 1:
            heading_warnings.append({'page':html_path.relative_to(ROOT).as_posix(),'h1':h1_count})
        if updated != text:
            html_path.write_text(updated,encoding='utf-8'); changed += 1
    robots='User-agent: *\nAllow: /\nSitemap: '+BASE_URL+'/sitemap.xml\n'
    (ROOT/'robots.txt').write_text(robots,encoding='utf-8')
    return {'scanned':scanned,'changed':changed,'heading_warnings':heading_warnings[:20]}


def audit_v3171_public_pages():
    result={'pages':0,'missing_title':[],'missing_description':[],'missing_canonical':[],'missing_main':[],'missing_alt':[]}
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts: continue
        try: text=html_path.read_text(encoding='utf-8')
        except Exception: continue
        rel=html_path.relative_to(ROOT).as_posix(); result['pages'] += 1
        if '<title>' not in text: result['missing_title'].append(rel)
        if 'name="description"' not in text: result['missing_description'].append(rel)
        if 'rel="canonical"' not in text: result['missing_canonical'].append(rel)
        if '<main' not in text: result['missing_main'].append(rel)
        if re.search(r'<img\b(?![^>]*\balt=)[^>]*>',text,re.I): result['missing_alt'].append(rel)
    return result


# ============================================================
# V3.1.74 · PROJECT / CASE STUDY MANAGEMENT LAYER
# Project metadata lives in persistent AppData `projects` collection.
# Source NFC / Corporate / Prototype records remain untouched.
# ============================================================

def load_project_overrides():
    data = get_collection('projects', [])
    if not isinstance(data, list):
        return []
    return [dict(x) for x in data if isinstance(x, dict) and str(x.get('id') or '').strip()]


def _project_source_id(item):
    kind = _project_kind(item)
    slug = str(item.get('source_slug') or item.get('slug') or item.get('name') or 'proje').strip()
    return f'{kind}:{slug}'


def collect_project_items(corporate_items, prototype_items):
    """Merge persistent project-only overrides without mutating source records."""
    overrides = {str(x.get('id')): x for x in load_project_overrides()}
    rows = []
    seen_slugs = set()
    sources = list(corporate_items or []) + [{**x, '_project_kind':'prototype'} for x in (prototype_items or [])]
    for source_index, raw in enumerate(sources, 1):
        if not isinstance(raw, dict) or not raw.get('active', True):
            continue
        item = dict(raw)
        kind = _project_kind(item)
        item['_project_kind'] = kind
        project_id = _project_source_id(item)
        override = dict(overrides.get(project_id) or {})
        if override and not bool(override.get('project_active', True)):
            continue
        item['_project_id'] = project_id
        item['_project_managed'] = bool(override)
        for key in ('client','title','summary','sector','need','solution','quantity','system','delivery','result','tags','metrics','seo_title','seo_description','cover_image','gallery_images'):
            if key in override:
                item['project_' + key] = override.get(key)
        try:
            item['_project_sort_order'] = int(override.get('sort_order') or 999999) if override else 999999
        except Exception:
            item['_project_sort_order'] = 999999
        item['_project_source_index'] = source_index
        slug = _project_slug(item)
        if slug in seen_slugs:
            slug = _project_slug(item, True)
        if slug in seen_slugs:
            base = slug
            i = 2
            while f'{base}-{i}' in seen_slugs:
                i += 1
            slug = f'{base}-{i}'
        item['_project_slug'] = slug
        seen_slugs.add(slug)
        rows.append(item)
    rows.sort(key=lambda x: (int(x.get('_project_sort_order') or 999999), int(x.get('_project_source_index') or 999999), str(x.get('project_title') or x.get('headline') or x.get('name') or '').casefold()))
    return rows


def _project_media(item, prefix='../', css_class=''):
    image = str(item.get('project_cover_image') or item.get('image') or '').strip()
    name = esc(item.get('project_client') or item.get('name') or item.get('project_title') or item.get('headline') or 'BG Studio projesi')
    klass = f' {css_class}' if css_class else ''
    if image:
        return f'<div class="project-media{klass}"><img src="{esc(prefix + image)}" alt="{name}" loading="lazy" decoding="async"></div>'
    return f'<div class="project-media project-media-fallback{klass}"><span>BG</span><strong>{name}</strong></div>'


def _project_sector(item):
    if 'project_sector' in item:
        return str(item.get('project_sector') or '').strip()
    return str(item.get('sector') or item.get('category') or _project_kind_label(item)).strip()


def _project_quantity(item):
    if 'project_quantity' in item:
        return str(item.get('project_quantity') or '').strip()
    return _project_optional(item, 'quantity', 'delivered_quantity', 'produced_quantity', 'stand_count')


def _project_metrics(item):
    has_override = 'project_metrics' in item
    raw = item.get('project_metrics') if has_override and isinstance(item.get('project_metrics'), dict) else (item.get('metrics') if isinstance(item.get('metrics'), dict) else {})
    aliases = [
        ('NFC taraması', ('nfc_scans','nfc_scan','scans')),
        ('Menü açılışı', ('menu_opens','menu_views','menu_clicks')),
        ('Feedback', ('feedback_count','feedbacks','reviews')),
        ('Google yönlendirmesi', ('google_redirects','google_clicks','google_transfers')),
    ]
    out=[]
    for label, keys in aliases:
        value = None
        for key in keys:
            if key in raw and raw.get(key) not in (None,''):
                value = raw.get(key); break
            if not has_override and key in item and item.get(key) not in (None,''):
                value = item.get(key); break
        if value in (None,''):
            continue
        try:
            if float(value) < 0:
                continue
        except Exception:
            pass
        out.append((label, str(value)))
    return out


def _project_tags(item):
    values = item.get('project_tags') if 'project_tags' in item else item.get('tags')
    return [str(x).strip() for x in (values or []) if str(x).strip()]


def _project_gallery(item):
    values = item.get('project_gallery_images') if 'project_gallery_images' in item else []
    return [str(x).strip() for x in (values or []) if str(x).strip()][:6]


def render_project_index(project_items):
    cards=[]
    counts={'all':len(project_items),'nfc':0,'corporate':0,'prototype':0}
    for idx,item in enumerate(project_items,1):
        kind=_project_kind(item)
        counts[kind]=counts.get(kind,0)+1
        name=esc(item.get('project_client') or item.get('name') or 'BG Studio')
        headline=esc(item.get('project_title') or item.get('headline') or item.get('name') or 'Proje')
        desc=esc(item.get('project_summary') if 'project_summary' in item else (item.get('description') or ''))
        sector=esc(_project_sector(item))
        tags=''.join(f'<span>{esc(t)}</span>' for t in _project_tags(item)[:4])
        media=_project_media(item,'../','project-index-media')
        cards.append(f'''<article class="project-index-card" data-project-card data-project-kind="{kind}" data-project-motion><a class="project-index-media-link" href="{esc(_project_slug(item))}/" aria-label="{name} projesini incele">{media}</a><div class="project-index-body"><div class="project-index-meta"><span>{idx:02d}</span><small>{esc(_project_kind_label(item))} · {sector}</small></div><h2>{headline}</h2><p>{desc}</p><div class="project-index-tags">{tags}</div><a class="project-index-link" href="{esc(_project_slug(item))}/">Projeyi incele ↗</a></div></article>''')
    filters=[]
    labels=[('all','Tümü'),('nfc','NFC + QR'),('corporate','Kurumsal'),('prototype','Prototip + Parça')]
    for key,label in labels:
        if key!='all' and not counts.get(key):
            continue
        active=' is-active' if key=='all' else ''
        filters.append(f'<button class="project-filter{active}" type="button" data-project-filter="{key}" aria-pressed="{str(key=="all").lower()}">{label}<span>{counts.get(key,0)}</span></button>')
    body=f'''<section class="project-index-hero"><div class="shell project-index-hero-grid"><div><p class="eyebrow">SAHADAN İŞLER</p><h1>Gerçek ihtiyaçlar.<br>Gerçek teslimler.</h1><p class="lead">Restoranlardan kurumsal üretime, NFC sistemlerinden teknik parçalara kadar tamamlanan BG Studio işlerini tek proje arşivinde incele.</p></div><div class="project-index-stat"><span>Aktif proje kaydı</span><strong>{len(project_items)}</strong><small>Ürün Yöneticisindeki proje kayıtlarından üretilir.</small></div></div></section><section class="section-pad shell"><div class="project-filterbar" aria-label="Proje filtreleri">{''.join(filters)}<div class="project-result-count"><strong data-project-count>{len(project_items)}</strong> proje gösteriliyor</div></div><div class="project-index-grid" data-project-grid>{''.join(cards)}</div><div class="project-empty" data-project-empty hidden>Bu filtrede yayınlanmış proje bulunmuyor.</div></section><section class="project-index-cta"><div class="shell"><div><p class="eyebrow">SIRADAKİ PROJE</p><h2>Senin işletmen veya parçan olabilir.</h2><p>Kurumsal üretim, özel parça, prototip veya NFC + QR sistemi için kapsamı gönder.</p></div><a class="primary-cta" href="../teklif/">Teklif Al ↗</a></div></section>'''
    return _project_page_shell('Projeler | BG Studio 3D','BG Studio 3D sahadan işler, kurumsal üretim, NFC + QR ve prototip proje arşivi.','/projeler/',body,'../')


def render_project_detail(item, project_items):
    slug=_project_slug(item)
    name=str(item.get('project_client') or item.get('name') or 'BG Studio')
    headline=str(item.get('project_title') or item.get('headline') or name)
    description=str(item.get('project_summary') if 'project_summary' in item else (item.get('description') or headline))
    sector=_project_sector(item)
    kind_label=_project_kind_label(item)
    quantity=_project_quantity(item)
    need=str(item.get('project_need') if 'project_need' in item else _project_optional(item,'need','project_need','ihtiyac')).strip()
    solution=str(item.get('project_solution') if 'project_solution' in item else _project_optional(item,'solution','project_solution','cozum')).strip()
    system=str(item.get('project_system') if 'project_system' in item else _project_optional(item,'system','project_system','sistem')).strip()
    delivery=str(item.get('project_delivery') if 'project_delivery' in item else _project_optional(item,'delivery','project_delivery','teslim')).strip()
    result=str(item.get('project_result') if 'project_result' in item else _project_optional(item,'result','project_result','sonuc')).strip()
    facts=[('Müşteri',name),('Sektör',sector)]
    if quantity: facts.append(('Üretilen adet',quantity))
    if system: facts.append(('Sistem',system))
    if delivery: facts.append(('Teslim',delivery))
    facts_html=''.join(f'<article><span>{esc(k)}</span><strong>{esc(v)}</strong></article>' for k,v in facts if v)
    tags=''.join(f'<span>{esc(t)}</span>' for t in _project_tags(item))
    story=[]
    if need: story.append(('01','İhtiyaç',need))
    if solution: story.append((f'{len(story)+1:02d}','BG Studio çözümü',solution))
    if result: story.append((f'{len(story)+1:02d}','Sonuç',result))
    if not story:
        story.append(('01','Proje özeti',description))
    story_html=''.join(f'<article class="project-story-card"><span>{num}</span><h2>{esc(title)}</h2><p>{esc(value)}</p></article>' for num,title,value in story)
    metrics=_project_metrics(item)
    metrics_html=''
    if metrics:
        metrics_html='<section class="section-pad-sm shell"><div class="project-metrics"><div><p class="eyebrow">GERÇEK SİSTEM VERİSİ</p><h2>Kayıtlı proje metrikleri.</h2><p>Yalnızca Ürün Yöneticisinde girilen değerler gösterilir.</p></div><div class="project-metric-grid">'+''.join(f'<article><strong>{esc(v)}</strong><span>{esc(k)}</span></article>' for k,v in metrics)+'</div></div></section>'
    media=_project_media(item,'../../','project-detail-media')
    gallery=_project_gallery(item)
    gallery_html=''
    if gallery:
        gallery_cards=''.join(f'<button class="project-gallery-item zoomable-media" type="button" aria-label="{esc(name)} proje görselini büyüt"><img src="../../{esc(src)}" alt="{esc(name)} proje görseli {idx}" loading="lazy" decoding="async"></button>' for idx,src in enumerate(gallery,1))
        gallery_html=f'<section class="section-pad-sm shell project-gallery-section"><div class="split-title"><div><p class="eyebrow">PROJE GÖRSELLERİ</p><h2>Uygulamadan detaylar.</h2></div></div><div class="project-gallery-grid">{gallery_cards}</div></section>'
    kind=_project_kind(item)
    service={'nfc':'../../nfc-qr/','prototype':'../../prototip-parca/','corporate':'../../kurumsal/'}.get(kind,'../../kurumsal/')
    offer={'nfc':'../../teklif/?tur=nfc','prototype':'../../teklif/?tur=prototip','corporate':'../../teklif/?tur=kurumsal'}.get(kind,'../../teklif/')
    related=[x for x in project_items if _project_slug(x)!=slug][:3]
    related_html=''.join(f'<a class="project-related-card" href="../{esc(_project_slug(x))}/">{_project_media(x,"../../","project-related-media")}<span>{esc(_project_kind_label(x))}</span><strong>{esc(x.get("project_client") or x.get("name") or x.get("project_title") or x.get("headline") or "Proje")}</strong></a>' for x in related)
    schema={'@context':'https://schema.org','@type':'CreativeWork','name':headline,'description':description,'creator':{'@type':'Organization','name':'BG Studio 3D','url':BASE_URL},'url':BASE_URL+'/projeler/'+slug+'/'}
    cover=str(item.get('project_cover_image') or item.get('image') or '').strip()
    if cover:
        schema['image']=BASE_URL+'/'+cover.lstrip('/')
    schema_json=json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json">{schema_json}</script><section class="project-detail-hero"><div class="shell project-detail-grid"><div class="project-detail-copy"><nav class="project-breadcrumb"><a href="../../projeler/">Projeler</a><span>/</span><b>{esc(name)}</b></nav><p class="eyebrow">{esc(kind_label)} · {esc(sector)}</p><h1>{esc(headline)}</h1><p class="lead">{esc(description)}</p><div class="hero-actions"><a class="primary-cta" href="{offer}">Benzer proje için teklif al ↗</a><a class="secondary-cta" href="{service}">İlgili hizmeti incele ↗</a></div></div>{media}</div></section><section class="project-facts-wrap"><div class="shell project-facts">{facts_html}</div></section><section class="section-pad shell"><div class="project-story-grid">{story_html}</div>{('<div class="project-scope"><p class="eyebrow">UYGULAMA KAPSAMI</p><div class="project-scope-tags">'+tags+'</div></div>') if tags else ''}</section>{gallery_html}{metrics_html}<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">DİĞER PROJELER</p><h2>Sahadan başka işler.</h2></div><a class="ghost-cta" href="../../projeler/">Tüm projeler ↗</a></div><div class="project-related-grid">{related_html}</div></section><section class="project-detail-cta"><div class="shell"><div><p class="eyebrow">BENZER BİR İHTİYAÇ MI VAR?</p><h2>Kapsamı gönder, üretim yolunu netleştirelim.</h2></div><a class="primary-cta" href="{offer}">Teklif Al ↗</a></div></section>'''
    seo_title=str(item.get('project_seo_title') or f'{headline} | BG Studio 3D Proje').strip()
    seo_description=clip_seo_text(item.get('project_seo_description') or description,160)
    return _project_page_shell(seo_title,seo_description,f'/projeler/{slug}/',body,'../../')


def build_site(nfc_family_theme_overrides=None):
    # V3.1.38: every reference page uses the same explicit card-tone source.
    ensure_explicit_reference_themes()
    # Kalıcı AppData kasasını her build öncesinde repo çıktısına yansıt.
    export_to_repo()
    products = load_products()
    active = [p for p in products if p.get('active', True)]

    cat_path = ROOT / 'urunler/index.html'
    cat = cat_path.read_text(encoding='utf-8')
    site_copy = website_copy_settings()
    catalog_intro = esc(site_copy.get('catalog_intro') or default_website_copy()['catalog_intro'])
    cat = re.sub(r'(<section\s+class="catalog-hero\s+shell">.*?<h1>Atölyeden çıkanlar\.</h1><p>).*?(</p>)', lambda m: m.group(1) + catalog_intro + m.group(2), cat, count=1, flags=re.S)
    cards = '\n'.join(render_card(p, '../', catalog=True, catalog_index=index) for index, p in enumerate(active, 1))
    cat = replace_between(cat, '<!-- PRODUCT_MANAGER:CATALOG_START -->', '<!-- PRODUCT_MANAGER:CATALOG_END -->', cards)

    # V3.1.64: premium catalog controls remain fully data-driven.
    present_categories = list(CATEGORY_ORDER)
    present_categories += sorted(
        {p.get('category') for p in active if p.get('category') and p.get('category') not in present_categories},
        key=lambda c: category_label({'category': c})
    )
    category_counts = {category: 0 for category in present_categories}
    for product in active:
        category = product.get('category')
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1

    filter_buttons = [
        f'<button aria-pressed="true" class="filter-btn active" data-filter="all" type="button">'
        f'<span class="filter-label">Tümü</span><span class="filter-count" aria-label="{len(active)} ürün">{len(active)}</span></button>'
    ]
    filter_buttons += [
        f'<button aria-pressed="false" class="filter-btn" data-filter="{esc(category)}" type="button">'
        f'<span class="filter-label">{esc(category_label({"category": category}))}</span><span class="filter-count" aria-label="{int(category_counts.get(category, 0))} ürün">{int(category_counts.get(category, 0))}</span></button>'
        for category in present_categories
    ]
    filter_html = '<div aria-label="Ürün kategorileri" class="filter-row catalog-category-row" role="group">' + ''.join(filter_buttons) + '</div>'

    material_map = {}
    for product in active:
        for key, label in catalog_materials(product):
            material_map[key] = label
    global_material_order = [str(item.get('id') or '') for item in load_materials()]
    material_order = [key for key in global_material_order if key in material_map]
    material_order += sorted(key for key in material_map if key not in material_order)
    material_options = ['<option value="">Tüm malzemeler</option>'] + [
        f'<option value="{esc(key)}">{esc(material_map[key])}</option>' for key in material_order
    ]
    featured_count = sum(1 for product in active if product.get('featured'))
    personalizable_count = sum(1 for product in active if catalog_personalizable(product))
    controls_html = (
        '<div class="catalog-tools catalog-tools-v3164" data-catalog-controls="">'
        '<label class="catalog-search" for="product-search"><span>Ürün ara</span>'
        '<input autocomplete="off" id="product-search" placeholder="Örn. lamba, anahtarlık, stand…" type="search"/></label>'
        '<div class="catalog-secondary-controls">'
        '<label class="catalog-select"><span>Sırala</span><select id="catalog-sort">'
        '<option value="recommended">Önerilen sıralama</option>'
        '<option value="newest">Yeni eklenenler</option>'
        '<option value="price-asc">Fiyat: düşükten yükseğe</option>'
        '<option value="price-desc">Fiyat: yüksekten düşüğe</option>'
        '</select></label>'
        + ('<label class="catalog-select"><span>Malzeme</span><select id="catalog-material">' + ''.join(material_options) + '</select></label>' if material_map else '') +
        f'<button aria-pressed="false" class="catalog-toggle" data-catalog-flag="featured" type="button">Öne çıkanlar <span class="filter-count">{featured_count}</span></button>'
        f'<button aria-pressed="false" class="catalog-toggle" data-catalog-flag="personalizable" type="button">Kişiselleştirilebilir <span class="filter-count">{personalizable_count}</span></button>'
        '</div>'
        f'<div class="catalog-result-line"><p aria-live="polite" class="catalog-count" id="catalog-count" role="status">{len(active)} ürün gösteriliyor</p>'
        '<button class="catalog-reset" data-catalog-reset="" hidden type="button">Filtreleri temizle</button></div>'
        '</div>'
    )

    catalog_controls = '<!-- BGSTUDIO:CATALOG_CONTROLS_START -->\n' + filter_html + controls_html + '\n<!-- BGSTUDIO:CATALOG_CONTROLS_END -->'
    if '<!-- BGSTUDIO:CATALOG_CONTROLS_START -->' in cat:
        cat = replace_between(cat, '<!-- BGSTUDIO:CATALOG_CONTROLS_START -->', '<!-- BGSTUDIO:CATALOG_CONTROLS_END -->', filter_html + controls_html)
    else:
        existing_filter = re.search(r'<div aria-label="Ürün kategorileri" class="filter-row" role="group">.*?</div>', cat, flags=re.S)
        existing_tools = re.search(r'<div class="catalog-tools">.*?</div>', cat, flags=re.S)
        if existing_filter and existing_tools and existing_filter.start() < existing_tools.end():
            cat = cat[:existing_filter.start()] + catalog_controls + cat[existing_tools.end():]
        elif existing_filter:
            cat = cat[:existing_filter.start()] + catalog_controls + cat[existing_filter.end():]
        else:
            grid_marker = '<!-- PRODUCT_MANAGER:CATALOG_START -->'
            cat = cat.replace(grid_marker, catalog_controls + '\n' + grid_marker, 1)

    cat = re.sub(
        r'<section(\s+class="[^"]*\bcatalog\b[^"]*"[^>]*)>',
        lambda m: '<section' + (m.group(1) if 'data-catalog-v3164' in m.group(1) else m.group(1) + ' data-catalog-v3164=""') + '>',
        cat,
        count=1,
        flags=re.I,
    )
    cat_path.write_text(cat, encoding='utf-8')

    home_path = ROOT / 'index.html'
    home = home_path.read_text(encoding='utf-8')
    featured = [p for p in active if p.get('featured')]
    homecards = '\n'.join(render_card(p, '') for p in featured)
    home = replace_between(home, '<!-- PRODUCT_MANAGER:FEATURED_START -->', '<!-- PRODUCT_MANAGER:FEATURED_END -->', homecards)
    home_path.write_text(home, encoding='utf-8')

    nfc_items = resolve_nfc_items()
    nfc_path = ROOT / 'nfc-qr/index.html'
    nfc_html = nfc_path.read_text(encoding='utf-8')
    # V3.1.43+: canonical platform/package content, independent from references.
    nfc_pricing = active_nfc_pricing()
    nfc_html = rebuild_nfc_platform_sections(nfc_html, theme_overrides=nfc_family_theme_overrides)
    nfc_html = sync_nfc_offer_schema(nfc_html, nfc_pricing)
    nfc_cards = '\n'.join(render_nfc_case(x, '../') for x in nfc_items)
    # V3.1.42: rebuild the *entire* reference section from persistent AppData.
    # This prevents any future static nfc-qr/index.html patch from downgrading
    # the live reference list to an older subset.
    nfc_html = rebuild_nfc_reference_section(nfc_html, nfc_cards)
    # V3.1.67 main flow: Hero -> Sahadan İşler -> Stand Şeması -> solution hub.
    nfc_html = ensure_nfc_v3167_stand_schema_after_references(nfc_html)
    validate_nfc_reference_output(nfc_html, nfc_items)
    validate_reference_theme_output(nfc_html, nfc_items, 'NFC & QR')
    nfc_path.write_text(nfc_html, encoding='utf-8')
    nfc_subpages = build_nfc_v3167_subpages(nfc_items)

    # Corporate-page visibility is independent from NFC publication. Linked NFC
    # records may stay live on NFC & QR (and on the homepage proof area) while
    # being temporarily hidden from the Corporate References page.
    corporate_all_active = [x for x in resolve_corporate_items() if x.get('active', True)]
    corporate_items = [x for x in corporate_all_active if not (x.get('source_kind') == 'nfc' and not bool(x.get('show_in_corporate', True)))]
    corporate_path = ROOT / 'kurumsal/index.html'
    corporate_html = render_corporate_page_v3169(corporate_items)
    validate_reference_theme_output(corporate_html, corporate_items, 'Kurumsal')
    corporate_path.write_text(corporate_html, encoding='utf-8')

    # V3.1.63: the homepage is now a focused editorial product experience.
    # Data-driven product/reference content remains sourced from Product Manager/AppData.
    home_html = rebuild_homepage_v3163(home_path.read_text(encoding='utf-8'), active, featured, corporate_all_active)
    home_path.write_text(home_html, encoding='utf-8')

    # Homepage Sahadan İşler remains independent from the Corporate-page mirror
    # switch, so hiding NFC cards from /kurumsal/ does not erase field proof.
    home_html = home_path.read_text(encoding='utf-8')
    if '<!-- CONTENT_MANAGER:HOME_FIELD_START -->' in home_html and '<!-- CONTENT_MANAGER:HOME_FIELD_END -->' in home_html:
        home_field_cards = '\n'.join(render_home_project_feature(x, i + 1, '') for i, x in enumerate(corporate_all_active[:4]))
        home_html = replace_between(home_html, '<!-- CONTENT_MANAGER:HOME_FIELD_START -->', '<!-- CONTENT_MANAGER:HOME_FIELD_END -->', home_field_cards)
        home_path.write_text(home_html, encoding='utf-8')

    prototype_items = [x for x in load_managed_content(PROTOTYPE_DATA) if x.get('active', True)]
    prototype_path = ROOT / 'prototip-parca/index.html'
    prototype_html = render_prototype_page_v3169(prototype_items)
    validate_reference_theme_output(prototype_html, prototype_items, 'Prototip')
    prototype_path.write_text(prototype_html, encoding='utf-8')

    about_path = ROOT / 'hakkimizda/index.html'
    about_path.parent.mkdir(parents=True, exist_ok=True)
    about_path.write_text(render_about_page_v3169(), encoding='utf-8')

    contact_path = ROOT / 'iletisim/index.html'
    contact_path.parent.mkdir(parents=True, exist_ok=True)
    contact_path.write_text(render_contact_page_v3169(), encoding='utf-8')

    quote_path = ROOT / 'teklif/index.html'
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.write_text(render_quote_center_v3170(), encoding='utf-8')
    legal_pages = build_legal_pages_v3171()

    project_items = collect_project_items(corporate_all_active, prototype_items)
    project_build = build_project_pages(project_items)

    for p in products:
        folder = ROOT / 'urunler' / p['slug']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(render_product_page(p, choose_related(products, p)), encoding='utf-8')

    # V3.1.72: canonical navigation, footer, SEO, accessibility and performance pass.
    nav_sync = sync_site_header_navigation()
    footer_sync = sync_global_footer()
    seo_a11y_sync = sync_seo_accessibility_performance_v3171()
    site_content_state = read_site_content_v3175()

    today = date.today().isoformat()
    static = [
        ('/', 1.0), ('/gizlilik/', .6), ('/hakkimizda/', .6), ('/iletisim/', .8),
        ('/kurumsal/', .9), ('/projeler/', .92), ('/kusadasi-3d-baski/', .95), ('/nfc-qr/', .95), ('/nfc-qr/restoran/', .92), ('/nfc-qr/hizli-baglanti/', .88), ('/nfc-qr/feedback/', .9), ('/nfc-qr/premium-plus/', .72), ('/prototip-parca/', .9), ('/ozel-uretim/', .9),
        ('/siparis-bilgilendirme/', .6), ('/kvkk/', .5), ('/teslimat-iade/', .5), ('/kisiye-ozel-urun-kosullari/', .45), ('/teklif/', .85), ('/urunler/', .9),
    ]
    urls = [(BASE_URL + path, prio) for path, prio in static] + [(f"{BASE_URL}/urunler/{p['slug']}/", .7) for p in active] + [(f"{BASE_URL}/projeler/{_project_slug(item)}/", .72) for item in project_items]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, prio in urls:
        lines.append(f'  <url><loc>{url}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{prio}</priority></url>')
    lines.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    asset_sync = sync_site_asset_versions()
    shell_verify = verify_v3164_public_shell()
    return {'navigation_sync': nav_sync, 'footer_sync': footer_sync, 'seo_a11y_sync': seo_a11y_sync, 'site_content': site_content_state, 'asset_sync': asset_sync, 'shell_verify': shell_verify, 'audit': audit_v3171_public_pages(), 'legal_pages': legal_pages, 'products': len(products), 'active': len(active), 'featured': len(featured), 'nfc_references': len(nfc_items), 'nfc_subpages': nfc_subpages, 'projects': project_build, 'corporate_references': len(corporate_items), 'prototypes': len(prototype_items), 'sitemap_urls': len(urls)}


if __name__ == '__main__':
    print(json.dumps(build_site(), ensure_ascii=False, indent=2))
