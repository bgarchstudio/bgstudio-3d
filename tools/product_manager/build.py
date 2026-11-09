from pathlib import Path
import json, re, html, sys, os
from datetime import date

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

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


def _clip_title_part(text, max_len):
    value = re.sub(r'\s+', ' ', str(text or '')).strip()
    if len(value) <= max_len:
        return value
    clipped = value[:max_len + 1]
    if ' ' in clipped:
        clipped = clipped.rsplit(' ', 1)[0]
    return clipped.rstrip(' |,.;:-–—')


def compact_serp_title(primary, context='', brand='BG Studio 3D', max_len=62):
    """Build a compact title for narrow/mobile SERPs without touching visible H1 copy.

    The contextual phrase is kept only when the full title fits. Otherwise the
    primary entity/product name is retained with the BG Studio 3D brand. Custom
    SEO titles entered in Product Manager remain authoritative elsewhere.
    """
    primary = re.sub(r'\s+', ' ', str(primary or '')).strip()
    context = re.sub(r'\s+', ' ', str(context or '')).strip()
    brand = re.sub(r'\s+', ' ', str(brand or '')).strip()
    candidates = []
    if primary and context and brand:
        candidates.append(f'{primary} | {context} | {brand}')
    if primary and brand:
        candidates.append(f'{primary} | {brand}')
    if primary:
        candidates.append(primary)
    for candidate in candidates:
        if len(candidate) <= max_len:
            return candidate
    suffix = f' | {brand}' if brand else ''
    room = max(18, max_len - len(suffix))
    return _clip_title_part(primary, room) + suffix


def make_seo(p):
    name = str(p.get('name') or '').strip()
    source = str(p.get('card_description') or p.get('description') or '').strip()
    if source and name:
        source = re.sub(r'^' + re.escape(name) + r'\s*[-—–:,.]*\s*', '', source, flags=re.I)
        source = re.sub(r'\s+', ' ', source).strip()
        source = re.sub(r'[.!?]+$', '', source).strip()
    # v3.3.41 — "Ürün, Büyük harfle devam eden cümle" birleşimi bozuk görünüyordu; ad kaynakta yoksa iki noktayla bağlanır.
    title = compact_serp_title(name, '3D Baskı') if name else ''
    suffix = '3D baskı ile üretilir, Türkiye geneli kargo.'
    if source:
        lead = f"{source}." if name and name.casefold() in source.casefold() else f"{name}: {source}."
        description = f"{lead} {suffix}"
    else:
        description = f"{name}: {suffix}"
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


def order_option_prices(p):
    """Read prices from options labeled like '40 cm · 549 TL'."""
    prices = {}
    for option in legacy_order_options(p):
        _, separator, label = option.rpartition(' · ')
        if separator and label.endswith(' TL'):
            price = canonical_price_value(label)
            if price:
                prices[option] = price
    return prices


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
        'hero_lead': '3D baskı ürünleri, özel üretim, prototip ve işletmeler için NFC + QR menü ve yorum standları.',
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


RESPONSIVE_IMAGE_WIDTHS_V3183 = (480, 800)


def _responsive_variant_path(raw, width):
    raw = str(raw or '').strip()
    if not raw:
        return ''
    src = Path(raw)
    return src.with_name(f'{src.stem}-{int(width)}.webp').as_posix()


def _ensure_responsive_variant(raw, width):
    """Create a lightweight WebP derivative when Pillow is available.
    Existing derivatives are reused. Failure is non-fatal so Product Manager
    still builds normally on machines without Pillow.
    """
    raw = str(raw or '').strip()
    if not raw:
        return ''
    variant_rel = _responsive_variant_path(raw, width)
    source = ROOT / raw
    target = ROOT / variant_rel
    if target.exists() and source.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return variant_rel
    if not source.exists() or PILImage is None:
        return variant_rel if target.exists() else ''
    try:
        with PILImage.open(source) as im:
            ow, oh = im.size
            if ow <= width:
                return ''
            nh = max(1, round(oh * (width / ow)))
            work = im.convert('RGBA') if im.mode in ('RGBA', 'LA', 'P') else im.convert('RGB')
            work = work.resize((int(width), int(nh)), PILImage.Resampling.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = dict(format='WEBP', quality=78, method=6)
            if work.mode == 'RGBA':
                save_kwargs['lossless'] = False
            work.save(target, **save_kwargs)
            return variant_rel
    except Exception:
        return variant_rel if target.exists() else ''


def _responsive_srcset_for_product(product, prefix=''):
    raw = str(product.get('main_image') or '').strip()
    if not raw:
        return ''
    entries = []
    for width in RESPONSIVE_IMAGE_WIDTHS_V3183:
        variant = _ensure_responsive_variant(raw, width)
        if variant:
            entries.append(f'{prefix}{variant} {width}w')
    original_width = int(product.get('main_image_width') or 1000)
    entries.append(f'{prefix}{raw} {original_width}w')
    return ', '.join(entries)


def _asset_dimensions_v3324(raw):
    raw = str(raw or '').strip().replace('\\','/').lstrip('/')
    if not raw or raw.startswith(('http://','https://','//','data:','blob:')):
        return None
    path = ROOT / raw
    if not path.is_file() or PILImage is None:
        return None
    try:
        with PILImage.open(path) as image:
            width, height = image.size
        return (int(width), int(height)) if width and height else None
    except Exception:
        return None


def _responsive_srcset_for_asset_v3324(raw, prefix='', widths=(640, 1200)):
    raw = str(raw or '').strip().replace('\\','/').lstrip('/')
    if not raw or raw.startswith(('http://','https://','//','data:','blob:')):
        return ''
    dims = _asset_dimensions_v3324(raw)
    if not dims:
        return ''
    original_width = int(dims[0])
    entries = []
    for width in widths:
        if int(width) >= original_width:
            continue
        variant = _ensure_responsive_variant(raw, int(width))
        if variant:
            entries.append(f'{prefix}{variant} {int(width)}w')
    entries.append(f'{prefix}{raw} {original_width}w')
    return ', '.join(entries)


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


def render_home_product_picture(product, prefix='', eager=False, css_class='', sizes='100vw'):
    name = esc(product.get('name') or 'BG Studio 3D ürünü')
    sources = _picture_sources_for_product(product, prefix)
    fallback = sources.get('fallback') or prefix + 'assets/brand/bgstudio3d-monogram.webp'
    width = int(product.get('main_image_width') or 1000)
    height = int(product.get('main_image_height') or 760)
    responsive = _responsive_srcset_for_product(product, prefix)
    source_html = ''
    if sources.get('avif'):
        source_html += f'<source srcset="{esc(sources["avif"])}" type="image/avif"/>'
    if sources.get('webp') and sources.get('webp') != fallback:
        source_html += f'<source srcset="{esc(sources["webp"])}" type="image/webp"/>'
    loading = 'eager' if eager else 'lazy'
    priority = ' fetchpriority="high"' if eager else ''
    klass = f' class="{esc(css_class)}"' if css_class else ''
    srcset_attr = f' srcset="{esc(responsive)}" sizes="{esc(sizes)}"' if responsive else ''
    return f'<picture{klass}>{source_html}<img alt="{name}" decoding="async" height="{height}" loading="{loading}" src="{esc(fallback)}" width="{width}"{srcset_attr}{priority}/></picture>'


def render_home_showcase_product(product, index=0):
    name = esc(product.get('name') or '')
    href = esc('urunler/' + str(product.get('slug') or '').strip('/') + '/')
    label = esc(category_label(product))
    price_html = card_price_html(product)
    picture = render_home_product_picture(product, '', eager=False, css_class='home-showcase-picture', sizes='(max-width: 760px) calc(100vw - 24px), (max-width: 1100px) 50vw, 34vw')
    return (
        f'<article class="home-showcase-card home-motion" data-home-motion data-product-carousel-card>'
        f'<a class="home-showcase-media" href="{href}">{picture}</a>'
        f'<div class="home-showcase-body"><div class="home-showcase-top"><span>{label}</span>{price_html}</div>'
        f'<h3><a href="{href}">{name}</a></h3>'
        f'<a class="home-showcase-link" href="{href}" aria-label="{name} ürününü incele">Ürünü incele ↗</a></div></article>'
    )


def render_home_project_feature(item, index, prefix=''):
    raw_name = str(item.get('name') or '').strip()
    name = esc(raw_name)
    headline = esc(item.get('headline') or raw_name)
    desc = esc(item.get('description') or '')
    category_raw = str(item.get('category') or ('NFC / QR saha uygulaması' if item.get('source_kind') == 'nfc' else 'Kurumsal üretim')).strip()
    category = esc(category_raw)
    raw_tags = [str(t).strip() for t in (item.get('tags') or []) if str(t).strip()][:3]
    tags = ''.join(f'<span>{esc(t)}</span>' for t in raw_tags)
    link = esc(project_public_url(item, ''))
    media_path = str(item.get('image') or item.get('profile_image') or '').strip()
    if media_path:
        media = f'<div class="home-project-media"><img alt="{name}" decoding="async" loading="lazy" src="{esc(prefix + media_path)}"/></div>'
    else:
        media = f'<div class="home-project-media home-project-media-fallback"><span>{index:02d}</span><strong>{name or "BG Studio"}</strong></div>'

    fact_candidates = [
        ('Adet', item.get('quantity') or item.get('delivered_quantity') or item.get('produced_quantity') or item.get('stand_count')),
        ('Sistem', item.get('system') or item.get('project_system')),
        ('Teslim', item.get('delivery') or item.get('project_delivery')),
    ]
    facts = []
    for label, value in fact_candidates:
        value = str(value or '').strip()
        if value:
            facts.append(f'<div><small>{esc(label)}</small><strong>{esc(value)}</strong></div>')
        if len(facts) >= 2:
            break
    if not facts:
        facts = [
            f'<div><small>Proje</small><strong>{index:02d}</strong></div>',
            f'<div><small>Kategori</small><strong>{category}</strong></div>',
        ]
    facts_html = ''.join(facts)

    ref_id = reference_identity(item, item.get('source_slug') if item.get('source_kind') == 'nfc' else item.get('slug'))
    return (
        f'<article class="home-project-card home-case-study-v3197 home-motion" data-home-motion data-reference-id="{esc(ref_id)}" data-reference-name="{name}">'
        f'<a class="home-case-study-media-link" href="{link}" aria-label="{name} projesini incele">{media}</a>'
        f'<div class="home-project-body home-case-study-body-v3197">'
        f'<div class="home-project-kicker home-case-study-kicker-v3197"><span>{index:02d}</span><small>{category}</small></div>'
        f'<p class="home-case-study-client-v3197">{name}</p><h3>{headline}</h3><p>{desc}</p>'
        f'<div class="home-case-study-facts-v3197">{facts_html}</div>'
        f'<div class="home-project-tags">{tags}</div>'
        f'<a class="home-project-link" href="{link}">Projeyi incele ↗</a></div></article>'
    )


def render_home_business_marquee_card(item, index, prefix=''):
    """Homepage client/reference logo card sourced from published field records.

    This is intentionally not a testimonial. It only identifies businesses that
    already exist in the managed Sahadan Isler / reference data.
    """
    raw_name = str(item.get('name') or '').strip()
    name = esc(raw_name or 'BG Studio referansi')
    category_raw = str(item.get('category') or ('NFC / QR' if item.get('source_kind') == 'nfc' else 'Kurumsal üretim')).strip()
    category = esc(category_raw)
    href = esc(project_public_url(item, prefix))
    media_path = str(item.get('profile_image') or item.get('logo') or item.get('business_logo') or item.get('image') or '').strip()
    initials = ''.join(part[:1] for part in raw_name.split()[:2]).upper() or 'BG'
    if media_path:
        media = f'<span class="home-client-mark-v3199r1"><img src="{esc(prefix + media_path)}" alt="" loading="lazy" decoding="async"/></span>'
    else:
        media = f'<span class="home-client-mark-v3199r1 home-client-mark-fallback-v3199r1" aria-hidden="true">{esc(initials)}</span>'
    return (
        f'<a class="home-client-card-v3199r1" href="{href}">'
        f'{media}<span class="home-client-copy-v3199r1"><small>SAHADAN REFERANS</small><strong>{name}</strong><em>{category}</em></span>'
        f'<span class="home-client-arrow-v3199r1" aria-hidden="true">↗</span></a>'
    )


def render_contextual_business_marquee(items, eyebrow, title, description, prefix='../', context='general'):
    """Render a page-specific client/reference marquee from real managed records.

    No testimonial copy is invented. Items are deduplicated by business name and
    keep their canonical project links. The caller decides the source list, so
    NFC, Corporate and Homepage rails never leak records across contexts.
    """
    selected = []
    seen = set()
    for item in (items or []):
        if not item or not item.get('active', True):
            continue
        raw_name = re.sub(r'\s+', ' ', str(item.get('name') or '').strip())
        key = raw_name.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= 18:
            break
    if not selected:
        return ''
    cards = ''.join(render_home_business_marquee_card(item, index + 1, prefix) for index, item in enumerate(selected))
    is_static = len(selected) <= 1
    loop = (
        f'<div class="home-client-marquee-group-v3199r1">{cards}</div>'
        + ('' if is_static else f'<div class="home-client-marquee-group-v3199r1" aria-hidden="true" inert>{cards}</div>')
    )
    safe_context = re.sub(r'[^a-z0-9-]+', '-', str(context or 'general').casefold()).strip('-') or 'general'
    static_class = ' is-static-v3201r1' if is_static else ''
    return (
        f'<section class="context-clients-v3200 context-clients-{esc(safe_context)}-v3200 home-clients-v3199r1 section-pad{static_class}" '
        f'aria-labelledby="context-clients-{esc(safe_context)}-title">'
        f'<div class="shell home-clients-head-v3199r1">'
        f'<div><p class="eyebrow">{esc(eyebrow)}</p><h2 id="context-clients-{esc(safe_context)}-title">{esc(title)}</h2></div>'
        f'<p>{esc(description)}</p></div>'
        f'<div class="home-client-marquee-v3199r1" data-client-marquee data-client-context="{esc(safe_context)}">'
        f'<div class="home-client-fade-v3199r1 home-client-fade-left-v3199r1" aria-hidden="true"></div>'
        f'<div class="home-client-fade-v3199r1 home-client-fade-right-v3199r1" aria-hidden="true"></div>'
        f'<div class="home-client-marquee-track-v3199r1">{loop}</div></div></section>'
    )


def _home_testimonial_text(item):
    """Return a real customer quote when one exists, otherwise a project note.

    We never synthesize customer praise. Managed records may opt into any of the
    supported feedback fields. Existing records without a quote fall back to the
    published project description and are explicitly labelled as a project note.
    """
    quote_keys = (
        'testimonial', 'testimonial_text', 'review_text', 'review_quote',
        'customer_quote', 'customer_feedback', 'feedback_text', 'quote',
    )
    for key in quote_keys:
        value = str(item.get(key) or '').strip()
        if value:
            return value, 'MÜŞTERİ GERİ BİLDİRİMİ', True
    value = str(item.get('description') or item.get('headline') or '').strip()
    return value, 'SAHADAN PROJE NOTU', False


def render_home_testimonial_card(item, index, prefix=''):
    name_raw = str(item.get('name') or 'BG Studio müşterisi').strip()
    name = esc(name_raw)
    text_raw, label_raw, is_quote = _home_testimonial_text(item)
    text_raw = re.sub(r'\s+', ' ', text_raw).strip()
    if len(text_raw) > 240:
        text_raw = text_raw[:237].rstrip() + '…'
    text = esc(text_raw or 'Tamamlanan BG Studio saha uygulaması.')
    label = esc(label_raw)
    category = esc(str(item.get('category') or ('NFC / QR' if item.get('source_kind') == 'nfc' else 'Kurumsal üretim')).strip())
    media_path = str(item.get('profile_image') or item.get('image') or '').strip()
    if media_path:
        avatar = f'<span class="home-testimonial-avatar-v3199"><img src="{esc(prefix + media_path)}" alt="" loading="lazy" decoding="async"/></span>'
    else:
        initials = ''.join(part[:1] for part in name_raw.split()[:2]).upper() or 'BG'
        avatar = f'<span class="home-testimonial-avatar-v3199 home-testimonial-avatar-fallback-v3199" aria-hidden="true">{esc(initials)}</span>'
    href = esc(project_public_url(item, ''))
    quote_attr = ' data-testimonial-quote="true"' if is_quote else ''
    return (
        f'<a class="home-testimonial-card-v3199" href="{href}"{quote_attr}>'
        f'<div class="home-testimonial-card-top-v3199"><span>{label}</span><small>{index:02d}</small></div>'
        f'<p>{text}</p>'
        f'<div class="home-testimonial-person-v3199">{avatar}<span><strong>{name}</strong><small>{category}</small></span></div>'
        f'</a>'
    )


def _home_visual_product(product, position='main', eager=False):
    if not product:
        return f'<div class="home-hero-visual-fallback home-hero-visual-{esc(position)}"><span>BG</span><small>STUDIO 3D</small></div>'
    sizes = '(max-width: 760px) 70vw, (max-width: 1100px) 72vw, 42vw' if position == 'main' else '(max-width: 760px) 1px, (max-width: 1100px) 30vw, 18vw'
    picture = render_home_product_picture(product, '', eager=eager, css_class='home-hero-picture', sizes=sizes)
    name = esc(product.get('name') or 'BG Studio 3D')
    price = esc(active_price_text(product))
    return (
        f'<figure class="home-hero-visual home-hero-visual-{esc(position)}{" home-hero-visual-desktop-extra" if position in ("side-one", "side-two") else ""}">{picture}'
        f'<figcaption><span>{name}</span><small>{price}</small></figcaption></figure>'
    )


def _home_spatial_product_copy(product, index=0):
    if not product:
        return {
            'name': f'BG Studio 3D Seçimi {index + 1}',
            'category': 'BG Studio 3D',
            'price': 'Teklif al',
            'description': 'Kişiye özel 3D üretim, prototip ve işletmelere yönelik fiziksel + dijital çözümler.',
            'href': 'urunler/'
        }
    raw_desc = str(product.get('card_description') or product.get('description') or '').strip()
    return {
        'name': str(product.get('name') or 'BG Studio 3D ürünü'),
        'category': str(category_label(product) or 'BG Studio 3D'),
        'price': str(active_price_text(product) or 'Teklif al'),
        'description': clip_seo_text(raw_desc, 190) if raw_desc else 'BG Studio 3D tarafından tasarlanan ve üretilen seçili ürün.',
        'href': ('urunler/' + str(product.get('slug') or '').strip('/') + '/') if str(product.get('slug') or '').strip('/') else 'urunler/'
    }


def render_home_spatial_product(product, index=0, eager=False):
    active_class = ' is-active' if index == 0 else ''
    hidden = 'false' if index == 0 else 'true'
    tabindex = '0' if index == 0 else '-1'
    copy = _home_spatial_product_copy(product, index)
    if not product:
        return (
            f'<a class="home-spatial-product home-spatial-product-fallback{active_class}" data-spatial-slide data-spatial-index="{index}" '
            f'href="urunler/" aria-hidden="{hidden}" tabindex="{tabindex}">'
            f'<div class="home-spatial-fallback-mark"><span>BG</span><small>STUDIO 3D</small></div></a>'
        )
    picture = render_home_product_picture(
        product,
        '',
        eager=eager,
        css_class='home-spatial-picture',
        sizes='(max-width: 760px) 78vw, (max-width: 1100px) 54vw, 44vw'
    )
    return (
        f'<a class="home-spatial-product{active_class}" data-spatial-slide data-spatial-index="{index}" '
        f'href="{esc(copy["href"])}" aria-label="{esc(copy["name"])} ürününü incele" aria-hidden="{hidden}" tabindex="{tabindex}">'
        f'<div class="home-spatial-media">{picture}</div>'
        f'</a>'
    )


def render_home_spatial_control(product, index=0):
    copy = _home_spatial_product_copy(product, index)
    active_class = ' is-active' if index == 0 else ''
    thumb_src = str((product or {}).get('main_image') or '').strip()
    # V3.3.31: the dock thumb renders ~58x44px; ship a 160px derivative instead
    # of the full product image (PageSpeed flagged ~200 KB per thumb).
    if thumb_src:
        thumb_src = _ensure_responsive_variant(thumb_src, 160) or _ensure_responsive_variant(thumb_src, 480) or thumb_src
    if thumb_src:
        thumb = f'<span class="home-spatial-control-thumb"><img src="{esc(thumb_src)}" alt="" width="160" height="160" loading="lazy" decoding="async"/></span>'
    else:
        thumb = '<span class="home-spatial-control-thumb home-spatial-control-thumb-fallback">BG</span>'
    return (
        f'<button class="home-spatial-control{active_class}" type="button" data-spatial-control="{index}" '
        f'data-spatial-name="{esc(copy["name"])}" data-spatial-category="{esc(copy["category"])}" '
        f'data-spatial-price="{esc(copy["price"])}" data-spatial-description="{esc(copy["description"])}" '
        f'data-spatial-href="{esc(copy["href"])}" aria-pressed="{"true" if index == 0 else "false"}" '
        f'aria-label="{esc(copy["name"])} ürününü göster">'
        f'{thumb}<span class="home-spatial-control-copy"><small>{index + 1:02d}</small><strong>{esc(copy["name"])}</strong></span>'
        f'</button>'
    )

PRINT_STORY_SVG_V3363 = '''<div class="print-story-v3363" data-print-story data-stage="0" aria-hidden="true"><svg viewBox="62 72 276 206" preserveAspectRatio="xMidYMid meet" focusable="false">
<defs>
<pattern id="psGrid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="rgba(246,241,234,.06)" stroke-width="1"/></pattern>
<pattern id="psLayers" width="8" height="3" patternUnits="userSpaceOnUse"><rect width="8" height="3" fill="#ece6dc"/><rect y="2.2" width="8" height=".8" fill="#c8894a" opacity=".55"/></pattern>
<clipPath id="psVaseClip"><path d="M184 236C179 214 168 198 172 180C175 163 189 154 191 138C192 129 188 123 190 119H210C212 123 208 129 209 138C211 154 225 163 228 180C232 198 221 214 216 236Z"/></clipPath>
</defs>
<rect width="400" height="300" fill="url(#psGrid)"/>
<line class="ps-floor" x1="70" y1="236" x2="330" y2="236"/>
<g class="ps-s ps-s0">
<path class="ps-sketch" pathLength="1" d="M184 236C179 214 168 198 172 180C175 163 189 154 191 138C192 129 188 123 190 119H210C212 123 208 129 209 138C211 154 225 163 228 180C232 198 221 214 216 236Z"/>
<path class="ps-sketch ps-sketch-2" pathLength="1" d="M150 120c18-14 34-10 40 4M236 92c14 6 20 18 14 30"/>
<g class="ps-pencil"><path d="M258 168l34-34 8 8-34 34-11 3z"/><path d="M292 134l8 8"/></g>
</g>
<g class="ps-s ps-s1">
<path class="ps-wire" d="M184 236C179 214 168 198 172 180C175 163 189 154 191 138C192 129 188 123 190 119H210C212 123 208 129 209 138C211 154 225 163 228 180C232 198 221 214 216 236Z"/>
<g class="ps-wire ps-rings"><ellipse cx="200" cy="236" rx="16" ry="4"/><ellipse cx="200" cy="214" rx="24" ry="5"/><ellipse cx="200" cy="196" rx="28" ry="5.5"/><ellipse cx="200" cy="178" rx="27" ry="5"/><ellipse cx="200" cy="160" rx="18" ry="4"/><ellipse cx="200" cy="142" rx="10" ry="3"/><ellipse cx="200" cy="120" rx="10" ry="2.5"/></g>
<path class="ps-wire" d="M200 119V236M190 120c-12 40-26 70-6 116M210 120c12 40 26 70 6 116"/>
<g class="ps-dim"><path d="M244 119v117M240 119h8M240 236h8"/><text x="252" y="182">120 mm</text><path d="M172 252h56M172 248v8M228 248v8"/><text x="181" y="268">Ø 56 mm</text></g>
</g>
<g class="ps-s ps-s2">
<path class="ps-proto" transform="translate(100 118) scale(.5)" d="M184 236C179 214 168 198 172 180C175 163 189 154 191 138C192 129 188 123 190 119H210C212 123 208 129 209 138C211 154 225 163 228 180C232 198 221 214 216 236Z"/>
<g class="ps-caliper"><path d="M178 170h94v8h-94z"/><path d="M178 170v-24h8v24M222 170v-24h8v24"/><path d="M262 178v14h10v-14"/></g>
<g class="ps-check"><circle cx="268" cy="118" r="16"/><path d="M260 118l6 6 11-12"/></g>
</g>
<g class="ps-s ps-s3">
<path class="ps-frame" d="M120 236V82h160v154M120 82h160"/>
<g clip-path="url(#psVaseClip)"><rect class="ps-fill" x="160" y="114" width="80" height="122" fill="url(#psLayers)"/></g>
<path class="ps-outline" d="M184 236C179 214 168 198 172 180C175 163 189 154 191 138C192 129 188 123 190 119H210C212 123 208 129 209 138C211 154 225 163 228 180C232 198 221 214 216 236Z"/>
<g class="ps-gantry"><line x1="124" y1="0" x2="276" y2="0" class="ps-rail"/><g transform="translate(200 0)"><g class="ps-head"><rect x="-11" y="-14" width="22" height="14" rx="4"/><path d="M-4 0h8l-4 5z" class="ps-nozzle"/></g></g></g>
</g>
<g class="ps-s ps-s4">
<path class="ps-box-back" d="M150 168h100v68H150z"/>
<path class="ps-vase-mini" d="M192 196c-2-8-6-13-5-19 1-6 6-9 7-14h12c1 5 6 8 7 14 1 6-3 11-5 19z"/>
<path class="ps-box-front" d="M150 196h100v40H150z"/>
<path class="ps-flap ps-flap-l" d="M150 168l-26 18 26 10z"/>
<path class="ps-flap ps-flap-r" d="M250 168l26 18-26 10z"/>
<path class="ps-tape" d="M194 196h12v40h-12z"/>
<g class="ps-route"><circle cx="96" cy="132" r="4"/><path d="M96 132C140 92 250 84 304 112"/><circle cx="304" cy="112" r="4"/><text x="72" y="152">Kuşadası</text><text x="282" y="132">Türkiye</text></g>
</g>
</svg></div>'''


def render_homepage_v3163(active, featured, field_items):
    # V3.1.76: editorial copy and every homepage product placement can be managed without touching code.
    home_copy = read_site_content_v3175()['home']
    hero_products = _homepage_slot_products(active, featured, home_copy.get('hero_product_slugs'), 3)
    hero_main = hero_products[0] if hero_products else None
    hero_side_1 = hero_products[1] if len(hero_products) > 1 else hero_main
    hero_side_2 = hero_products[2] if len(hero_products) > 2 else hero_side_1
    # v3.3.45 — vitrin şeridi üstteki 3 ürünü tekrar etmez ve (otomatik moddayken) tüm öne çıkan ürünleri gösterir;
    # şerit kaydırmalı olduğu için 6 ile sınırlı değildir. Site İçerikleri'nden elle seçilen yuvalar aynen korunur.
    showcase_config = list(home_copy.get('showcase_product_slugs') or [])[:6]
    if any(str(token or '').strip() for token in showcase_config):
        showcase_slots = _homepage_slot_products(active, featured, showcase_config, 6, allow_hide=True)
    else:
        hero_slugs = {str(p.get('slug') or '') for p in hero_products if p}
        showcase_slots = [p for p in (featured or []) if str(p.get('slug') or '') not in hero_slugs]
        if len(showcase_slots) < 6:
            used = hero_slugs | {str(p.get('slug') or '') for p in showcase_slots}
            showcase_slots += [p for p in (active or []) if str(p.get('slug') or '') not in used][:6 - len(showcase_slots)]
    product_cards = '\n'.join(render_home_showcase_product(product, i) for i, product in enumerate(showcase_slots) if product)
    project_cards = '\n'.join(render_home_project_feature(x, i + 1, '') for i, x in enumerate((field_items or [])[:4]))
    production_product = _homepage_single_product(active, featured, home_copy.get('production_product_slug'), fallback_index=1)
    production_visual = _home_visual_product(production_product, 'production', eager=False)
    # V3.1.98: homepage stats are derived only from currently published panel data.
    # No marketing number is hardcoded here.
    home_active_product_count = len(active or [])
    home_personalizable_count = sum(1 for product in (active or []) if catalog_personalizable(product))
    home_field_items = [x for x in (field_items or []) if x.get('active', True)]
    home_field_count = len(home_field_items)
    home_category_count = len({str(product.get('category') or '').strip() for product in (active or []) if str(product.get('category') or '').strip()})
    # V3.1.99-R1: this rail shows real published client/reference names, not testimonials.
    # Deduplicate businesses because an NFC-backed reference can also appear in corporate data.
    client_items = []
    client_seen = set()
    for item in home_field_items:
        client_name = str(item.get('name') or '').strip()
        client_key = re.sub(r'\s+', ' ', client_name).casefold()
        if not client_key or client_key in client_seen:
            continue
        client_seen.add(client_key)
        client_items.append(item)
        if len(client_items) >= 12:
            break
    client_cards = ''.join(render_home_business_marquee_card(item, index + 1, '') for index, item in enumerate(client_items))
    client_loop = (
        f'<div class="home-client-marquee-group-v3199r1">{client_cards}</div>'
        f'<div class="home-client-marquee-group-v3199r1" aria-hidden="true" inert>{client_cards}</div>'
    ) if client_cards else ''

    return f'''<main class="home-v3163" id="main-content">
<section class="home-hero-v3191" aria-labelledby="home-hero-title" data-spatial-hero data-spatial-variant="0">
  <div class="shell home-hero-v3191-shell">
    <div class="home-spatial-visual home-motion" data-home-motion data-spatial-stage aria-label="Öne çıkan BG Studio 3D ürünleri">
      <div class="home-spatial-reactive-glow" aria-hidden="true"></div>
      <div class="home-spatial-orbit home-spatial-orbit-one" aria-hidden="true"></div>
      <div class="home-spatial-orbit home-spatial-orbit-two" aria-hidden="true"></div>
      <div class="home-spatial-orbit home-spatial-orbit-three" aria-hidden="true"></div>
      <div class="home-spatial-slides">
        {render_home_spatial_product(hero_main, 0, eager=True)}
        {render_home_spatial_product(hero_side_1, 1, eager=False)}
        {render_home_spatial_product(hero_side_2, 2, eager=False)}
      </div>
      <div class="home-spatial-stage-controls" aria-label="Ürünler arasında geçiş">
        <button type="button" data-spatial-prev aria-label="Önceki ürünü göster">←</button>
        <button type="button" data-spatial-next aria-label="Sonraki ürünü göster">→</button>
      </div>
      <div class="home-spatial-visual-status"><span class="home-spatial-dot"></span><b data-spatial-status-label>SEÇİLİ ÜRÜN</b><strong data-spatial-status>01 / 03</strong></div>
    </div>

    <div class="home-spatial-info home-motion" data-home-motion data-spatial-info>
      <div class="home-spatial-info-topline">
        <p class="eyebrow">{esc(home_copy["hero_eyebrow"])}</p>
        <span>Tasarım + Üretim</span>
      </div>
      <h1 id="home-hero-title">{esc(home_copy["hero_title"])}</h1>
      <p class="home-hero-lead">{esc(home_copy["hero_lead"])}</p>

      <div class="home-spatial-product-copy">
        <div class="home-spatial-product-kicker"><span data-spatial-category>{esc(_home_spatial_product_copy(hero_main, 0)["category"])}</span><small data-spatial-counter>01 / 03</small></div>
        <h2 data-spatial-name>{esc(_home_spatial_product_copy(hero_main, 0)["name"])}</h2>
        <p data-spatial-description>{esc(_home_spatial_product_copy(hero_main, 0)["description"])}</p>
        <div class="home-spatial-spec-card">
          <div><span>Aktif fiyat</span><strong data-spatial-price>{esc(_home_spatial_product_copy(hero_main, 0)["price"])}</strong></div>
          <div><span>Üretim</span><strong>Kuşadası</strong></div>
        </div>
      </div>

      <div class="hero-actions home-hero-actions-v3191"><a class="primary-cta" href="{esc(home_copy["hero_primary_url"])}">{esc(home_copy["hero_primary_label"])}</a><a class="secondary-cta" href="{esc(home_copy["hero_secondary_url"])}">{esc(home_copy["hero_secondary_label"])}</a></div>
    </div>

    <div class="home-spatial-dock-wrap">
      <div class="home-spatial-progress" aria-hidden="true"><span data-spatial-progress></span></div>
      <div class="home-spatial-dock" role="group" aria-label="Öne çıkan ürün seçimi">
        {render_home_spatial_control(hero_main, 0)}
        {render_home_spatial_control(hero_side_1, 1)}
        {render_home_spatial_control(hero_side_2, 2)}
      </div>
    </div>
    <span class="sr-only" aria-live="polite" data-spatial-live>Seçili ürün: {esc(_home_spatial_product_copy(hero_main, 0)["name"])}</span>
  </div>
</section>

<section class="home-products-v3163 bg-section" aria-labelledby="home-products-title">
  <div class="shell">
    <div class="home-product-carousel-head home-motion" data-home-motion>
      <div class="home-product-carousel-heading"><p class="eyebrow">ÜRÜNLER</p><h2 id="home-products-title">Tasarlandı. Basıldı. Kullanıma hazır.</h2></div>
      <div class="home-product-carousel-actions">
        <a class="text-cta" href="urunler/">Tüm ürünler ↗</a>
        <div class="home-product-carousel-nav" aria-label="Ürün vitrini kontrolleri">
          <span data-product-carousel-status>01 / 01</span>
          <button type="button" data-product-carousel-prev aria-label="Önceki ürün">←</button>
          <button type="button" data-product-carousel-next aria-label="Sonraki ürün">→</button>
        </div>
      </div>
    </div>
    <div class="home-product-carousel-viewport" data-product-carousel-viewport>
      <div class="home-showcase-grid home-product-carousel-track" data-product-carousel-track tabindex="0" aria-label="Öne çıkan ürünler">
<!-- PRODUCT_MANAGER:FEATURED_START -->
{product_cards}
<!-- PRODUCT_MANAGER:FEATURED_END -->
      </div>
    </div>
  </div>
</section>

<section class="home-process-v3200 bg-section" aria-labelledby="home-process-title" data-how-it-works>
  <div class="shell home-process-grid-v3200">
    <div class="home-process-sticky-v3200 home-motion" data-home-motion>
      <div class="home-process-copy-v3200"><p class="eyebrow">NASIL İLERLİYORUZ?</p><h2 id="home-process-title">Fikirden teslimata. Beş net adım.</h2><p>{esc(home_copy["production_lead"])}</p><a class="primary-cta" href="{esc(home_copy["production_cta_url"])}">{esc(home_copy["production_cta_label"])}</a></div>
      <div class="home-process-visual-v3200 home-process-story-v3363">{PRINT_STORY_SVG_V3363}<div class="home-process-visual-badge-v3200"><span data-print-story-label>01 · Fikir</span><strong data-print-story-caption>Fikrin kâğıda dökülür.</strong></div></div>
    </div>
    <div class="home-process-timeline-v3200">
      <div class="home-process-rail-v3200" aria-hidden="true"><span data-how-progress></span></div>
      <article class="home-process-step-v3200 is-active" data-how-step="0" tabindex="0"><span>01</span><div><small>FİKİR</small><h3>İhtiyacı tarif et.</h3><p>Fotoğraf, eskiz, ölçü, örnek ürün veya kısa bir fikirle başlayabiliriz. Nasıl kullanacağını birlikte netleştiririz.</p></div></article>
      <article class="home-process-step-v3200" data-how-step="1" tabindex="0"><span>02</span><div><small>MODELLEME</small><h3>Üretilebilir geometri.</h3><p>Mevcut modeli kontrol eder veya gereken parçayı ölçü, detay ve baskı koşullarına göre modelleriz.</p></div></article>
      <article class="home-process-step-v3200" data-how-step="2" tabindex="0"><span>03</span><div><small>TEST</small><h3>Ölçü, uyum ve malzeme.</h3><p>Gereken işlerde prototip veya baskı testiyle tolerans, renk, bağlantı ve kullanım davranışını kontrol ederiz.</p></div></article>
      <article class="home-process-step-v3200" data-how-step="3" tabindex="0"><span>04</span><div><small>ÜRETİM</small><h3>Onaylanan işi bas.</h3><p>Malzeme, renk, baskı yönü ve üretim ayarları netleşir. Tek adetten toplu siparişe kadar üretime başlarız.</p></div></article>
      <article class="home-process-step-v3200" data-how-step="4" tabindex="0"><span>05</span><div><small>TESLİM</small><h3>Kontrol et. Paketle. Gönder.</h3><p>Son kontrol sonrası Kuşadası elden teslim veya uygun siparişlerde Türkiye geneli kargo ile işi tamamlarız.</p></div></article>
    </div>
  </div>
</section>

<section class="home-business-v3163 bg-section" aria-labelledby="home-business-title">
  <div class="shell home-split-panel home-split-business">
    <figure class="home-business-visual home-motion zoomable-media" data-home-motion tabindex="0" role="button" aria-label="BG Studio NFC stand sistemini büyüt"><img alt="BG Studio NFC restoran stand şeması" decoding="async" height="1254" loading="lazy" src="assets/images/nfc-stand-semasi.webp" width="1254"/></figure>
    <div class="home-split-copy home-motion" data-home-motion><p class="eyebrow">İŞLETME ÇÖZÜMLERİ</p><h2 id="home-business-title">Fiziksel ürünün ötesinde.</h2><p>İşletmeye özel 3D standı NFC, QR, dijital menü, değerlendirme ve yönetim altyapısıyla tek deneyimde birleştiriyoruz.</p><div class="home-business-points"><span>İşletmeye özel fiziksel stand</span><span>NFC + QR erişimi</span><span>Dijital işletme altyapısı</span></div><a class="secondary-cta" href="nfc-qr/">NFC Sistemlerini İncele ↗</a></div>
  </div>
</section>

<section class="home-projects-v3163 home-projects-v3197 bg-section" id="sahadan-isler" aria-labelledby="home-projects-title">
  <div class="shell">
    <div class="home-section-head home-motion" data-home-motion><div><p class="eyebrow">SAHADAN İŞLER</p><h2 id="home-projects-title">Gerçek ihtiyaçlar. Gerçek teslimler.</h2></div><p>Tamamlanan işletme ve üretim projelerinden seçilen uygulamalar.</p></div>
    <div class="home-project-grid home-case-studies-v3197">
<!-- CONTENT_MANAGER:HOME_FIELD_START -->
{project_cards}
<!-- CONTENT_MANAGER:HOME_FIELD_END -->
    </div>
    <div class="home-project-actions"><a class="secondary-cta" href="kurumsal/">Kurumsal işleri gör ↗</a><a class="ghost-cta" href="nfc-qr/">NFC saha çözümleri ↗</a></div>
  </div>
</section>

<section class="home-stats-v3198 bg-section-compact" aria-labelledby="home-stats-title">
  <div class="shell home-stats-shell-v3198">
    <div class="home-stats-head-v3198 home-motion" data-home-motion>
      <div><p class="eyebrow">RAKAMLARLA BG STUDIO</p><h2 id="home-stats-title">BG Studio 3D, tek bakışta.</h2></div>
      <p>Kuşadası atölyemizde ürettiğimiz ürünler ve işletmelere teslim ettiğimiz işler.</p>
    </div>
    <div class="home-stats-grid-v3198">
      <article class="home-stat-card-v3198 home-motion" data-home-motion><span>01</span><strong>{home_active_product_count}</strong><div><b>Katalogdaki ürün</b><small>Sipariş verilebilir tasarımlar</small></div></article>
      <article class="home-stat-card-v3198 home-motion" data-home-motion><span>02</span><strong>{home_personalizable_count}</strong><div><b>Kişiselleştirilebilir</b><small>İsim, renk veya ürün seçeneği</small></div></article>
      <article class="home-stat-card-v3198 home-motion" data-home-motion><span>03</span><strong>{home_field_count}</strong><div><b>Sahadan iş</b><small>İşletmelere teslim edilen projeler</small></div></article>
      <article class="home-stat-card-v3198 home-motion" data-home-motion><span>04</span><strong>{home_category_count}</strong><div><b>Ürün kategorisi</b><small>Dekordan aksesuara ürün grupları</small></div></article>
    </div>
    <div class="home-stats-foot-v3198 home-motion" data-home-motion><span>KUŞADASI MERKEZLİ ÜRETİM</span><i></i><strong>TÜRKİYE GENELİ KARGO</strong></div>
  </div>
</section>

<section class="home-clients-v3199r1 bg-section-compact" aria-labelledby="home-clients-title">
  <div class="shell home-clients-head-v3199r1 home-motion" data-home-motion>
    <div><p class="eyebrow">SAHADAN REFERANSLAR</p><h2 id="home-clients-title">BG Studio ile çalışan işletmeler.</h2></div>
    <p>Restoranlardan kurumsal firmalara, Kuşadası ve çevresinde birlikte çalıştığımız işletmeler.</p>
  </div>
  <div class="home-client-marquee-v3199r1" data-client-marquee>
    <div class="home-client-fade-v3199r1 home-client-fade-left-v3199r1" aria-hidden="true"></div>
    <div class="home-client-fade-v3199r1 home-client-fade-right-v3199r1" aria-hidden="true"></div>
    <div class="home-client-marquee-track-v3199r1">
      {client_loop}
    </div>
  </div>
</section>

<section class="home-reviews-v3328 home-gplace-v3350 bg-section-compact" aria-labelledby="home-reviews-title">
  <div class="shell gplace-card-v3350">
    <a class="gplace-map-v3350" href="{GOOGLE_REVIEWS_URL_V3328}" rel="noopener" target="_blank" aria-label="BG Studio 3D'yi Google Haritalar'da aç">
      <svg class="gplace-map-art-v3350 m-drone" data-drone-map data-level="3" data-views='{{"tr": [-548, -3439, 24104, 18078], "ege": [1315, 5617, 3725, 2794], "kus": [2752, 7026, 548, 411]}}' viewBox="2752 7026 548 411" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false" text-rendering="geometricPrecision"><rect x="-20000" y="-20000" width="80000" height="60000" class="m-sea"/><path class="m-nb" d="M2009 1802 L1876 1749 L1702 1818 L1836 2195 L1776 2299 L1514 2374 L1436 2323 L1293 2384 L1152 2358 L810 2463 L659 2329 L423 2239 L301 2313 L88 2183 L11 2014 L-223 2079 L-273 2011 L-361 2084 L-464 2050 L-510 2168 L-663 2150 L-972 2281 L-1328 2243 L-1471 2357 L-1734 2330 L-1693 2195 L-1713 1923 L-1634 1764 L-1774 1578 L-1821 1373 L-2157 1219 L-2361 961 L-2275 944 L-2155 759 L-2273 598 L-2210 373 L-2271 261 L-2122 162 L-1943 158 L-1888 28 L-1692 -152 L-1664 -279 L-2171 -664 L-2228 -909 L-2356 -1131 L-2301 -1391 L-2089 -1489 L-2075 -1644 L-1981 -1720 L-1610 -1530 L-1618 -1444 L-1769 -1392 L-1807 -1256 L-1765 -1175 L-1112 -1233 L-373 -1054 L-37 -1123 L225 -1041 L508 -1049 L990 -910 L1404 -1025 L1809 -1417 L2769 -1648 L3014 -1571 L3160 -1421 L3433 -1442 L3530 -1328 L3738 -1391 L3814 -1189 L4077 -1067 L4468 -1038 L4496 -753 L4449 -635 L4353 -514 L4187 -600 L3965 -548 L3854 -326 L3730 -283 L3775 -236 L3707 -43 L3717 405 L3542 400 L3549 474 L3428 519 L3451 619 L3332 608 L3235 728 L3249 800 L3257 753 L3429 758 L3527 819 L3522 911 L3602 965 L3567 1038 L3820 1299 L3853 1438 L3629 1407 L3632 1474 L3492 1444 L3338 1538 L3039 1272 L2930 1320 L2790 1284 L2672 1405 L2307 1446 L2238 1511 L2220 1646 L2010 1695ZM18682 831 L18626 503 L18543 364 L18243 286 L18104 14 L18006 24 L17920 -88 L17631 -120 L17419 -227 L17350 -197 L17223 -447 L16967 -545 L17062 -771 L17163 -806 L17552 -707 L17697 -755 L18091 -526 L18495 -469 L18711 -301 L19221 -253 L19562 -330 L19848 -192 L20083 -236 L20270 -138 L20268 -59 L20440 81 L21147 355 L21061 525 L21299 627 L21581 519 L21663 417 L21922 350 L22110 387 L22213 546 L22279 372 L22355 346 L22493 436 L22631 429 L22814 658 L23226 689 L23268 773 L23153 1118 L23427 1257 L23499 1368 L23802 1409 L24002 1519 L24029 1553 L23916 1727 L23764 1764 L23768 1946 L23835 1938 L23900 2109 L24205 2278 L24318 2422 L24216 2668 L24077 2738 L23807 2526 L23523 2564 L23238 2425 L23212 2385 L23276 2330 L22770 2166 L22412 2432 L22264 2417 L22294 2508 L22037 2488 L21969 2552 L21563 2478 L21502 2551 L21096 2648 L20763 2653 L20689 2538 L20522 2558 L20383 2452 L20471 2381 L20125 2100 L20014 2094 L20051 1989 L19815 1990 L19681 2195 L19117 2092 L18969 2209 L18848 2115 L18649 2080 L18926 1650 L18906 1391 L18806 1240ZM22463 2393 L22499 2523 L22680 2600 L22535 2645 L22538 2713 L22803 2805 L22920 2776 L22917 2854 L23117 2992 L23070 3113 L22870 3255 L23037 3583 L23534 3887 L23418 4186 L23162 4164 L23096 4242 L23275 4283 L23356 4425 L23534 4524 L23758 4769 L23933 4734 L24131 4824 L24095 4947 L23952 5026 L24217 5298 L23990 5327 L24095 5485 L24077 5669 L24120 5765 L23971 5705 L23705 5791 L23511 5388 L23541 5251 L23292 5083 L23341 4973 L23300 4814 L22937 4916 L22746 4760 L22623 4795 L22627 4665 L22498 4521 L22214 4616 L21937 4293 L21722 4151 L21401 4188 L20999 4046 L21060 3963 L20921 3716 L20955 3612 L20883 3531 L21044 3343 L21059 3132 L20967 2893 L20774 2768 L20752 2651 L21096 2648 L21502 2551 L21563 2478 L21969 2552 L22037 2488 L22294 2508 L22264 2417ZM23024 3357 L22986 3290 L23075 3293ZM22438 2685 L22478 2767 L22425 2737ZM22463 2393 L22734 2178 L22970 2198 L23276 2330 L23212 2385 L23360 2508 L23576 2571 L23787 2520 L24101 2737 L24237 2640 L24311 2402 L24205 2278 L23900 2109 L23835 1938 L23797 1969 L23754 1883 L23764 1764 L23900 1741 L24029 1553 L24152 1576 L24178 1699 L24368 1608 L24399 1714 L24545 1802 L24682 2020 L24807 2027 L24946 2376 L25252 2512 L25560 2522 L25632 2493 L25630 2403 L25806 2154 L26178 1962 L26382 1617 L26890 2220 L26992 2415 L27058 2720 L27262 2987 L27434 3097 L27434 3284 L27738 3408 L27996 3382 L28199 3505 L28323 3660 L28368 3871 L28191 3720 L27921 3746 L27822 3683 L27741 3791 L27383 3984 L27388 4068 L27317 4112 L27374 4216 L27308 4290 L27308 4607 L27192 4730 L27156 4869 L27292 5059 L27289 5147 L27245 5109 L27289 5195 L27143 5129 L27066 5552 L26930 5651 L26905 5589 L27005 5483 L26919 5444 L26889 5342 L26808 5343 L26758 5690 L26659 5780 L26706 6392 L26414 6446 L26203 6135 L26088 6160 L25998 6073 L25992 5990 L25740 5810 L25812 5672 L26070 5594 L26045 5448 L25904 5346 L25864 5223 L26119 5069 L25716 4614 L25554 4648 L24764 5168 L24675 5334 L24506 5368 L24120 5765 L24077 5669 L24095 5485 L23990 5327 L24217 5298 L23952 5026 L24095 4947 L24131 4824 L23933 4734 L23758 4769 L23534 4524 L23356 4425 L23275 4283 L23096 4242 L23162 4164 L23418 4186 L23534 3887 L23037 3583 L22870 3255 L23070 3113 L23117 2992 L22917 2854 L22920 2776 L22803 2805 L22538 2713 L22535 2645 L22680 2600 L22499 2523ZM23705 5791 L22941 5594 L22802 5319 L22628 5301 L22566 5122 L22414 4992 L22336 4752 L22214 4616 L22498 4521 L22627 4665 L22623 4795 L22746 4760 L22937 4916 L23244 4803 L23324 4831 L23341 4973 L23292 5083 L23541 5251 L23511 5388ZM22249 4704 L22321 4725 L22414 4992 L22557 5109 L22628 5301 L22802 5319 L22941 5594 L23695 5792 L23971 5705 L24163 5754 L24506 5368 L24675 5334 L24764 5168 L25554 4648 L25716 4614 L26119 5069 L25864 5223 L25904 5346 L26045 5448 L26070 5594 L25812 5672 L25740 5810 L25992 5990 L25998 6073 L26088 6160 L26203 6135 L26414 6446 L26706 6392 L26783 7135 L26859 7365 L26989 7527 L27327 7707 L27867 7736 L28153 7855 L28292 8185 L29040 8725 L30031 8984 L32329 8466 L32264 8542 L31893 8572 L31994 8657 L32337 8650 L32344 8361 L32227 7920 L32548 7946 L32906 7783 L33038 7786 L33185 7666 L33227 7371 L33560 7067 L33908 6883 L34194 6834 L34473 6907 L34841 6888 L34845 6749 L34991 6643 L35312 6621 L35651 6738 L35800 6611 L35986 6887 L35995 7045 L36876 7297 L36931 7450 L37096 7513 L37230 7498 L37285 7419 L37451 7500 L37582 7427 L38032 7677 L38142 7658 L38206 7953 L38306 8109 L38409 8123 L38463 8227 L38516 8190 L38917 8364 L39271 8908 L40173 8909 L40152 9300 L40237 9627 L40134 9841 L40255 9949 L40245 10259 L40309 10433 L40196 10779 L40110 10811 L40097 10930 L40153 11057 L40063 11459 L39947 11588 L39934 11707 L39662 11877 L39871 12154 L39601 12171 L39436 12405 L39456 13106 L39614 13216 L39905 13280 L39807 13322 L39804 13417 L39518 13788 L39512 13918 L39805 15052 L39745 15362 L39796 16107 L40744 16278 L40805 16351 L40897 16779 L40870 17014 L39821 18399 L40361 19076 L40356 19215 L40526 19487 L40504 19542 L40612 19781 L40969 20240 L41484 20414 L41718 20679 L41921 20655 L41893 21007 L41980 21707 L41900 22026 L42065 22101 L42377 22038 L42533 22236 L42436 22308 L42473 22554 L42382 22638 L42362 22897 L41913 22898 L41545 23013 L41407 23098 L41377 23295 L41223 23276 L41190 23359 L40904 23484 L40818 24052 L40715 24123 L40671 24800 L40636 24917 L40599 24844 L40603 24919 L40520 24929 L40566 24958 L40442 25117 L40025 24906 L39590 24815 L39498 24574 L39329 24671 L39408 24794 L39213 24672 L39116 24680 L39125 24752 L38986 24688 L38790 24738 L38649 24654 L38389 24640 L38297 24554 L37848 24641 L37608 24415 L37163 24343 L36891 24438 L36784 24411 L36664 24230 L36454 24310 L36437 24160 L35950 24102 L35791 23684 L35842 23567 L35697 23219 L35707 22934 L35636 22609 L35527 22463 L35579 22396 L35461 22383 L35482 22291 L35399 22205 L34900 22118 L34649 22175 L34447 22363 L34147 22406 L34025 22540 L34055 22521 L34053 22597 L33989 22702 L33714 22690 L33188 23106 L33001 23088 L32937 22981 L32748 22953 L32659 22799 L32339 22751 L32011 22808 L31765 22604 L31713 22434 L31257 22254 L30789 21906 L30765 21850 L30865 21772 L30634 21514 L30399 21446 L30143 21234 L29784 21237 L29504 21054 L29473 21096 L29330 20803 L29347 20663 L29123 20253 L29099 19970 L29011 19857 L28899 19835 L28821 19693 L28841 19605 L28924 19671 L28958 19524 L28860 19403 L28645 19399 L28695 19193 L28657 18971 L28374 18683 L28098 18287 L28079 18031 L28020 17926 L27845 17915 L27427 18168 L27369 17981 L27112 17981 L27086 17830 L27020 17887 L26757 17667 L26911 17629 L27066 17715 L27133 17570 L27075 17491 L27028 17532 L27026 17488 L26823 17478 L26784 17528 L26884 17594 L26772 17614 L26693 17716 L26773 17906 L26751 18141 L26453 18122 L26470 18223 L26417 18260 L26257 18215 L26168 18006 L26183 17891 L26073 17752 L25967 17746 L25902 17581 L25763 17551 L25761 16815 L25389 16807 L25396 16229 L25566 15672 L25286 15251 L25190 15192 L25210 15101 L25093 14947 L25102 14847 L24943 14721 L24751 14736 L24082 14151 L23856 14057 L23663 14064 L23688 13914 L23590 13852 L23740 13764 L23727 13636 L23528 13313 L23395 13308 L23478 13229 L23432 13117 L23266 13184 L22993 12686 L22878 12637 L23057 12405 L23072 12163 L22966 12123 L22918 11978 L23012 11908 L23009 11772 L23229 11828 L23148 11591 L23191 11470 L23278 11423 L23288 11326 L23392 11330 L23400 11170 L23461 11078 L23567 11115 L23722 11044 L23742 10897 L23668 10872 L23688 10754 L23517 10508 L23561 10256 L23817 10198 L23915 10075 L23736 10083 L23623 10000 L23282 10065 L23052 9808 L22812 9808 L22842 9677 L22723 9236 L22540 9207 L22451 9053 L22499 8835 L22267 8667 L22333 8558 L22337 8378 L22190 8255 L22243 7990 L21992 7797 L22009 7582 L21958 7514 L22018 7397 L21920 7309 L21843 7325 L21767 7196 L21587 7144 L21868 6526 L21682 6465 L21691 6129 L21633 6077 L21667 5819 L21532 5650 L21570 5397 L21450 5320 L21381 5076 L21790 5020 L21869 4622 L21985 4528ZM22205 8201 L22205 8289 L22337 8378 L22276 8691 L22457 8762 L22511 8865 L22451 9053 L22553 9222 L22723 9236 L22842 9677 L22812 9808 L23052 9808 L23282 10065 L23623 10000 L23736 10083 L23915 10075 L23817 10198 L23561 10256 L23517 10508 L23688 10754 L23668 10872 L23742 10897 L23722 11044 L23567 11115 L23461 11078 L23400 11170 L23392 11330 L23288 11326 L23278 11423 L23191 11470 L23148 11591 L23229 11828 L23009 11772 L23012 11908 L22918 11978 L22966 12123 L23072 12163 L23057 12405 L22878 12637 L22993 12686 L23266 13184 L23432 13117 L23478 13229 L23395 13308 L23528 13313 L23727 13636 L23740 13764 L23590 13852 L23688 13914 L23663 14064 L23856 14057 L24082 14151 L24751 14736 L24943 14721 L25102 14847 L25093 14947 L25210 15101 L25190 15192 L25286 15251 L25566 15672 L25396 16229 L25389 16807 L25761 16815 L25763 17551 L25891 17574 L25967 17746 L26083 17762 L26196 17917 L26165 17997 L26244 18198 L26361 18275 L26199 18286 L25878 18137 L25714 18194 L25676 18050 L25691 18208 L25391 18062 L25045 18071 L24868 18152 L24773 18255 L24492 18978 L24140 19466 L23948 19512 L22123 19317 L19257 16688 L17447 15511 L16047 15235 L16207 15058 L16145 14906 L15918 14940 L15863 14735 L15950 14705 L15640 13480 L17739 12136 L18040 12037 L18302 11490 L18299 10860 L18364 10508 L18477 10283 L18467 10044 L18338 9716 L18382 9303 L18501 9077 L19003 8935 L19587 8313 L19565 8246 L19789 8195 L19958 7903 L20042 7876 L20201 7952 L20395 7880 L20795 8059 L21156 8120 L21355 7962 L21462 7964 L21623 8069 L21637 8162 L21562 8277 L21677 8443 L21741 8341 L22034 8150ZM12334 14358 L12477 14077 L12341 13532 L12512 13353 L12527 13261 L12639 13205 L12514 13104 L12543 13007 L12752 12809 L12992 12847 L13003 12799 L12895 12731 L12916 12675 L13028 12537 L13121 12525 L13262 12321 L13175 12008 L12950 11880 L13082 11719 L12938 11637 L12887 11722 L12567 11690 L12454 11306 L12477 11047 L12559 10923 L12511 10615 L12297 10385 L12425 10154 L12379 10010 L12578 9902 L12604 9983 L12773 10048 L12816 9868 L12992 9808 L13009 9481 L13328 9479 L13182 9129 L13301 8641 L13657 8745 L13754 8932 L13961 8878 L14184 8912 L15037 8528 L15317 8602 L15586 8828 L16149 8874 L16725 8761 L17759 8259 L18604 8294 L19184 8154 L19405 7945 L19554 8064 L19587 8313 L19003 8935 L18501 9077 L18382 9303 L18338 9716 L18467 10044 L18477 10283 L18364 10508 L18299 10860 L18302 11490 L18040 12037 L17739 12136 L15640 13480 L13498 14956 L13025 14869 L12794 14662 L12673 14676 L12539 14433ZM10083 11217 L9977 11450 L9598 11619 L9408 11627 L9272 11725 L9299 11657 L9159 11619 L8992 11696 L8720 11589 L8578 11359 L8515 11098 L8671 11140 L8818 10954 L8899 10987 L8940 10938 L9122 11117 L9504 10972 L9643 11041 L9769 10976 L9816 11231 L9882 11138 L9911 11207ZM10297 11114 L10433 11120 L10517 11249 L10240 11256 L10194 11131ZM10422 11111 L10313 11108 L10273 11033 L10263 11107 L10152 11156 L10088 11159 L10096 11107 L9947 11150 L9905 11098 L9835 11196 L9766 10921 L9658 10973 L9486 10941 L9154 11089 L8996 10955 L9195 10955 L9226 10643 L9781 10740 L10037 10697 L11058 10231 L11036 10299 L10560 10619 L10473 10746 L10356 10764 L10299 10970Z"/><path class="m-isle" d="M-3873 3011 L-3712 3004 L-3634 2982 L-3511 2995 L-3457 2978 L-3417 2939 L-3391 2928 L-3277 2939 L-3228 2981 L-3198 2987 L-3151 2948 L-3124 2946 L-3115 2914 L-3084 2901 L-3027 2913 L-2996 2907 L-2982 2893 L-2976 2850 L-2924 2809 L-2909 2783 L-2855 2725 L-2852 2686 L-2839 2664 L-2777 2626 L-2707 2606 L-2686 2587 L-2670 2608 L-2626 2630 L-2603 2622 L-2563 2587 L-2514 2574 L-2408 2596 L-2401 2625 L-2323 2616 L-2277 2639 L-2244 2641 L-2191 2629 L-2137 2634 L-2093 2625 L-2055 2586 L-2050 2552 L-2033 2548 L-2020 2551 L-2001 2581 L-1967 2604 L-1955 2596 L-1942 2568 L-1932 2514 L-1927 2403 L-1916 2359 L-1883 2331 L-1834 2323 L-1517 2362 L-1471 2357 L-1425 2334 L-1414 2284 L-1398 2269 L-1348 2244 L-1328 2243 L-1286 2283 L-1263 2280 L-1189 2240 L-1081 2243 L-1009 2279 L-972 2281 L-928 2243 L-907 2236 L-817 2239 L-792 2199 L-710 2185 L-663 2150 L-603 2187 L-587 2186 L-547 2150 L-510 2168 L-491 2152 L-496 2064 L-464 2050 L-420 2053 L-388 2063 L-361 2084 L-349 2048 L-292 2013 L-273 2011 L-234 2043 L-234 2075 L-223 2079 L-67 2061 L-45 2031 L11 2014 L34 2033 L47 2070 L54 2120 L89 2156 L88 2183 L105 2198 L158 2201 L151 2215 L218 2227 L301 2313 L322 2314 L332 2293 L332 2250 L423 2239 L636 2332 L659 2329 L676 2351 L742 2389 L789 2450 L810 2463 L861 2465 L1045 2407 L1101 2407 L1122 2392 L1137 2363 L1152 2358 L1249 2365 L1293 2384 L1334 2360 L1384 2353 L1436 2323 L1461 2332 L1493 2366 L1514 2374 L1557 2358 L1599 2359 L1667 2322 L1776 2299 L1818 2209 L1836 2195 L1834 2176 L1803 2131 L1818 2109 L1822 2059 L1811 2034 L1787 2026 L1786 1984 L1770 1937 L1760 1926 L1717 1910 L1704 1892 L1696 1835 L1710 1810 L1733 1804 L1762 1781 L1852 1771 L1876 1749 L1891 1750 L1944 1799 L1967 1806 L2037 1799 L2057 1805 L2087 1831 L2165 1854 L2152 1892 L2275 1973 L2296 1943 L2303 1981 L2299 1997 L2303 2034 L2296 2048 L2308 2068 L2341 2241 L2336 2299 L2312 2337 L2268 2333 L2235 2307 L2180 2365 L2168 2367 L2095 2428 L2076 2437 L2007 2444 L1995 2455 L2012 2480 L1995 2537 L1999 2562 L2012 2586 L1991 2617 L1991 2629 L2015 2640 L1997 2676 L2000 2696 L2024 2743 L2053 2756 L2047 2789 L2012 2804 L2008 2813 L2012 2825 L2037 2849 L1966 2903 L1977 2927 L1953 2930 L1929 2911 L1906 2960 L1898 2960 L1891 2941 L1890 2963 L1876 2969 L1883 2979 L1869 2989 L1876 3014 L1817 3063 L1800 3089 L1791 3126 L1767 3154 L1733 3170 L1692 3166 L1673 3085 L1650 3074 L1650 3065 L1702 3057 L1710 3051 L1703 3037 L1657 3046 L1650 3026 L1642 3026 L1650 3056 L1642 3056 L1591 3016 L1554 3006 L1530 3017 L1452 3010 L1428 3001 L1350 3008 L1210 2973 L1169 2988 L1137 2981 L1081 2944 L1008 2931 L921 2882 L876 2867 L839 2902 L746 2880 L695 2852 L701 2823 L734 2806 L700 2786 L591 2792 L591 2815 L568 2835 L539 2844 L547 2870 L537 2881 L497 2882 L430 2911 L398 2933 L366 2975 L331 3005 L291 2988 L229 3008 L208 2998 L216 2988 L178 2968 L141 2998 L105 2938 L110 2921 L83 2903 L73 2868 L6 2854 L-30 2868 L-39 2882 L-62 2873 L-119 2889 L-140 2920 L-205 2968 L-184 2992 L-185 3003 L-208 3009 L-213 3022 L-202 3035 L-175 3036 L-427 3181 L-468 3190 L-563 3175 L-686 3111 L-721 3103 L-757 3107 L-842 3147 L-880 3190 L-886 3226 L-876 3257 L-857 3278 L-816 3296 L-782 3351 L-775 3377 L-716 3416 L-670 3411 L-641 3446 L-640 3459 L-649 3464 L-725 3474 L-742 3490 L-746 3517 L-738 3554 L-692 3621 L-640 3655 L-587 3669 L-545 3659 L-535 3651 L-535 3637 L-557 3592 L-549 3583 L-557 3573 L-535 3571 L-490 3651 L-454 3688 L-429 3700 L-407 3689 L-351 3708 L-324 3756 L-292 3756 L-197 3881 L-128 3949 L-116 3987 L-152 4015 L-199 4025 L-219 4021 L-234 3975 L-287 3938 L-363 3815 L-407 3794 L-527 3765 L-617 3689 L-730 3679 L-811 3711 L-843 3697 L-877 3743 L-884 3767 L-881 3790 L-859 3843 L-813 3876 L-806 3898 L-790 3916 L-693 3958 L-679 3953 L-661 3960 L-613 4002 L-569 4017 L-557 4034 L-559 4046 L-573 4059 L-572 4073 L-542 4106 L-546 4118 L-565 4125 L-562 4141 L-555 4147 L-535 4139 L-534 4163 L-527 4177 L-561 4214 L-549 4235 L-581 4245 L-578 4253 L-557 4254 L-557 4265 L-636 4261 L-632 4235 L-657 4240 L-655 4216 L-700 4192 L-718 4166 L-741 4169 L-738 4188 L-783 4106 L-774 4069 L-791 4058 L-806 4023 L-903 3895 L-940 3870 L-1052 3857 L-1113 3823 L-1163 3809 L-1207 3811 L-1244 3834 L-1271 3881 L-1274 3908 L-1245 3989 L-1205 3998 L-1129 4106 L-1097 4141 L-983 4202 L-909 4220 L-903 4254 L-880 4283 L-824 4297 L-873 4322 L-968 4307 L-1127 4240 L-1154 4235 L-1248 4254 L-1225 4196 L-1248 4154 L-1257 4120 L-1308 4054 L-1293 4008 L-1288 3955 L-1294 3905 L-1316 3870 L-1461 3808 L-1480 3813 L-1537 3771 L-1612 3744 L-1632 3708 L-1683 3669 L-1723 3656 L-1766 3659 L-1756 3637 L-1764 3614 L-1797 3573 L-1789 3565 L-1829 3520 L-1839 3497 L-1815 3487 L-1707 3476 L-1662 3426 L-1669 3401 L-1707 3378 L-1699 3352 L-1716 3317 L-1742 3298 L-1772 3294 L-1803 3305 L-1796 3331 L-1807 3369 L-1845 3401 L-1886 3391 L-1908 3405 L-1922 3423 L-1926 3444 L-1917 3468 L-1932 3459 L-1932 3479 L-1947 3468 L-1951 3485 L-1960 3484 L-1985 3462 L-2001 3462 L-2018 3477 L-2020 3494 L-1999 3505 L-2016 3510 L-2026 3538 L-2052 3525 L-2079 3526 L-2105 3545 L-2078 3578 L-2075 3621 L-2038 3663 L-2018 3669 L-2015 3683 L-2059 3765 L-2092 3862 L-2092 3878 L-2134 3967 L-2137 3999 L-2111 4077 L-2113 4124 L-2095 4137 L-2081 4177 L-2008 4236 L-1964 4254 L-1961 4293 L-1939 4360 L-1886 4410 L-1861 4424 L-1808 4493 L-1784 4598 L-1725 4761 L-1710 4787 L-1638 4839 L-1582 4862 L-1537 4898 L-1506 4964 L-1412 5069 L-1398 5098 L-1346 5148 L-1323 5223 L-1268 5330 L-1267 5349 L-1313 5388 L-1414 5415 L-1391 5426 L-1391 5435 L-1420 5454 L-1458 5451 L-1517 5476 L-1586 5463 L-1563 5426 L-1569 5407 L-1555 5394 L-1518 5377 L-1533 5454 L-1455 5411 L-1444 5395 L-1451 5382 L-1445 5378 L-1425 5388 L-1406 5349 L-1451 5272 L-1446 5249 L-1458 5224 L-1496 5184 L-1536 5163 L-1621 5155 L-1623 5137 L-1646 5100 L-1714 5095 L-1706 5118 L-1721 5146 L-1718 5163 L-1706 5176 L-1816 5196 L-1834 5219 L-1834 5290 L-1803 5377 L-1774 5349 L-1778 5333 L-1764 5342 L-1758 5358 L-1751 5349 L-1730 5425 L-1714 5444 L-1706 5435 L-1714 5415 L-1686 5433 L-1646 5502 L-1652 5520 L-1646 5531 L-1680 5551 L-1689 5565 L-1683 5587 L-1597 5544 L-1563 5541 L-1563 5549 L-1618 5588 L-1636 5636 L-1660 5664 L-1691 5664 L-1714 5674 L-1706 5694 L-1755 5713 L-1812 5703 L-1822 5745 L-1857 5753 L-1871 5771 L-1936 5779 L-1952 5754 L-1984 5771 L-2058 5720 L-2103 5749 L-2134 5755 L-2149 5771 L-2164 5760 L-2164 5799 L-2111 5790 L-2111 5799 L-2132 5813 L-2122 5829 L-2101 5835 L-2081 5818 L-2089 5838 L-2046 5831 L-2037 5838 L-1969 5809 L-1920 5881 L-1886 5906 L-1845 5895 L-1831 5899 L-1797 5926 L-1789 5943 L-1767 5920 L-1737 5914 L-1703 5939 L-1626 5944 L-1597 5955 L-1578 5981 L-1544 6091 L-1529 6106 L-1508 6108 L-1472 6085 L-1444 6085 L-1429 6067 L-1459 6049 L-1439 6040 L-1365 6073 L-1308 6086 L-1281 6118 L-1278 6154 L-1322 6189 L-1331 6221 L-1320 6205 L-1307 6204 L-1270 6236 L-1225 6251 L-1225 6260 L-1271 6269 L-1283 6288 L-1276 6295 L-1185 6294 L-1074 6313 L-1049 6284 L-1022 6298 L-985 6336 L-1015 6355 L-1015 6365 L-990 6375 L-986 6383 L-993 6403 L-959 6420 L-906 6501 L-866 6529 L-787 6519 L-644 6582 L-601 6593 L-492 6705 L-472 6713 L-472 6757 L-460 6768 L-478 6783 L-483 6816 L-490 6797 L-506 6799 L-560 6828 L-538 6943 L-512 6989 L-535 7046 L-530 7088 L-535 7105 L-510 7108 L-497 7132 L-535 7152 L-517 7168 L-490 7171 L-497 7181 L-475 7190 L-483 7212 L-475 7228 L-490 7248 L-463 7264 L-452 7301 L-458 7346 L-483 7373 L-468 7382 L-468 7392 L-483 7392 L-475 7421 L-478 7413 L-483 7421 L-469 7435 L-512 7488 L-603 7452 L-610 7434 L-610 7382 L-633 7390 L-655 7305 L-670 7316 L-695 7269 L-715 7255 L-730 7258 L-753 7238 L-759 7268 L-782 7263 L-790 7277 L-793 7260 L-806 7258 L-799 7240 L-804 7225 L-827 7199 L-830 7173 L-876 7105 L-880 7085 L-898 7076 L-955 7094 L-940 7066 L-957 7074 L-975 7053 L-1029 7038 L-1038 7027 L-998 6991 L-988 6970 L-996 6946 L-1014 6935 L-1072 6940 L-1102 6960 L-1150 6970 L-1210 7017 L-1173 7027 L-1195 7036 L-1282 7027 L-1395 7037 L-1540 7125 L-1586 7105 L-1627 7105 L-1632 7144 L-1649 7165 L-1644 7192 L-1630 7213 L-1608 7209 L-1563 7222 L-1518 7209 L-1483 7244 L-1444 7267 L-1450 7294 L-1444 7316 L-1503 7335 L-1511 7363 L-1484 7384 L-1451 7392 L-1464 7446 L-1451 7497 L-1466 7497 L-1459 7540 L-1391 7584 L-1383 7574 L-1343 7614 L-1275 7650 L-1249 7633 L-1250 7596 L-1270 7560 L-1301 7545 L-1301 7536 L-1262 7512 L-1207 7507 L-1195 7524 L-1200 7561 L-1215 7600 L-1233 7622 L-1211 7642 L-1181 7650 L-1181 7661 L-1210 7669 L-1210 7679 L-1165 7689 L-1118 7713 L-1068 7756 L-1075 7766 L-1068 7785 L-1154 7820 L-1308 7823 L-1301 7842 L-1356 7839 L-1354 7853 L-1391 7862 L-1391 7875 L-1361 7881 L-1368 7900 L-1339 7910 L-1356 7918 L-1440 7923 L-1440 7935 L-1420 7976 L-1459 7981 L-1488 7967 L-1488 7957 L-1466 7957 L-1466 7948 L-1508 7945 L-1518 7929 L-1496 7939 L-1509 7916 L-1533 7900 L-1542 7909 L-1563 7903 L-1564 7838 L-1539 7855 L-1528 7844 L-1518 7804 L-1488 7823 L-1499 7772 L-1537 7753 L-1576 7763 L-1593 7756 L-1578 7747 L-1593 7718 L-1631 7743 L-1638 7756 L-1665 7688 L-1683 7669 L-1706 7669 L-1714 7650 L-1729 7644 L-1751 7642 L-1737 7646 L-1729 7661 L-1750 7651 L-1769 7654 L-1803 7679 L-1841 7650 L-1834 7631 L-1860 7615 L-1867 7603 L-1864 7593 L-1886 7564 L-1930 7587 L-1943 7607 L-1947 7642 L-1932 7674 L-1939 7708 L-1917 7747 L-1917 7780 L-1901 7795 L-1909 7842 L-1841 7919 L-1849 7939 L-1834 7939 L-1841 7957 L-1746 8129 L-1740 8143 L-1753 8158 L-1758 8213 L-1750 8230 L-1729 8235 L-1691 8226 L-1683 8246 L-1691 8251 L-1683 8255 L-1691 8266 L-1664 8284 L-1666 8291 L-1683 8284 L-1644 8353 L-1646 8370 L-1631 8419 L-1654 8419 L-1638 8446 L-1631 8438 L-1626 8463 L-1631 8486 L-1590 8572 L-1593 8583 L-1541 8654 L-1543 8682 L-1555 8687 L-1555 8696 L-1518 8706 L-1540 8735 L-1546 8774 L-1586 8754 L-1610 8784 L-1615 8798 L-1601 8811 L-1608 8830 L-1578 8830 L-1606 8855 L-1604 8891 L-1555 8989 L-1474 9042 L-1488 9052 L-1481 9076 L-1496 9089 L-1477 9118 L-1420 9161 L-1429 9194 L-1466 9175 L-1477 9190 L-1491 9192 L-1540 9180 L-1571 9137 L-1564 9110 L-1588 9069 L-1604 9061 L-1674 9072 L-1721 8965 L-1781 8917 L-1765 8901 L-1770 8884 L-1822 8839 L-1841 8869 L-1846 8861 L-1844 8795 L-1862 8714 L-1877 8689 L-1901 8674 L-1988 8667 L-2057 8675 L-2106 8704 L-2105 8763 L-2141 8790 L-2164 8841 L-2147 8841 L-2137 8850 L-2134 8889 L-2141 8889 L-2154 8861 L-2173 8867 L-2180 8893 L-2157 8914 L-2163 8943 L-2177 8956 L-2186 8926 L-2202 8936 L-2209 8951 L-2206 9065 L-2179 9147 L-2183 9154 L-2179 9167 L-2193 9177 L-2198 9191 L-2186 9234 L-2196 9233 L-2201 9253 L-2213 9237 L-2224 9167 L-2278 9137 L-2292 9118 L-2310 9130 L-2321 9127 L-2351 9083 L-2337 9033 L-2319 9038 L-2314 9022 L-2318 8999 L-2330 8984 L-2314 8956 L-2337 8956 L-2332 8900 L-2314 8898 L-2314 8889 L-2335 8881 L-2333 8857 L-2314 8811 L-2346 8817 L-2384 8739 L-2404 8715 L-2403 8688 L-2420 8652 L-2496 8543 L-2520 8531 L-2547 8552 L-2588 8516 L-2593 8495 L-2577 8462 L-2571 8370 L-2686 8351 L-2789 8395 L-2801 8409 L-2825 8591 L-2810 8632 L-2817 8649 L-2787 8675 L-2772 8678 L-2772 8687 L-2799 8694 L-2809 8728 L-2868 8783 L-2877 8783 L-2933 8668 L-2998 8687 L-3036 8662 L-3043 8649 L-3060 8655 L-3080 8611 L-3080 8552 L-3057 8504 L-3057 8480 L-3065 8460 L-3081 8450 L-3103 8457 L-3088 8438 L-3103 8441 L-3110 8457 L-3117 8407 L-3178 8336 L-3201 8293 L-3211 8237 L-3213 8181 L-3205 8131 L-3186 8092 L-3087 8003 L-3072 7957 L-3077 7901 L-3095 7846 L-3170 7701 L-3232 7614 L-3349 7534 L-3394 7482 L-3459 7463 L-3480 7469 L-3486 7507 L-3493 7507 L-3497 7467 L-3508 7458 L-3494 7430 L-3493 7383 L-3523 7301 L-3586 7263 L-3701 7228 L-3717 7202 L-3713 7181 L-3718 7171 L-3688 7075 L-3655 7099 L-3607 7076 L-3531 6999 L-3515 7004 L-3478 6970 L-3486 6951 L-3523 6979 L-3433 6830 L-3425 6798 L-3425 6691 L-3387 6740 L-3396 6699 L-3374 6717 L-3315 6726 L-3261 6768 L-3174 6787 L-3153 6783 L-3095 6748 L-3066 6713 L-2998 6586 L-2904 6522 L-2832 6537 L-2787 6529 L-2763 6547 L-2717 6561 L-2698 6605 L-2686 6615 L-2641 6634 L-2615 6625 L-2582 6651 L-2562 6702 L-2513 6720 L-2500 6737 L-2457 6740 L-2396 6759 L-2376 6750 L-2341 6778 L-2285 6807 L-2265 6799 L-2179 6819 L-2059 6883 L-1994 6907 L-1886 6999 L-1867 7032 L-1839 7043 L-1789 7085 L-1702 7075 L-1670 7029 L-1697 6997 L-1754 6961 L-1774 6960 L-1767 6953 L-1803 6951 L-1780 6931 L-1740 6916 L-1706 6883 L-1677 6885 L-1623 6909 L-1601 6902 L-1568 6918 L-1454 6889 L-1436 6868 L-1406 6855 L-1431 6822 L-1451 6816 L-1451 6797 L-1399 6787 L-1399 6777 L-1503 6759 L-1480 6740 L-1509 6709 L-1523 6706 L-1570 6744 L-1608 6740 L-1608 6730 L-1586 6730 L-1616 6697 L-1696 6685 L-1716 6689 L-1729 6710 L-1698 6706 L-1684 6714 L-1677 6730 L-1728 6724 L-1744 6730 L-1758 6662 L-1766 6662 L-1774 6682 L-1781 6662 L-1856 6682 L-1901 6653 L-1864 6605 L-1926 6584 L-1976 6556 L-1999 6519 L-1989 6495 L-2005 6466 L-2031 6454 L-2052 6480 L-2033 6483 L-2031 6493 L-2041 6501 L-2068 6491 L-2096 6529 L-2096 6537 L-2075 6548 L-2084 6565 L-2081 6576 L-2094 6590 L-2123 6589 L-2141 6576 L-2163 6536 L-2149 6529 L-2164 6498 L-2226 6410 L-2299 6365 L-2292 6418 L-2330 6451 L-2316 6468 L-2307 6461 L-2302 6474 L-2322 6499 L-2314 6509 L-2320 6520 L-2386 6509 L-2427 6514 L-2447 6498 L-2493 6496 L-2524 6525 L-2532 6548 L-2554 6509 L-2579 6504 L-2577 6490 L-2594 6478 L-2685 6442 L-2707 6441 L-2727 6451 L-2753 6425 L-2785 6424 L-2871 6471 L-2888 6471 L-2914 6442 L-2924 6445 L-2978 6491 L-2989 6533 L-2999 6540 L-3050 6499 L-3114 6499 L-3163 6517 L-3178 6509 L-3248 6560 L-3261 6586 L-3268 6586 L-3278 6577 L-3313 6572 L-3365 6537 L-3347 6532 L-3298 6567 L-3306 6546 L-3298 6529 L-3313 6519 L-3313 6509 L-3298 6499 L-3320 6499 L-3313 6480 L-3332 6487 L-3350 6480 L-3372 6490 L-3365 6463 L-3379 6448 L-3421 6442 L-3430 6429 L-3440 6345 L-3481 6305 L-3497 6308 L-3493 6319 L-3448 6394 L-3463 6394 L-3455 6403 L-3466 6446 L-3516 6471 L-3508 6480 L-3516 6490 L-3531 6481 L-3539 6485 L-3543 6494 L-3537 6504 L-3573 6536 L-3602 6537 L-3627 6522 L-3636 6537 L-3616 6548 L-3643 6561 L-3644 6576 L-3664 6575 L-3681 6529 L-3741 6519 L-3719 6506 L-3718 6480 L-3733 6490 L-3718 6461 L-3722 6471 L-3710 6477 L-3681 6442 L-3701 6426 L-3718 6442 L-3740 6425 L-3748 6394 L-3741 6383 L-3718 6404 L-3707 6401 L-3703 6383 L-3718 6394 L-3713 6375 L-3724 6349 L-3718 6326 L-3748 6317 L-3726 6308 L-3741 6297 L-3730 6255 L-3740 6249 L-3783 6284 L-3796 6290 L-3801 6284 L-3816 6236 L-3808 6148 L-3831 6123 L-3848 6070 L-3858 6058 L-3915 6053 L-3929 6039 L-3963 5909 L-3974 5887 L-3988 5875 L-4020 5897 L-4041 5932 L-4049 5917 L-4083 5935 L-4094 5906 L-4131 5875 L-4131 5866 L-4109 5800 L-4048 5785 L-4060 5768 L-4093 5751 L-4102 5730 L-4100 5684 L-4087 5657 L-4074 5691 L-4035 5710 L-4015 5700 L-3988 5655 L-3981 5655 L-3976 5674 L-3981 5684 L-3975 5694 L-3981 5703 L-3940 5701 L-3927 5689 L-3922 5664 L-3904 5678 L-3862 5674 L-3805 5694 L-3807 5743 L-3741 5790 L-3737 5770 L-3726 5760 L-3734 5734 L-3723 5725 L-3702 5726 L-3685 5736 L-3659 5771 L-3640 5774 L-3636 5760 L-3649 5746 L-3652 5725 L-3665 5721 L-3681 5682 L-3673 5664 L-3679 5653 L-3676 5640 L-3659 5636 L-3660 5603 L-3741 5512 L-3753 5530 L-3748 5549 L-3774 5547 L-3794 5569 L-3771 5587 L-3831 5579 L-3831 5569 L-3872 5545 L-3885 5552 L-3896 5546 L-3906 5521 L-3891 5512 L-3891 5502 L-3922 5510 L-3943 5492 L-3951 5492 L-3981 5526 L-3976 5540 L-3959 5549 L-4005 5548 L-3988 5541 L-3991 5518 L-3994 5508 L-4003 5512 L-4003 5492 L-4018 5492 L-4026 5502 L-4012 5472 L-4016 5448 L-4029 5440 L-4041 5454 L-4048 5444 L-4059 5462 L-4079 5473 L-4079 5483 L-4063 5487 L-4071 5531 L-4096 5555 L-4100 5569 L-4116 5559 L-4114 5579 L-4100 5579 L-4028 5631 L-4019 5651 L-4091 5631 L-4125 5670 L-4161 5602 L-4146 5579 L-4157 5532 L-4178 5499 L-4278 5427 L-4363 5319 L-4406 5285 L-4402 5272 L-4410 5243 L-4402 5204 L-4426 5212 L-4439 5195 L-4471 5203 L-4499 5184 L-4530 5197 L-4574 5175 L-4610 5133 L-4612 5089 L-4635 5058 L-4647 5044 L-4672 5041 L-4664 5023 L-4694 4984 L-4638 4974 L-4641 4955 L-4694 4916 L-4694 4907 L-4651 4911 L-4641 4888 L-4687 4870 L-4687 4888 L-4722 4870 L-4709 4858 L-4730 4853 L-4784 4858 L-4771 4834 L-4770 4801 L-4754 4810 L-4739 4792 L-4739 4763 L-4724 4754 L-4731 4726 L-4768 4707 L-4833 4658 L-4931 4629 L-4913 4618 L-4833 4644 L-4729 4708 L-4711 4704 L-4707 4676 L-4698 4666 L-4680 4663 L-4661 4672 L-4658 4641 L-4621 4614 L-4602 4580 L-4628 4536 L-4619 4508 L-4631 4485 L-4624 4474 L-4604 4472 L-4523 4502 L-4504 4483 L-4495 4455 L-4500 4430 L-4550 4348 L-4582 4314 L-4604 4218 L-4518 4209 L-4492 4137 L-4456 4111 L-4420 4115 L-4383 4100 L-4297 4106 L-4221 4068 L-4198 4007 L-4207 3950 L-4180 3932 L-4167 3899 L-4164 3810 L-4123 3775 L-4086 3692 L-4086 3609 L-4044 3589 L-4025 3549 L-4010 3540 L-3981 3539 L-3931 3557 L-3904 3538 L-3887 3509 L-3881 3479 L-3855 3467 L-3814 3417 L-3795 3304 L-3796 3277 L-3814 3233 L-3875 3170 L-3886 3137 L-3897 3129 L-3878 3107 L-3871 3077ZM-407 11403 L-415 11429 L-400 11459 L-429 11457 L-497 11411 L-497 11403 L-475 11398 L-460 11383 L-407 11392ZM2713 10596 L2752 10587 L2754 10596 L2739 10606 L2747 10643 L2694 10654 L2604 10711 L2590 10705 L2573 10679 L2619 10630 L2630 10606 L2656 10615ZM1995 10759 L1986 10784 L1935 10836 L1954 10908 L1972 10940 L1995 10923 L1956 10989 L1966 11009 L1948 11060 L1901 11152 L1805 11197 L1759 11201 L1733 11172 L1666 11171 L1627 11145 L1600 11159 L1560 11152 L1514 11162 L1433 11192 L1207 11181 L1102 11222 L1003 11209 L929 11212 L881 11221 L792 11264 L713 11262 L689 11268 L666 11287 L613 11279 L569 11296 L530 11286 L261 11296 L280 11259 L276 11206 L285 11162 L266 11092 L227 11065 L130 11064 L88 11047 L71 11051 L35 11009 L1 10987 L-21 10982 L-39 10990 L-105 10955 L-107 10932 L-227 10945 L-309 10932 L-324 10912 L-347 10923 L-426 10923 L-455 10914 L-460 10928 L-493 10932 L-513 10923 L-544 10883 L-561 10873 L-655 10876 L-701 10869 L-738 10846 L-754 10857 L-768 10855 L-787 10871 L-864 10869 L-895 10884 L-910 10868 L-1000 10865 L-1008 10836 L-1038 10826 L-1076 10788 L-1068 10779 L-1076 10769 L-1038 10750 L-1050 10729 L-1045 10701 L-1053 10676 L-1015 10591 L-1030 10567 L-1011 10510 L-1010 10499 L-1023 10490 L-1016 10471 L-1023 10462 L-1007 10426 L-1008 10394 L-981 10342 L-977 10428 L-964 10466 L-943 10473 L-940 10490 L-921 10498 L-873 10496 L-856 10482 L-846 10458 L-843 10424 L-863 10350 L-851 10336 L-864 10292 L-859 10274 L-831 10238 L-790 10260 L-802 10285 L-790 10347 L-790 10394 L-768 10438 L-748 10451 L-626 10471 L-609 10465 L-520 10471 L-499 10461 L-485 10426 L-445 10424 L-458 10374 L-422 10358 L-372 10364 L-347 10380 L-325 10441 L-347 10481 L-392 10490 L-459 10479 L-475 10490 L-469 10502 L-343 10567 L-304 10554 L-271 10529 L-259 10594 L-257 10682 L-175 10712 L-79 10682 L-39 10693 L-16 10679 L103 10652 L194 10607 L242 10602 L351 10622 L373 10634 L433 10606 L501 10634 L516 10606 L568 10619 L580 10635 L606 10634 L599 10667 L608 10703 L632 10718 L764 10711 L790 10730 L884 10720 L927 10729 L944 10720 L952 10730 L960 10720 L1014 10781 L1045 10788 L1076 10784 L1271 10711 L1323 10730 L1387 10730 L1367 10765 L1342 10788 L1350 10797 L1343 10810 L1347 10830 L1358 10836 L1356 10812 L1362 10801 L1371 10802 L1379 10816 L1374 10826 L1379 10836 L1373 10846 L1364 10840 L1350 10855 L1353 10868 L1336 10904 L1342 10932 L1329 10944 L1346 11013 L1373 11014 L1419 11039 L1458 11029 L1477 10989 L1515 10970 L1530 10941 L1620 10926 L1680 10884 L1704 10882 L1710 10873 L1775 10899 L1762 10912 L1786 10926 L1840 10910 L1860 10893 L1853 10884 L1928 10802 L1966 10797 L1957 10779 L1973 10779 L1966 10759ZM2971 10471 L2995 10494 L2999 10509 L2994 10539 L2966 10531 L2937 10543 L2916 10570 L2911 10606 L2927 10596 L2921 10607 L2888 10634 L2896 10611 L2858 10596 L2841 10567 L2842 10554 L2858 10548 L2851 10529 L2869 10524 L2858 10471 L2864 10429 L2858 10414 L2814 10375 L2815 10357 L2833 10323 L2866 10301 L2879 10229 L2908 10195 L2916 10154 L2911 10078 L2927 10068 L2941 10078 L2964 10049 L2981 10039 L2994 10049 L2971 10112 L2979 10183 L2947 10224 L2937 10258 L2916 10288 L2911 10312 L2913 10343 L2941 10366 L2981 10429 L2964 10452 L2962 10462ZM1354 9263 L1389 9238 L1428 9255 L1463 9287 L1485 9291 L1476 9310 L1444 9291 L1399 9305 L1366 9299 L1350 9278 L1348 9268ZM4097 9194 L4082 9215 L4094 9278 L4066 9299 L4059 9348 L4027 9393 L4014 9467 L3997 9484 L3978 9540 L3948 9540 L3939 9565 L3929 9569 L3902 9637 L3940 9655 L3918 9694 L3933 9723 L3876 9704 L3828 9713 L3761 9765 L3685 9883 L3646 9921 L3594 9954 L3542 9919 L3520 9866 L3534 9846 L3565 9748 L3572 9713 L3569 9682 L3516 9622 L3520 9598 L3496 9591 L3489 9579 L3585 9523 L3580 9512 L3589 9504 L3594 9474 L3619 9422 L3657 9407 L3725 9324 L3790 9301 L3965 9201 L4036 9206 L4069 9162 L4088 9170ZM966 9129 L1006 9141 L1044 9170 L1073 9206 L1086 9243 L1084 9271 L1057 9321 L1015 9327 L944 9301 L996 9291 L1026 9253 L1014 9202 L1004 9194 L1010 9168 L952 9147 L952 9137ZM3174 9186 L3164 9211 L3177 9226 L3200 9228 L3220 9215 L3226 9234 L3208 9261 L3195 9268 L3153 9265 L3131 9226 L3137 9205 L3122 9196 L3110 9200 L3092 9224 L3084 9224 L3064 9201 L3065 9149 L3069 9137 L3079 9159 L3129 9129 L3143 9139 L3157 9178ZM2040 8907 L2074 8909 L2115 8934 L2147 8965 L2154 8984 L2142 8992 L2131 8975 L2099 8995 L2052 8999 L2025 9042 L2026 9078 L2018 9087 L1992 9089 L1973 9081 L1953 9044 L1935 9033 L1943 9014 L1930 8977 L1935 8966 L1951 8975 L1966 8965 L2018 9003 L2044 8975 L2086 8975 L2065 8953 L2070 8937 L2040 8917ZM3692 8975 L3700 9014 L3685 9022 L3700 9042 L3663 9061 L3647 9061 L3647 9052 L3670 9033 L3607 9006 L3624 8994 L3572 8994 L3601 8951 L3602 8936 L3617 8926 L3617 8936 L3636 8912 L3662 8897 L3682 8895 L3685 8907 L3640 8927 L3632 8946 L3647 8942 L3655 8956 L3692 8926 L3700 8936 L3685 8956 L3696 8952ZM403 8869 L491 8926 L508 8965 L463 8957 L433 8926 L383 8894 L373 8869ZM708 8792 L751 8793 L749 8811 L650 8909 L622 8907 L663 8821ZM-28 8754 L37 8725 L50 8744 L50 8836 L41 8846 L-17 8869 L-148 8872 L-190 8889 L-194 8869 L-185 8838 L-190 8821 L-175 8803 L-190 8792 L-160 8744 L-130 8773 L-115 8770 L-102 8810 L-81 8821 L-43 8821 L-31 8814 L-34 8799 L-54 8773 L-69 8782 L-80 8773 L-100 8735 L-87 8721ZM156 8696 L182 8715 L184 8730 L175 8749 L159 8754 L119 8706 L133 8687 L152 8688ZM847 8792 L854 8783 L824 8783 L835 8750 L836 8725 L884 8687 L929 8754 L985 8781 L996 8803 L975 8815 L981 8850 L957 8885 L918 8864ZM119 8630 L80 8705 L44 8702 L23 8656 L37 8629 L68 8616 L94 8629 L110 8620ZM1011 8634 L1038 8600 L1072 8581 L1064 8591 L1072 8596 L1071 8631 L1049 8645 L1024 8648ZM3047 8529 L3059 8551 L3113 8565 L3129 8591 L3093 8612 L2974 8647 L2948 8663 L2881 8735 L2830 8734 L2791 8715 L2730 8745 L2713 8763 L2724 8792 L2708 8797 L2702 8812 L2709 8850 L2670 8830 L2649 8797 L2658 8728 L2671 8735 L2694 8706 L2724 8725 L2762 8668 L2806 8625 L2919 8552ZM1215 8563 L1221 8549 L1260 8524 L1298 8552 L1286 8569ZM1650 8486 L1682 8522 L1725 8543 L1724 8551 L1698 8544 L1650 8552 L1557 8623 L1527 8675 L1512 8687 L1423 8718 L1376 8722 L1358 8687 L1373 8696 L1396 8670 L1412 8667 L1432 8678 L1450 8668 L1474 8668 L1494 8630 L1481 8636 L1474 8629 L1474 8611 L1613 8543 L1613 8534 L1589 8524 L1589 8514ZM637 8466 L621 8463 L599 8443 L581 8415 L576 8389 L587 8369 L628 8341 L644 8341 L613 8438ZM224 8351 L276 8420 L291 8471 L231 8534 L196 8468 L185 8430 L193 8399 L169 8366 L156 8361 L164 8341 L156 8332 L171 8332 L207 8359ZM2642 8476 L2664 8446 L2657 8426 L2689 8361 L2677 8343 L2656 8351 L2648 8342 L2633 8313 L2614 8294 L2618 8274 L2631 8292 L2724 8332 L2724 8341 L2709 8341 L2720 8360 L2746 8377 L2747 8399 L2775 8383 L2784 8389 L2788 8405 L2776 8466 L2791 8457 L2783 8477 L2732 8466 L2721 8499 L2713 8504 L2686 8496 L2679 8504 L2662 8480ZM1432 8255 L1425 8266 L1403 8226 L1421 8227 L1462 8207 L1455 8226 L1470 8246 L1465 8257 L1445 8264ZM854 8332 L842 8335 L802 8393 L754 8421 L715 8419 L661 8382 L672 8312 L719 8274 L697 8269 L712 8245 L778 8198 L809 8187 L793 8212 L802 8221 L832 8226 L847 8207 L839 8187 L869 8187 L836 8274 L836 8294 L854 8303 L854 8313 L839 8313 L839 8323 L854 8323ZM1124 8125 L1133 8119 L1177 8150 L1197 8200 L1200 8260 L1184 8375 L1153 8443 L1124 8457 L1086 8495 L1041 8514 L1022 8485 L1011 8446 L974 8419 L980 8403 L965 8374 L966 8351 L950 8317 L922 8293 L922 8284 L955 8275 L996 8226 L1068 8173 L1090 8135ZM-62 8150 L-70 8140 L-35 8117 L22 8115 L35 8140 L35 8218 L29 8198 L21 8198 L17 8228 L-2 8246 L-10 8229 L-2 8226 L-21 8218 L-39 8226 L-44 8208 L-54 8218 L-72 8212 L-85 8226 L-89 8210 L-76 8198 L-84 8183 L-70 8169 L-71 8154ZM-145 7823 L-137 7786 L-70 7718 L-62 7718 L-62 7738 L-76 7776 L-34 7802 L-19 7823 L-24 7853 L-40 7848 L-52 7863 L-62 7910 L-97 7946 L-145 7967 L-125 7894 L-107 7881 L-107 7872 L-122 7862 L-113 7838 L-115 7824 L-127 7816ZM981 7815 L884 7823 L887 7789 L900 7785 L905 7752 L901 7741 L884 7738 L890 7716 L929 7689 L961 7746 L970 7714 L981 7708 L1055 7742 L1058 7751 L1049 7776 L995 7788 L989 7815ZM486 7790 L508 7815 L508 7838 L418 7891 L426 7842 L396 7842 L403 7819 L418 7804 L403 7795 L424 7791 L436 7772 L441 7728 L433 7685 L471 7689 L491 7720 L501 7756ZM648 7584 L599 7536 L546 7507 L528 7462 L531 7450 L546 7445 L611 7452 L622 7458 L613 7478 L633 7483 L644 7497 L662 7485 L682 7488 L712 7517 L728 7496 L817 7526 L809 7536 L825 7548 L832 7574 L805 7612 L797 7648 L784 7654 L734 7646 L685 7622 L674 7616 L661 7590ZM-137 7439 L-107 7482 L-114 7525 L-205 7646 L-226 7664 L-246 7656 L-243 7528 L-231 7497 L-213 7475 L-197 7478 L-189 7469 L-182 7458 L-197 7458 L-197 7450 L-186 7442 L-152 7450 L-152 7441ZM2040 7439 L1993 7512 L1896 7600 L1784 7622 L1707 7673 L1618 7678 L1613 7650 L1621 7632 L1657 7595 L1689 7536 L1725 7507 L1815 7514 L1838 7507 L1860 7515 L1922 7487 L1951 7454ZM2791 7382 L2804 7373 L2811 7379 L2806 7411 L2780 7402 L2740 7411 L2641 7451 L2596 7497 L2517 7497 L2506 7494 L2477 7434 L2419 7401 L2364 7413 L2332 7433 L2326 7450 L2311 7439 L2299 7452 L2283 7414 L2279 7363 L2295 7334 L2349 7319 L2364 7290 L2489 7260 L2527 7260 L2566 7267 L2610 7300 L2648 7311 L2702 7353 L2706 7338 L2679 7296 L2710 7302 L2732 7285 L2733 7302 L2814 7316 L2776 7334 L2774 7346ZM539 7324 L542 7344 L532 7370 L501 7411 L508 7439 L501 7439 L456 7392 L430 7324 L400 7317 L347 7247 L329 7258 L322 7219 L302 7193 L261 7152 L237 7169 L232 7162 L239 7142 L201 7094 L214 7090 L208 7061 L212 7048 L282 7005 L306 7000 L322 7008 L323 7032 L362 7052 L370 7104 L382 7119 L411 7132 L497 7132 L508 7144 L486 7219 L531 7258 L516 7267 L517 7285 L501 7316 L509 7324 L526 7316ZM1823 6240 L1809 6257 L1802 6310 L1777 6317 L1800 6336 L1793 6345 L1812 6346 L1800 6375 L1796 6414 L1808 6519 L1823 6576 L1794 6581 L1768 6602 L1755 6634 L1766 6688 L1687 6720 L1672 6766 L1654 6781 L1605 6759 L1580 6727 L1561 6716 L1545 6682 L1523 6691 L1523 6653 L1505 6664 L1497 6656 L1508 6615 L1553 6595 L1571 6576 L1604 6576 L1617 6528 L1635 6519 L1629 6503 L1631 6469 L1627 6451 L1619 6461 L1608 6442 L1589 6432 L1595 6401 L1582 6365 L1569 6352 L1523 6336 L1472 6279 L1460 6238 L1478 6187 L1638 6154 L1661 6157 L1714 6174 L1762 6240 L1777 6221 L1770 6211 L1787 6206 L1801 6210ZM1193 6144 L1230 6189 L1222 6192 L1211 6251 L1174 6242 L1162 6251 L1162 6211 L1121 6164 L1132 6150 L1147 6164 L1161 6147 L1184 6154 L1184 6144ZM193 5866 L200 5902 L187 5906 L173 5923 L156 5914 L137 5923 L125 5918 L110 5890 L77 5911 L73 5932 L35 5885 L81 5866 L62 5816 L50 5828 L31 5808 L6 5818 L6 5803 L-19 5792 L-24 5771 L-32 5780 L-50 5761 L-70 5771 L-67 5744 L-41 5725 L-47 5684 L-43 5645 L-32 5632 L-9 5627 L67 5678 L81 5694 L79 5742 L86 5774 L156 5822ZM96 6777 L88 6882 L104 6913 L73 7017 L10 7052 L-25 7053 L-32 7027 L-57 6985 L-77 6970 L-106 6983 L-124 7005 L-107 7017 L-107 7027 L-124 7041 L-141 7039 L-177 7005 L-204 6959 L-204 6951 L-190 6940 L-203 6909 L-213 6900 L-228 6902 L-234 6879 L-253 6866 L-275 6864 L-294 6874 L-309 6864 L-324 6874 L-317 6863 L-317 6826 L-326 6818 L-344 6822 L-347 6811 L-317 6768 L-345 6695 L-376 6679 L-392 6682 L-385 6702 L-410 6696 L-404 6670 L-369 6625 L-380 6606 L-407 6625 L-410 6641 L-428 6641 L-422 6615 L-437 6615 L-415 6567 L-461 6544 L-520 6537 L-482 6522 L-475 6509 L-483 6496 L-483 6471 L-502 6438 L-505 6446 L-569 6442 L-644 6451 L-719 6432 L-774 6442 L-866 6422 L-932 6432 L-970 6355 L-978 6365 L-993 6365 L-947 6299 L-955 6279 L-947 6260 L-971 6219 L-986 6200 L-1052 6185 L-1090 6164 L-1098 6117 L-1147 6079 L-1155 6053 L-1225 6010 L-1274 5965 L-1290 5932 L-1422 5838 L-1486 5809 L-1568 5815 L-1604 5776 L-1677 5755 L-1691 5760 L-1691 5771 L-1661 5777 L-1652 5789 L-1654 5809 L-1663 5817 L-1801 5834 L-1826 5848 L-1826 5816 L-1822 5804 L-1781 5775 L-1604 5703 L-1593 5674 L-1548 5664 L-1537 5639 L-1540 5617 L-1504 5592 L-1425 5587 L-1344 5546 L-1316 5541 L-1282 5569 L-1236 5586 L-1225 5598 L-1233 5625 L-1222 5645 L-1177 5664 L-1150 5776 L-1117 5827 L-1069 5848 L-1021 5889 L-993 5895 L-993 5922 L-978 5914 L-964 5928 L-918 5943 L-906 5935 L-895 5943 L-874 5929 L-852 5933 L-834 5951 L-818 5993 L-753 6029 L-704 6044 L-605 6063 L-584 6062 L-565 6039 L-542 6051 L-468 6049 L-377 6086 L-410 6111 L-415 6149 L-409 6162 L-311 6245 L-294 6269 L-322 6290 L-342 6336 L-346 6384 L-324 6422 L-345 6429 L-317 6471 L-312 6529 L-271 6591 L-271 6628 L-265 6637 L-279 6662 L-271 6681 L-228 6720 L-190 6740 L-170 6777 L-118 6770 L-87 6794 L-24 6806ZM2314 5531 L2312 5568 L2298 5583 L2265 5569 L2248 5579 L2234 5573 L2212 5549 L2220 5541 L2209 5526 L2220 5483 L2208 5473 L2198 5447 L2180 5441 L2142 5444 L2122 5455 L2140 5479 L2182 5512 L2223 5571 L2243 5587 L2243 5617 L2214 5629 L2108 5646 L2015 5624 L1946 5585 L1825 5569 L1804 5555 L1770 5507 L1740 5492 L1740 5483 L1763 5470 L1819 5463 L1853 5421 L1891 5415 L1965 5352 L1950 5325 L1891 5309 L1849 5317 L1819 5343 L1803 5382 L1750 5452 L1714 5473 L1598 5435 L1556 5408 L1522 5397 L1484 5359 L1462 5349 L1462 5338 L1475 5333 L1485 5290 L1470 5281 L1483 5269 L1489 5237 L1515 5223 L1553 5184 L1560 5184 L1574 5213 L1650 5199 L1680 5204 L1695 5176 L1702 5195 L1710 5195 L1724 5176 L1746 5165 L1822 5147 L1833 5130 L1823 5070 L2019 5064 L2040 5070 L2032 5101 L2101 5137 L2059 5204 L2062 5212 L2108 5257 L2154 5279 L2196 5341 L2235 5368 L2220 5377 L2225 5389 L2243 5411 L2247 5433 L2265 5435 L2264 5463 L2278 5495ZM561 4811 L600 4837 L592 4871 L539 4946 L531 4946 L519 4880 L522 4847 L546 4830 L544 4813ZM1041 4149 L1026 4168 L1041 4216 L988 4251 L970 4278 L974 4313 L947 4316 L929 4331 L952 4341 L922 4363 L921 4376 L937 4388 L923 4404 L953 4456 L937 4466 L930 4497 L871 4469 L866 4437 L847 4430 L829 4402 L809 4399 L854 4355 L849 4335 L822 4314 L809 4313 L764 4350 L794 4360 L775 4364 L761 4377 L742 4417 L757 4407 L769 4423 L790 4466 L783 4475 L705 4456 L734 4412 L728 4397 L697 4427 L689 4427 L682 4399 L599 4427 L622 4399 L599 4388 L599 4370 L613 4360 L606 4341 L622 4331 L613 4331 L623 4311 L599 4274 L598 4221 L584 4216 L584 4207 L693 4188 L719 4207 L794 4188 L819 4197 L834 4213 L862 4254 L860 4265 L929 4226 L929 4214 L966 4168 L1000 4168ZM1305 3573 L1310 3594 L1296 3608 L1193 3643 L1169 3640 L1059 3562 L1034 3525 L1054 3526 L1147 3479 L1179 3479 L1267 3505 L1284 3518 L1312 3555ZM314 3171 L291 3172 L284 3187 L292 3204 L314 3209 L314 3237 L295 3243 L291 3262 L309 3332 L307 3343 L280 3332 L268 3348 L199 3367 L156 3401 L126 3362 L110 3362 L110 3343 L95 3329 L34 3317 L18 3305 L13 3266 L20 3230 L37 3195 L73 3142 L156 3074 L191 3092 L254 3103 L267 3137 L302 3152ZM3359 9457 L3415 9460 L3417 9481 L3408 9497 L3321 9504 L3308 9496 L3306 9477 L3316 9464ZM2943 8938 L2965 8978 L2956 9004 L2916 9015 L2881 9003 L2877 8988 L2889 8960 L2922 8939ZM2599 8212 L2615 8237 L2615 8252 L2597 8263 L2575 8262 L2561 8253 L2561 8243 L2577 8226 L2539 8232 L2531 8219 L2539 8195 L2494 8162 L2490 8144 L2503 8132 L2518 8133 L2520 8121 L2529 8120 L2575 8138 L2578 8145 L2568 8173 L2590 8185ZM2300 7902 L2308 7925 L2271 7914 L2245 7943 L2263 7968 L2265 8015 L2254 8020 L2242 8012 L2240 7996 L2227 7992 L2223 7979 L2234 7927 L2231 7878 L2266 7876ZM262 7541 L264 7566 L239 7569 L175 7550 L213 7539 L237 7517 L255 7515 L264 7524ZM-459 5107 L-444 5116 L-445 5138 L-458 5173 L-479 5184 L-489 5173 L-483 5160 L-502 5137 L-499 5122 L-484 5094 L-474 5092 L-471 5116Z"/><path class="m-land" d="M20752 2651 L20748 2683 L20757 2728 L20774 2768 L20795 2787 L20842 2794 L20889 2817 L20932 2851 L20967 2893 L20979 2921 L20992 3007 L21003 3035 L21049 3106 L21059 3132 L21069 3252 L21036 3312 L21044 3343 L20998 3396 L20983 3425 L20984 3459 L20961 3448 L20970 3468 L20944 3471 L20920 3487 L20883 3531 L20887 3549 L20955 3612 L20937 3678 L20921 3716 L20932 3738 L20961 3766 L21010 3828 L21027 3866 L21007 3881 L21019 3906 L21053 3947 L21060 3963 L21049 3981 L21000 3992 L20984 4005 L20999 4046 L21049 4073 L21149 4101 L21269 4166 L21401 4188 L21418 4182 L21456 4156 L21480 4150 L21514 4169 L21645 4139 L21682 4139 L21722 4151 L21874 4239 L21937 4293 L21978 4344 L21987 4378 L22013 4399 L22021 4437 L22035 4428 L22075 4473 L22095 4485 L22113 4484 L22123 4490 L22197 4588 L22225 4634 L22237 4687 L22249 4704 L22139 4623 L22074 4593 L22029 4532 L22012 4520 L21985 4528 L21869 4622 L21864 4638 L21869 4684 L21867 4706 L21824 4796 L21819 4815 L21817 4838 L21822 4892 L21811 4909 L21805 4940 L21809 4992 L21790 5020 L21769 5035 L21688 5066 L21661 5064 L21585 5027 L21559 5024 L21499 5039 L21432 5040 L21394 5059 L21381 5076 L21388 5093 L21417 5127 L21428 5170 L21441 5198 L21439 5230 L21456 5270 L21450 5320 L21570 5397 L21579 5431 L21557 5474 L21551 5496 L21561 5551 L21551 5568 L21533 5582 L21518 5608 L21532 5650 L21557 5676 L21560 5711 L21576 5753 L21591 5774 L21608 5791 L21667 5819 L21672 5860 L21642 5961 L21638 5989 L21651 6049 L21633 6077 L21675 6096 L21683 6106 L21691 6129 L21685 6213 L21695 6284 L21694 6308 L21680 6365 L21683 6417 L21679 6453 L21682 6465 L21709 6479 L21763 6490 L21813 6465 L21846 6485 L21859 6504 L21868 6526 L21868 6549 L21844 6584 L21804 6615 L21773 6651 L21778 6718 L21760 6793 L21752 6804 L21724 6820 L21722 6832 L21731 6859 L21725 6868 L21689 6889 L21661 6958 L21634 6988 L21615 7027 L21606 7061 L21612 7099 L21591 7128 L21587 7144 L21606 7175 L21644 7181 L21715 7172 L21767 7196 L21779 7204 L21796 7250 L21808 7266 L21831 7265 L21840 7271 L21835 7309 L21843 7325 L21859 7327 L21890 7312 L21920 7309 L21951 7323 L21978 7347 L22018 7397 L22021 7410 L22010 7428 L21963 7472 L21958 7514 L21980 7539 L22005 7558 L22009 7582 L21992 7645 L21990 7680 L22000 7732 L21985 7774 L21992 7797 L22007 7805 L22048 7809 L22064 7822 L22080 7862 L22090 7874 L22130 7868 L22140 7881 L22156 7919 L22219 7961 L22243 7990 L22240 8036 L22227 8053 L22198 8073 L22191 8099 L22194 8127 L22211 8174 L22205 8201 L22191 8177 L22169 8166 L22034 8150 L21999 8167 L21956 8199 L21917 8237 L21890 8271 L21863 8293 L21834 8309 L21741 8341 L21732 8356 L21729 8378 L21701 8432 L21691 8442 L21677 8443 L21632 8431 L21622 8423 L21571 8306 L21562 8277 L21563 8248 L21573 8219 L21591 8195 L21628 8179 L21637 8162 L21638 8131 L21623 8069 L21610 8044 L21567 8009 L21462 7964 L21404 7954 L21355 7962 L21315 7998 L21249 8085 L21190 8096 L21170 8117 L21156 8120 L21114 8084 L21088 8077 L21059 8074 L20947 8082 L20921 8079 L20893 8067 L20864 8047 L20850 8045 L20795 8059 L20777 8052 L20726 8009 L20682 7986 L20638 7952 L20604 7952 L20585 7967 L20566 7968 L20414 7886 L20395 7880 L20317 7896 L20275 7914 L20247 7935 L20201 7952 L20156 7945 L20066 7914 L20056 7907 L20052 7883 L20029 7874 L19958 7903 L19943 7945 L19806 8149 L19789 8195 L19771 8203 L19677 8219 L19614 8240 L19565 8246 L19562 8187 L19541 8160 L19561 8082 L19554 8064 L19509 8030 L19494 8001 L19487 7999 L19467 8016 L19418 7997 L19418 7960 L19405 7945 L19370 7971 L19314 8045 L19232 8125 L19184 8154 L18604 8294 L18299 8309 L18226 8282 L17965 8228 L17759 8259 L17705 8281 L17559 8364 L17436 8394 L17191 8562 L17150 8581 L17069 8603 L16960 8670 L16725 8761 L16149 8874 L16091 8877 L15922 8818 L15865 8823 L15841 8830 L15663 8839 L15586 8828 L15519 8793 L15371 8633 L15317 8602 L15109 8538 L15037 8528 L15000 8532 L14926 8562 L14800 8644 L14769 8652 L14594 8735 L14412 8775 L14346 8805 L14184 8912 L14139 8912 L13961 8878 L13867 8899 L13810 8889 L13789 8898 L13764 8929 L13754 8932 L13712 8901 L13707 8885 L13717 8840 L13716 8811 L13707 8793 L13657 8745 L13615 8723 L13524 8714 L13322 8641 L13301 8641 L13305 8675 L13261 8754 L13252 8840 L13239 8873 L13224 8932 L13225 8994 L13219 9055 L13187 9108 L13182 9129 L13206 9229 L13219 9246 L13242 9258 L13250 9277 L13251 9300 L13238 9334 L13233 9334 L13244 9345 L13280 9349 L13298 9356 L13311 9372 L13329 9416 L13334 9468 L13328 9479 L13250 9495 L13146 9481 L13126 9484 L13114 9489 L13108 9508 L13094 9520 L13036 9508 L13009 9481 L12996 9495 L13012 9514 L13010 9526 L12995 9546 L12993 9566 L12990 9769 L12992 9808 L12969 9816 L12926 9799 L12904 9808 L12895 9858 L12877 9862 L12851 9854 L12816 9868 L12792 9908 L12785 10007 L12773 10048 L12752 10052 L12688 10004 L12656 9988 L12604 9983 L12592 9972 L12592 9919 L12578 9902 L12513 9919 L12503 9915 L12563 9809 L12575 9799 L12573 9774 L12543 9677 L12438 9501 L12426 9458 L12379 9406 L12367 9374 L12369 9352 L12408 9295 L12443 9282 L12461 9243 L12500 9215 L12511 9173 L12537 9150 L12589 9129 L12649 9047 L12661 9046 L12779 8969 L12796 8965 L12807 8954 L12831 8901 L12837 8879 L12836 8861 L12822 8821 L12822 8723 L12807 8678 L12742 8583 L12705 8544 L12664 8514 L12622 8503 L12584 8518 L12546 8553 L12484 8631 L12440 8658 L12387 8715 L12345 8725 L12254 8730 L12214 8744 L12201 8758 L12189 8784 L12177 8792 L12182 8776 L12169 8763 L12132 8819 L12139 8841 L12156 8818 L12180 8825 L12183 8803 L12194 8808 L12199 8821 L12206 8801 L12199 8783 L12214 8773 L12225 8795 L12233 8803 L12267 8786 L12281 8792 L12217 8823 L12186 8847 L12169 8879 L12171 8894 L12186 8884 L12235 8825 L12266 8811 L12225 8855 L12198 8917 L12196 8950 L12188 8956 L12160 8972 L12115 8978 L12101 8975 L12056 8936 L12041 8941 L12032 8950 L12029 8962 L12086 8984 L12040 8971 L11992 8965 L11957 8983 L11947 8999 L11914 9014 L11883 9042 L11872 9036 L11855 9009 L11827 8999 L11485 8791 L11446 8781 L11395 8792 L11403 8763 L11388 8756 L11343 8706 L11253 8658 L11247 8668 L11215 8650 L11168 8661 L11095 8696 L11050 8706 L11016 8725 L10994 8763 L10960 8783 L10864 8872 L10746 8948 L10711 8978 L10617 9102 L10603 9137 L10570 9157 L10531 9199 L10493 9221 L10491 9258 L10496 9302 L10494 9340 L10472 9358 L10408 9376 L10397 9406 L10407 9400 L10404 9409 L10374 9454 L10370 9491 L10364 9501 L10345 9501 L10355 9467 L10349 9429 L10333 9393 L10267 9359 L10250 9373 L10220 9420 L10202 9426 L10217 9436 L10205 9448 L10189 9477 L10127 9501 L10086 9546 L10073 9598 L10067 9608 L10037 9555 L10032 9536 L10022 9530 L9992 9540 L9967 9564 L9918 9621 L9894 9617 L9909 9608 L9909 9598 L9815 9579 L9792 9583 L9736 9608 L9671 9590 L9651 9615 L9578 9617 L9546 9626 L9520 9624 L9485 9608 L9460 9616 L9436 9655 L9409 9684 L9391 9675 L9342 9675 L9248 9655 L9165 9699 L9156 9715 L9098 9762 L9051 9759 L8952 9735 L8910 9713 L8840 9665 L8780 9656 L8696 9606 L8677 9577 L8618 9551 L8567 9480 L8557 9479 L8532 9457 L8527 9449 L8520 9397 L8494 9359 L8428 9298 L8408 9237 L8380 9193 L8362 9186 L8329 9119 L8313 9109 L8238 9035 L8204 9030 L8183 9014 L8117 9012 L8095 8986 L8067 8976 L8036 8971 L8017 8975 L8006 8964 L7964 8946 L7929 8901 L7892 8899 L7809 8861 L7775 8826 L7568 8731 L7537 8725 L7534 8691 L7495 8668 L7056 8600 L6876 8611 L6846 8602 L6778 8552 L6715 8597 L6685 8627 L6670 8670 L6650 8706 L6646 8820 L6658 8841 L6658 8850 L6643 8872 L6635 8907 L6637 8933 L6658 8975 L6665 8965 L6663 8995 L6648 9044 L6650 9061 L6613 9093 L6597 9114 L6584 9164 L6560 9202 L6561 9215 L6546 9238 L6548 9262 L6560 9282 L6576 9291 L6568 9311 L6596 9321 L6551 9368 L6538 9397 L6550 9391 L6561 9397 L6521 9433 L6509 9465 L6494 9483 L6463 9512 L6465 9453 L6460 9428 L6447 9416 L6421 9424 L6305 9368 L6282 9368 L6200 9382 L6190 9394 L6185 9444 L6178 9444 L6170 9416 L6163 9454 L6147 9444 L6147 9464 L6106 9454 L6079 9438 L6064 9444 L6087 9444 L6087 9454 L6013 9495 L5997 9493 L5984 9501 L5935 9493 L5896 9522 L5840 9540 L5848 9544 L5847 9551 L5810 9559 L5810 9569 L5832 9569 L5802 9597 L5785 9605 L5765 9608 L5765 9598 L5780 9579 L5766 9581 L5758 9589 L5745 9575 L5718 9572 L5705 9579 L5697 9595 L5686 9598 L5667 9627 L5663 9599 L5625 9580 L5614 9551 L5629 9559 L5635 9551 L5634 9538 L5626 9532 L5570 9540 L5570 9532 L5580 9526 L5614 9521 L5590 9510 L5502 9512 L5472 9505 L5404 9464 L5391 9477 L5385 9464 L5381 9426 L5375 9436 L5360 9426 L5349 9431 L5336 9444 L5322 9470 L5313 9474 L5304 9468 L5291 9444 L5284 9454 L5212 9384 L5188 9346 L5122 9324 L5104 9301 L5089 9311 L5085 9293 L5089 9272 L5058 9272 L5067 9263 L5054 9255 L5036 9253 L5050 9231 L5073 9224 L5072 9216 L5067 9215 L5073 9189 L5067 9165 L5052 9147 L5036 9137 L5036 9129 L5067 9109 L5062 9050 L5056 9026 L5036 9033 L5023 9016 L4970 9037 L4946 9033 L4966 9027 L4971 9014 L4953 8975 L4976 8926 L4992 8940 L5019 8906 L5036 8898 L5030 8922 L5039 8927 L5052 8923 L5058 8912 L5050 8887 L5036 8869 L4968 8819 L4883 8781 L4871 8768 L4864 8748 L4846 8762 L4811 8803 L4811 8811 L4818 8811 L4818 8821 L4781 8830 L4777 8842 L4780 8865 L4766 8869 L4781 8889 L4774 8898 L4788 8917 L4795 8917 L4808 8892 L4810 8879 L4803 8860 L4823 8878 L4816 8902 L4781 8936 L4788 8951 L4776 8958 L4743 8956 L4732 8944 L4732 8931 L4741 8921 L4758 8917 L4758 8907 L4717 8883 L4698 8889 L4692 8852 L4653 8823 L4604 8813 L4563 8830 L4558 8805 L4546 8794 L4532 8800 L4518 8821 L4510 8812 L4496 8773 L4506 8754 L4510 8726 L4508 8701 L4496 8687 L4495 8681 L4504 8678 L4499 8666 L4504 8658 L4496 8658 L4489 8687 L4466 8653 L4433 8647 L4409 8661 L4413 8696 L4402 8686 L4368 8678 L4383 8668 L4383 8658 L4343 8654 L4334 8640 L4331 8611 L4343 8610 L4346 8605 L4330 8563 L4325 8564 L4323 8577 L4313 8589 L4248 8604 L4248 8612 L4263 8630 L4289 8628 L4300 8639 L4269 8695 L4248 8696 L4180 8658 L4173 8658 L4180 8687 L4140 8685 L4135 8673 L4140 8660 L4180 8649 L4180 8639 L4134 8607 L4117 8615 L4101 8638 L4094 8661 L4097 8682 L4112 8696 L4107 8726 L4151 8760 L4158 8792 L4128 8777 L4112 8781 L4105 8803 L4091 8792 L4089 8803 L4082 8811 L4089 8814 L4091 8821 L4034 8842 L4013 8858 L3957 8954 L3931 8975 L3902 8965 L3895 8979 L3881 8984 L3887 9003 L3874 9009 L3855 9006 L3850 8994 L3839 9013 L3825 9016 L3810 9008 L3798 8994 L3805 8975 L3790 8956 L3873 8956 L3894 8947 L3933 8898 L3918 8879 L3887 8907 L3887 8898 L3898 8886 L3902 8869 L3898 8853 L3876 8833 L3873 8855 L3867 8862 L3835 8850 L3813 8854 L3802 8848 L3798 8836 L3842 8821 L3835 8811 L3865 8811 L3881 8792 L3922 8789 L3933 8783 L3929 8805 L3945 8807 L3962 8794 L3963 8773 L3952 8765 L3931 8763 L3925 8754 L3927 8745 L3955 8715 L3978 8744 L3970 8691 L3965 8679 L3952 8676 L3929 8685 L3910 8715 L3887 8731 L3878 8730 L3873 8715 L3856 8732 L3798 8754 L3790 8754 L3785 8737 L3745 8763 L3739 8744 L3731 8746 L3715 8763 L3693 8746 L3685 8763 L3677 8763 L3644 8740 L3623 8735 L3602 8744 L3602 8735 L3589 8742 L3546 8735 L3527 8741 L3504 8772 L3489 8783 L3492 8804 L3477 8849 L3474 8879 L3418 8853 L3400 8850 L3352 8856 L3347 8841 L3272 8869 L3257 8889 L3230 8869 L3195 8863 L3182 8869 L3180 8852 L3171 8842 L3159 8841 L3145 8850 L3144 8842 L3137 8841 L3143 8832 L3143 8824 L3129 8811 L3129 8803 L3161 8813 L3179 8813 L3193 8807 L3203 8792 L3207 8770 L3232 8744 L3269 8744 L3349 8732 L3388 8735 L3409 8729 L3422 8678 L3446 8671 L3496 8702 L3512 8696 L3529 8706 L3559 8702 L3572 8706 L3600 8678 L3615 8671 L3710 8668 L3722 8663 L3729 8672 L3769 8686 L3828 8682 L3846 8688 L3865 8706 L3868 8692 L3896 8668 L3889 8651 L3878 8643 L3842 8639 L3850 8630 L3860 8633 L3862 8625 L3842 8600 L3858 8591 L3866 8596 L3896 8581 L3896 8572 L3874 8549 L3858 8524 L3873 8534 L3881 8524 L3865 8504 L3902 8504 L3902 8495 L3881 8495 L3881 8486 L3906 8485 L3925 8495 L3937 8487 L3948 8495 L3966 8487 L3990 8500 L4007 8495 L4016 8524 L4019 8493 L4007 8486 L4007 8476 L4026 8476 L4038 8486 L4068 8438 L4068 8427 L4053 8427 L4068 8399 L4085 8413 L4103 8417 L4112 8409 L4105 8389 L4196 8357 L4196 8349 L4180 8332 L4169 8329 L4026 8351 L3973 8350 L3952 8355 L3955 8380 L3937 8370 L3820 8351 L3782 8370 L3738 8361 L3710 8363 L3621 8394 L3602 8389 L3594 8409 L3575 8404 L3549 8409 L3528 8393 L3493 8392 L3458 8405 L3436 8427 L3386 8402 L3361 8405 L3355 8438 L3318 8412 L3257 8409 L3220 8361 L3203 8362 L3186 8376 L3180 8367 L3182 8361 L3174 8361 L3159 8409 L3154 8399 L3159 8389 L3152 8380 L3157 8373 L3152 8361 L3099 8380 L3104 8404 L3097 8420 L3084 8432 L3069 8438 L3077 8457 L3054 8457 L3047 8446 L3027 8451 L3016 8430 L3009 8375 L2990 8313 L3001 8284 L3029 8275 L3048 8262 L3062 8246 L3045 8235 L3024 8246 L3016 8226 L3024 8235 L3037 8220 L3071 8233 L3092 8226 L3095 8193 L3092 8178 L3111 8189 L3114 8218 L3121 8218 L3135 8192 L3144 8189 L3152 8198 L3159 8187 L3159 8211 L3163 8218 L3182 8218 L3205 8233 L3220 8226 L3211 8235 L3227 8264 L3243 8275 L3260 8270 L3332 8224 L3358 8224 L3370 8218 L3370 8207 L3355 8210 L3347 8218 L3339 8173 L3330 8150 L3317 8140 L3317 8130 L3369 8118 L3383 8122 L3370 8150 L3391 8140 L3407 8120 L3390 8114 L3384 8104 L3385 8077 L3407 8054 L3414 8015 L3390 8003 L3385 8015 L3345 8018 L3334 8050 L3320 8069 L3303 8079 L3287 8073 L3306 8056 L3309 8037 L3297 8025 L3272 8025 L3247 8047 L3242 8039 L3245 8025 L3272 7987 L3278 7942 L3265 7919 L3257 7919 L3252 7958 L3228 7972 L3197 7967 L3174 7948 L3165 7917 L3174 7888 L3194 7866 L3220 7853 L3206 7832 L3185 7822 L3163 7823 L3145 7833 L3130 7869 L3118 7881 L3092 7881 L3092 7891 L3108 7902 L3101 7908 L3037 7912 L3009 7929 L2993 7913 L2979 7919 L2971 7900 L2960 7907 L2948 7900 L2967 7873 L2969 7858 L2964 7842 L2987 7833 L2977 7796 L2983 7733 L2964 7738 L2958 7730 L2950 7730 L2934 7747 L2948 7682 L2941 7661 L2945 7652 L2937 7638 L2941 7622 L2959 7633 L2968 7611 L2972 7580 L2968 7564 L2952 7559 L2888 7517 L2793 7490 L2752 7468 L2762 7439 L2781 7434 L2855 7439 L2879 7436 L2973 7401 L2987 7391 L3013 7358 L3020 7337 L3026 7275 L3024 7258 L2999 7216 L3001 7190 L3024 7162 L3030 7138 L3024 7113 L3040 7099 L3031 7068 L3001 7017 L2974 7027 L2934 7027 L2894 7020 L2867 7008 L2851 6982 L2816 6972 L2810 6943 L2800 6936 L2769 6931 L2712 6909 L2684 6906 L2622 6921 L2609 6946 L2600 6951 L2591 6944 L2566 6893 L2572 6876 L2571 6855 L2559 6816 L2547 6797 L2513 6759 L2494 6769 L2489 6752 L2491 6710 L2476 6697 L2419 6710 L2351 6711 L2340 6715 L2326 6806 L2318 6797 L2311 6797 L2314 6835 L2309 6848 L2295 6854 L2288 6848 L2265 6797 L2265 6826 L2254 6829 L2217 6794 L2208 6768 L2212 6748 L2182 6756 L2128 6703 L2101 6691 L2108 6720 L2101 6720 L2071 6687 L2076 6648 L2071 6634 L2063 6634 L2054 6671 L2031 6680 L2004 6671 L1958 6635 L1901 6617 L1899 6608 L1905 6586 L1934 6599 L1957 6554 L1981 6548 L1981 6537 L1960 6523 L1957 6497 L1966 6482 L1981 6499 L1985 6480 L1995 6471 L2001 6503 L1988 6529 L2023 6540 L2027 6552 L2034 6556 L2065 6554 L2073 6545 L2063 6529 L2063 6519 L2081 6530 L2101 6529 L2165 6486 L2166 6458 L2156 6429 L2138 6414 L2138 6403 L2166 6417 L2179 6431 L2189 6430 L2206 6394 L2163 6360 L2141 6352 L2126 6338 L2116 6336 L2106 6342 L2097 6361 L2090 6365 L2068 6364 L2086 6317 L2082 6301 L2048 6251 L2055 6260 L2037 6192 L2025 6130 L2026 6110 L2034 6074 L2097 6049 L2154 6058 L2197 6086 L2252 6152 L2258 6174 L2283 6215 L2334 6273 L2342 6304 L2343 6331 L2348 6345 L2333 6355 L2313 6344 L2288 6355 L2307 6365 L2306 6377 L2288 6414 L2314 6417 L2325 6433 L2344 6476 L2363 6540 L2381 6570 L2405 6562 L2410 6544 L2403 6532 L2386 6519 L2378 6461 L2384 6437 L2396 6412 L2413 6398 L2431 6403 L2431 6394 L2438 6394 L2463 6433 L2484 6490 L2506 6480 L2515 6498 L2570 6480 L2656 6471 L2728 6442 L2754 6422 L2786 6429 L2799 6422 L2800 6428 L2806 6422 L2836 6437 L2862 6420 L2888 6393 L2919 6375 L2919 6365 L2908 6357 L2896 6365 L2888 6355 L2867 6365 L2830 6361 L2821 6365 L2793 6352 L2764 6353 L2668 6391 L2679 6375 L2660 6362 L2627 6307 L2574 6283 L2549 6263 L2536 6240 L2572 6271 L2601 6290 L2618 6289 L2618 6279 L2605 6263 L2559 6231 L2574 6164 L2558 6148 L2535 6163 L2513 6164 L2521 6144 L2497 6135 L2469 6135 L2476 6106 L2461 6106 L2431 6086 L2447 6071 L2469 6067 L2447 6034 L2431 5991 L2452 5977 L2508 5965 L2540 5942 L2553 5954 L2577 5956 L2617 5972 L2633 5972 L2627 5952 L2655 5933 L2664 5943 L2668 5921 L2664 5895 L2656 5906 L2627 5857 L2671 5838 L2678 5868 L2696 5871 L2708 5853 L2694 5818 L2729 5803 L2754 5780 L2776 5795 L2799 5780 L2808 5758 L2784 5752 L2803 5714 L2802 5698 L2784 5684 L2753 5709 L2720 5713 L2698 5684 L2667 5697 L2656 5684 L2607 5717 L2593 5721 L2581 5715 L2564 5690 L2527 5670 L2517 5638 L2519 5602 L2536 5579 L2536 5569 L2513 5569 L2552 5534 L2600 5512 L2611 5500 L2602 5473 L2577 5430 L2546 5391 L2488 5358 L2452 5324 L2453 5309 L2431 5232 L2412 5223 L2333 5224 L2311 5215 L2322 5204 L2328 5175 L2337 5161 L2351 5155 L2361 5161 L2360 5171 L2340 5176 L2340 5184 L2362 5188 L2378 5204 L2372 5183 L2378 5172 L2401 5157 L2420 5128 L2536 5041 L2521 5031 L2521 4993 L2576 4984 L2589 4974 L2577 4953 L2594 4940 L2662 4917 L2679 4845 L2678 4815 L2671 4795 L2654 4785 L2622 4782 L2597 4792 L2577 4811 L2556 4820 L2529 4801 L2144 4870 L2040 4926 L1958 4917 L1932 4926 L1917 4948 L1897 4936 L1811 4957 L1767 4957 L1725 4936 L1720 4905 L1748 4832 L1765 4763 L1806 4724 L1815 4691 L1823 4614 L1793 4542 L1795 4530 L1808 4513 L1813 4443 L1810 4431 L1793 4427 L1815 4341 L1808 4293 L1827 4237 L1860 4188 L1919 4207 L1984 4173 L2030 4127 L2040 4111 L2048 4056 L2074 4048 L2086 4005 L2085 3979 L2078 3958 L2090 3929 L2127 3925 L2192 3902 L2213 3885 L2261 3822 L2309 3793 L2426 3653 L2449 3635 L2494 3632 L2589 3640 L2627 3631 L2667 3651 L2730 3656 L2754 3651 L2784 3627 L2811 3593 L2845 3567 L2896 3565 L2975 3573 L2999 3567 L3037 3545 L3054 3545 L3072 3558 L3099 3621 L3084 3631 L3077 3631 L3071 3625 L3062 3631 L3109 3682 L3170 3721 L3235 3749 L3312 3768 L3343 3768 L3355 3765 L3393 3740 L3411 3737 L3493 3761 L3520 3746 L3542 3756 L3575 3758 L3604 3751 L3630 3714 L3689 3684 L3707 3659 L3687 3658 L3632 3640 L3607 3650 L3600 3622 L3580 3611 L3568 3594 L3561 3559 L3534 3554 L3489 3505 L3489 3497 L3513 3483 L3531 3463 L3542 3457 L3561 3465 L3572 3448 L3594 3479 L3604 3480 L3610 3471 L3621 3468 L3802 3496 L3850 3512 L3873 3536 L3853 3568 L3758 3616 L3730 3640 L3734 3676 L3774 3688 L3865 3679 L3957 3646 L4216 3634 L4273 3644 L4368 3640 L4347 3648 L4337 3669 L4382 3652 L4432 3652 L4484 3665 L4533 3689 L4540 3680 L4556 3689 L4586 3669 L4648 3659 L4681 3636 L4803 3659 L4863 3689 L4968 3690 L4987 3686 L5002 3674 L5029 3602 L5043 3608 L5061 3607 L5096 3592 L5053 3547 L5027 3532 L5002 3525 L4942 3525 L4897 3554 L4839 3541 L4742 3482 L4683 3468 L4703 3425 L4741 3401 L4818 3372 L4851 3351 L4898 3305 L4915 3297 L5239 3268 L5285 3253 L5360 3209 L5387 3239 L5436 3214 L5445 3193 L5456 3186 L5480 3180 L5508 3190 L5525 3206 L5532 3233 L5544 3233 L5756 3186 L5881 3180 L5920 3197 L5943 3197 L5960 3171 L5949 3139 L5906 3131 L5780 3152 L5739 3122 L5660 3103 L5400 3114 L5344 3141 L5322 3133 L5302 3097 L5291 3094 L5307 3083 L5302 3069 L5276 3046 L5271 3055 L5261 3046 L5252 3054 L5209 3065 L5209 3056 L5227 3049 L5231 3026 L5246 3036 L5246 3027 L5254 3026 L5220 2982 L5194 2964 L5172 2968 L5151 2948 L5089 2920 L5022 2856 L4961 2825 L4969 2815 L4956 2809 L4939 2757 L4959 2746 L4981 2722 L4999 2693 L5014 2640 L5027 2620 L5030 2603 L5006 2586 L5032 2547 L5073 2503 L5116 2474 L5156 2479 L5167 2465 L5184 2463 L5390 2500 L5608 2550 L5900 2591 L6176 2599 L6207 2595 L6249 2570 L6264 2566 L6274 2558 L6290 2531 L6298 2537 L6323 2504 L6336 2498 L6350 2510 L6395 2519 L6431 2546 L6792 2630 L6846 2671 L6939 2688 L7221 2681 L7258 2663 L7307 2671 L7352 2663 L7375 2671 L7383 2669 L7394 2652 L7440 2635 L7476 2613 L7552 2536 L7561 2517 L7569 2452 L7581 2408 L7556 2386 L7552 2375 L7564 2357 L7588 2348 L7638 2345 L7668 2307 L7844 2243 L8077 2094 L8210 2031 L8261 1994 L8364 1961 L8395 1943 L8413 1908 L8484 1830 L8506 1792 L8543 1782 L8603 1779 L8605 1770 L8625 1761 L8631 1744 L8637 1741 L8655 1761 L8675 1752 L8715 1712 L8803 1665 L8834 1656 L8850 1664 L8863 1642 L8889 1625 L8918 1619 L8944 1631 L8962 1629 L9045 1597 L9092 1596 L9124 1589 L9143 1578 L9155 1584 L9232 1565 L9271 1548 L9322 1516 L9494 1460 L9669 1373 L9708 1371 L9789 1385 L9905 1385 L9985 1409 L10219 1431 L10239 1424 L10270 1436 L10413 1424 L10772 1473 L10897 1438 L10938 1435 L11024 1467 L11169 1476 L11226 1469 L11284 1453 L11383 1389 L11415 1350 L11441 1303 L11447 1262 L11494 1272 L11508 1281 L11511 1272 L11531 1270 L11538 1287 L11558 1309 L11553 1328 L11594 1359 L11619 1369 L11651 1367 L11680 1342 L11692 1338 L11708 1341 L11741 1367 L11741 1376 L11683 1370 L11655 1373 L11632 1390 L11613 1442 L11605 1501 L11612 1522 L11642 1575 L11675 1616 L11734 1664 L11734 1674 L11719 1674 L11736 1714 L11751 1733 L11782 1749 L11814 1786 L11831 1799 L11896 1824 L11944 1832 L11996 1875 L12037 1897 L12085 1912 L12136 1918 L12183 1914 L12248 1880 L12316 1869 L12431 1822 L12484 1810 L12529 1775 L12553 1769 L12553 1779 L12542 1796 L12522 1807 L12524 1829 L12503 1872 L12507 1895 L12515 1895 L12518 1862 L12528 1831 L12543 1806 L12570 1780 L12576 1778 L12642 1837 L12642 1818 L12649 1818 L12732 1921 L12747 1961 L12747 2019 L12732 2062 L12731 2108 L12736 2129 L12747 2153 L12796 2212 L12824 2231 L12859 2298 L12932 2340 L12964 2348 L12969 2354 L12977 2396 L13010 2412 L13033 2441 L13064 2448 L13094 2463 L13122 2457 L13167 2432 L13225 2383 L13235 2370 L13259 2319 L13265 2287 L13279 2275 L13336 2287 L13431 2287 L13517 2309 L13679 2388 L13712 2416 L13731 2460 L13733 2522 L13739 2546 L13781 2561 L13844 2595 L13984 2593 L14024 2603 L14061 2633 L14129 2648 L14174 2691 L14219 2705 L14249 2740 L14271 2748 L14314 2743 L14332 2749 L14362 2729 L14397 2658 L14432 2616 L14451 2603 L14461 2626 L14479 2639 L14500 2639 L14519 2623 L14526 2633 L14554 2628 L14556 2716 L14575 2740 L14647 2778 L14677 2825 L14720 2807 L14771 2814 L14903 2856 L14968 2867 L15012 2882 L15037 2882 L15085 2869 L15106 2874 L15154 2915 L15176 2915 L15218 2902 L15287 2917 L15299 2907 L15382 2902 L15439 2852 L15489 2834 L15503 2835 L15534 2872 L15545 2866 L15578 2863 L15606 2839 L15619 2835 L15650 2798 L15751 2773 L15787 2747 L15808 2740 L15933 2739 L16021 2720 L16058 2691 L16071 2688 L16128 2698 L16162 2726 L16186 2729 L16235 2705 L16269 2696 L16328 2663 L16345 2646 L16358 2643 L16427 2659 L16470 2709 L16536 2765 L16577 2788 L16621 2796 L16665 2779 L16687 2776 L16716 2797 L16763 2800 L16828 2850 L16868 2863 L16886 2851 L16955 2828 L16982 2825 L17045 2882 L17076 2903 L17121 2911 L17139 2908 L17236 2874 L17262 2858 L17312 2844 L17492 2729 L17530 2746 L17562 2749 L17593 2741 L17627 2720 L17669 2685 L17717 2677 L17748 2663 L17813 2578 L17889 2523 L17902 2518 L17918 2521 L17965 2537 L17993 2533 L18034 2505 L18100 2487 L18125 2475 L18211 2400 L18287 2386 L18391 2305 L18454 2278 L18506 2269 L18526 2254 L18543 2229 L18554 2199 L18558 2168 L18634 2106 L18649 2080 L18779 2130 L18812 2127 L18848 2115 L18848 2143 L18853 2152 L18912 2165 L18956 2204 L18969 2209 L19023 2167 L19058 2120 L19073 2109 L19117 2092 L19195 2121 L19250 2102 L19265 2100 L19296 2109 L19347 2100 L19381 2126 L19461 2125 L19654 2197 L19681 2195 L19704 2181 L19737 2133 L19761 2109 L19772 2087 L19782 2030 L19793 2006 L19815 1990 L19843 1981 L19898 1976 L20051 1989 L20072 1999 L20064 2012 L20053 2052 L20014 2094 L20042 2110 L20063 2132 L20083 2138 L20110 2109 L20125 2100 L20148 2142 L20189 2157 L20223 2188 L20256 2247 L20272 2264 L20352 2317 L20405 2362 L20439 2377 L20471 2381 L20473 2389 L20442 2422 L20383 2452 L20412 2461 L20458 2461 L20480 2485 L20506 2547 L20522 2558 L20623 2531 L20655 2529 L20689 2538 L20719 2555 L20749 2581 L20765 2614ZM3853 1438 L3869 1521 L3881 1533 L3886 1544 L3884 1554 L3874 1560 L3842 1549 L3824 1550 L3810 1558 L3801 1577 L3798 1611 L3804 1649 L3858 1721 L3879 1784 L3921 1831 L3932 1852 L3930 1866 L3919 1866 L3918 1875 L3941 1923 L3959 1944 L3990 1961 L4030 2019 L4090 2073 L4256 2174 L4493 2271 L4830 2427 L4939 2450 L4957 2460 L4980 2441 L5006 2445 L5033 2455 L5050 2471 L5040 2505 L5025 2531 L5006 2555 L4975 2570 L5008 2618 L4999 2633 L4995 2661 L4977 2707 L4965 2725 L4937 2738 L4919 2756 L4922 2789 L4911 2798 L4887 2796 L4871 2787 L4852 2806 L4820 2822 L4766 2835 L4748 2850 L4735 2854 L4696 2848 L4679 2829 L4651 2828 L4520 2844 L4487 2831 L4496 2787 L4483 2774 L4465 2767 L4473 2735 L4462 2707 L4440 2687 L4413 2681 L4419 2701 L4442 2725 L4451 2749 L4449 2783 L4441 2802 L4428 2815 L4396 2810 L4340 2754 L4312 2740 L4275 2734 L4199 2707 L4124 2701 L4094 2681 L4034 2691 L4016 2681 L3849 2743 L3820 2767 L3796 2805 L3789 2823 L3790 2835 L3770 2840 L3682 2830 L3632 2796 L3590 2785 L3548 2782 L3313 2815 L3279 2835 L3256 2881 L3228 2994 L3205 3036 L3102 3135 L3055 3215 L2956 3286 L2934 3314 L2896 3322 L2865 3341 L2791 3343 L2773 3358 L2741 3402 L2728 3411 L2642 3429 L2579 3468 L2543 3496 L2476 3505 L2420 3548 L2392 3562 L2382 3604 L2371 3621 L2335 3640 L2328 3651 L2319 3697 L2303 3715 L2235 3775 L2203 3783 L2188 3794 L2131 3862 L2111 3878 L2060 3904 L2037 3909 L2022 3920 L2026 3946 L2039 3972 L2055 3985 L2003 4034 L1943 4070 L1896 4109 L1838 4129 L1826 4130 L1816 4123 L1828 4089 L1852 4068 L1879 3996 L1928 3928 L1941 3877 L1936 3839 L1915 3809 L1882 3784 L1894 3775 L1897 3766 L1874 3749 L1884 3736 L1918 3711 L1974 3689 L1995 3689 L2012 3661 L2066 3626 L2118 3584 L2182 3561 L2262 3501 L2326 3479 L2377 3485 L2393 3479 L2446 3411 L2472 3423 L2507 3412 L2538 3387 L2552 3357 L2509 3275 L2426 3288 L2386 3305 L2311 3305 L2281 3314 L2197 3362 L2166 3342 L2131 3333 L2081 3354 L2052 3340 L1975 3358 L1772 3357 L1744 3352 L1728 3343 L1702 3275 L1710 3254 L1707 3223 L1696 3193 L1680 3171 L1692 3166 L1733 3170 L1767 3154 L1791 3126 L1800 3089 L1817 3063 L1876 3014 L1868 2998 L1869 2989 L1883 2979 L1876 2978 L1876 2969 L1890 2963 L1891 2941 L1898 2960 L1906 2960 L1920 2939 L1929 2911 L1935 2911 L1953 2930 L1977 2927 L1966 2903 L1979 2890 L2011 2875 L2037 2849 L2012 2825 L2008 2813 L2012 2804 L2047 2789 L2054 2773 L2053 2756 L2024 2743 L2000 2696 L1997 2676 L2015 2640 L1991 2629 L1991 2617 L2012 2586 L1999 2562 L1995 2537 L2012 2480 L1995 2455 L2007 2444 L2076 2437 L2095 2428 L2154 2384 L2168 2367 L2180 2365 L2235 2307 L2247 2322 L2291 2339 L2312 2337 L2326 2323 L2336 2299 L2341 2270 L2341 2241 L2318 2144 L2308 2068 L2296 2048 L2303 2034 L2299 1997 L2303 1981 L2297 1963 L2296 1943 L2275 1973 L2264 1962 L2214 1937 L2152 1892 L2162 1874 L2165 1854 L2087 1831 L2057 1805 L2037 1799 L2009 1802 L1998 1787 L1990 1759 L1994 1728 L2010 1695 L2055 1657 L2168 1661 L2220 1646 L2235 1627 L2244 1601 L2256 1538 L2257 1530 L2238 1511 L2289 1458 L2307 1446 L2327 1443 L2430 1460 L2451 1457 L2486 1427 L2499 1423 L2529 1445 L2541 1448 L2587 1417 L2619 1420 L2642 1404 L2672 1405 L2703 1360 L2740 1340 L2764 1297 L2790 1284 L2831 1290 L2866 1313 L2903 1313 L2930 1320 L2962 1277 L2976 1266 L3000 1263 L3039 1272 L3074 1291 L3103 1320 L3150 1388 L3174 1415 L3200 1437 L3281 1480 L3297 1494 L3323 1529 L3338 1538 L3356 1531 L3341 1525 L3353 1515 L3343 1506 L3366 1498 L3386 1480 L3400 1486 L3407 1465 L3492 1444 L3532 1445 L3604 1480 L3632 1474 L3636 1466 L3619 1456 L3621 1423 L3624 1409 L3629 1407 L3673 1406 L3744 1431 L3797 1425ZM1710 4427 L1728 4417 L1734 4431 L1733 4480 L1726 4501 L1708 4499 L1640 4460 L1626 4449 L1619 4432 L1628 4421 L1648 4417 L1699 4418ZM1657 3967 L1657 3996 L1633 4008 L1608 4017 L1534 4028 L1486 4049 L1387 4064 L1338 4053 L1320 4039 L1275 4023 L1275 4015 L1300 3975 L1336 3938 L1379 3911 L1454 3897 L1562 3860 L1576 3862 L1597 3888 L1613 3890 L1608 3929 L1608 3947 L1613 3958 L1603 3980 L1614 3985ZM3460 3286 L3477 3281 L3509 3286 L3537 3300 L3542 3325 L3522 3339 L3460 3352 L3423 3384 L3402 3392 L3344 3373 L3326 3357 L3330 3327 L3316 3305 L3321 3290 L3337 3276 L3343 3279 L3347 3294 L3402 3271 L3431 3271ZM3446 3556 L3459 3559 L3459 3571 L3447 3573 L3431 3565 L3393 3559 L3377 3548 L3375 3533 L3386 3523 L3404 3492 L3441 3508 L3443 3518 L3435 3547Z"/><path class="m-road" data-lvl="3" d="M3026 7199 L3068 7154 L3106 7105 L3139 7077"/><path class="m-road" data-lvl="3" d="M3026 7199 L3068 7241 L3134 7294 L3188 7347"/><path class="m-road" data-lvl="3" d="M3026 7199 L3022 7252 L3008 7301 L2975 7371"/><text class="m-lab m-big" data-lvl="1" x="9532" y="4900" font-size="1100">TÜRKİYE</text><text class="m-lab m-sea-lab" data-lvl="1" x="1205" y="5740" font-size="420">Ege Denizi</text><text class="m-lab m-sea-lab" data-lvl="1" x="9313" y="420" font-size="420">Karadeniz</text><text class="m-lab m-sea-lab" data-lvl="1" x="6026" y="10360" font-size="420">Akdeniz</text><circle class="m-dot" data-lvl="2" cx="2893" cy="6412" r="24"/><text class="m-lab" data-lvl="2" x="2947" y="6440" font-size="95">İzmir</text><circle class="m-dot" data-lvl="2" cx="3210" cy="8344" r="24"/><text class="m-lab" data-lvl="2" x="3265" y="8358" font-size="95">Bodrum</text><circle class="m-dot" data-lvl="2" cx="3035" cy="7882" r="24"/><text class="m-lab" data-lvl="2" x="3090" y="7896" font-size="95">Didim</text><circle class="m-dot" data-lvl="2" cx="3026" cy="7199" r="30"/><text class="m-lab m-strong" data-lvl="2" x="3079" y="7196" font-size="110">Kuşadası</text><text class="m-lab m-sea-lab" data-lvl="2" x="1753" y="7070" font-size="150">Ege Denizi</text><circle class="m-dot" data-lvl="3" cx="3139" cy="7077" r="5"/><text class="m-lab" data-lvl="3" x="3148" y="7069" font-size="15">Selçuk · Efes</text><circle class="m-dot" data-lvl="3" cx="3188" cy="7347" r="5"/><text class="m-lab" data-lvl="3" x="3197" y="7356" font-size="15">Söke</text><circle class="m-dot" data-lvl="3" cx="3044" cy="7067" r="5"/><text class="m-lab" data-lvl="3" x="3052" y="7053" font-size="15">Pamucak</text><circle class="m-dot" data-lvl="3" cx="2987" cy="7385" r="5"/><text class="m-lab" data-lvl="3" x="2903" y="7368" font-size="15">Güzelçamlı</text><text class="m-lab m-sea-lab" data-lvl="3" x="2805" y="7161" font-size="22">Ege Denizi</text><text class="m-lab m-sea-lab" data-lvl="3" x="2739" y="7371" font-size="15">Sisam</text></svg>
      <span class="gplace-zoom-tag" data-drone-tag aria-hidden="true">Türkiye</span><span class="gplace-pin-v3350" aria-hidden="true"><span class="gplace-pin-head-v3350"><img src="assets/brand/bgstudio3d-monogram.webp" alt="" width="40" height="40" loading="lazy" decoding="async"/></span></span>
      <span class="gplace-place-v3350"><strong>BG Studio 3D</strong><small>Kuşadası, Aydın · Haritada aç ↗</small></span>
    </a>
    <div class="gplace-copy-v3350">
      <p class="gplace-source-v3350"><svg viewBox="0 0 48 48" width="20" height="20" aria-hidden="true" focusable="false"><path fill="#4285F4" d="M45.1 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h11.8c-.5 2.8-2.1 5.1-4.4 6.7v5.5h7.1c4.2-3.8 6.6-9.5 6.6-16.2z"/><path fill="#34A853" d="M24 46c6 0 11-2 14.6-5.3l-7.1-5.5c-2 1.3-4.5 2.1-7.5 2.1-5.8 0-10.6-3.9-12.4-9.1H4.3v5.7C7.9 41.1 15.4 46 24 46z"/><path fill="#FBBC05" d="M11.6 28.2c-.4-1.3-.7-2.7-.7-4.2s.3-2.9.7-4.2v-5.7H4.3C2.8 17.1 2 20.5 2 24s.8 6.9 2.3 9.9l7.3-5.7z"/><path fill="#EA4335" d="M24 10.7c3.3 0 6.2 1.1 8.5 3.3l6.3-6.3C35 4.2 30 2 24 2 15.4 2 7.9 6.9 4.3 14.1l7.3 5.7c1.8-5.2 6.6-9.1 12.4-9.1z"/></svg>Google İşletme Profili</p>
      <h2 id="home-reviews-title">Kuşadası'ndayız. Müşterilerimiz bizi Google'da anlatıyor.</h2>
      <div class="gplace-score-v3350">
        <strong class="review-score-v3328">{google_review_values_v3351()['label']}</strong>
        <span class="gplace-score-meta-v3350"><span class="review-stars-v3328" role="img" aria-label="5 üzerinden {google_review_values_v3351()['label']} yıldız" style="--rating-pct:{google_review_values_v3351()['pct']}%">★★★★★</span><span class="review-count-v3328">{google_review_values_v3351()['count']} Google yorumu</span></span>
      </div>
      <div class="gplace-actions-v3350">
        <a class="primary-cta" href="{GOOGLE_REVIEWS_URL_V3328}" rel="noopener" target="_blank">Yorumları oku</a>
        <a class="secondary-cta" href="{GOOGLE_WRITE_REVIEW_URL_V3328}" rel="noopener" target="_blank">Yorum yaz</a>
      </div>
    </div>
  </div>
</section>

<section class="home-why-v3163 home-why-v3196 bg-section" aria-labelledby="home-why-title">
  <div class="shell home-why-shell home-why-shell-v3196">
    <div class="home-why-heading home-motion" data-home-motion><div class="home-why-kicker"><p class="eyebrow">{esc(home_copy["why_eyebrow"])}</p><p class="home-why-intro">Fikir, model, üretim ve teslim adımlarını birbirinden koparmadan tek stüdyo içinde yürütüyoruz.</p></div><h2 id="home-why-title">{_site_why_title_html(home_copy["why_title"])}</h2></div>
    <div class="home-bento-grid-v3196">
      <article class="home-bento-card-v3196 home-bento-primary-v3196 home-motion" data-home-motion>
        <div class="home-bento-card-head-v3196"><span class="home-bento-index-v3196">01</span><span class="home-bento-label-v3196">TASARIM + ÜRETİM</span></div>
        <div class="bento-print-stage" aria-hidden="true"><svg viewBox="0 0 240 170" focusable="false"><defs><clipPath id="bentoVaseClip"><path d="M98 156C92 130 80 112 84 92C88 72 104 62 106 44C107 34 102 28 104 24H136C138 28 133 34 134 44C136 62 152 72 156 92C160 112 148 130 142 156Z"/></clipPath><pattern id="bentoLayers" width="8" height="3.2" patternUnits="userSpaceOnUse"><rect width="8" height="3.2" fill="#c08550"/><rect y="2.4" width="8" height=".8" fill="#8a4e0e" opacity=".55"/></pattern></defs><rect class="bento-print-plate" x="44" y="156" width="152" height="6" rx="3"/><g clip-path="url(#bentoVaseClip)"><rect class="bento-print-fill" x="70" y="20" width="100" height="136" fill="url(#bentoLayers)"/></g><path class="bento-print-outline" d="M98 156C92 130 80 112 84 92C88 72 104 62 106 44C107 34 102 28 104 24H136C138 28 133 34 134 44C136 62 152 72 156 92C160 112 148 130 142 156Z" pathLength="1"/><g class="bento-print-gantry"><line class="bento-print-rail" x1="28" y1="0" x2="212" y2="0"/><g transform="translate(120 0)"><g class="bento-print-head"><rect x="-10" y="-13" width="20" height="13" rx="3.5"/><path d="M-3.5 0h7l-3.5 5z"/></g></g></g></svg></div>
        <div class="home-bento-copy-v3196"><h3>Fikirden üretilebilir ürüne.</h3><p>Görsel fikri ölçü, malzeme, baskı süresi ve nasıl kullanılacağıyla birlikte ele alıyoruz. Tasarım ekranda kalmıyor, üretime bağlanıyor.</p></div>
        <div class="home-bento-flow-v3196" aria-hidden="true"><span style="--i:0">Fikir</span><i></i><span style="--i:1">Model</span><i></i><span style="--i:2">Test</span><i></i><span style="--i:3">Üretim</span></div>
      </article>
      <article class="home-bento-card-v3196 home-bento-volume-v3196 home-motion" data-home-motion>
        <div class="home-bento-card-head-v3196"><span class="home-bento-index-v3196">02</span><span class="home-bento-label-v3196">ÖLÇEKLENEBİLİR ÜRETİM</span></div>
        <div class="bento-qty-stage" aria-hidden="true"><div class="bento-qty-one"><i style="--i:0"></i></div><div class="bento-qty-ten"><i style="--i:1"></i><i style="--i:2"></i><i style="--i:3"></i><i style="--i:4"></i><i style="--i:5"></i><i style="--i:6"></i><i style="--i:7"></i><i style="--i:8"></i><i style="--i:9"></i><i style="--i:10"></i></div><div class="bento-qty-hundred"><i style="--i:0"></i><i style="--i:1"></i><i style="--i:2"></i><i style="--i:3"></i><i style="--i:4"></i><i style="--i:5"></i><i style="--i:6"></i><i style="--i:7"></i><i style="--i:8"></i><i style="--i:9"></i><i style="--i:10"></i><i style="--i:11"></i><i style="--i:12"></i><i style="--i:13"></i><i style="--i:14"></i><i style="--i:15"></i><i style="--i:16"></i><i style="--i:17"></i><i style="--i:18"></i><i style="--i:19"></i><i style="--i:20"></i><i style="--i:21"></i><i style="--i:22"></i><i style="--i:23"></i><i style="--i:24"></i><i style="--i:25"></i><i style="--i:26"></i><i style="--i:27"></i><i style="--i:28"></i><i style="--i:29"></i><i style="--i:30"></i><i style="--i:31"></i><i style="--i:32"></i><i style="--i:33"></i><i style="--i:34"></i><i style="--i:35"></i><i style="--i:36"></i><i style="--i:37"></i><i style="--i:38"></i><i style="--i:39"></i><i style="--i:40"></i><i style="--i:41"></i><i style="--i:42"></i><i style="--i:43"></i><i style="--i:44"></i><i style="--i:45"></i><i style="--i:46"></i><i style="--i:47"></i><i style="--i:48"></i><i style="--i:49"></i><i style="--i:50"></i><i style="--i:51"></i><i style="--i:52"></i><i style="--i:53"></i><i style="--i:54"></i><i style="--i:55"></i><i style="--i:56"></i><i style="--i:57"></i><i style="--i:58"></i><i style="--i:59"></i><i style="--i:60"></i><i style="--i:61"></i><i style="--i:62"></i><i style="--i:63"></i><i style="--i:64"></i><i style="--i:65"></i><i style="--i:66"></i><i style="--i:67"></i><i style="--i:68"></i><i style="--i:69"></i><i style="--i:70"></i><i style="--i:71"></i><i style="--i:72"></i><i style="--i:73"></i><i style="--i:74"></i><i style="--i:75"></i><i style="--i:76"></i><i style="--i:77"></i><i style="--i:78"></i><i style="--i:79"></i><i style="--i:80"></i><i style="--i:81"></i><i style="--i:82"></i><i style="--i:83"></i><i style="--i:84"></i><i style="--i:85"></i><i style="--i:86"></i><i style="--i:87"></i><i style="--i:88"></i><i style="--i:89"></i><i style="--i:90"></i><i style="--i:91"></i><i style="--i:92"></i><i style="--i:93"></i><i style="--i:94"></i><i style="--i:95"></i><i style="--i:96"></i><i style="--i:97"></i><i style="--i:98"></i><i style="--i:99"></i></div></div>
        <div class="home-bento-copy-v3196"><h3>Tek adetten toplu üretime.</h3><p>Prototip, kişisel sipariş ve işletme için adetli üretim aynı süreçte ilerler.</p></div>
        <div class="home-bento-quantity-v3196" aria-hidden="true"><span><b>1</b><small>PROTOTİP</small></span><span><b>10</b><small>KÜÇÜK SERİ</small></span><span><b>100+</b><small>TOPLU</small></span></div>
      </article>
      <article class="home-bento-card-v3196 home-bento-digital-v3196 home-motion" data-home-motion>
        <div class="home-bento-card-head-v3196"><span class="home-bento-index-v3196">03</span><span class="home-bento-label-v3196">İŞLETME SİSTEMLERİ</span></div>
        <div class="bento-nfc-stage" aria-hidden="true"><div class="bento-nfc-stand"><svg viewBox="0 0 24 24" focusable="false"><path d="M7 7.5a6 6 0 0 1 0 9M10.2 5.2a9.5 9.5 0 0 1 0 13.6M13.4 3a13 13 0 0 1 0 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></div><span class="bento-nfc-ring"></span><span class="bento-nfc-ring bento-nfc-ring-late"></span><div class="bento-nfc-phone"><div class="bento-nfc-screen"><span style="--i:0"><b>NFC</b><small>Dokun, bağlan</small></span><span style="--i:1"><b>QR</b><small>Okut, aç</small></span><span style="--i:2"><b>Menü</b><small>Dijital menü</small></span><span style="--i:3"><b>Yorum</b><small>Google yorumu</small></span><span style="--i:4"><b>Sosyal</b><small>Instagram</small></span></div></div></div>
        <div class="home-bento-copy-v3196"><h3>Fiziksel + dijital.</h3><p>3D üretilen standları NFC, QR ve işletmeye özel dijital deneyimlerle bir araya getiriyoruz.</p></div>
        <div class="home-bento-signal-v3196" aria-hidden="true"><span style="--i:0">NFC</span><span style="--i:1">QR</span><span style="--i:2">MENÜ</span><span style="--i:3">YORUM</span><span style="--i:4">SOSYAL</span></div>
      </article>
      <article class="home-bento-card-v3196 home-bento-local-v3196 home-motion" data-home-motion>
        <div class="home-bento-card-head-v3196"><span class="home-bento-index-v3196">04</span><span class="home-bento-label-v3196">KUŞADASI MERKEZLİ</span></div>
        <div class="bento-map-stage"><svg class="bento-map-svg" viewBox="0 0 310 136" aria-hidden="true" focusable="false"><g class="bento-map-dots"><circle cx="30.0" cy="9.0" r="1.5"/><circle cx="126.0" cy="9.0" r="1.5"/><circle cx="132.0" cy="9.0" r="1.5"/><circle cx="138.0" cy="9.0" r="1.5"/><circle cx="144.0" cy="9.0" r="1.5"/><circle cx="150.0" cy="9.0" r="1.5"/><circle cx="15.0" cy="15.0" r="1.5"/><circle cx="21.0" cy="15.0" r="1.5"/><circle cx="27.0" cy="15.0" r="1.5"/><circle cx="33.0" cy="15.0" r="1.5"/><circle cx="39.0" cy="15.0" r="1.5"/><circle cx="111.0" cy="15.0" r="1.5"/><circle cx="117.0" cy="15.0" r="1.5"/><circle cx="123.0" cy="15.0" r="1.5"/><circle cx="129.0" cy="15.0" r="1.5"/><circle cx="135.0" cy="15.0" r="1.5"/><circle cx="141.0" cy="15.0" r="1.5"/><circle cx="147.0" cy="15.0" r="1.5"/><circle cx="153.0" cy="15.0" r="1.5"/><circle cx="18.0" cy="21.0" r="1.5"/><circle cx="24.0" cy="21.0" r="1.5"/><circle cx="30.0" cy="21.0" r="1.5"/><circle cx="36.0" cy="21.0" r="1.5"/><circle cx="42.0" cy="21.0" r="1.5"/><circle cx="48.0" cy="21.0" r="1.5"/><circle cx="96.0" cy="21.0" r="1.5"/><circle cx="102.0" cy="21.0" r="1.5"/><circle cx="108.0" cy="21.0" r="1.5"/><circle cx="114.0" cy="21.0" r="1.5"/><circle cx="120.0" cy="21.0" r="1.5"/><circle cx="126.0" cy="21.0" r="1.5"/><circle cx="132.0" cy="21.0" r="1.5"/><circle cx="138.0" cy="21.0" r="1.5"/><circle cx="144.0" cy="21.0" r="1.5"/><circle cx="150.0" cy="21.0" r="1.5"/><circle cx="156.0" cy="21.0" r="1.5"/><circle cx="162.0" cy="21.0" r="1.5"/><circle cx="168.0" cy="21.0" r="1.5"/><circle cx="252.0" cy="21.0" r="1.5"/><circle cx="258.0" cy="21.0" r="1.5"/><circle cx="264.0" cy="21.0" r="1.5"/><circle cx="270.0" cy="21.0" r="1.5"/><circle cx="15.0" cy="27.0" r="1.5"/><circle cx="21.0" cy="27.0" r="1.5"/><circle cx="27.0" cy="27.0" r="1.5"/><circle cx="33.0" cy="27.0" r="1.5"/><circle cx="39.0" cy="27.0" r="1.5"/><circle cx="45.0" cy="27.0" r="1.5"/><circle cx="51.0" cy="27.0" r="1.5"/><circle cx="57.0" cy="27.0" r="1.5"/><circle cx="63.0" cy="27.0" r="1.5"/><circle cx="69.0" cy="27.0" r="1.5"/><circle cx="75.0" cy="27.0" r="1.5"/><circle cx="81.0" cy="27.0" r="1.5"/><circle cx="87.0" cy="27.0" r="1.5"/><circle cx="93.0" cy="27.0" r="1.5"/><circle cx="99.0" cy="27.0" r="1.5"/><circle cx="105.0" cy="27.0" r="1.5"/><circle cx="111.0" cy="27.0" r="1.5"/><circle cx="117.0" cy="27.0" r="1.5"/><circle cx="123.0" cy="27.0" r="1.5"/><circle cx="129.0" cy="27.0" r="1.5"/><circle cx="135.0" cy="27.0" r="1.5"/><circle cx="141.0" cy="27.0" r="1.5"/><circle cx="147.0" cy="27.0" r="1.5"/><circle cx="153.0" cy="27.0" r="1.5"/><circle cx="159.0" cy="27.0" r="1.5"/><circle cx="165.0" cy="27.0" r="1.5"/><circle cx="171.0" cy="27.0" r="1.5"/><circle cx="177.0" cy="27.0" r="1.5"/><circle cx="183.0" cy="27.0" r="1.5"/><circle cx="189.0" cy="27.0" r="1.5"/><circle cx="243.0" cy="27.0" r="1.5"/><circle cx="249.0" cy="27.0" r="1.5"/><circle cx="255.0" cy="27.0" r="1.5"/><circle cx="261.0" cy="27.0" r="1.5"/><circle cx="267.0" cy="27.0" r="1.5"/><circle cx="273.0" cy="27.0" r="1.5"/><circle cx="279.0" cy="27.0" r="1.5"/><circle cx="285.0" cy="27.0" r="1.5"/><circle cx="12.0" cy="33.0" r="1.5"/><circle cx="18.0" cy="33.0" r="1.5"/><circle cx="24.0" cy="33.0" r="1.5"/><circle cx="30.0" cy="33.0" r="1.5"/><circle cx="36.0" cy="33.0" r="1.5"/><circle cx="42.0" cy="33.0" r="1.5"/><circle cx="48.0" cy="33.0" r="1.5"/><circle cx="54.0" cy="33.0" r="1.5"/><circle cx="60.0" cy="33.0" r="1.5"/><circle cx="66.0" cy="33.0" r="1.5"/><circle cx="72.0" cy="33.0" r="1.5"/><circle cx="78.0" cy="33.0" r="1.5"/><circle cx="84.0" cy="33.0" r="1.5"/><circle cx="90.0" cy="33.0" r="1.5"/><circle cx="96.0" cy="33.0" r="1.5"/><circle cx="102.0" cy="33.0" r="1.5"/><circle cx="108.0" cy="33.0" r="1.5"/><circle cx="114.0" cy="33.0" r="1.5"/><circle cx="120.0" cy="33.0" r="1.5"/><circle cx="126.0" cy="33.0" r="1.5"/><circle cx="132.0" cy="33.0" r="1.5"/><circle cx="138.0" cy="33.0" r="1.5"/><circle cx="144.0" cy="33.0" r="1.5"/><circle cx="150.0" cy="33.0" r="1.5"/><circle cx="156.0" cy="33.0" r="1.5"/><circle cx="162.0" cy="33.0" r="1.5"/><circle cx="168.0" cy="33.0" r="1.5"/><circle cx="174.0" cy="33.0" r="1.5"/><circle cx="180.0" cy="33.0" r="1.5"/><circle cx="186.0" cy="33.0" r="1.5"/><circle cx="192.0" cy="33.0" r="1.5"/><circle cx="198.0" cy="33.0" r="1.5"/><circle cx="204.0" cy="33.0" r="1.5"/><circle cx="210.0" cy="33.0" r="1.5"/><circle cx="216.0" cy="33.0" r="1.5"/><circle cx="222.0" cy="33.0" r="1.5"/><circle cx="228.0" cy="33.0" r="1.5"/><circle cx="234.0" cy="33.0" r="1.5"/><circle cx="240.0" cy="33.0" r="1.5"/><circle cx="246.0" cy="33.0" r="1.5"/><circle cx="252.0" cy="33.0" r="1.5"/><circle cx="258.0" cy="33.0" r="1.5"/><circle cx="264.0" cy="33.0" r="1.5"/><circle cx="270.0" cy="33.0" r="1.5"/><circle cx="276.0" cy="33.0" r="1.5"/><circle cx="282.0" cy="33.0" r="1.5"/><circle cx="9.0" cy="39.0" r="1.5"/><circle cx="15.0" cy="39.0" r="1.5"/><circle cx="21.0" cy="39.0" r="1.5"/><circle cx="27.0" cy="39.0" r="1.5"/><circle cx="33.0" cy="39.0" r="1.5"/><circle cx="39.0" cy="39.0" r="1.5"/><circle cx="45.0" cy="39.0" r="1.5"/><circle cx="51.0" cy="39.0" r="1.5"/><circle cx="57.0" cy="39.0" r="1.5"/><circle cx="63.0" cy="39.0" r="1.5"/><circle cx="69.0" cy="39.0" r="1.5"/><circle cx="75.0" cy="39.0" r="1.5"/><circle cx="81.0" cy="39.0" r="1.5"/><circle cx="87.0" cy="39.0" r="1.5"/><circle cx="93.0" cy="39.0" r="1.5"/><circle cx="99.0" cy="39.0" r="1.5"/><circle cx="105.0" cy="39.0" r="1.5"/><circle cx="111.0" cy="39.0" r="1.5"/><circle cx="117.0" cy="39.0" r="1.5"/><circle cx="123.0" cy="39.0" r="1.5"/><circle cx="129.0" cy="39.0" r="1.5"/><circle cx="135.0" cy="39.0" r="1.5"/><circle cx="141.0" cy="39.0" r="1.5"/><circle cx="147.0" cy="39.0" r="1.5"/><circle cx="153.0" cy="39.0" r="1.5"/><circle cx="159.0" cy="39.0" r="1.5"/><circle cx="165.0" cy="39.0" r="1.5"/><circle cx="171.0" cy="39.0" r="1.5"/><circle cx="177.0" cy="39.0" r="1.5"/><circle cx="183.0" cy="39.0" r="1.5"/><circle cx="189.0" cy="39.0" r="1.5"/><circle cx="195.0" cy="39.0" r="1.5"/><circle cx="201.0" cy="39.0" r="1.5"/><circle cx="207.0" cy="39.0" r="1.5"/><circle cx="213.0" cy="39.0" r="1.5"/><circle cx="219.0" cy="39.0" r="1.5"/><circle cx="225.0" cy="39.0" r="1.5"/><circle cx="231.0" cy="39.0" r="1.5"/><circle cx="237.0" cy="39.0" r="1.5"/><circle cx="243.0" cy="39.0" r="1.5"/><circle cx="249.0" cy="39.0" r="1.5"/><circle cx="255.0" cy="39.0" r="1.5"/><circle cx="261.0" cy="39.0" r="1.5"/><circle cx="267.0" cy="39.0" r="1.5"/><circle cx="273.0" cy="39.0" r="1.5"/><circle cx="279.0" cy="39.0" r="1.5"/><circle cx="285.0" cy="39.0" r="1.5"/><circle cx="18.0" cy="45.0" r="1.5"/><circle cx="24.0" cy="45.0" r="1.5"/><circle cx="30.0" cy="45.0" r="1.5"/><circle cx="36.0" cy="45.0" r="1.5"/><circle cx="42.0" cy="45.0" r="1.5"/><circle cx="48.0" cy="45.0" r="1.5"/><circle cx="54.0" cy="45.0" r="1.5"/><circle cx="60.0" cy="45.0" r="1.5"/><circle cx="66.0" cy="45.0" r="1.5"/><circle cx="72.0" cy="45.0" r="1.5"/><circle cx="78.0" cy="45.0" r="1.5"/><circle cx="84.0" cy="45.0" r="1.5"/><circle cx="90.0" cy="45.0" r="1.5"/><circle cx="96.0" cy="45.0" r="1.5"/><circle cx="102.0" cy="45.0" r="1.5"/><circle cx="108.0" cy="45.0" r="1.5"/><circle cx="114.0" cy="45.0" r="1.5"/><circle cx="120.0" cy="45.0" r="1.5"/><circle cx="126.0" cy="45.0" r="1.5"/><circle cx="132.0" cy="45.0" r="1.5"/><circle cx="138.0" cy="45.0" r="1.5"/><circle cx="144.0" cy="45.0" r="1.5"/><circle cx="150.0" cy="45.0" r="1.5"/><circle cx="156.0" cy="45.0" r="1.5"/><circle cx="162.0" cy="45.0" r="1.5"/><circle cx="168.0" cy="45.0" r="1.5"/><circle cx="174.0" cy="45.0" r="1.5"/><circle cx="180.0" cy="45.0" r="1.5"/><circle cx="186.0" cy="45.0" r="1.5"/><circle cx="192.0" cy="45.0" r="1.5"/><circle cx="198.0" cy="45.0" r="1.5"/><circle cx="204.0" cy="45.0" r="1.5"/><circle cx="210.0" cy="45.0" r="1.5"/><circle cx="216.0" cy="45.0" r="1.5"/><circle cx="222.0" cy="45.0" r="1.5"/><circle cx="228.0" cy="45.0" r="1.5"/><circle cx="234.0" cy="45.0" r="1.5"/><circle cx="240.0" cy="45.0" r="1.5"/><circle cx="246.0" cy="45.0" r="1.5"/><circle cx="252.0" cy="45.0" r="1.5"/><circle cx="258.0" cy="45.0" r="1.5"/><circle cx="264.0" cy="45.0" r="1.5"/><circle cx="270.0" cy="45.0" r="1.5"/><circle cx="276.0" cy="45.0" r="1.5"/><circle cx="282.0" cy="45.0" r="1.5"/><circle cx="288.0" cy="45.0" r="1.5"/><circle cx="294.0" cy="45.0" r="1.5"/><circle cx="15.0" cy="51.0" r="1.5"/><circle cx="21.0" cy="51.0" r="1.5"/><circle cx="27.0" cy="51.0" r="1.5"/><circle cx="33.0" cy="51.0" r="1.5"/><circle cx="39.0" cy="51.0" r="1.5"/><circle cx="45.0" cy="51.0" r="1.5"/><circle cx="51.0" cy="51.0" r="1.5"/><circle cx="57.0" cy="51.0" r="1.5"/><circle cx="63.0" cy="51.0" r="1.5"/><circle cx="69.0" cy="51.0" r="1.5"/><circle cx="75.0" cy="51.0" r="1.5"/><circle cx="81.0" cy="51.0" r="1.5"/><circle cx="87.0" cy="51.0" r="1.5"/><circle cx="93.0" cy="51.0" r="1.5"/><circle cx="99.0" cy="51.0" r="1.5"/><circle cx="105.0" cy="51.0" r="1.5"/><circle cx="111.0" cy="51.0" r="1.5"/><circle cx="117.0" cy="51.0" r="1.5"/><circle cx="123.0" cy="51.0" r="1.5"/><circle cx="129.0" cy="51.0" r="1.5"/><circle cx="135.0" cy="51.0" r="1.5"/><circle cx="141.0" cy="51.0" r="1.5"/><circle cx="147.0" cy="51.0" r="1.5"/><circle cx="153.0" cy="51.0" r="1.5"/><circle cx="159.0" cy="51.0" r="1.5"/><circle cx="165.0" cy="51.0" r="1.5"/><circle cx="171.0" cy="51.0" r="1.5"/><circle cx="177.0" cy="51.0" r="1.5"/><circle cx="183.0" cy="51.0" r="1.5"/><circle cx="189.0" cy="51.0" r="1.5"/><circle cx="195.0" cy="51.0" r="1.5"/><circle cx="201.0" cy="51.0" r="1.5"/><circle cx="207.0" cy="51.0" r="1.5"/><circle cx="213.0" cy="51.0" r="1.5"/><circle cx="219.0" cy="51.0" r="1.5"/><circle cx="225.0" cy="51.0" r="1.5"/><circle cx="231.0" cy="51.0" r="1.5"/><circle cx="237.0" cy="51.0" r="1.5"/><circle cx="243.0" cy="51.0" r="1.5"/><circle cx="249.0" cy="51.0" r="1.5"/><circle cx="255.0" cy="51.0" r="1.5"/><circle cx="261.0" cy="51.0" r="1.5"/><circle cx="267.0" cy="51.0" r="1.5"/><circle cx="273.0" cy="51.0" r="1.5"/><circle cx="279.0" cy="51.0" r="1.5"/><circle cx="285.0" cy="51.0" r="1.5"/><circle cx="291.0" cy="51.0" r="1.5"/><circle cx="297.0" cy="51.0" r="1.5"/><circle cx="12.0" cy="57.0" r="1.5"/><circle cx="18.0" cy="57.0" r="1.5"/><circle cx="24.0" cy="57.0" r="1.5"/><circle cx="30.0" cy="57.0" r="1.5"/><circle cx="36.0" cy="57.0" r="1.5"/><circle cx="42.0" cy="57.0" r="1.5"/><circle cx="48.0" cy="57.0" r="1.5"/><circle cx="54.0" cy="57.0" r="1.5"/><circle cx="60.0" cy="57.0" r="1.5"/><circle cx="66.0" cy="57.0" r="1.5"/><circle cx="72.0" cy="57.0" r="1.5"/><circle cx="78.0" cy="57.0" r="1.5"/><circle cx="84.0" cy="57.0" r="1.5"/><circle cx="90.0" cy="57.0" r="1.5"/><circle cx="96.0" cy="57.0" r="1.5"/><circle cx="102.0" cy="57.0" r="1.5"/><circle cx="108.0" cy="57.0" r="1.5"/><circle cx="114.0" cy="57.0" r="1.5"/><circle cx="120.0" cy="57.0" r="1.5"/><circle cx="126.0" cy="57.0" r="1.5"/><circle cx="132.0" cy="57.0" r="1.5"/><circle cx="138.0" cy="57.0" r="1.5"/><circle cx="144.0" cy="57.0" r="1.5"/><circle cx="150.0" cy="57.0" r="1.5"/><circle cx="156.0" cy="57.0" r="1.5"/><circle cx="162.0" cy="57.0" r="1.5"/><circle cx="168.0" cy="57.0" r="1.5"/><circle cx="174.0" cy="57.0" r="1.5"/><circle cx="180.0" cy="57.0" r="1.5"/><circle cx="186.0" cy="57.0" r="1.5"/><circle cx="192.0" cy="57.0" r="1.5"/><circle cx="198.0" cy="57.0" r="1.5"/><circle cx="204.0" cy="57.0" r="1.5"/><circle cx="210.0" cy="57.0" r="1.5"/><circle cx="216.0" cy="57.0" r="1.5"/><circle cx="222.0" cy="57.0" r="1.5"/><circle cx="228.0" cy="57.0" r="1.5"/><circle cx="234.0" cy="57.0" r="1.5"/><circle cx="240.0" cy="57.0" r="1.5"/><circle cx="246.0" cy="57.0" r="1.5"/><circle cx="252.0" cy="57.0" r="1.5"/><circle cx="258.0" cy="57.0" r="1.5"/><circle cx="264.0" cy="57.0" r="1.5"/><circle cx="270.0" cy="57.0" r="1.5"/><circle cx="276.0" cy="57.0" r="1.5"/><circle cx="282.0" cy="57.0" r="1.5"/><circle cx="288.0" cy="57.0" r="1.5"/><circle cx="294.0" cy="57.0" r="1.5"/><circle cx="300.0" cy="57.0" r="1.5"/><circle cx="21.0" cy="63.0" r="1.5"/><circle cx="27.0" cy="63.0" r="1.5"/><circle cx="33.0" cy="63.0" r="1.5"/><circle cx="39.0" cy="63.0" r="1.5"/><circle cx="45.0" cy="63.0" r="1.5"/><circle cx="51.0" cy="63.0" r="1.5"/><circle cx="57.0" cy="63.0" r="1.5"/><circle cx="63.0" cy="63.0" r="1.5"/><circle cx="69.0" cy="63.0" r="1.5"/><circle cx="75.0" cy="63.0" r="1.5"/><circle cx="81.0" cy="63.0" r="1.5"/><circle cx="87.0" cy="63.0" r="1.5"/><circle cx="93.0" cy="63.0" r="1.5"/><circle cx="99.0" cy="63.0" r="1.5"/><circle cx="105.0" cy="63.0" r="1.5"/><circle cx="111.0" cy="63.0" r="1.5"/><circle cx="117.0" cy="63.0" r="1.5"/><circle cx="123.0" cy="63.0" r="1.5"/><circle cx="129.0" cy="63.0" r="1.5"/><circle cx="135.0" cy="63.0" r="1.5"/><circle cx="141.0" cy="63.0" r="1.5"/><circle cx="147.0" cy="63.0" r="1.5"/><circle cx="153.0" cy="63.0" r="1.5"/><circle cx="159.0" cy="63.0" r="1.5"/><circle cx="165.0" cy="63.0" r="1.5"/><circle cx="171.0" cy="63.0" r="1.5"/><circle cx="177.0" cy="63.0" r="1.5"/><circle cx="183.0" cy="63.0" r="1.5"/><circle cx="189.0" cy="63.0" r="1.5"/><circle cx="195.0" cy="63.0" r="1.5"/><circle cx="201.0" cy="63.0" r="1.5"/><circle cx="207.0" cy="63.0" r="1.5"/><circle cx="213.0" cy="63.0" r="1.5"/><circle cx="219.0" cy="63.0" r="1.5"/><circle cx="225.0" cy="63.0" r="1.5"/><circle cx="231.0" cy="63.0" r="1.5"/><circle cx="237.0" cy="63.0" r="1.5"/><circle cx="243.0" cy="63.0" r="1.5"/><circle cx="249.0" cy="63.0" r="1.5"/><circle cx="255.0" cy="63.0" r="1.5"/><circle cx="261.0" cy="63.0" r="1.5"/><circle cx="267.0" cy="63.0" r="1.5"/><circle cx="273.0" cy="63.0" r="1.5"/><circle cx="279.0" cy="63.0" r="1.5"/><circle cx="285.0" cy="63.0" r="1.5"/><circle cx="291.0" cy="63.0" r="1.5"/><circle cx="297.0" cy="63.0" r="1.5"/><circle cx="24.0" cy="69.0" r="1.5"/><circle cx="30.0" cy="69.0" r="1.5"/><circle cx="36.0" cy="69.0" r="1.5"/><circle cx="42.0" cy="69.0" r="1.5"/><circle cx="48.0" cy="69.0" r="1.5"/><circle cx="54.0" cy="69.0" r="1.5"/><circle cx="60.0" cy="69.0" r="1.5"/><circle cx="66.0" cy="69.0" r="1.5"/><circle cx="72.0" cy="69.0" r="1.5"/><circle cx="78.0" cy="69.0" r="1.5"/><circle cx="84.0" cy="69.0" r="1.5"/><circle cx="90.0" cy="69.0" r="1.5"/><circle cx="96.0" cy="69.0" r="1.5"/><circle cx="102.0" cy="69.0" r="1.5"/><circle cx="108.0" cy="69.0" r="1.5"/><circle cx="114.0" cy="69.0" r="1.5"/><circle cx="120.0" cy="69.0" r="1.5"/><circle cx="126.0" cy="69.0" r="1.5"/><circle cx="132.0" cy="69.0" r="1.5"/><circle cx="138.0" cy="69.0" r="1.5"/><circle cx="144.0" cy="69.0" r="1.5"/><circle cx="150.0" cy="69.0" r="1.5"/><circle cx="156.0" cy="69.0" r="1.5"/><circle cx="162.0" cy="69.0" r="1.5"/><circle cx="168.0" cy="69.0" r="1.5"/><circle cx="174.0" cy="69.0" r="1.5"/><circle cx="180.0" cy="69.0" r="1.5"/><circle cx="186.0" cy="69.0" r="1.5"/><circle cx="192.0" cy="69.0" r="1.5"/><circle cx="198.0" cy="69.0" r="1.5"/><circle cx="204.0" cy="69.0" r="1.5"/><circle cx="210.0" cy="69.0" r="1.5"/><circle cx="216.0" cy="69.0" r="1.5"/><circle cx="222.0" cy="69.0" r="1.5"/><circle cx="228.0" cy="69.0" r="1.5"/><circle cx="234.0" cy="69.0" r="1.5"/><circle cx="240.0" cy="69.0" r="1.5"/><circle cx="246.0" cy="69.0" r="1.5"/><circle cx="252.0" cy="69.0" r="1.5"/><circle cx="258.0" cy="69.0" r="1.5"/><circle cx="264.0" cy="69.0" r="1.5"/><circle cx="270.0" cy="69.0" r="1.5"/><circle cx="276.0" cy="69.0" r="1.5"/><circle cx="282.0" cy="69.0" r="1.5"/><circle cx="288.0" cy="69.0" r="1.5"/><circle cx="294.0" cy="69.0" r="1.5"/><circle cx="21.0" cy="75.0" r="1.5"/><circle cx="27.0" cy="75.0" r="1.5"/><circle cx="33.0" cy="75.0" r="1.5"/><circle cx="39.0" cy="75.0" r="1.5"/><circle cx="45.0" cy="75.0" r="1.5"/><circle cx="51.0" cy="75.0" r="1.5"/><circle cx="57.0" cy="75.0" r="1.5"/><circle cx="63.0" cy="75.0" r="1.5"/><circle cx="69.0" cy="75.0" r="1.5"/><circle cx="75.0" cy="75.0" r="1.5"/><circle cx="81.0" cy="75.0" r="1.5"/><circle cx="87.0" cy="75.0" r="1.5"/><circle cx="93.0" cy="75.0" r="1.5"/><circle cx="99.0" cy="75.0" r="1.5"/><circle cx="105.0" cy="75.0" r="1.5"/><circle cx="111.0" cy="75.0" r="1.5"/><circle cx="117.0" cy="75.0" r="1.5"/><circle cx="123.0" cy="75.0" r="1.5"/><circle cx="129.0" cy="75.0" r="1.5"/><circle cx="135.0" cy="75.0" r="1.5"/><circle cx="141.0" cy="75.0" r="1.5"/><circle cx="147.0" cy="75.0" r="1.5"/><circle cx="153.0" cy="75.0" r="1.5"/><circle cx="159.0" cy="75.0" r="1.5"/><circle cx="165.0" cy="75.0" r="1.5"/><circle cx="171.0" cy="75.0" r="1.5"/><circle cx="177.0" cy="75.0" r="1.5"/><circle cx="183.0" cy="75.0" r="1.5"/><circle cx="189.0" cy="75.0" r="1.5"/><circle cx="195.0" cy="75.0" r="1.5"/><circle cx="201.0" cy="75.0" r="1.5"/><circle cx="207.0" cy="75.0" r="1.5"/><circle cx="213.0" cy="75.0" r="1.5"/><circle cx="219.0" cy="75.0" r="1.5"/><circle cx="225.0" cy="75.0" r="1.5"/><circle cx="231.0" cy="75.0" r="1.5"/><circle cx="237.0" cy="75.0" r="1.5"/><circle cx="243.0" cy="75.0" r="1.5"/><circle cx="249.0" cy="75.0" r="1.5"/><circle cx="255.0" cy="75.0" r="1.5"/><circle cx="261.0" cy="75.0" r="1.5"/><circle cx="267.0" cy="75.0" r="1.5"/><circle cx="273.0" cy="75.0" r="1.5"/><circle cx="279.0" cy="75.0" r="1.5"/><circle cx="285.0" cy="75.0" r="1.5"/><circle cx="291.0" cy="75.0" r="1.5"/><circle cx="18.0" cy="81.0" r="1.5"/><circle cx="24.0" cy="81.0" r="1.5"/><circle cx="30.0" cy="81.0" r="1.5"/><circle cx="36.0" cy="81.0" r="1.5"/><circle cx="42.0" cy="81.0" r="1.5"/><circle cx="48.0" cy="81.0" r="1.5"/><circle cx="54.0" cy="81.0" r="1.5"/><circle cx="60.0" cy="81.0" r="1.5"/><circle cx="66.0" cy="81.0" r="1.5"/><circle cx="72.0" cy="81.0" r="1.5"/><circle cx="78.0" cy="81.0" r="1.5"/><circle cx="84.0" cy="81.0" r="1.5"/><circle cx="90.0" cy="81.0" r="1.5"/><circle cx="96.0" cy="81.0" r="1.5"/><circle cx="102.0" cy="81.0" r="1.5"/><circle cx="108.0" cy="81.0" r="1.5"/><circle cx="114.0" cy="81.0" r="1.5"/><circle cx="120.0" cy="81.0" r="1.5"/><circle cx="126.0" cy="81.0" r="1.5"/><circle cx="132.0" cy="81.0" r="1.5"/><circle cx="138.0" cy="81.0" r="1.5"/><circle cx="144.0" cy="81.0" r="1.5"/><circle cx="150.0" cy="81.0" r="1.5"/><circle cx="156.0" cy="81.0" r="1.5"/><circle cx="162.0" cy="81.0" r="1.5"/><circle cx="168.0" cy="81.0" r="1.5"/><circle cx="174.0" cy="81.0" r="1.5"/><circle cx="180.0" cy="81.0" r="1.5"/><circle cx="186.0" cy="81.0" r="1.5"/><circle cx="192.0" cy="81.0" r="1.5"/><circle cx="198.0" cy="81.0" r="1.5"/><circle cx="204.0" cy="81.0" r="1.5"/><circle cx="210.0" cy="81.0" r="1.5"/><circle cx="216.0" cy="81.0" r="1.5"/><circle cx="222.0" cy="81.0" r="1.5"/><circle cx="228.0" cy="81.0" r="1.5"/><circle cx="234.0" cy="81.0" r="1.5"/><circle cx="240.0" cy="81.0" r="1.5"/><circle cx="246.0" cy="81.0" r="1.5"/><circle cx="252.0" cy="81.0" r="1.5"/><circle cx="258.0" cy="81.0" r="1.5"/><circle cx="264.0" cy="81.0" r="1.5"/><circle cx="270.0" cy="81.0" r="1.5"/><circle cx="276.0" cy="81.0" r="1.5"/><circle cx="282.0" cy="81.0" r="1.5"/><circle cx="288.0" cy="81.0" r="1.5"/><circle cx="294.0" cy="81.0" r="1.5"/><circle cx="21.0" cy="87.0" r="1.5"/><circle cx="27.0" cy="87.0" r="1.5"/><circle cx="33.0" cy="87.0" r="1.5"/><circle cx="39.0" cy="87.0" r="1.5"/><circle cx="45.0" cy="87.0" r="1.5"/><circle cx="51.0" cy="87.0" r="1.5"/><circle cx="57.0" cy="87.0" r="1.5"/><circle cx="63.0" cy="87.0" r="1.5"/><circle cx="69.0" cy="87.0" r="1.5"/><circle cx="75.0" cy="87.0" r="1.5"/><circle cx="81.0" cy="87.0" r="1.5"/><circle cx="87.0" cy="87.0" r="1.5"/><circle cx="93.0" cy="87.0" r="1.5"/><circle cx="99.0" cy="87.0" r="1.5"/><circle cx="105.0" cy="87.0" r="1.5"/><circle cx="111.0" cy="87.0" r="1.5"/><circle cx="117.0" cy="87.0" r="1.5"/><circle cx="123.0" cy="87.0" r="1.5"/><circle cx="129.0" cy="87.0" r="1.5"/><circle cx="135.0" cy="87.0" r="1.5"/><circle cx="141.0" cy="87.0" r="1.5"/><circle cx="147.0" cy="87.0" r="1.5"/><circle cx="153.0" cy="87.0" r="1.5"/><circle cx="159.0" cy="87.0" r="1.5"/><circle cx="165.0" cy="87.0" r="1.5"/><circle cx="171.0" cy="87.0" r="1.5"/><circle cx="177.0" cy="87.0" r="1.5"/><circle cx="183.0" cy="87.0" r="1.5"/><circle cx="189.0" cy="87.0" r="1.5"/><circle cx="195.0" cy="87.0" r="1.5"/><circle cx="201.0" cy="87.0" r="1.5"/><circle cx="207.0" cy="87.0" r="1.5"/><circle cx="213.0" cy="87.0" r="1.5"/><circle cx="219.0" cy="87.0" r="1.5"/><circle cx="225.0" cy="87.0" r="1.5"/><circle cx="231.0" cy="87.0" r="1.5"/><circle cx="237.0" cy="87.0" r="1.5"/><circle cx="243.0" cy="87.0" r="1.5"/><circle cx="249.0" cy="87.0" r="1.5"/><circle cx="255.0" cy="87.0" r="1.5"/><circle cx="261.0" cy="87.0" r="1.5"/><circle cx="267.0" cy="87.0" r="1.5"/><circle cx="273.0" cy="87.0" r="1.5"/><circle cx="279.0" cy="87.0" r="1.5"/><circle cx="285.0" cy="87.0" r="1.5"/><circle cx="291.0" cy="87.0" r="1.5"/><circle cx="297.0" cy="87.0" r="1.5"/><circle cx="30.0" cy="93.0" r="1.5"/><circle cx="36.0" cy="93.0" r="1.5"/><circle cx="42.0" cy="93.0" r="1.5"/><circle cx="48.0" cy="93.0" r="1.5"/><circle cx="54.0" cy="93.0" r="1.5"/><circle cx="60.0" cy="93.0" r="1.5"/><circle cx="66.0" cy="93.0" r="1.5"/><circle cx="72.0" cy="93.0" r="1.5"/><circle cx="78.0" cy="93.0" r="1.5"/><circle cx="84.0" cy="93.0" r="1.5"/><circle cx="90.0" cy="93.0" r="1.5"/><circle cx="96.0" cy="93.0" r="1.5"/><circle cx="102.0" cy="93.0" r="1.5"/><circle cx="108.0" cy="93.0" r="1.5"/><circle cx="114.0" cy="93.0" r="1.5"/><circle cx="120.0" cy="93.0" r="1.5"/><circle cx="126.0" cy="93.0" r="1.5"/><circle cx="132.0" cy="93.0" r="1.5"/><circle cx="138.0" cy="93.0" r="1.5"/><circle cx="144.0" cy="93.0" r="1.5"/><circle cx="150.0" cy="93.0" r="1.5"/><circle cx="156.0" cy="93.0" r="1.5"/><circle cx="162.0" cy="93.0" r="1.5"/><circle cx="168.0" cy="93.0" r="1.5"/><circle cx="174.0" cy="93.0" r="1.5"/><circle cx="180.0" cy="93.0" r="1.5"/><circle cx="186.0" cy="93.0" r="1.5"/><circle cx="192.0" cy="93.0" r="1.5"/><circle cx="198.0" cy="93.0" r="1.5"/><circle cx="204.0" cy="93.0" r="1.5"/><circle cx="210.0" cy="93.0" r="1.5"/><circle cx="216.0" cy="93.0" r="1.5"/><circle cx="222.0" cy="93.0" r="1.5"/><circle cx="228.0" cy="93.0" r="1.5"/><circle cx="234.0" cy="93.0" r="1.5"/><circle cx="240.0" cy="93.0" r="1.5"/><circle cx="246.0" cy="93.0" r="1.5"/><circle cx="252.0" cy="93.0" r="1.5"/><circle cx="258.0" cy="93.0" r="1.5"/><circle cx="264.0" cy="93.0" r="1.5"/><circle cx="270.0" cy="93.0" r="1.5"/><circle cx="276.0" cy="93.0" r="1.5"/><circle cx="282.0" cy="93.0" r="1.5"/><circle cx="288.0" cy="93.0" r="1.5"/><circle cx="294.0" cy="93.0" r="1.5"/><circle cx="300.0" cy="93.0" r="1.5"/><circle cx="27.0" cy="99.0" r="1.5"/><circle cx="33.0" cy="99.0" r="1.5"/><circle cx="39.0" cy="99.0" r="1.5"/><circle cx="45.0" cy="99.0" r="1.5"/><circle cx="51.0" cy="99.0" r="1.5"/><circle cx="57.0" cy="99.0" r="1.5"/><circle cx="63.0" cy="99.0" r="1.5"/><circle cx="69.0" cy="99.0" r="1.5"/><circle cx="75.0" cy="99.0" r="1.5"/><circle cx="81.0" cy="99.0" r="1.5"/><circle cx="87.0" cy="99.0" r="1.5"/><circle cx="93.0" cy="99.0" r="1.5"/><circle cx="99.0" cy="99.0" r="1.5"/><circle cx="105.0" cy="99.0" r="1.5"/><circle cx="111.0" cy="99.0" r="1.5"/><circle cx="117.0" cy="99.0" r="1.5"/><circle cx="123.0" cy="99.0" r="1.5"/><circle cx="129.0" cy="99.0" r="1.5"/><circle cx="135.0" cy="99.0" r="1.5"/><circle cx="141.0" cy="99.0" r="1.5"/><circle cx="147.0" cy="99.0" r="1.5"/><circle cx="153.0" cy="99.0" r="1.5"/><circle cx="159.0" cy="99.0" r="1.5"/><circle cx="165.0" cy="99.0" r="1.5"/><circle cx="171.0" cy="99.0" r="1.5"/><circle cx="177.0" cy="99.0" r="1.5"/><circle cx="183.0" cy="99.0" r="1.5"/><circle cx="189.0" cy="99.0" r="1.5"/><circle cx="195.0" cy="99.0" r="1.5"/><circle cx="201.0" cy="99.0" r="1.5"/><circle cx="207.0" cy="99.0" r="1.5"/><circle cx="213.0" cy="99.0" r="1.5"/><circle cx="219.0" cy="99.0" r="1.5"/><circle cx="225.0" cy="99.0" r="1.5"/><circle cx="231.0" cy="99.0" r="1.5"/><circle cx="237.0" cy="99.0" r="1.5"/><circle cx="243.0" cy="99.0" r="1.5"/><circle cx="249.0" cy="99.0" r="1.5"/><circle cx="255.0" cy="99.0" r="1.5"/><circle cx="261.0" cy="99.0" r="1.5"/><circle cx="267.0" cy="99.0" r="1.5"/><circle cx="273.0" cy="99.0" r="1.5"/><circle cx="279.0" cy="99.0" r="1.5"/><circle cx="285.0" cy="99.0" r="1.5"/><circle cx="291.0" cy="99.0" r="1.5"/><circle cx="297.0" cy="99.0" r="1.5"/><circle cx="303.0" cy="99.0" r="1.5"/><circle cx="30.0" cy="105.0" r="1.5"/><circle cx="36.0" cy="105.0" r="1.5"/><circle cx="42.0" cy="105.0" r="1.5"/><circle cx="48.0" cy="105.0" r="1.5"/><circle cx="54.0" cy="105.0" r="1.5"/><circle cx="60.0" cy="105.0" r="1.5"/><circle cx="66.0" cy="105.0" r="1.5"/><circle cx="72.0" cy="105.0" r="1.5"/><circle cx="78.0" cy="105.0" r="1.5"/><circle cx="84.0" cy="105.0" r="1.5"/><circle cx="90.0" cy="105.0" r="1.5"/><circle cx="96.0" cy="105.0" r="1.5"/><circle cx="102.0" cy="105.0" r="1.5"/><circle cx="108.0" cy="105.0" r="1.5"/><circle cx="114.0" cy="105.0" r="1.5"/><circle cx="120.0" cy="105.0" r="1.5"/><circle cx="126.0" cy="105.0" r="1.5"/><circle cx="132.0" cy="105.0" r="1.5"/><circle cx="138.0" cy="105.0" r="1.5"/><circle cx="144.0" cy="105.0" r="1.5"/><circle cx="150.0" cy="105.0" r="1.5"/><circle cx="156.0" cy="105.0" r="1.5"/><circle cx="162.0" cy="105.0" r="1.5"/><circle cx="168.0" cy="105.0" r="1.5"/><circle cx="174.0" cy="105.0" r="1.5"/><circle cx="180.0" cy="105.0" r="1.5"/><circle cx="186.0" cy="105.0" r="1.5"/><circle cx="192.0" cy="105.0" r="1.5"/><circle cx="198.0" cy="105.0" r="1.5"/><circle cx="204.0" cy="105.0" r="1.5"/><circle cx="210.0" cy="105.0" r="1.5"/><circle cx="216.0" cy="105.0" r="1.5"/><circle cx="222.0" cy="105.0" r="1.5"/><circle cx="228.0" cy="105.0" r="1.5"/><circle cx="234.0" cy="105.0" r="1.5"/><circle cx="240.0" cy="105.0" r="1.5"/><circle cx="246.0" cy="105.0" r="1.5"/><circle cx="252.0" cy="105.0" r="1.5"/><circle cx="258.0" cy="105.0" r="1.5"/><circle cx="264.0" cy="105.0" r="1.5"/><circle cx="270.0" cy="105.0" r="1.5"/><circle cx="276.0" cy="105.0" r="1.5"/><circle cx="45.0" cy="111.0" r="1.5"/><circle cx="51.0" cy="111.0" r="1.5"/><circle cx="57.0" cy="111.0" r="1.5"/><circle cx="63.0" cy="111.0" r="1.5"/><circle cx="69.0" cy="111.0" r="1.5"/><circle cx="75.0" cy="111.0" r="1.5"/><circle cx="81.0" cy="111.0" r="1.5"/><circle cx="87.0" cy="111.0" r="1.5"/><circle cx="93.0" cy="111.0" r="1.5"/><circle cx="99.0" cy="111.0" r="1.5"/><circle cx="105.0" cy="111.0" r="1.5"/><circle cx="111.0" cy="111.0" r="1.5"/><circle cx="117.0" cy="111.0" r="1.5"/><circle cx="123.0" cy="111.0" r="1.5"/><circle cx="129.0" cy="111.0" r="1.5"/><circle cx="135.0" cy="111.0" r="1.5"/><circle cx="141.0" cy="111.0" r="1.5"/><circle cx="147.0" cy="111.0" r="1.5"/><circle cx="153.0" cy="111.0" r="1.5"/><circle cx="159.0" cy="111.0" r="1.5"/><circle cx="165.0" cy="111.0" r="1.5"/><circle cx="171.0" cy="111.0" r="1.5"/><circle cx="177.0" cy="111.0" r="1.5"/><circle cx="183.0" cy="111.0" r="1.5"/><circle cx="189.0" cy="111.0" r="1.5"/><circle cx="195.0" cy="111.0" r="1.5"/><circle cx="201.0" cy="111.0" r="1.5"/><circle cx="207.0" cy="111.0" r="1.5"/><circle cx="213.0" cy="111.0" r="1.5"/><circle cx="219.0" cy="111.0" r="1.5"/><circle cx="225.0" cy="111.0" r="1.5"/><circle cx="231.0" cy="111.0" r="1.5"/><circle cx="54.0" cy="117.0" r="1.5"/><circle cx="60.0" cy="117.0" r="1.5"/><circle cx="66.0" cy="117.0" r="1.5"/><circle cx="72.0" cy="117.0" r="1.5"/><circle cx="78.0" cy="117.0" r="1.5"/><circle cx="96.0" cy="117.0" r="1.5"/><circle cx="102.0" cy="117.0" r="1.5"/><circle cx="108.0" cy="117.0" r="1.5"/><circle cx="114.0" cy="117.0" r="1.5"/><circle cx="120.0" cy="117.0" r="1.5"/><circle cx="126.0" cy="117.0" r="1.5"/><circle cx="132.0" cy="117.0" r="1.5"/><circle cx="168.0" cy="117.0" r="1.5"/><circle cx="174.0" cy="117.0" r="1.5"/><circle cx="180.0" cy="117.0" r="1.5"/><circle cx="63.0" cy="123.0" r="1.5"/><circle cx="69.0" cy="123.0" r="1.5"/><circle cx="75.0" cy="123.0" r="1.5"/><circle cx="111.0" cy="123.0" r="1.5"/><circle cx="117.0" cy="123.0" r="1.5"/><circle cx="123.0" cy="123.0" r="1.5"/><circle cx="129.0" cy="123.0" r="1.5"/><circle cx="171.0" cy="123.0" r="1.5"/><circle cx="168.0" cy="129.0" r="1.5"/></g><g><path class="bento-map-arc" style="--i:0" d="M26.6 90.8Q40.3 -3.5 54.1 27.8" pathLength="1"/><path class="bento-map-arc" style="--i:1" d="M26.6 90.8Q71.3 10.7 116.0 49.4" pathLength="1"/><path class="bento-map-arc" style="--i:2" d="M26.6 90.8Q25.6 51.4 24.6 79.6" pathLength="1"/><path class="bento-map-arc" style="--i:3" d="M26.6 90.8Q54.2 56.2 81.8 110.0" pathLength="1"/><path class="bento-map-arc" style="--i:4" d="M26.6 90.8Q126.2 -23.9 225.9 28.0" pathLength="1"/><path class="bento-map-arc" style="--i:5" d="M26.6 90.8Q130.2 36.9 233.9 89.8" pathLength="1"/></g><g><circle class="bento-map-city" style="--i:0" cx="54.1" cy="27.8" r="3.2"/><circle class="bento-map-city" style="--i:1" cx="116.0" cy="49.4" r="3.2"/><circle class="bento-map-city" style="--i:2" cx="24.6" cy="79.6" r="3.2"/><circle class="bento-map-city" style="--i:3" cx="81.8" cy="110.0" r="3.2"/><circle class="bento-map-city" style="--i:4" cx="225.9" cy="28.0" r="3.2"/><circle class="bento-map-city" style="--i:5" cx="233.9" cy="89.8" r="3.2"/></g><circle class="bento-map-home-ring" cx="26.6" cy="90.8" r="5"/><circle class="bento-map-home" cx="26.6" cy="90.8" r="4.2"/><text class="bento-map-label" x="20.6" y="106.8">Kuşadası</text></svg></div>
        <div class="home-bento-copy-v3196"><h3>Yakında üret, Türkiye'ye gönder.</h3><p>Kuşadası'nda üretim ve elden teslim. Uygun siparişlerde Türkiye geneli kargo.</p><a class="text-cta local-seo-link" href="kusadasi-3d-baski/">Kuşadası 3D baskı hizmetini incele ↗</a></div>
        
      </article>
    </div>
    <a class="home-architecture-branch home-architecture-branch-v3196 arch-band-v3353 home-motion" data-home-motion href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span class="arch-band-copy"><small>BG Studio'nun diğer iş kolu</small><strong>Architecture</strong></span><span class="arch-link-domain">bgstudio.com.tr</span><span class="arch-link-arrow"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 17 17 7M9 7h8v8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span></a>
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
            hero_srcset = _responsive_srcset_for_product(hero_first, '')
            hero_sizes = '(max-width: 760px) 70vw, (max-width: 1100px) 72vw, 42vw'
            srcset_bits = f' imagesrcset="{esc(hero_srcset)}" imagesizes="{esc(hero_sizes)}"' if hero_srcset else ''
            preload = f'<!-- BGSTUDIO:HOME_HERO_PRELOAD --><link rel="preload" as="image" href="{esc(hero_src)}"{srcset_bits} fetchpriority="high"/>'
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
    responsive_srcset = _responsive_srcset_for_product(p, prefix)
    card_sizes = '(max-width: 760px) calc(100vw - 24px), (max-width: 1100px) 50vw, 33vw'
    responsive_attrs = f' srcset="{esc(responsive_srcset)}" sizes="{card_sizes}"' if responsive_srcset else ''

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
            f'<a class="product-image" href="{href}">{badge_markup}<img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{img}" width="{w}"{responsive_attrs}/></a>\n'
            f'<div class="product-card-body"><span class="catalog-card-category">{label}</span>'
            f'<h3><a href="{href}">{name}</a></h3>'
            f'<div class="catalog-card-footer"><span class="catalog-card-price">{price_markup}</span>'
            f'<a class="product-link" href="{href}" aria-label="{name} ürününü incele">İncele ↗</a></div>'
            f'</div>\n</article>'
        )

    return (
        f'<article class="product-card" data-category="{esc(p.get("category"))}" data-search="{esc(search)}">\n'
        f'<a class="product-image" href="{href}"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{img}" width="{w}"{responsive_attrs}/></a>\n'
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

def schema_price_value(p):
    """Return a trustworthy numeric price for Google Product markup.

    V3.1.77 keeps the authoritative numeric price fields first, but also
    accepts legacy catalog records whose visible ``price_text`` is a plain
    numeric TL amount (for example ``249 TL``). Quote-only labels such as
    ``Ölçüye göre fiyatlandırma`` intentionally return ``None`` so we never
    invent a price just to satisfy rich-result validation.
    """
    direct = active_price_value(p)
    if direct not in (None, ''):
        return direct
    return canonical_price_value(p.get('price_text'))


def product_schema_images_v3320(p):
    """Return the product's real public images without inventing media."""
    values = []
    for raw in [p.get('main_image'), p.get('poster_image')]:
        if raw:
            values.append(str(raw))
    for item in (p.get('gallery_images') or []):
        if isinstance(item, str) and item:
            values.append(item)
        elif isinstance(item, dict) and item.get('path'):
            values.append(str(item.get('path')))
    out = []
    seen = set()
    for rel in values:
        rel = str(rel or '').strip().lstrip('/')
        if not rel or rel in seen:
            continue
        seen.add(rel)
        out.append(f'{BASE_URL}/{rel}')
    return out


def product_schema_properties_v3320(p):
    rows = []
    materials = [label for _key, label in catalog_materials(p)]
    if materials:
        rows.append({'@type':'PropertyValue','name':'Malzeme','value':', '.join(materials)})
    for label, key in (
        ('Ölçüler','dimensions'),
        ('Ağırlık','weight'),
        ('Baskı yöntemi','print_method'),
    ):
        value = str(p.get(key) or '').strip()
        if value:
            rows.append({'@type':'PropertyValue','name':label,'value':value})
    return rows


def product_service_links_v3320(p):
    """Contextual links between product intent and service/local landing pages."""
    personalizable = catalog_personalizable(p)
    primary_href = '../../ozel-uretim/' if personalizable else '../../prototip-parca/'
    primary_label = 'Kişiye özel üretim' if personalizable else 'Prototip & Parça'
    primary_copy = (
        'Bu ürünü farklı isim, renk veya uygun bir kişiselleştirmeyle düşünüyorsan özel üretim sürecini inceleyebilirsin.'
        if personalizable else
        'Elinde benzer bir ürün, ölçü veya parça ihtiyacı varsa teknik üretim sürecini inceleyebilirsin.'
    )
    return (
        '<div class="detail-section product-discovery-links">'
        '<h2>Benzer bir üretim mi arıyorsun?</h2>'
        f'<p>{esc(primary_copy)}</p>'
        '<div class="product-action-row">'
        f'<a class="secondary-cta" href="{primary_href}">{esc(primary_label)}</a>'
        '<a class="secondary-cta" href="../../kusadasi-3d-baski/">Kuşadası 3D Baskı</a>'
        '</div></div>'
    )


def render_schema(p):
    canonical = f"{BASE_URL}/urunler/{p['slug']}/"
    images = product_schema_images_v3320(p)
    image = images[0] if images else f"{BASE_URL}/{p['main_image']}"
    tiers = effective_pricing_tiers(p)
    option_prices = order_option_prices(p)
    fallback_price = schema_price_value(p)

    # Google Product snippets require at least one of offers, review or
    # aggregateRating. We do not fabricate ratings/reviews. Products whose
    # price is genuinely quote/measurement based therefore use ItemPage
    # markup instead of emitting an invalid Product rich-result item.
    if not tiers and not option_prices and fallback_price in (None, ''):
        obj = {
            '@context': 'https://schema.org',
            '@type': 'ItemPage',
            '@id': canonical + '#itempage',
            'name': p['name'],
            'description': p.get('description', ''),
            'url': canonical,
            'primaryImageOfPage': {
                '@type': 'ImageObject',
                'url': image,
            },
            'image': images or [image],
            'about': {
                '@type': 'Thing',
                'name': p['name'],
            },
            'isPartOf': {'@id': BASE_URL + '/#website'},
        }
        if p.get('tags'):
            obj['keywords'] = ', '.join(str(x) for x in p.get('tags') or [])
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

    obj = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        '@id': canonical + '#product',
        'name': p['name'],
        'description': p.get('description', ''),
        'brand': {'@type': 'Brand', 'name': 'BG Studio 3D', 'url': BASE_URL},
        'url': canonical,
        'image': images or [image],
        'category': category_label(p),
        'sku': str(p.get('slug') or ''),
    }
    if p.get('tags'):
        obj['keywords'] = ', '.join(str(x) for x in p.get('tags') or [])
    additional = product_schema_properties_v3320(p)
    if additional:
        obj['additionalProperty'] = additional

    if tiers:
        offers = []
        for t in tiers:
            price_value = canonical_price_value(t.get('price_value'))
            if price_value in (None, ''):
                continue
            offers.append({
                '@type': 'Offer',
                'name': str(t.get('label') or f"{t.get('quantity', 1)} adet"),
                'priceCurrency': 'TRY',
                'price': str(price_value),
                'availability': product_schema_availability(p),
                'itemCondition': 'https://schema.org/NewCondition',
                'url': canonical,
                'seller': {'@id': BASE_URL + '/#organization'},
                'eligibleQuantity': {'@type': 'QuantitativeValue', 'value': int(t.get('quantity') or 1), 'unitText': 'adet'},
            })
        if offers:
            obj['offers'] = offers
    elif option_prices:
        obj['offers'] = [
            {
                '@type': 'Offer', 'name': option, 'priceCurrency': 'TRY', 'price': price,
                'availability': product_schema_availability(p), 'url': canonical,
                'itemCondition': 'https://schema.org/NewCondition',
                'seller': {'@id': BASE_URL + '/#organization'},
            }
            for option, price in option_prices.items()
        ]
    elif fallback_price not in (None, ''):
        obj['offers'] = {
            '@type': 'Offer',
            'priceCurrency': 'TRY',
            'price': str(fallback_price),
            'availability': product_schema_availability(p),
            'itemCondition': 'https://schema.org/NewCondition',
            'url': canonical,
            'seller': {'@id': BASE_URL + '/#organization'},
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
    stored_title = str(p.get('seo_title') or '').strip()
    legacy_auto_title = f"{str(p.get('name') or '').strip()} | Kuşadası 3D Baskı | BG Studio 3D"
    serp_known_overrides = {
        '3-lu-dis-fircasi-dis-macunu-standi': ('Diş Fırçası & Diş Macunu Standı | Kuşadası 3D Baskı | BG Studio 3D', 'Diş Fırçası & Macun Standı | BG Studio 3D'),
        'batman-katmanli-yuz-dekor': ('Batman Katmanlı Duvar Dekoru | Kuşadası 3D Baskı | BG Studio 3D', 'Batman Katmanlı Duvar Dekoru | BG Studio 3D'),
        'doldurulabilir-ice-roller-buzlu-yuz-masaj-aparati': ('Doldurulabilir Ice Roller | Buzlu Yüz Masaj Aparatı | BG Studio 3D', 'Doldurulabilir Ice Roller | BG Studio 3D'),
        'heykel-bust-masa-lambasi': ('3D Baskı Heykeli Masa Lambası | Kuşadası 3D Baskı | BG Studio 3D', 'Heykel Büst Masa Lambası | BG Studio 3D'),
    }
    known_old, known_new = serp_known_overrides.get(str(p.get('slug') or ''), ('', ''))
    if stored_title and known_old and stored_title == known_old:
        effective_title = known_new
    elif not stored_title or stored_title == legacy_auto_title:
        effective_title = default_title
    else:
        effective_title = stored_title
    title = esc(effective_title)
    seo_desc = esc(clip_seo_text(p.get('seo_description') or default_description, 160))
    canonical = f"{BASE_URL}/urunler/{esc(p['slug'])}/"
    main_rel = '../../' + p['main_image']
    main_abs = f"{BASE_URL}/{p['main_image']}"
    w = int(p.get('main_image_width') or 1000)
    h = int(p.get('main_image_height') or 760)
    og_path, og_w, og_h = product_og_media(p)
    og_abs = f"{BASE_URL}/{og_path}" if og_path else main_abs

    # v3.3.39 — ürün görselleri tek tip: en fazla 5 görsel, hepsi 1000×760. Tek görselde küçük resim
    # şeridi gösterilmez; 2–5 görselde eşit boy küçük resimlerle geçiş yapılır. Eski afiş kaydı varsa
    # sıradan bir ürün görseli gibi listeye katılır.
    slide_items = [(esc(main_rel), w, h, name)]
    legacy_media = []
    if p.get('poster_image'):
        legacy_media.append({'path': p['poster_image'], 'width': p.get('poster_image_width') or 1254, 'height': p.get('poster_image_height') or 1254})
    legacy_media += list(p.get('gallery_images') or [])
    for item in legacy_media:
        if isinstance(item, str):
            item = {'path': item, 'width': 1000, 'height': 760}
        path = item.get('path') if isinstance(item, dict) else None
        if not path:
            continue
        n = len(slide_items) + 1
        galt = esc(item.get('alt') or f"{p['name']} ürün görseli {n}")
        slide_items.append((esc('../../' + path), int(item.get('width') or 1000), int(item.get('height') or 760), galt))
    gallery_thumbs_html = ''
    # V3.3.58: ürünün gerçek baskı modeli varsa "3D'de döndür" butonu.
    model3d_html = ''
    if (ROOT / 'assets' / 'models' / f"{p.get('slug')}.glb").is_file():
        model3d_html = (f'<button type="button" class="model3d-btn" data-model3d="../../assets/models/{esc(p.get("slug"))}.glb?v={SITE_ASSET_VERSION}" data-model3d-name="{esc(p.get("name") or "")}">'
                        '<span class="model3d-btn-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/></svg></span>'
                        '<span><strong>3D’de döndür</strong><small>Gerçek baskı modelini incele</small></span></button>'
                        f'<script defer src="../../assets/js/product-3d.js?v={SITE_ASSET_VERSION}"></script>')
    if len(slide_items) > 1:
        gallery_thumbs_html = '<div aria-label="Ürün görselleri" class="gallery-thumbs gallery-thumbs-slots">' + ''.join(
            f'<button aria-label="{i}. ürün görselini göster" aria-pressed="{"true" if i == 1 else "false"}" '
            f'class="gallery-thumb{" active" if i == 1 else ""}" data-gallery-alt="{galt}" data-gallery-src="{src}" type="button">'
            f'<img alt="" decoding="async" height="{gh}" loading="lazy" src="{src}" width="{gw}"/></button>'
            for i, (src, gw, gh, galt) in enumerate(slide_items, 1)
        ) + '</div>'

    color_entries = product_color_entries(p)
    legacy_options = legacy_order_options(p)
    option_prices = order_option_prices(p)
    options_html = ''.join(
        f'<option value="{esc(o)}" data-option-price="{esc(option_prices.get(o, ""))}">{esc(o)}</option>'
        if o in option_prices else f'<option value="{esc(o)}">{esc(o)}</option>'
        for o in legacy_options
    )
    option_field_html = ''
    option_chips_html = ''
    if legacy_options:
        # V3.3.29: options render as visible choice cards; the hidden select stays
        # the single source of truth the order configurator reads.
        option_field_html = f'<select aria-hidden="true" data-order-option="" hidden tabindex="-1">{options_html}</select>'
        option_buttons = ''.join(
            f'<button aria-pressed="{"true" if i == 0 else "false"}" class="order-option-choice{" selected" if i == 0 else ""}" data-option-value="{esc(o)}" type="button">{esc(o)}</button>'
            for i, o in enumerate(legacy_options)
        )
        option_chips_html = (
            '<div class="order-color-section order-option-section"><div class="order-color-head"><span>Seçenek</span></div>'
            f'<div aria-label="Ürün seçeneği" class="order-option-chips" data-order-option-chips="" role="group">{option_buttons}</div></div>'
        )

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
<meta charset="utf-8"/><meta content="width=device-width, initial-scale=1" name="viewport"/><meta content="#ffffff" name="theme-color"/>
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
<main id="main-content"><section class="product-detail shell"><div class="breadcrumb"><a href="../../">Ana Sayfa</a><span>/</span><a href="../">Ürünler</a><span>/</span><span>{name}</span></div><div class="product-detail-grid"><div class="product-gallery"><div aria-label="Seçili ürün görselini büyüt" class="gallery-stage zoomable-media" data-gallery-stage="" role="button" tabindex="0"><img alt="{name}" data-gallery-main="" decoding="async" fetchpriority="high" height="{h}" src="{esc(main_rel)}" width="{w}"/></div>{gallery_thumbs_html}<p class="gallery-hint">Görseli büyütmek için ana görsele tıkla.</p>{model3d_html}</div>
<div class="product-info"><p class="eyebrow">{label.upper()}</p><h1>{name}</h1><p class="product-lead">{desc}</p>{status_badge_html}<div class="price-block{' has-discount' if sale_info else ''}"><small>Fiyat</small><div class="price-display-row">{price_list_html}<strong data-product-price-display="">{selected_display_price}</strong>{discount_badge_html}</div></div>{tier_cards_html}<div class="order-configurator" data-order-config="" data-product-name="{name}" data-product-price="{price}" data-product-base-price-value="{esc(active_base_value or '')}"><div class="order-config-head"><strong>Siparişini hazırla</strong><span>Seçimini yap, mesajı hazır gönder.</span></div>{option_chips_html}<div class="order-controls{' has-tier' if pricing_tiers else ''}{' color-mode' if color_public else ''}{' option-mode' if legacy_options else ''}">{option_field_html}{tier_field_html}<div class="order-field order-qty-field"><span>{'Set adedi' if pricing_tiers else 'Adet'}</span><div class="qty-stepper"><button aria-label="Adedi azalt" data-qty-minus="" type="button">−</button><input aria-label="Adet" data-order-qty="" max="12" min="1" type="number" value="1"/><button aria-label="Adedi artır" data-qty-plus="" type="button">+</button></div></div></div>{color_picker_html}{color_data_html}<label class="order-field order-note-field"><span>Not (isteğe bağlı)</span><input data-order-note="" maxlength="160" placeholder="Örn. hediye olacak, teslim notu…" type="text"/></label><div class="order-summary"><span>Seçim:</span><strong data-order-summary="">{esc(initial_summary)}</strong></div><a class="primary-cta wide-cta smart-order-whatsapp" data-order-whatsapp="" href="#" rel="noopener" target="_blank">Seçimi WhatsApp’tan gönder ↗</a><p class="order-local-note">Seçimin site üzerinde kaydedilmez; yalnızca WhatsApp mesajını hazırlamak için kullanılır.</p></div><div class="product-action-row share-only-row"><button class="secondary-cta share-product" data-share-title="{name}" type="button">Ürün linkini paylaş</button></div><div class="detail-note">📍 Kuşadası elden teslim   •   📦 Türkiye geneli kargo</div><div class="product-facts"><div><small>Üretim</small><strong>3D baskı</strong></div><div><small>Teslim</small><strong>Kuşadası / kargo</strong></div><div><small>Seçenek</small><strong>Ürüne göre</strong></div><div><small>Sipariş</small><strong>WhatsApp</strong></div></div>{technical_html}<div class="detail-section"><h2>Öne çıkan özellikler</h2><ul>{feats}</ul></div><div class="detail-section"><h2>{detail_options_heading}</h2><div class="option-tags">{tags or '<span>WhatsApp üzerinden netleştirilir.</span>'}</div></div>{product_tag_section}{product_service_links_v3320(p)}<div class="detail-section"><h2>Üretim notu</h2><p>{production}</p></div></div></div><div class="assurance-strip"><div><strong>Kuşadası</strong><span>Elden teslim</span></div><div><strong>Türkiye</strong><span>Kargo seçeneği</span></div><div><strong>Atölye</strong><span>3D baskı üretim</span></div><div><strong>Sipariş</strong><span>WhatsApp üzerinden</span></div></div></section>
<section class="order-process shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ SÜRECİ</p><h2>Nasıl ilerliyoruz?</h2></div></div><div class="order-steps"><article class="order-step"><span>01</span><h3>Ürünü seç</h3><p>Renk, adet ve varsa kişiselleştirme isteğini bize ilet.</p></article><article class="order-step"><span>02</span><h3>Detayları netleştir</h3><p>Üretim seçeneği ve teslim/kargo detaylarını sipariş öncesi netleştir.</p></article><article class="order-step"><span>03</span><h3>Üretim</h3><p>Ürün atölyede 3D baskı ile hazırlanır ve kontrol edilir.</p></article><article class="order-step"><span>04</span><h3>Teslim</h3><p>Kuşadası elden teslim veya uygun kargo seçeneğiyle gönderim.</p></article></div></section>
<section class="product-faq shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ ÖNCESİ</p><h2>Bilmen gerekenler.</h2></div></div><div class="faq">{faq_html}</div></section>
<section class="related-products shell"><div class="section-title"><div><p class="eyebrow">BUNLAR DA İLGİNİ ÇEKEBİLİR</p><h2>Atölyeden başka seçenekler.</h2></div></div><div class="related-grid">{related_html}</div></section><section class="detail-back shell"><a class="text-cta" href="../">← Tüm ürünlere dön</a></section></main>
<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı ve özel üretim.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a aria-label="BG Studio 3D Instagram" class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>bgstudio.3dtr</span></a><a aria-label="BG Studio 3D Facebook" class="footer-social icon-facebook" href="https://www.facebook.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>Facebook · BG Studio 3D</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../prototip-parca/">Prototip &amp; Parça Üretim</a><a href="../../kusadasi-3d-baski/">Kuşadası 3D Baskı</a><a href="../../iletisim/">İletişim</a><a href="../../gizlilik/">Gizlilik</a><a href="../../siparis-bilgilendirme/">Sipariş Bilgilendirme</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır. | 3D baskı, özel üretim ve kurumsal çözümler.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>
<script defer="" src="../../assets/js/consent.js"></script><script defer="" src="../../assets/js/main.js?v=3.1.4"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div><div class="mobile-product-cta"><div><strong>{name}</strong><span class="mobile-price-wrap">{price_list_html}<b data-mobile-price="">{selected_display_price}</b></span></div><a data-mobile-order-whatsapp="" href="#" rel="noopener" target="_blank">Siparişi hazırla</a></div></body></html>'''



# V3.3.04 · Floating Back-To-Top Polish
SITE_ASSET_VERSION = '3.3.76'

# Homepage Google reviews block (static, no Places API). Update the rating by
# hand if the Google Business score changes. The lrd fragment ",3" opens
# Google's write-review dialog for this listing.
GOOGLE_RATING_V3328 = '5,0'
GOOGLE_REVIEW_COUNT_V3350 = 11


def google_review_values_v3351():
    # V3.3.51: panelden (site_settings.website_copy) gelen Google puanı ve yorum sayısı.
    copy = load_site_settings().get('website_copy') or {}
    try:
        rating = float(str(copy.get('google_rating', 5.0)).replace(',', '.'))
    except (TypeError, ValueError):
        rating = 5.0
    rating = min(5.0, max(1.0, round(rating, 1)))
    try:
        count = max(0, int(copy.get('google_review_count', GOOGLE_REVIEW_COUNT_V3350)))
    except (TypeError, ValueError):
        count = GOOGLE_REVIEW_COUNT_V3350
    return {'label': f'{rating:.1f}'.replace('.', ','), 'count': count, 'pct': round(rating / 5 * 100, 1)}
GOOGLE_REVIEWS_URL_V3328 = 'https://maps.google.com/?cid=7240535998596070578'
GOOGLE_WRITE_REVIEW_URL_V3328 = 'https://www.google.com/search?q=BG+Studio+3D+Ku%C5%9Fadas%C4%B1#lrd=0x8ea54b705e76b9c9:0x647b8d20f3bf3cb2,3'
RELEASE_CHANNEL = 'stable'
RELEASE_CANDIDATE = 'V3.3.25-STABLE'


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
    if rel.startswith('kusadasi-3d-baski/'):
        return 'local-production'
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

    def rich_item(href, title, description, active='', external=False):
        attrs = ' rel="noopener" target="_blank"' if external else ''
        return (
            f'<a{active} href="{href}"{attrs}>'
            f'<span class="nav-rich-copy"><strong>{title}</strong><small>{description}</small></span>'
            f'<span class="nav-rich-arrow" aria-hidden="true">↗</span>'
            f'</a>'
        )

    return (
        '<header class="site-header" id="top" data-bg-nav="v3.2.03"><div class="shell nav-shell">'
        f'<a aria-label="BG Studio 3D ana sayfa" class="brand" href="{prefix}"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a>'
        '<button aria-controls="primary-navigation" aria-expanded="false" aria-label="Menüyü aç" class="menu-toggle" type="button"><span></span><span></span></button>'
        '<nav aria-label="Ana menü" class="main-nav" id="primary-navigation">'
        f'<a{direct_active("products")} href="{prefix}urunler/">Ürünler</a>'
        f'<div class="{group_class("custom-production", "prototype", "local-production")}">'
        '<button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-production">Üretim</button>'
        '<div class="nav-submenu nav-submenu-rich" id="nav-production">'
        '<div class="nav-rich-head"><span>ÜRETİM</span><small>Fikirden çalışan fiziksel ürüne.</small></div>'
        + rich_item(f'{prefix}ozel-uretim/','Özel Üretim','Fikir, görsel veya ölçüden kişiye özel ürün.',child_active('custom-production'))
        + rich_item(f'{prefix}prototip-parca/','Prototip & Parça','Kırılan, kaybolan ya da bulunamayan parçayı üretiriz.',child_active('prototype'))
        + rich_item(f'{prefix}mimari-maket-3d-baski/','Mimari Maket','Kütle, cephe ve vaziyet maketleri.',child_active('maket'))
        + rich_item(f'{prefix}kusadasi-3d-baski/','Kuşadası 3D Baskı','Kuşadası ve Aydın için yerel 3D baskı hizmeti.',child_active('local-production'))
        + '</div></div>'
        f'<div class="{group_class("corporate", "nfc")}">'
        '<button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-business">İşletmeler</button>'
        '<div class="nav-submenu nav-submenu-rich" id="nav-business">'
        '<div class="nav-rich-head"><span>İŞLETMELER</span><small>Markaya ve sahaya göre üretim.</small></div>'
        + rich_item(f'{prefix}kurumsal/','Kurumsal Üretim','Toplu, markalı ve işletmeye özel fiziksel üretim.',child_active('corporate'))
        + rich_item(f'{prefix}nfc-qr/','NFC + QR Sistemleri','Dijital menü, müşteri yorumları ve masa bazlı raporlar.',child_active('nfc'))
        + '</div></div>'
        f'<a{direct_active("projects")} href="{prefix}projeler/">Projeler</a>'
        f'<div class="{group_class("about", "contact")}">'
        '<button class="nav-group-toggle" type="button" aria-expanded="false" aria-controls="nav-studio">BG Studio</button>'
        '<div class="nav-submenu nav-submenu-rich nav-submenu-studio" id="nav-studio">'
        '<div class="nav-rich-head"><span>BG STUDIO</span><small>Stüdyo, iletişim ve mimarlık.</small></div>'
        + rich_item(f'{prefix}hakkimizda/','Hakkımızda','Üretim yaklaşımı, stüdyo ve çalışma biçimi.',child_active('about'))
        + rich_item(f'{prefix}iletisim/','İletişim','Kuşadası, teklif ve iletişim kanalları.',child_active('contact'))
        + rich_item('https://bgstudio.com.tr','Architecture','Mimarlık ve görselleştirme projeleri.',' class="arch-link"',True)
        + '</div></div>'
        '<div class="nav-actions"><a class="nav-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a></div>'
        '</nav></div></header>'
    )

def ensure_404_root_base():
    """Keep 404 assets/navigation valid when the browser URL is a nested missing route."""
    path = ROOT / '404.html'
    if not path.exists():
        return {'ok': True, 'changed': False, 'missing': True}
    text = path.read_text(encoding='utf-8')
    original = text
    if not re.search(r'<base\s+href=["\']/["\']\s*/?>', text, flags=re.I):
        text = text.replace('<head>', '<head><base href="/">', 1)
    if text != original:
        path.write_text(text, encoding='utf-8')
    return {'ok': True, 'changed': text != original, 'missing': False}


def sync_site_header_navigation():
    """Give every public page one canonical V3.2.03 Rich Navigation header without touching page data."""
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


def _bg_assistant_payload(prefix=''):
    products = [p for p in load_products() if p.get('active', True)]
    product_rows = []
    for product in products:
        description = str(product.get('card_description') or product.get('description') or '').strip()
        materials = [label for _key, label in catalog_materials(product)]
        tiers = []
        for tier in effective_pricing_tiers(product):
            price_value = tier.get('price_value')
            tiers.append({
                'label': str(tier.get('label') or ''),
                'quantity': int(tier.get('quantity') or 1),
                'price': format_try(price_value) or str(price_value or ''),
                'note': str(tier.get('note') or '')[:140],
            })
        product_rows.append({
            'slug': str(product.get('slug') or '').strip(),
            'name': str(product.get('name') or 'Ürün').strip(),
            'category': str(category_label(product) or '').strip(),
            'price': str(active_price_text(product) or 'Fiyat için iletişim').strip(),
            'description': clip_seo_text(description, 280),
            'href': f"{prefix}urunler/{str(product.get('slug') or '').strip()}/",
            'featured': bool(product.get('featured')),
            'personalizable': bool(catalog_personalizable(product)),
            'materials': materials[:8],
            'features': [str(x)[:140] for x in (product.get('features') or []) if str(x).strip()][:10],
            'tags': [str(x)[:80] for x in (product.get('tags') or []) if str(x).strip()][:12],
            'dimensions': str(product.get('dimensions') or '')[:120],
            'weight': str(product.get('weight') or '')[:100],
            'production_time': str(product.get('estimated_production_time') or product.get('production_time') or '')[:120],
            'technical_info': clip_seo_text(product.get('technical_info') or '', 260),
            'usage_info': clip_seo_text(product.get('usage_info') or '', 220),
            'personalization_info': clip_seo_text(product.get('personalization_info') or '', 220),
            'pricing_tiers': tiers[:8],
            'production_status': str(product_production_status(product) or 'active'),
        })

    pricing = active_nfc_pricing()
    package_labels = {
        'baslangic': ('Başlangıç', 10),
        'profesyonel': ('Profesyonel', 15),
        'premium': ('Premium', 20),
        'hizli_stand': ('Hızlı Bağlantı Standı', 1),
        'feedback_duo': ('Premium Feedback Duo', None),
    }
    package_rows = []
    for key, row in (pricing.get('packages') or {}).items():
        label, capacity = package_labels.get(key, (key, None))
        item = {
            'key': key,
            'name': label,
            'price': row.get('price'),
            'list_price': row.get('list_price'),
            'renewal': row.get('renewal'),
        }
        if key in ('baslangic', 'profesyonel', 'premium'):
            item.update({
                'tables': capacity,
                'nfc_per_table': 3,
                'total_nfc': int(capacity or 0) * 3,
                'qr_optional': True,
                'qr_per_table_if_selected': 3,
            })
        elif key == 'hizli_stand':
            item.update({'stands': 1, 'total_nfc': 3, 'qr_optional': True, 'qr_if_selected': 3})
        package_rows.append(item)

    duo_rows = []
    for key, row in (pricing.get('feedback_duo_packages') or {}).items():
        stands = int(row.get('stands') or key)
        nfc = int(row.get('nfc') or stands * 2)
        duo_rows.append({
            'stands': stands,
            'nfc': nfc,
            'price': row.get('price'),
            'renewal': row.get('renewal'),
            'qr_optional': True,
            'qr_per_stand_if_selected': 2,
            'qr_count_if_selected': nfc,
        })

    restaurant_rows = []
    for key, row in (pricing.get('special_restaurant_packages') or {}).items():
        restaurant_rows.append({
            'tables': int(row.get('tables') or key),
            'nfc': int(row.get('nfc') or 0),
            'price': row.get('price'),
            'renewal': row.get('renewal'),
        })

    def reference_rows(items, kind, limit=24):
        out = []
        seen = set()
        for item in items:
            if not item.get('active', True):
                continue
            name = str(item.get('name') or '').strip()
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            out.append({
                'name': name,
                'kind': kind,
                'headline': str(item.get('headline') or '')[:180],
                'description': clip_seo_text(item.get('description') or item.get('headline') or '', 280),
                'category': str(item.get('category') or '')[:120],
                'tags': [str(x)[:80] for x in (item.get('tags') or []) if str(x).strip()][:10],
            })
            if len(out) >= limit:
                break
        return out

    nfc_refs = reference_rows(resolve_nfc_items(), 'NFC + QR')
    corporate_refs = reference_rows(resolve_corporate_items(), 'Kurumsal')
    prototype_refs = reference_rows(load_managed_content(PROTOTYPE_DATA), 'Prototip / Parça')

    return {
        'version': SITE_ASSET_VERSION,
        'assistant_api': {'endpoint': 'https://ai.bgstudio.com.tr/api/bg-assistant'},
        'business': {
            'brand': 'BG Studio',
            'brand_3d': 'BG Studio 3D',
            'brand_architecture': 'BG Studio Architecture',
            'location': 'Kuşadası, Aydın',
            'founder': {
                'name': 'Berkant Gökbel',
                'role': 'BG Studio kurucusu ve mimar',
                'ownership': 'BG Studio markası, BG Studio Architecture ve BG Studio 3D Berkant Gökbel’e aittir.',
                'architecture': 'BG Studio Architecture, Berkant Gökbel’in mimarlık koludur; mimari tasarım ve mimari görselleştirme çalışmaları bu marka altında yürütülür.',
                'studio_3d': 'BG Studio 3D, Berkant Gökbel’in 3D üretim koludur; 3D baskı ürünleri, kişiye özel üretim, prototip/parça, kurumsal üretim ve NFC + QR işletme çözümleri bu yapı altında geliştirilir.',
                'summary': 'Berkant Gökbel, mimar ve BG Studio markasının kurucusudur. BG Studio çatısı altında BG Studio Architecture ile mimarlık ve mimari görselleştirme; BG Studio 3D ile 3D baskı, özel üretim, prototip, kurumsal üretim ve NFC + QR çözümlerini yürütür.',
            },
            'scope': ['3D baskı ürünleri', 'kişiye özel üretim', 'prototip ve parça üretimi', 'kurumsal toplu üretim', 'NFC + QR işletme sistemleri'],
            'production_note': 'Ürünler ürün kaydında aksi belirtilmedikçe doğrudan baskı kalitesiyle sunulur; özel son işlem veya boya vaat edilmez.',
            'pricing_rule': 'Hazır ürünlerde sitedeki güncel fiyat geçerlidir. Özel üretim, prototip, kurumsal ve kapsamı değişen işlerde ölçü/adet/detaya göre teklif hazırlanır.',
        },
        'products': product_rows,
        'nfc': {
            'year': str(pricing.get('year') or '2026'),
            'definition': 'NFC, uyumlu telefonun standa veya etikete çok yaklaştırılmasıyla bağlantı ya da dijital içeriği temassız açan kısa menzilli iletişim teknolojisidir.',
            'qr_definition': 'QR kod, telefon kamerasıyla taranan görsel koddur. NFC ile aynı hedefe alternatif erişim sunabilir; NFC dokundur/yaklaştır, QR ise kamerayla tara mantığıyla çalışır.',
            'system_summary': 'BG Studio NFC + QR sistemi yalnızca dijital menü değildir; masa/stand bazlı erişim, dijital menü, sosyal yönlendirmeler, işletme içi feedback akışı, Google yorumuna devam adımı, müşteri paneli ve etkileşim analitiği gibi modülleri işletmeye göre bir araya getirir.',
            'feedback_rule': 'Değerlendirme akışında kullanıcı önce BG Studio işletme içi feedback/değerlendirme ekranına yönlenebilir; uygun akışta ardından Google yorum adımı gösterilir. Sistemi doğrudan Google linki olarak tanımlama.',
            'feedback_trio': {'name': 'Premium Feedback Trio', 'pricing_mode': 'quote_only', 'nfc_per_stand': 3, 'qr_optional': True, 'pricing_note': 'Premium Feedback Trio için sabit hazır tarife yayınlanmıyor; güncel fiyat stand adedi ve kapsam netleştikten sonra teklif kapsamında belirlenir.'},
            'menu': 'Menüler işletmeye göre TR/EN görsel içerik, ek dillerde metin içerik, ürün içeriği, alerjen ve kalori bilgileri barındırabilir.',
            'analytics': 'İşletmeye göre masa, NFC tarama, menü tıklaması, değerlendirme/yorum ve sosyal medya gibi etkileşimler panelde izlenebilir.',
            'premium_plus': 'Premium Plus geliştiriliyor/yakında. Aktif olmayan özellikleri varmış gibi vaat etme; garson çağır veya hesap iste gibi özellikleri güncel paketin parçası diye söyleme.',
            'qr_unit': pricing.get('qr_unit'),
            'menu_design': pricing.get('menu_design'),
            'logo_design': pricing.get('logo_design'),
            'packages': package_rows,
            'feedback_duo_packages': duo_rows,
            'special_restaurant_packages': restaurant_rows,
            'package_rules': {
                'standard_packages': 'Başlangıç, Profesyonel ve Premium restoran paketlerinde masa başına 3 NFC mantığı kullanılır.',
                'qr': 'QR opsiyoneldir; seçilirse standart restoran kapsamlarında masa başına 3 QR hesabı kullanılabilir. Güncel birim QR bedelini nfc.qr_unit alanından kullan.',
                'design': 'Menü ve logo tasarımı ayrı kalem olabilir; güncel bedelleri nfc.menu_design ve nfc.logo_design alanından kullan.',
                'quick_stand': 'Hızlı Bağlantı Standı 1 stand / 3 NFC temel yapısındadır; QR seçilirse 3 QR eklenebilir.',
                'feedback_duo': 'Feedback Duo kapasite ve fiyatı feedback_duo_packages tablosundan seçilir; her stand için 2 NFC kullanılır. QR seçilirse stand başına 2 QR eklenir ve nfc.qr_unit üzerinden ayrıca hesaplanır.',
                'special_restaurant': '25-120 masa özel restoran hazır paketleri special_restaurant_packages tablosundan seçilir; her masa için 3 NFC hesabı kullanılır.',
            },
        },
        'services': {
            'custom_production': 'Fikir, fotoğraf, eskiz, ölçü veya örnek üründen başlanabilir. Üretilebilir geometri, malzeme ve kullanım koşulu değerlendirilir; kapsam netleşince teklif hazırlanır.',
            'prototype': 'Ölçü, uyum ve işlev odaklı prototip/parça üretimi yapılabilir. Teknik ölçüler ve kullanım koşulları önemlidir.',
            'corporate': 'İşletmelere logolu, markalı veya adetli 3D üretim yapılabilir. Adet, ebat, malzeme ve kişiselleştirme teklif üzerinde etkilidir.',
            'architecture': 'Mimarlık ve mimari görselleştirme BG Studio Architecture tarafında yürütülür: https://bgstudio.com.tr',
            'materials_general': 'PLA ve PETG gibi malzemeler ürün ve kullanım yerine göre değerlendirilebilir. Belirli ürün için yalnızca ürün kaydındaki material bilgisini kesin kabul et.',
            '3d_printing_general': 'FDM 3D baskıda katman çizgileri üretim yönteminin doğal karakteridir. Tolerans, duvar kalınlığı, yönlendirme ve malzeme seçimi parçanın kullanımına göre değişir.',
        },
        'references': {
            'nfc': nfc_refs,
            'corporate': corporate_refs,
            'prototype': prototype_refs,
        },
        'faq': [{'question': q, 'answer': a} for q, a in FAQ],
        'links': {
            'products': f'{prefix}urunler/',
            'nfc': f'{prefix}nfc-qr/',
            'custom': f'{prefix}ozel-uretim/',
            'prototype': f'{prefix}prototip-parca/',
            'corporate': f'{prefix}kurumsal/',
            'projects': f'{prefix}projeler/',
            'quote': f'{prefix}teklif/',
            'contact': f'{prefix}iletisim/',
            'about': f'{prefix}hakkimizda/',
            'architecture': 'https://bgstudio.com.tr',
            'whatsapp': 'https://wa.me/905302466903',
        },
        'delivery': {
            'local': 'Kuşadası elden teslim',
            'shipping': 'Türkiye geneli kargo',
            'timing': 'Üretim ve teslim süresi ürün, adet ve atölye yoğunluğuna göre değişir; kesin süreyi sipariş/teklif öncesinde netleştir.',
        },
    }


def render_bg_assistant_widget(prefix=''):
    payload = json.dumps(_bg_assistant_payload(prefix), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    logo_src = f'{prefix}assets/brand/bgstudio3d-monogram.webp'
    return f"""<!-- BGSTUDIO:ASSISTANT_START -->
<aside class="bg-assistant-panel" id="bg-assistant-panel" data-bg-assistant="v3.3.03" aria-label="BG Studio 3D Assistant" aria-hidden="true" hidden>
  <header class="bg-assistant-head">
    <div class="bg-assistant-identity">
      <span class="bg-assistant-mark" aria-hidden="true"><img src="{logo_src}" alt="" decoding="async"></span>
      <div class="bg-assistant-identity-copy">
        <span class="bg-assistant-title-row"><strong>BG Studio Asistan</strong></span>
        <small><i aria-hidden="true"></i> Ürünler, siparişler, NFC ve kurucumuz hakkında sorularını yanıtlar</small>
      </div>
    </div>
    <button class="bg-assistant-close" data-bg-assistant-close type="button" aria-label="BG Assistant'ı kapat"><span aria-hidden="true">×</span></button>
  </header>

  <div class="bg-assistant-body">
    <div class="bg-assistant-messages" data-bg-assistant-messages aria-live="polite"></div>

    <div class="bg-assistant-quick" aria-label="Hızlı sorular">
      <button type="button" data-bg-assistant-prompt="Bana uygun ürün bul"><span>Ürün bul</span></button>
      <button type="button" data-bg-assistant-prompt="NFC nedir, BG Studio sisteminde nasıl kullanılıyor?"><span>NFC nedir?</span></button>
      <button type="button" data-bg-assistant-prompt="Özel üretim nasıl çalışıyor"><span>Özel üretim</span></button>
      <button type="button" data-bg-assistant-prompt="Teklif almak istiyorum"><span>Teklif</span></button>
    </div>
  </div>

  <footer class="bg-assistant-compose">
    <form data-bg-assistant-form>
      <label class="bg-assistant-input-wrap">
        <span class="bg-assistant-sr">BG Assistant'a mesaj yaz</span>
        <input data-bg-assistant-input type="text" maxlength="240" autocomplete="off" placeholder="Ürün, NFC, 3D baskı... her şeyi sor" />
      </label>
      <button class="bg-assistant-send" type="submit" aria-label="Mesajı gönder">
        <span aria-hidden="true">↑</span>
      </button>
    </form>

    <div class="bg-assistant-compose-meta">
      <span>Ekibimizle konuşmak istersen</span>
      <button class="bg-assistant-handoff" data-bg-assistant-whatsapp type="button">
        <span>WhatsApp'ta devam et</span><b aria-hidden="true">↗</b>
      </button>
    </div>
  </footer>
</aside>
<script type="application/json" data-bg-assistant-data>{payload}</script>
<script defer="" src="{prefix}assets/js/bg-assistant.js?v={SITE_ASSET_VERSION}"></script>
<!-- BGSTUDIO:ASSISTANT_END -->"""


def sync_bg_assistant_widget():
    """Install the OpenAI-connected BG Assistant on every public page."""
    scanned = changed = 0
    marker_pattern = re.compile(
        r'<!-- BGSTUDIO:ASSISTANT_START -->.*?<!-- BGSTUDIO:ASSISTANT_END -->',
        flags=re.I | re.S
    )
    trigger_pattern = re.compile(
        r'<button\b[^>]*data-bg-assistant-trigger[^>]*>.*?</button>',
        flags=re.I | re.S
    )
    floating_pattern = re.compile(
        r'(<(?:div|aside)\b[^>]*class="[^"]*\bfloating-actions\b[^"]*"[^>]*>)',
        flags=re.I
    )
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            source = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if '<body' not in source.lower() or 'site-header' not in source:
            continue
        scanned += 1
        prefix = _relative_prefix_for_html(html_path)
        updated = marker_pattern.sub('', source)
        updated = trigger_pattern.sub('', updated)

        trigger = (
            '<button class="bg-assistant-trigger" data-bg-assistant-trigger type="button" '
            'aria-controls="bg-assistant-panel" aria-expanded="false" aria-label="BG Studio 3D Assistant aç">'
            f'<span class="bg-assistant-trigger-logo" aria-hidden="true"><img src="{prefix}assets/brand/bgstudio3d-monogram.webp" alt="" decoding="async"></span>'
            '<span class="bg-assistant-trigger-glow" aria-hidden="true"></span></button>'
        )
        if floating_pattern.search(updated):
            updated = floating_pattern.sub(lambda m: m.group(1) + trigger, updated, count=1)
        else:
            fallback = f'<div aria-label="Hızlı işlemler" class="floating-actions">{trigger}</div>'
            updated = updated.replace('</body>', fallback + '</body>', 1)

        widget = render_bg_assistant_widget(prefix)
        updated = updated.replace('</body>', widget + '</body>', 1)

        if updated != source:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed}



CRITICAL_CSS_V3183 = ':root{--paper:#ffffff;--paper-2:#f4f3f1;--ink:#2d1f14;--ink-soft:#6d5b4b;--brown:#8a4e0e;--line:rgba(72,46,25,.15);--border:var(--line);--accent:var(--brown);--text-secondary:var(--ink-soft);--dark:#16120f}*{box-sizing:border-box}html{background:#fff;scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font-family:Arial,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}a{color:inherit}img{display:block;width:100%;height:auto}.shell{width:min(1360px,calc(100% - 48px));margin-inline:auto}.site-header{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);border-bottom:1px solid var(--line);padding-top:env(safe-area-inset-top)}.nav-shell{height:82px;display:flex;align-items:center;justify-content:space-between;gap:28px}.brand{display:flex;align-items:center;gap:12px;text-decoration:none;min-width:max-content}.brand-monogram{display:inline-block;width:38px;height:38px;flex:0 0 38px;font-size:0;background:url("/assets/brand/bgstudio3d-monogram.webp") center/contain no-repeat}.brand-text{display:grid;line-height:1}.brand-text strong{font-size:.95rem;letter-spacing:.24em;font-weight:600}.brand-text small{font-size:.63rem;letter-spacing:.35em;margin-top:5px;color:var(--ink-soft)}.main-nav{display:flex;align-items:center;gap:15px}.main-nav a,.nav-group-toggle{text-decoration:none;font-size:.82rem;font-weight:600;color:#514235}.nav-group{position:relative;display:flex;align-items:center}.nav-group-toggle{border:0;background:transparent;min-height:44px;padding:0 9px}.nav-submenu{display:grid;opacity:0;visibility:hidden;pointer-events:none}.nav-whatsapp{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:999px;background:var(--ink);color:#fff!important;text-decoration:none}.menu-toggle{display:none;width:44px;height:44px;border:1px solid var(--line);background:transparent;border-radius:50%;position:relative}.menu-toggle span{position:absolute;left:12px;right:12px;height:1px;background:var(--ink)}.menu-toggle span:first-child{top:16px}.menu-toggle span:last-child{top:25px}.primary-cta,.secondary-cta,.ghost-cta{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 18px;border-radius:999px;text-decoration:none;font-size:.82rem;font-weight:700}.primary-cta{background:var(--ink);color:#fff}.secondary-cta{border:1px solid var(--line);background:rgba(255,255,255,.36)}.home-v3163{overflow:clip}.home-v3163 .eyebrow{margin:0 0 14px;color:var(--accent);font-size:.7rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}.home-v3163 h1,.home-v3163 h2,.home-v3163 h3{font-family:Georgia,serif;font-weight:500}.home-hero-v3163{position:relative;padding-top:clamp(54px,6vw,92px);padding-bottom:clamp(74px,8vw,128px)}.home-hero-grid-v3163{display:grid;grid-template-columns:minmax(0,.82fr) minmax(520px,1.18fr);gap:clamp(38px,6vw,92px);align-items:center}.home-hero-copy-v3163{position:relative;z-index:2;max-width:680px}.home-hero-copy-v3163 h1{font-size:clamp(4.6rem,8.2vw,9.1rem);line-height:.84;letter-spacing:-.06em;margin:0 0 28px;max-width:8.4ch}.home-hero-lead{margin:0;max-width:620px;color:var(--text-secondary);font-size:clamp(1.06rem,1.35vw,1.28rem);line-height:1.68}.home-hero-actions-v3163{display:flex;gap:10px;flex-wrap:wrap;margin-top:32px}.home-hero-proof{display:flex;gap:9px;flex-wrap:wrap;margin-top:30px}.home-hero-proof span{display:inline-flex;align-items:center;min-height:32px;padding:0 11px;border:1px solid var(--border);border-radius:999px;background:rgba(255,255,255,.26);font-size:.66rem;font-weight:700}.home-hero-stage-v3163{position:relative;min-height:clamp(560px,62vw,780px);border-radius:clamp(26px,3vw,42px);overflow:hidden;background:linear-gradient(145deg,#15110e,#201711 62%,#2b1c11);border:1px solid rgba(255,255,255,.06)}.home-hero-visual{position:absolute;margin:0;overflow:hidden;background:#17120f}.home-hero-visual-main{left:7%;top:9%;width:64%;height:78%;border-radius:28px;z-index:2}.home-hero-visual-side-one{right:5%;top:8%;width:28%;height:33%;border-radius:22px;z-index:3}.home-hero-visual-side-two{right:5%;bottom:13%;width:31%;height:35%;border-radius:22px;z-index:3}.home-hero-picture,.home-hero-picture img{width:100%;height:100%;display:block}.home-hero-picture img{object-fit:cover}.home-hero-visual figcaption{position:absolute;left:0;right:0;bottom:0;padding:46px 18px 16px;background:linear-gradient(transparent,rgba(17,13,10,.84));color:#fff;display:grid;gap:3px}.home-hero-stage-label{position:absolute;left:7%;bottom:4%;z-index:4;color:#fff}.page-hero{padding:clamp(64px,8vw,112px) 0}.page-hero h1{font-family:Georgia,serif;font-size:clamp(3.2rem,7vw,7rem);line-height:.9;margin:0}.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:12px;top:12px;z-index:999;background:#fff;padding:10px}@media(max-width:1040px){.nav-shell{height:72px}.menu-toggle{display:block}.main-nav{position:absolute;left:24px;right:24px;top:calc(100% + 8px);display:none;flex-direction:column;align-items:stretch;gap:5px;padding:12px;border-radius:22px;background:#fff;border:1px solid var(--border);max-height:calc(100dvh - 100px);overflow:auto}.main-nav.open{display:flex}.main-nav>a,.nav-link,.nav-group-toggle{width:100%;min-height:48px;justify-content:space-between;padding:0 14px}.nav-group{display:grid}.nav-group.is-open>.nav-submenu{display:grid}.nav-submenu{position:static;padding-left:10px}.nav-actions{display:grid}.nav-whatsapp{width:100%;min-height:50px}.home-hero-grid-v3163{grid-template-columns:1fr}.home-hero-stage-v3163{min-height:680px}}@media(max-width:760px){.shell{width:min(100% - 24px,1360px)}.nav-shell{height:68px}.brand-monogram{width:34px;height:34px;flex-basis:34px}.home-hero-v3163{padding-top:32px;padding-bottom:58px}.home-hero-grid-v3163{gap:24px}.home-hero-copy-v3163 h1{font-size:clamp(3.55rem,18vw,5.6rem);line-height:.88;margin-bottom:20px}.home-hero-lead{font-size:.96rem}.home-hero-proof{gap:6px;margin-top:20px}.home-hero-proof span{font-size:.58rem}.home-hero-stage-v3163{min-height:390px;border-radius:24px}.home-hero-visual-main{left:4%;top:5%;width:92%;height:88%;border-radius:20px}.home-hero-visual-desktop-extra{display:none!important}.home-hero-stage-label{left:6%;bottom:3%}.home-hero-actions-v3163{display:grid;grid-template-columns:1fr}.home-hero-actions-v3163 a{width:100%}}'

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
        updated = re.sub(r'((?:\.\./)*assets/css/(?:styles|styles\.min)\.css\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', text)
        main_version = SITE_ASSET_VERSION + ('-option-price' if 'data-option-price=' in text else '')
        updated = re.sub(r'((?:\.\./)*assets/js/main\.js\?v=)[^"\']+', rf'\g<1>{main_version}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/navigation\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        # V3.3.31: consent.js was loaded without a version, so fixes reached visitors only after cache expiry.
        updated = re.sub(r'((?:\.\./)*assets/js/consent\.js)(?:\?v=[^"\']*)?(?=["\'])', rf'\g<1>?v={SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/homepage\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/catalog\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/nfc-hub\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/projects\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/quote-center\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        updated = re.sub(r'((?:\.\./)*assets/js/bg-assistant\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
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
        if 'data-bg-assistant="v3.3.03"' in updated and 'assets/js/bg-assistant.js' not in updated:
            assistant_tag = f'<script defer="" src="{prefix}assets/js/bg-assistant.js?v={SITE_ASSET_VERSION}"></script>'
            updated = updated.replace('</body>', assistant_tag + '</body>', 1)
        # V3.1.83: iOS safe-area viewport and non-blocking first-paint assets.
        updated = re.sub(
            r'<meta\s+[^>]*name=["\']viewport["\'][^>]*>',
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
            updated, count=1, flags=re.I
        )
        if 'name="viewport"' not in updated and '</head>' in updated:
            updated = updated.replace('</head>', '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head>', 1)

        # Clean previous async blocks and old blocking links so rebuilds stay idempotent.
        updated = re.sub(r'<!-- BGSTUDIO:ASYNC_FONTS_V3183_START -->.*?<!-- BGSTUDIO:ASYNC_FONTS_V3183_END -->', '', updated, flags=re.I | re.S)
        updated = re.sub(r'<!-- BGSTUDIO:ASYNC_CSS_V3183_START -->.*?<!-- BGSTUDIO:ASYNC_CSS_V3183_END -->', '', updated, flags=re.I | re.S)
        updated = re.sub(r'<link\b[^>]*href=["\']https://fonts\.googleapis\.com/css2\?[^"\']+["\'][^>]*>', '', updated, flags=re.I)
        updated = re.sub(r'<link\b[^>]*href=["\'](?:\.\./)*assets/css/(?:styles|styles\.min)\.css(?:\?v=[^"\']*)?["\'][^>]*>', '', updated, flags=re.I)
        updated = re.sub(r'<noscript>\s*</noscript>', '', updated, flags=re.I)

        font_url = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap'
        async_font = (f'<!-- BGSTUDIO:ASYNC_FONTS_V3183_START -->'
                      f'<link rel="preload" as="style" href="{font_url}">'
                      f'<link rel="stylesheet" href="{font_url}" media="print" onload="this.media=\'all\'">'
                      f'<noscript><link rel="stylesheet" href="{font_url}"></noscript>'
                      f'<!-- BGSTUDIO:ASYNC_FONTS_V3183_END -->')

        target_css = f'{prefix}assets/css/styles.min.css?v={SITE_ASSET_VERSION}'
        async_css = (f'<!-- BGSTUDIO:ASYNC_CSS_V3183_START -->'
                     f'<link rel="preload" as="style" href="{target_css}">'
                     f'<link rel="stylesheet" href="{target_css}" media="print" onload="this.media=\'all\'">'
                     f'<noscript><link rel="stylesheet" href="{target_css}"></noscript>'
                     f'<!-- BGSTUDIO:ASYNC_CSS_V3183_END -->')
        home_blocking_css = (f'<link rel="preload" as="style" href="{target_css}">'
                             f'<link rel="stylesheet" href="{target_css}">')

        # V3.1.93: the home page hero changed substantially after the V3.1.83
        # critical CSS snapshot. Using that old snapshot while the full stylesheet
        # loads asynchronously causes a visible first-paint flash of the raw hero
        # image. On the flagship home page, load the canonical stylesheet before
        # first paint and omit the obsolete critical block. Other pages keep the
        # existing async/critical strategy.
        updated = re.sub(r'<style\s+data-critical-v3183[^>]*>.*?</style>', '', updated, flags=re.I | re.S)
        if html_path == ROOT / 'index.html':
            updated = updated.replace('</head>', async_font + home_blocking_css + '</head>', 1)
        else:
            updated = updated.replace('</head>', async_font + async_css + f'<style data-critical-v3183>{CRITICAL_CSS_V3183}</style></head>', 1)

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
<section class="page-hero nfc-platform-hero"><div class="shell page-hero-grid reveal"><div><p class="eyebrow">BG STUDIO NFC İŞLETME PLATFORMU</p><h1>Bir etiketten fazlası. İşletmen için dijital altyapı.</h1><p class="lead">BG Studio NFC; işletmeye özel fiziksel standları, NFC ve isteğe bağlı QR erişimini, müşteri etkileşimlerini, dijital menüyü, değerlendirme akışını, analitikleri ve yönetim panelini tek altyapıda birleştirir.</p><div class="hero-actions"><a class="primary-cta" href="../teklif/?tur=nfc">İşletmen için teklif al ↗</a><a class="secondary-cta" href="#urun-aileleri">Çözümleri incele ↓</a></div></div><aside class="info-panel info-panel-dark nfc-platform-metrics"><p class="eyebrow">TEK SİSTEMDE</p><div class="metric-grid"><div class="metric"><strong>Fiziksel</strong><span>İşletmeye özel 3D stand</span></div><div class="metric"><strong>Dijital</strong><span>Menü, feedback ve bağlantılar</span></div><div class="metric"><strong>Panel</strong><span>İşletme müşteri paneli</span></div><div class="metric"><strong>Raporlar</strong><span>Stand / masa bazlı performans</span></div></div></aside></div></section>
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
<article class="package package-detailed"><div class="package-head"><span class="package-kicker">10 MASA · 30 NFC</span><span class="package-badge">Başlangıç</span></div><h3>Başlangıç</h3><p>10 masaya kadar restoranlar için BG Studio NFC işletme altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('baslangic').get('price'))}</strong><span>{normal_and_renewal('baslangic')}</span></div><div class="package-capacity"><span><b>10</b>Masa</span><span><b>30</b>NFC</span><span><b>30</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>10 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Masa bazlı kullanım analitiği</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Uzaktan hedef ve içerik yönetimi</li><li>Anlık bildirimler</li><li>Linkleri uzaktan güncelleme</li></ul>{restaurant_option_picker('baslangic','Başlangıç',10,30,'secondary-cta')}</article>
<article class="package package-detailed featured"><div class="package-head"><span class="package-kicker">15 MASA · 45 NFC</span><span class="package-badge">Öne çıkan</span></div><h3>Profesyonel</h3><p>15 masalık restoranlar için 45 NFC erişim noktası, dijital menü, panel ve analitik altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('profesyonel').get('price'))}</strong><span>{normal_and_renewal('profesyonel')}</span></div><div class="package-capacity"><span><b>15</b>Masa</span><span><b>45</b>NFC</span><span><b>45</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>15 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Masa bazlı kullanım analitiği</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Uzaktan hedef ve içerik yönetimi</li><li>Anlık bildirimler</li><li>Linkleri uzaktan güncelleme</li></ul>{restaurant_option_picker('profesyonel','Profesyonel',15,45,'primary-cta')}</article>
<article class="package package-detailed"><div class="package-head"><span class="package-kicker">20 MASA · 60 NFC</span><span class="package-badge">Premium</span></div><h3>Premium</h3><p>20 masalık restoranlar için 60 NFC erişim noktası ve BG Studio NFC platformunun tam restoran altyapısı.</p><div class="package-price"><small>{year} paket fiyatı</small><strong>{money(pack('premium').get('price'))}</strong><span>{normal_and_renewal('premium')}</span></div><div class="package-capacity"><span><b>20</b>Masa</span><span><b>60</b>NFC</span><span><b>60</b>QR opsiyonu</span></div><ul class="nfc-package-features"><li>20 özel tasarım stand · stand başına 3 NFC</li><li>Akıllı Menü + 10 dil desteği</li><li>İşletme müşteri paneli</li><li>Detaylı masa bazlı analitik</li><li>Değerlendirme ve geri bildirim sistemi</li><li>Uzaktan hedef ve içerik yönetimi</li><li>Anlık bildirimler</li><li>Linkleri uzaktan güncelleme</li></ul>{restaurant_option_picker('premium','Premium',20,60,'secondary-cta')}</article>
</div>
<div class="nfc-package-rule"><strong>QR sistemi restoran paketlerine zorunlu dahil değildir.</strong><span>Her masa 3 NFC erişim noktasıyla gelir. QR tercih edilirse masa başına 3 QR eklenir. Menü Tasarımı ve Logo Tasarımı da ayrı opsiyonel kalemlerdir.</span></div>

<div class="restaurant-common-platform"><div class="restaurant-common-head"><div><p class="eyebrow">TÜM STANDART RESTORAN PAKETLERİNDE MEVCUT</p><h3>Mevcut restoran altyapısı tüm kapasitelerde devam eder.</h3></div><p>Başlangıç, Profesyonel, Premium ve 25–120 masa Özel Restoran Hazır Paketleri aynı sistem çekirdeğini kullanır. Premium Plus bu kapsamın yerine geçmez.</p></div><div class="restaurant-common-grid"><article><h4>Akıllı Menü</h4><ul><li>Akıllı Menü ve çoklu dil altyapısı</li><li>Türkçe + İngilizce görsel menü</li><li>8 ek dilde dijital metin menü</li><li>Ürün içerikleri</li><li>14 alerjen bilgi katmanı</li><li>Yaklaşık kalori bilgileri</li></ul></article><article><h4>Değerlendirme & Google</h4><ul><li>Müşteri değerlendirme sistemi</li><li>Google değerlendirme devam akışı</li><li>Google puan ve yorum performansı</li><li>Sosyal medya / iletişim yönlendirmeleri</li></ul></article><article><h4>Panel & Analitik</h4><ul><li>İşletme müşteri paneli</li><li>Masa ve alan bazlı kullanım analitikleri</li><li>Anlık bildirimler</li><li>Linkleri uzaktan güncelleme</li></ul></article><article class="restaurant-common-accent"><h4>Uzaktan Yönetim</h4><ul><li>Dijital hedef yönetimi</li><li>Menü ve yönlendirme güncellemeleri</li><li>İşletme bazlı sistem ayarları</li><li>Fiziksel standı yeniden basmadan bağlantı yönetimi</li></ul><p>Aktif özellikler yalnızca yayındaki sistem kapsamına göre gösterilir; geliştirme aşamasındaki modüller mevcut paket özelliği gibi sunulmaz.</p></article></div></div>

<div class="special-ready-card"><div class="special-ready-copy"><p class="eyebrow">ÖZEL RESTORAN HAZIR PAKETLERİ</p><h3>Yüksek kapasitede restoran altyapısı.</h3><p>20 masanın üzerindeki restoranlarda aynı Standart Restoran altyapısı işletmenin kapasitesine göre ölçeklenir. Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ve Uzaktan yönetim mevcut kapsamda devam eder. Masa sayını seç; NFC paket bedeli, QR hesabı ve ek tasarım hizmetleri sağdaki kartta anında hesaplansın.</p><div class="special-ready-tags"><span>Akıllı Menü + çoklu dil</span><span>14 alerjen + yaklaşık kalori</span><span>Google performansı + değerlendirme</span><span>Uzaktan yönetim</span></div><div class="nfc-capacity-selector-head"><strong>Masa sayını seç</strong><span>Aşağıdaki kartlardan birine tıkla. Sağdaki hesap anında yenilenir.</span></div><div class="nfc-capacity-chips" role="group" aria-label="Özel Restoran hazır masa kapasitesi">{capacity_chips}</div></div><div class="special-ready-highlight" data-special-package-calculator data-qr-unit="{qr_unit}" data-menu-price="{menu_design}" data-logo-price="{logo_design}"><span class="package-kicker" data-special-title>GÜNCEL {special_default_key} MASA HAZIR PAKETİ</span><div class="special-ready-metrics"><span><b data-special-tables>{special_default_key}</b>Masa</span><span><b data-special-nfc>{special_qr_count}</b>NFC</span></div><div class="special-ready-price"><small data-special-price-year>{year} NFC hazır paket bedeli</small><strong data-special-base-price>{money(special_default.get('price'))}</strong><span data-special-renewal>Yıllık yenileme: {money(special_default.get('renewal'))}</span></div><div class="special-ready-options"><button type="button" data-special-option="qr" aria-pressed="false"><span>QR sistemi</span><b data-special-qr-cost>+{money(special_qr_cost)}</b><small data-special-qr-copy>{special_qr_count} QR × {money(qr_unit)} / QR</small></button><button type="button" data-special-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b data-special-menu-cost>+{money(menu_design)}</b><small>{esc(menu_scope_copy)}</small></button><button type="button" data-special-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b data-special-logo-cost>+{money(logo_design)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button></div><div class="special-ready-breakdown"><div><span>NFC hazır paket</span><b data-special-line-base>{money(special_default.get('price'))}</b></div><div><span>QR sistemi</span><b data-special-line-qr>Seçilmedi</b></div><div><span>Menü Tasarımı</span><b data-special-line-menu>Seçilmedi</b></div><div><span>Logo Tasarımı</span><b data-special-line-logo>Seçilmedi</b></div></div><div class="special-ready-total"><span>Seçili toplam</span><strong data-special-total>{money(special_default.get('price'))}</strong><small>NFC paket bedeli + seçtiğin ek hizmetler</small></div><a class="secondary-cta" data-special-offer href="../teklif/?tur=nfc&amp;paket=ozel-kapasite&amp;masa={special_default_key}">{special_default_key} masa için teklifi al</a></div></div>
</section>

<section class="section-pad-sm shell premium-plus-teaser" id="premium-plus" data-premium-plus-roadmap="3.1.61" aria-labelledby="premium-plus-title"><div class="premium-plus-shell"><div class="premium-plus-head"><div class="premium-plus-copy"><p class="eyebrow">YAKINDA</p><h2 id="premium-plus-title">Premium Plus</h2><p>Mevcut Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ile Uzaktan yönetim özellikleri tüm Standart Restoran paketlerinde devam eder.</p><p>Premium Plus bunların üzerine doğrudan masa siparişi, Akıllı Misafir Profili ve CRM, sadakat sistemi, rezervasyon / masa yönetimi ve AI destekli müşteri deneyimi araçlarını ekleyen gelişmiş üst katman olarak konumlandırılacaktır.</p></div><div class="premium-plus-state" aria-label="Premium Plus ürün durumu"><span class="premium-plus-badge">YAKINDA</span><span class="premium-plus-progress">Geliştiriliyor</span><small>Henüz satışta değil</small></div></div><div class="premium-plus-roadmap-head"><div><p class="eyebrow">YAKINDA GELECEK ÖZELLİKLER</p><h3>Restoran deneyiminin bir sonraki katmanı.</h3></div><p>Özellik başlığına tıklayarak planlanan kapsamın ayrıntısını görebilirsin.</p></div><div class="premium-plus-grid">
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
</div><div class="premium-plus-note-group"><p class="premium-plus-note"><strong>Premium Plus mevcut paket özelliklerini yeniden paketlemez.</strong> Uzaktan yönetim zaten tüm Standart Restoran paketlerinin mevcut kapsamındadır. Premium Plus; NFC menüden doğrudan sipariş, müşteri sipariş notları, Akıllı Misafir Profili ve CRM, sadakat ve ziyaret ödülleri, VIP / tekrar gelen misafir tanıma, otomatik müşteri segmentleri, geri kazanım kampanyaları, rezervasyon ve dijital bekleme listesi, AI ürün önerileri ve AI yönetici özetleri için geliştirilen ayrı bir üst katmandır.</p><p class="premium-plus-release-note">Çıkış tarihi, kesin özellik kapsamı ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="premium-plus-footer"><span class="premium-plus-follow">Premium Plus gelişmelerini takip et</span><span class="premium-plus-coming">YAKINDA</span></div></div></section>

<section class="section-pad-sm shell reveal solution-detail solution-quick" id="hizli-stand"><div class="solution-heading"><div><p class="eyebrow">02 · BAĞIMSIZ İŞLETME ÇÖZÜMÜ</p><h2>Hızlı Bağlantı Standı</h2><p>Menü altyapısına ihtiyaç duymayan işletmeler için üç bağımsız NFC hedefini tek, işletmeye özel tasarım stand üzerinde birleştiren hızlı bağlantı çözümü.</p></div><div class="solution-price-stack"><small>{year} başlangıç fiyatı</small><strong>{money(quick_price)}</strong><span>{money(quick_renewal)} yıllık yenileme</span><em>3 NFC / stand</em></div></div>
<div class="solution-two-col"><div class="solution-panel"><h3>Tek stand, üç bağımsız hedef.</h3><p>Her NFC alanı ayrı bir bağlantıya yönlendirilebilir ve hedefler uzaktan değiştirilebilir.</p><div class="channel-cloud">{channels}</div><div class="solution-feature-list"><span>1 özel tasarım fiziksel stand</span><span>Stand başına 3 NFC</span><span>İşletme müşteri paneli</span><span>NFC / QR okutma analitiği</span><span>Google performans takibi</span><span>Uzaktan hedef yönetimi</span></div></div><div class="solution-panel solution-panel-accent"><h3>Opsiyonlar ve liste hesabı</h3><div class="quick-option-summary"><div><span>QR sistemi</span><strong>3 QR · +{money(quick_qr_cost)}</strong><small>{year}: 3 × {money(qr_unit)}</small></div><div><span>Logo Tasarımı</span><strong>+{money(logo_design)}</strong><small>{year} liste bedeli</small></div><div class="disabled-option"><span>Menü Tasarımı</span><strong>Bulunmaz</strong><small>Hızlı Stand menü sistemi içermez.</small></div></div><details class="solution-details"><summary>{year} örnek liste hesaplarını gör</summary><div class="quick-price-examples"><div><span>Sadece Hızlı Stand</span><b>{money(quick_price)}</b></div><div><span>Hızlı Stand + QR</span><b>{money(quick_with_qr)}</b></div><div><span>Hızlı Stand + Logo Tasarımı</span><b>{money(quick_with_logo)}</b></div><div><span>Hızlı Stand + QR + Logo Tasarımı</span><b>{money(quick_full)}</b></div></div><p>Bunlar liste fiyatlarıdır. İşletmeye özel teklif uygulanabilir.</p></details><div class="future-rate"><span>2027 QR opsiyonu: 3 × {money(qr_2027)} = <b>+{money(qr_2027*3)}</b></span><span>2027 Logo Tasarımı: <b>{money(logo_2027)}</b></span></div></div></div>
<div class="solution-actions"><a class="primary-cta" href="../teklif/?tur=nfc&amp;paket=hizli-stand">Hızlı Stand için teklif al ↗</a><a class="text-cta" href="#referans-koala-petshop">Koala Petshop saha referansını gör ↓</a></div></section>

<section class="section-pad-sm shell reveal solution-detail solution-feedback" id="premium-feedback-duo"><div class="solution-heading"><div><p class="eyebrow">03 · BAĞIMSIZ İŞLETME ÇÖZÜMÜ</p><h2>Premium Feedback Duo</h2><p>Müşteri geri bildirimini, Google değerlendirme devam akışını ve işletmenin seçtiği sosyal / iletişim bağlantısını aynı fiziksel stand üzerinde birleştiren gelişmiş müşteri deneyimi sistemi.</p></div><div class="solution-price-stack dark"><small>{year} başlayan kurulum</small><strong>{money(duo_start_price)}</strong><span>{money(duo_start_renewal)}'den başlayan yıllık yenileme</span><em>2 NFC / stand · 10–120 stand</em></div></div>
<div class="feedback-duo-flow"><article><span class="flow-no">NFC 1</span><h3>5 sorulu işletme içi değerlendirme</h3><p>Müşteri önce BG Studio feedback akışına alınır. Serbest görüşünü de bırakabilir; sonuç işletmenin müşteri paneline düşer ve ardından Google değerlendirme adımına devam edebilir.</p><div class="feedback-topic-chips">{feedback_topics}</div></article><article><span class="flow-no">NFC 2</span><h3>Seçilebilir sosyal / iletişim hedefi</h3><p>İkinci NFC Instagram'a sabit değildir. İşletmenin ihtiyacına göre sosyal medya, iletişim veya web hedeflerinden biri seçilir ve uzaktan yönetilebilir.</p><div class="channel-cloud compact">{channels}</div></article></div>
<div class="feedback-feature-grid"><article><h4>Müşteri deneyimi</h4><ul><li>İşletmeye özel fiziksel standlar</li><li>5 sorulu Feedback sistemi</li><li>Serbest müşteri görüşü</li><li>Google değerlendirme devam akışı</li><li>Seçilebilir sosyal / iletişim bağlantısı</li></ul></article><article><h4>Panel ve analitik</h4><ul><li>İşletme müşteri paneli</li><li>Stand bazlı NFC okutma analitiği</li><li>Feedback performans analitiği</li><li>Google puanı ve yorum performansı</li></ul></article><article><h4>Bildirim ve rapor</h4><ul><li>Bildirim Merkezi</li><li>Push bildirim altyapısı</li><li>Haftalık performans raporu</li><li>Genel işletme raporları</li></ul></article><article><h4>Yıllık haklar</h4><ul><li>2 sosyal / iletişim bağlantısı güncellemesi</li><li>1 işletme değerlendirme bağlantısı güncellemesi</li><li>Uzaktan bağlantı yönetimi</li><li>BG Studio yönetim altyapısı</li></ul></article></div>
<div class="feedback-price-summary"><div><span><b>2 NFC</b> / stand</span><span><b>{first_duo.get('stands',10)} stand / {first_duo.get('nfc',20)} NFC</b>'den başlayan hazır çözümler</span><span><b>{money(duo_start_price)}</b>'den başlayan kurulum</span><span><b>{money(duo_start_renewal)}</b>'den başlayan yıllık yenileme</span><span><b>10–120 stand</b> hazır kapasite</span></div></div>
<details class="feedback-pricing-details" id="feedback-fiyatlari"><summary><span>Tüm kapasite ve fiyatları gör</span><b>21 hazır kapasite</b></summary><div class="feedback-pricing-body"><div class="feedback-price-table-wrap"><table class="feedback-price-table"><thead><tr><th>Stand</th><th>NFC</th><th>Kurulum / Satış</th><th>Yıllık Yenileme</th></tr></thead><tbody>{duo_table_rows}</tbody></table></div><div class="feedback-price-mobile">{duo_mobile_cards}</div><p class="feedback-price-note">Hazır kapasiteler dışında işletmeye özel adet ve anlaşmalı fiyatlandırma yapılabilir.</p></div></details>
<p class="renewal-explain">Yıllık yenileme; müşteri paneli, feedback sistemi, analizler, bildirim / push altyapısı, raporlama ve sistem hizmetlerinin devam bedelidir.</p><div class="solution-actions"><a class="primary-cta" href="../teklif/?tur=nfc&amp;paket=feedback-duo&amp;masa={first_duo.get('stands',10)}">Premium Feedback Duo için teklif al ↗</a></div></section>

<section class="section-pad-sm shell reveal solution-compare"><div class="split-title"><div><p class="eyebrow">HANGİ ÇÖZÜM?</p><h2>Hızlı Stand mı, Premium Feedback Duo mu?</h2></div><p>İkisi de bağımsız işletme çözümüdür. Seçim, doğrudan bağlantı mı yoksa gelişmiş müşteri feedback ve raporlama akışı mı gerektiğine göre yapılır.</p></div><div class="compare-grid"><article><p class="eyebrow">HIZLI BAĞLANTI STANDI</p><h3>Doğrudan bağlantı</h3><div class="compare-metrics"><span><b>3 NFC</b>/ stand</span><span><b>{money(quick_price)}</b>başlangıç</span><span><b>{money(quick_renewal)}</b>yenileme</span></div><ul><li>3 bağımsız bağlantı hedefi</li><li>Menü sistemi yok</li><li>QR opsiyonel</li><li>Logo Tasarımı opsiyonel</li><li>İşletme paneli ve okutma analitiği</li></ul></article><article class="dark"><p class="eyebrow">PREMIUM FEEDBACK DUO</p><h3>Feedback + Google + raporlama</h3><div class="compare-metrics"><span><b>2 NFC</b>/ stand</span><span><b>{money(duo_start_price)}</b>başlangıç</span><span><b>{money(duo_start_renewal)}</b>'den yenileme</span></div><ul><li>NFC 1: 5 sorulu feedback + Google devamı</li><li>NFC 2: seçilebilir sosyal / iletişim hedefi</li><li>Feedback analitiği ve Google performansı</li><li>Anlık bildirimler</li><li>Haftalık raporlama · 10–120 stand</li></ul></article></div></section>

<section class="section-pad-sm shell reveal nfc-platform-block-wrap"><div class="nfc-platform-block"><div class="nfc-platform-title"><div><p class="eyebrow">BG STUDIO NFC YÖNETİM PANELİ</p><h3>Fiziksel ürünün arkasında çalışan sistem.</h3></div><p>Çözüme göre özellik seti değişse de işletme paneli, uzaktan hedef yönetimi, analitik ve BG Studio yönetim altyapısı fiziksel standları dijital sisteme bağlar.</p></div><div class="nfc-infra-grid"><article class="nfc-infra-card"><span>01</span><h4>İşletme paneli</h4><p>Kullanım verileri, bildirimler, paket ve sistem durumları tek merkezde takip edilir.</p></article><article class="nfc-infra-card"><span>02</span><h4>Raporlar</h4><p>Masa veya stand bazlı NFC / QR etkileşimleri çözüm tipine göre raporlanır.</p></article><article class="nfc-infra-card"><span>03</span><h4>Uzaktan hedef yönetimi</h4><p>Bağlantılar ve dijital hedefler fiziksel ürünü yeniden üretmeden yönetilebilir.</p></article><article class="nfc-infra-card"><span>04</span><h4>Özel tasarım ve üretim</h4><p>Standlar hazır pleksi üstüne etiket yapıştırılan ürünler değildir; tasarım ve 3D üretim işletmeye göre hazırlanır.</p></article></div></div>
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
        '<section class="section-pad custom-band nfc-reference-first" id="sahadan-isler"><div class="shell">'
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
        'provider': {'@id': BASE_URL + '/#organization'},
        'areaServed': 'Türkiye',
        'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': f'{year} NFC & QR İşletme Çözümleri', 'itemListElement': offers},
    }
    script = '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(',', ':')) + '</script>'
    pattern = re.compile(r'<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"Service","name":"BG Studio NFC.*?</script>', flags=re.S)
    if pattern.search(html_text):
        return pattern.sub(script, html_text, count=1)
    return html_text


def verify_v3164_public_shell(include_home=True, include_catalog=True):
    """Fail loudly if a public page misses the current V3.3.03 public shell."""
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
            'data-bg-nav="v3.2.03"',
            '>Üretim</button>',
            '>İşletmeler</button>',
            '>Projeler</a>',
            '>BG Studio</button>',
            f'assets/js/navigation.js?v={SITE_ASSET_VERSION}',
            'data-bg-assistant="v3.3.03"',
            'data-bg-assistant-trigger',
            f'assets/js/bg-assistant.js?v={SITE_ASSET_VERSION}',
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
        raise RuntimeError('V3.3.15 STABLE public shell doğrulaması başarısız. Rich Navigation veya BG Assistant uygulanmamış sayfalar var: ' + sample)
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
    if not image and key == 'restaurant_packages':
        image = 'assets/images/nfc-stand-semasi.webp'
    if image:
        dims = _asset_dimensions_v3324(image) or (1600, 900)
        srcset = _responsive_srcset_for_asset_v3324(image, prefix, widths=(640, 1000))
        srcset_attr = f' srcset="{esc(srcset)}" sizes="(max-width:760px) calc(100vw - 24px), (max-width:1100px) 48vw, 42vw"' if srcset else ''
        fallback = ' nfc-v3167-media-fallback' if key == 'restaurant_packages' and not row.get('image') else ''
        return f'<div class="nfc-v3167-media{fallback} zoomable-media" role="button" tabindex="0" aria-label="{esc(alt)} görselini büyüt"><img src="{prefix}{esc(image)}" alt="{esc(alt)}" width="{dims[0]}" height="{dims[1]}" loading="eager" fetchpriority="high" decoding="async"{srcset_attr}></div>'
    return '<div class="nfc-v3167-media nfc-v3167-media-fallback"><span>BG Studio NFC + QR</span><small>İşletmeye özel fiziksel + dijital sistem</small></div>'


def _nfc_v3167_browser_frame(title='İşletme paneli'):
    modules = ['NFC taramaları','Menü etkileşimleri','Feedback','Google yönlendirme','Sosyal medya','Çoklu dil','Alerjen','Kalori','Bildirimler']
    module_html = ''.join(f'<span>{esc(x)}</span>' for x in modules)
    return f'''<div class="nfc-browser-frame" aria-label="BG Studio NFC yazılım arayüzü sunumu"><div class="nfc-browser-top"><span></span><span></span><span></span><b>{esc(title)}</b></div><div class="nfc-browser-body"><aside role="none"><strong>BG NFC</strong><i>Panel</i><i>Raporlar</i><i>Menü</i><i>Değerlendirme Standları</i><i>Ayarlar</i></aside><div class="nfc-browser-content"><div class="nfc-browser-title"><div><small>YÖNETİM PANELİ</small><strong>Standın arkasında neler var?</strong></div><span>Nasıl çalışır?</span></div><div class="nfc-browser-module-grid">{module_html}</div><div class="nfc-browser-panels"><div><small>MİSAFİRİN GÖZÜNDEN</small><strong>Dokun → Aç → Takip et</strong></div><div><small>YÖNETİM</small><strong>Uzaktan hedef ve içerik yönetimi</strong></div></div></div></div></div>'''


def _nfc_v3167_flow():
    return '''<div class="nfc-digital-flow" role="region" tabindex="0" aria-label="BG Studio NFC sistem akışı"><span><b>01</b>Stand</span><i>→</i><span><b>02</b>Telefon</span><i>→</i><span><b>03</b>Dijital deneyim</span><i>→</i><span><b>04</b>İşletme paneli</span></div>'''


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
    return f'''<div class="nfc-capacity-lab" data-capacity-stepper-root><div class="nfc-capacity-lab-copy"><p class="eyebrow">25–120 MASA</p><h3>Masa sayını seç. Toplamı anında gör.</h3><p>Uzun fiyat listesine bakmak yerine masa sayısını kaydırıcı veya + / − ile değiştir; toplam anında güncellenir.</p><div class="nfc-capacity-stepper"><button type="button" data-capacity-prev aria-label="Önceki kapasite">−</button><div><small>Masa sayısı</small><strong data-capacity-display>{first}</strong><span data-capacity-nfc-display>{first_nfc} NFC</span></div><button type="button" data-capacity-next aria-label="Sonraki kapasite">+</button></div><input class="nfc-capacity-range" data-capacity-range type="range" min="0" max="{len(capacities)-1}" step="1" value="0" aria-label="Masa kapasitesi"><div class="nfc-capacity-range-labels"><span>25</span><span>60</span><span>120 masa</span></div><div class="nfc-capacity-data" hidden>{buttons}</div><details class="nfc-all-prices"><summary>Tüm fiyatları göster <span>{len(capacities)} hazır kapasite</span></summary><div class="nfc-all-prices-table"><table><thead><tr><th>Kapasite</th><th>NFC</th><th>Paket plan bedeli</th><th>Yıllık yenileme</th></tr></thead><tbody>{table_rows}</tbody></table></div></details></div><div class="special-ready-highlight nfc-capacity-live-card" data-special-package-calculator data-offer-base="{offer_prefix}teklif/" data-qr-unit="{qr_unit}" data-menu-price="{menu_price}" data-logo-price="{logo_price}"><span class="package-kicker" data-special-title>GÜNCEL {first} MASA HAZIR PAKETİ</span><div class="special-ready-metrics"><span><b data-special-tables>{first}</b>Masa</span><span><b data-special-nfc>{first_nfc}</b>NFC</span></div><div class="special-ready-price"><small data-special-price-year>{year} paket plan bedeli</small><strong data-special-base-price>{_nfc_money(first_row.get('price'))}</strong><span data-special-renewal>Yıllık yenileme: {_nfc_money(first_row.get('renewal'))}</span></div><div class="special-ready-options"><button type="button" data-special-option="qr" aria-pressed="false"><span>QR sistemi</span><b data-special-qr-cost>+{_nfc_money(first_nfc*qr_unit)}</b><small data-special-qr-copy>{first_nfc} QR × {_nfc_money(qr_unit)} / QR</small></button><button type="button" data-special-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b data-special-menu-cost>+{_nfc_money(menu_price)}</b><small>TR + EN görsel menü · 8 ek dijital dil · ürün içerikleri · 14 alerjen · yaklaşık kalori</small></button><button type="button" data-special-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b data-special-logo-cost>+{_nfc_money(logo_price)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button></div><div class="special-ready-breakdown"><div><span>Paket plan bedeli</span><b data-special-line-base>{_nfc_money(first_row.get('price'))}</b></div><div><span>QR</span><b data-special-line-qr>Seçilmedi</b></div><div><span>Menü Tasarımı</span><b data-special-line-menu>Seçilmedi</b></div><div><span>Logo Tasarımı</span><b data-special-line-logo>Seçilmedi</b></div></div><div class="special-ready-total"><span>Toplam satış</span><strong data-special-total>{_nfc_money(first_row.get('price'))}</strong><small>Seçilen kapasite + ek hizmetler</small></div><a class="primary-cta" data-special-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket=ozel-kapasite&amp;masa={first}">{first} masa için teklif al</a></div></div>'''



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
    return f'''<div class="nfc-duo-calculator" data-duo-calculator data-qr-unit="{qr_unit}" data-offer-base="{offer_prefix}teklif/"><div class="nfc-duo-selector"><div><p class="eyebrow">DUO CANLI HESAP</p><h3>Stand sayısını seç.</h3><p>Paket plan bedeli güncel Duo tarifesidir. QR açılırsa stand başına 2 QR ayrıca hesaplanır.</p></div><div class="nfc-capacity-stepper"><button type="button" data-duo-prev aria-label="Önceki Duo kapasitesi">−</button><div><small>Stand sayısı</small><strong data-duo-stands-display>{stands}</strong><span data-duo-nfc-display>{nfc} NFC</span></div><button type="button" data-duo-next aria-label="Sonraki Duo kapasitesi">+</button></div><input class="nfc-capacity-range" data-duo-range type="range" min="0" max="{len(ordered)-1}" step="1" value="0" aria-label="Duo stand kapasitesi"><div class="nfc-duo-data" hidden>{''.join(buttons)}</div></div><div class="nfc-duo-live-card"><span class="package-kicker">PREMIUM FEEDBACK DUO</span><div class="special-ready-metrics"><span><b data-duo-live-stands>{stands}</b>Stand</span><span><b data-duo-live-nfc>{nfc}</b>NFC</span><span data-duo-live-qr-metric hidden><b data-duo-live-qr>{nfc}</b>QR</span></div><div class="special-ready-price"><small>Paket plan bedeli</small><strong data-duo-base>{_nfc_money(first.get('price'))}</strong><span data-duo-renewal>Yıllık yenileme: {_nfc_money(first.get('renewal'))}</span></div><button class="nfc-duo-qr-toggle" type="button" data-duo-qr-toggle aria-pressed="false"><span>QR sistemini ekle</span><b data-duo-qr-price>+{_nfc_money(nfc*qr_unit)}</b><small data-duo-qr-copy>{nfc} QR × {_nfc_money(qr_unit)}</small></button><div class="special-ready-breakdown"><div><span>Paket plan bedeli</span><b data-duo-line-base>{_nfc_money(first.get('price'))}</b></div><div data-duo-qr-line hidden><span>QR sistemi</span><b data-duo-line-qr>+{_nfc_money(nfc*qr_unit)}</b></div></div><div class="special-ready-total"><span>Toplam satış</span><strong data-duo-total>{_nfc_money(first.get('price'))}</strong><small>QR seçimi değiştikçe toplam güncellenir.</small></div><a class="primary-cta" data-duo-offer href="{offer_prefix}teklif/?tur=nfc&amp;paket=feedback-duo&amp;masa={stands}">{stands} stand için teklif al ↗</a></div></div>'''

def _nfc_v3167_software_showcase():
    return f'''<section class="section-pad shell nfc-software-showcase" id="yazilim"><div class="split-title"><div><p class="eyebrow">YAZILIM + FİZİKSEL ÜRÜN</p><h2>Standın arkasında sizin yönettiğiniz panel.</h2></div><p>BG Studio NFC yalnızca fiziksel bir stand değildir. NFC ve QR erişimleri dijital deneyim, analitik, feedback ve yönetim araçlarıyla aynı sistemde buluşur.</p></div>{_nfc_v3167_flow()}<div class="nfc-software-grid"><div class="nfc-software-copy"><article><span>01</span><h3>İşletme paneli</h3><p>Kaç kişinin okuttuğunu, menüde neye baktığını ve gelen yorumları tek ekrandan görürsünüz.</p></article><article><span>02</span><h3>Müşteri deneyimi</h3><p>Menünüz çok dilli; alerjen ve kalori bilgisiyle birlikte, misafir telefonunu standa yaklaştırınca açılır.</p></article><article><span>03</span><h3>Raporlar ve bildirimler</h3><p>Hangi masanın ne kadar kullanıldığını ve kaç yorum geldiğini görürsünüz.</p></article><article><span>04</span><h3>Uzaktan yönetim</h3><p>Stand yeniden basılmadan yönlendirdiği linkleri istediğiniz an değiştirirsiniz. Yeni yorum geldiğinde anında haber alırsınız.</p></article></div>{_nfc_v3167_browser_frame()}</div></section>'''



def _nfc_v3201_standard_comparison(pricing, offer_prefix='../'):
    """V3.2.01: data-driven comparison for the three standard restaurant packages."""
    year = str(pricing.get('year') or '2026')
    qr_unit = int(pricing.get('qr_unit') or 0)
    menu_price = int(pricing.get('menu_design') or 0)
    logo_price = int(pricing.get('logo_design') or 0)
    packages = pricing.get('packages') if isinstance(pricing.get('packages'), dict) else {}
    specs = [
        ('baslangic', 'Başlangıç', 10, 30),
        ('profesyonel', 'Profesyonel', 15, 45),
        ('premium', 'Premium', 20, 60),
    ]

    def row_for(code):
        value = packages.get(code)
        return value if isinstance(value, dict) else {}

    def cell(value):
        return esc(str(value))

    plan_headers = []
    price_cells = []
    list_cells = []
    renewal_cells = []
    qr_cells = []
    for code, label, tables, nfc in specs:
        row = row_for(code)
        featured = ' is-featured' if code == 'profesyonel' else ''
        badge = '<span class="nfc-compare-badge">ÖNE ÇIKAN</span>' if code == 'profesyonel' else ''
        plan_headers.append(
            f'<th class="nfc-compare-plan{featured}" scope="col">{badge}'
            f'<small>{tables} MASA · {nfc} NFC</small><strong>{esc(label)}</strong>'
            f'<a href="{offer_prefix}teklif/?tur=nfc&amp;paket={code}">Teklif al ↗</a></th>'
        )
        price_cells.append(f'<td class="{featured.strip()}"><strong>{_nfc_money(row.get("price"))}</strong><small>{year} paket plan bedeli</small></td>')
        list_cells.append(f'<td class="{featured.strip()}">{_nfc_money(row.get("list_price")) if row.get("list_price") else "—"}</td>')
        renewal_cells.append(f'<td class="{featured.strip()}">{_nfc_money(row.get("renewal"))}</td>')
        qr_cells.append(f'<td class="{featured.strip()}"><strong>+{_nfc_money(nfc * qr_unit)}</strong><small>{nfc} QR × {_nfc_money(qr_unit)}</small></td>')

    common = ['<span class="nfc-compare-check">✓</span>'] * 3
    optional = ['<span class="nfc-compare-optional">Opsiyonel</span>'] * 3

    rows = [
        ('Kapasite', [f'<strong>{tables} masa</strong><small>{tables} özel stand</small>' for _,_,tables,_ in specs]),
        ('NFC', [f'<strong>{nfc} NFC</strong><small>Stand başına 3 NFC</small>' for *_,nfc in specs]),
        ('Akıllı Menü + çoklu dil', common),
        ('İşletme müşteri paneli', common),
        ('Masa bazlı raporlar', common),
        ("Önce size, sonra Google'a yorum", common),
        ('Uzaktan hedef yönetimi', common),
        ('Anlık bildirimler', common),
        ('Linkleri uzaktan güncelleme', common),
        ('QR sistemi', qr_cells),
        ('Menü Tasarımı', [f'<span class="nfc-compare-optional">Opsiyonel</span><small>+{_nfc_money(menu_price)}</small>'] * 3),
        ('Logo Tasarımı', [f'<span class="nfc-compare-optional">Opsiyonel</span><small>+{_nfc_money(logo_price)}</small>'] * 3),
        (f'{year} paket plan bedeli', price_cells),
        ('Normal fiyat', list_cells),
        ('Yıllık yenileme', renewal_cells),
    ]

    body = []
    for label, values in rows:
        rendered_values = []
        for value in values:
            if isinstance(value, str) and value.startswith('<td'):
                rendered_values.append(value)
            else:
                rendered_values.append(f'<td>{value}</td>')
        body.append(f'<tr><th scope="row">{esc(label)}</th>{"".join(rendered_values)}</tr>')

    return (
        '<section class="section-pad shell nfc-package-comparison-v3201" id="paket-karsilastirma">'
        '<div class="split-title"><div><p class="eyebrow">PAKET KARŞILAŞTIRMA</p>'
        '<h2>Üç paket. Aynı özellikler. Masa sayınıza göre.</h2></div>'
        '<p>Başlangıç, Profesyonel ve Premium arasındaki ana fark masa, stand ve NFC kapasitesidir. '
        'Ortak dijital altyapı paketlerin tamamında devam eder.</p></div>'
        '<div class="nfc-compare-frame"><div class="nfc-compare-scroll" tabindex="0" aria-label="Standart restoran paket karşılaştırma tablosu">'
        '<table class="nfc-compare-table"><thead><tr><th class="nfc-compare-feature" scope="col">'
        '<span>Özellik</span><small>Standart Restoran</small></th>'
        + ''.join(plan_headers) +
        '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'
        '<div class="nfc-compare-foot"><span>QR, Menü Tasarımı ve Logo Tasarımı ayrı seçimdir.</span>'
        '<a href="' + offer_prefix + 'teklif/?tur=nfc&amp;paket=profesyonel">Paket hesabına geç ↗</a></div></div></section>'
    )



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
    nfc_marquee = render_contextual_business_marquee(
        resolve_nfc_items(),
        'NFC + QR REFERANSLARI',
        'NFC + QR sistemimizi kullanan işletmeler.',
        'BG Studio NFC + QR sistemini kullanan işletmelerden bazıları.',
        prefix='../',
        context='nfc',
    )
    return f'''<!-- NFC_PLATFORM_V167_START -->
<section class="page-hero nfc-platform-hero nfc-hub-hero" data-nfc-hub-v3167="main"><div class="shell nfc-hub-hero-grid"><div class="nfc-hub-hero-copy"><p class="eyebrow">BG STUDIO NFC + QR</p><h1>Fiziksel temas. Dijital deneyim. Tek sistem.</h1><p class="lead">İşletmeler için fiziksel + dijital müşteri etkileşim sistemi. Özel tasarım 3D standları NFC, QR, Akıllı Menü, feedback, analitik ve yönetim altyapısıyla birleştiriyoruz.</p><div class="hero-actions"><a class="primary-cta" href="#sistemler">Sistemleri İncele ↓</a><a class="secondary-cta" href="../teklif/?tur=nfc">Teklif Al ↗</a></div><div class="nfc-hub-proof"><span>İşletmeye özel 3D üretim</span><span>NFC + QR</span><span>Panel + analitik</span><span>Kuşadası merkezli</span></div></div><div class="nfc-hub-hero-visual"><img src="../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC ve QR restoran stand sistemi" width="1254" height="1254" fetchpriority="high" decoding="async"><div class="nfc-hub-hero-badge"><strong>Fiziksel + Dijital</strong><span>Stand → Telefon → Sistem</span></div></div></div></section>
{nfc_marquee}
<section class="section-pad shell nfc-solution-hub" id="sistemler"><div class="split-title"><div><p class="eyebrow">ÇÖZÜM MERKEZİ</p><h2>İşletmene uygun sistemi seç.</h2></div><p>Sistemleri burada kısaca karşılaştırın; paketler ve güncel fiyatlar için ilgili çözüm sayfasına geçin.</p></div><div class="nfc-solution-grid"><article class="nfc-solution-card nfc-solution-card-large {'dark' if restaurant_theme=='dark' else ''}" id="restoran-sistemleri" data-family-key="restaurant_packages" data-family-theme="{restaurant_theme}">{restaurant_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>RESTORAN SİSTEMLERİ</span><b>{year} · {_nfc_money(restaurant.get('price'))}'den</b></div><h3>Masadan dijital deneyime.</h3><p>Akıllı Menü, çoklu dil, 14 alerjen, yaklaşık kalori, feedback, analitik ve Uzaktan yönetim altyapısı.</p><ul><li>Stand başına 3 NFC</li><li>QR opsiyonel</li><li>10–120 masa ölçeklenebilir</li></ul><a class="primary-cta" href="restoran/">Restoran Sistemlerini İncele ↗</a></div></article><article class="nfc-solution-card {'dark' if quick_theme=='dark' else ''}" data-family-key="quick_stand" data-family-theme="{quick_theme}">{quick_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>HIZLI BAĞLANTI</span><b>{_nfc_money(quick.get('price'))}</b></div><h3>Tek stand, üç bağlantı.</h3><p>Instagram, Google, WhatsApp, web veya işletmenin seçtiği farklı hedefleri tek fiziksel noktada birleştir.</p><ul><li>3 NFC / stand</li><li>QR opsiyonel</li><li>Uzaktan hedef yönetimi</li></ul><a class="secondary-cta" href="hizli-baglanti/">Hızlı Standı İncele ↗</a></div></article><article class="nfc-solution-card {'dark' if feedback_theme=='dark' else ''}" data-family-key="feedback_duo" data-family-theme="{feedback_theme}">{feedback_media}<div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>PREMIUM FEEDBACK</span><b>{_nfc_money(duo.get('price'))}'den</b></div><h3>Duo + Trio müşteri deneyimi.</h3><p>Feedback, Google devam akışı, sosyal / iletişim hedefleri ve raporlama odaklı gelişmiş işletme çözümü.</p><ul><li>Duo: 2 NFC / stand</li><li>Trio: 3 NFC / stand</li><li>QR paket dışında opsiyonel</li></ul><a class="secondary-cta" href="feedback/">Duo / Trio Detayları ↗</a></div></article><article class="nfc-solution-card nfc-solution-premium-plus {'dark' if premium_plus_theme=='dark' else 'light'}" data-family-key="premium_plus" data-family-theme="{premium_plus_theme}"><div class="nfc-premium-plus-visual"><span>YAKINDA</span><strong>Premium<br>Plus</strong><small>Geliştiriliyor</small></div><div class="nfc-solution-card-body"><div class="nfc-solution-meta"><span>ÜST KATMAN</span><b>Henüz satışta değil</b></div><h3>CRM, sadakat, rezervasyon ve AI.</h3><p>Doğrudan masa siparişi, misafir profili, sadakat, segmentasyon, rezervasyon ve AI araçları için geliştirilen ayrı üst katman.</p><ul><li>Doğrudan masa siparişi</li><li>Misafir CRM + sadakat</li><li>Rezervasyon + AI araçları</li></ul><a class="ghost-cta" href="premium-plus/">Premium Plus Yol Haritası ↗</a></div></article></div></section>
{_nfc_v3201_standard_comparison(pricing, offer_prefix='../')}
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
    desc = 'BG Studio NFC + QR; restoran sistemleri, Hızlı Bağlantı ve Premium Feedback çözümleriyle fiziksel stand, dijital erişim ve işletme deneyimini birleştirir.'
    html_text = re.sub(r'(<meta\s+content=")[^"]*("\s+name="description"\s*/?>)', lambda m: m.group(1)+desc+m.group(2), html_text, count=1, flags=re.I)
    html_text = re.sub(r'(<title>).*?(</title>)', lambda m: m.group(1)+'Restoran NFC ve QR Menü Standı Sistemleri | BG Studio 3D'+m.group(2), html_text, count=1, flags=re.I|re.S)
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
        cards.append(f'''<article class="nfc-v3167-package-card{' featured' if code == 'profesyonel' else ''}"><div class="package-head"><span class="package-kicker">{tables} MASA · {nfc} NFC</span><span class="package-badge">{esc(label)}</span></div><h3>{esc(label)}</h3><div class="package-price"><small>{year} paket plan bedeli</small><strong>{_nfc_money(row.get('price'))}</strong><span>{('Normal fiyat: ' + normal + ' · ') if normal else ''}Yıllık yenileme: {renewal}</span></div><ul><li>Stand başına 3 NFC</li><li>Akıllı Menü + çoklu dil</li><li>Önce size, sonra Google'a yorum</li><li>Raporlar + yönetim paneli</li><li>Uzaktan hedef yönetimi</li></ul>{_nfc_v3167_option_calculator(code,label,tables,nfc,row.get('price'),qr_unit,menu_price,logo_price)}</article>''')
    return ''.join(cards)


def _nfc_v3167_restaurant_page(nfc_items):
    pricing = active_nfc_pricing()
    refs = ''.join(render_nfc_case(item, '../../') for item in nfc_items[:4])
    content = f'''<section class="nfc-sub-hero"><div class="shell nfc-sub-hero-grid"><div><nav class="nfc-breadcrumb"><a href="../../nfc-qr/">NFC + QR</a><span>/</span><b>Restoran Sistemleri</b></nav><p class="eyebrow">BG STUDIO NFC RESTORAN</p><h1>Masanın üzerindeki standdan işletme paneline.</h1><p class="lead">Restoranlar için NFC + QR erişimi, Akıllı Menü, değerlendirme, analitik ve dijital yönlendirmeleri tek işletme altyapısında birleştiren sistem.</p><div class="hero-actions"><a class="primary-cta" href="#paketler">Paketleri İncele ↓</a><a class="secondary-cta" href="../../teklif/?tur=nfc&amp;paket=baslangic">Teklif Al ↗</a></div></div>{_nfc_v3167_media('restaurant_packages','BG Studio NFC restoran sistemi')}</div></section><nav class="shell nfc-section-nav" aria-label="Restoran sistemi bölümleri"><a href="#nasil-calisir">Nasıl çalışır</a><a href="#stand">Stand</a><a href="#yazilim">Yazılım</a><a href="#paketler">Paketler</a><a href="#kapasite">25–120 masa</a><a href="#saha">Saha</a><a href="#sss">SSS</a></nav><section class="section-pad shell" id="nasil-calisir"><div class="split-title"><div><p class="eyebrow">SİSTEM NEDİR?</p><h2>Fiziksel ürün ve dijital işletme sistemi birlikte çalışır.</h2></div><p>Her stand işletmenin kullanım senaryosuna göre NFC erişim noktaları taşır. QR opsiyonu aynı hedeflere alternatif erişim sunar. Dijital hedefler panel üzerinden yönetilir.</p></div>{_nfc_v3167_flow()}<div class="nfc-feature-matrix"><article><span>NFC</span><h3>Temassız erişim</h3><p>Misafir telefonu ilgili NFC alanına yaklaştırarak menü, değerlendirme veya seçilen hedefe geçer.</p></article><article><span>QR</span><h3>İsteğe bağlı alternatif</h3><p>QR seçilirse restoran sistemlerinde masa başına 3 QR eklenir ve ayrı fiyatlandırılır.</p></article><article><span>MENÜ</span><h3>Akıllı Menü</h3><p>Çoklu dil, ürün içerikleri, 14 alerjen bilgi katmanı ve yaklaşık kalori bilgileri desteklenir.</p></article><article><span>FEEDBACK</span><h3>Müşteri değerlendirmesi</h3><p>İşletme içi değerlendirme akışı, Google devam adımı ve müşteri deneyimi takibi aynı sistemde buluşur.</p></article></div></section><section class="section-pad-sm shell" id="stand"><div class="split-title"><div><p class="eyebrow">STAND</p><h2>İşletmeye özel tasarlanır ve 3D üretilir.</h2></div><p>Logo, QR alanları, uygulama ikonları, NFC temas bölgeleri ve restoran kurulumlarında arka yüz masa numarası işletmeye göre hazırlanır.</p></div><figure class="nfc-v3167-schema zoomable-media" role="button" tabindex="0"><img src="../../assets/images/nfc-stand-semasi.webp" alt="BG Studio NFC restoran stand şeması" loading="lazy" decoding="async"><figcaption>Görseli büyütmek için tıkla veya dokun</figcaption></figure></section>{_nfc_v3167_software_showcase()}<section class="section-pad shell" id="paketler"><div class="split-title"><div><p class="eyebrow">STANDART RESTORAN PAKETLERİ</p><h2>Başlangıçtan Premium'a.</h2></div><p>Uzaktan yönetim tüm Standart Restoran paketlerinde mevcut ortak özelliktir. QR, Menü Tasarımı ve Logo Tasarımı seçimleri ayrı kalemlerdir.</p></div><div class="nfc-v3167-package-grid">{_nfc_v3167_standard_package_cards(pricing)}</div></section>{_nfc_v3201_standard_comparison(pricing, offer_prefix="../../")}<section class="section-pad shell" id="kapasite"><div class="split-title"><div><p class="eyebrow">ÖZEL RESTORAN HAZIR PAKETLERİ</p><h2>25–120 masa için canlı kapasite hesabı.</h2></div><p>Aynı restoran altyapısı kapasiteye göre ölçeklenir. Slider ile masa sayısını değiştir; sağ kartta paket plan bedeli ve seçilen ek hizmetlerle toplam satış güncellensin.</p></div>{_nfc_v3167_capacity_calculator(pricing)}</section><section class="section-pad shell" id="saha"><div class="split-title"><div><p class="eyebrow">SAHADAN</p><h2>Çalışan sistem örnekleri.</h2></div><p>BG Studio NFC sistemlerinin farklı işletmelerdeki fiziksel ve dijital kurulumlarından seçilen örnekler.</p></div><div class="reference-grid">{refs}</div><div class="section-actions"><a class="secondary-cta" href="../../nfc-qr/#sahadan-isler">Tüm NFC saha işlerini gör ↗</a></div></section><section class="section-pad shell" id="sss"><div class="split-title"><div><p class="eyebrow">SSS</p><h2>Restoran sistemi hakkında kısa cevaplar.</h2></div></div><div class="faq"><details><summary>QR zorunlu mu?</summary><p>Hayır. QR opsiyoneldir. Seçilirse masa başına 3 QR eklenir ve QR bedeli paket plan bedelinden ayrı hesaplanır.</p></details><details><summary>Uzaktan yönetim hangi pakette?</summary><p>Başlangıç, Profesyonel, Premium ve 25–120 masa Özel Restoran Hazır Paketlerinde mevcut ortak sistem özelliğidir.</p></details><details><summary>Menü Tasarımı neleri kapsar?</summary><p>Güncel kapsam; Türkçe ve İngilizce görsel menü, 8 ek dilde dijital metin menü, ürün içerikleri, 14 alerjen bilgi katmanı ve yaklaşık kalori bilgileridir.</p></details><details><summary>Stand yeniden basılmadan bağlantı değişebilir mi?</summary><p>Dijital hedefler sistem yapısına göre uzaktan yönetilebilir. Fiziksel ürünün yeniden üretilmesi her bağlantı değişikliğinde gerekmez.</p></details></div><div class="nfc-page-cta"><h3>Restoranın masa sayısını biliyorsan hesabı hazırla.</h3><a class="primary-cta" href="../../teklif/?tur=nfc&amp;paket=baslangic">Restoran için teklif al ↗</a></div></section>'''
    return _nfc_v3167_page('NFC + QR Restoran Sistemleri | BG Studio 3D', 'Restoranlar için NFC + QR, Akıllı Menü, feedback, analitik, panel ve 10–120 masa ölçeklenebilir BG Studio sistemi.', 'restoran', content)


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
    content=f'''<section class="nfc-sub-hero nfc-premium-plus-page-hero theme-{premium_plus_theme}" data-family-key="premium_plus" data-family-theme="{premium_plus_theme}"><div class="shell"><div class="premium-plus-state"><span class="premium-plus-badge">YAKINDA</span><span class="premium-plus-progress">Geliştiriliyor</span><small>Henüz satışta değil</small></div><p class="eyebrow">PREMIUM PLUS</p><h1>Restoran deneyiminin bir sonraki üst katmanı.</h1><p class="lead">Mevcut Akıllı Menü, çoklu dil, ürün içerikleri, 14 alerjen, yaklaşık kalori, Google performansı, müşteri değerlendirme sistemi ve Uzaktan yönetim Standart Restoran paketlerinde devam eder. Premium Plus bunların üzerine yeni CRM, sadakat, rezervasyon ve AI araçları eklemek için geliştiriliyor.</p><div class="hero-actions"><a class="secondary-cta" href="../../nfc-qr/restoran/">Mevcut Restoran Sistemleri ↗</a><span class="primary-cta is-disabled" aria-disabled="true">Premium Plus · Yakında</span></div></div></section><section class="section-pad shell nfc-premium-plus-roadmap theme-{premium_plus_theme}"><div class="split-title"><div><p class="eyebrow">YOL HARİTASI</p><h2>Planlanan Premium Plus modülleri.</h2></div><p>Bu özellikler geliştirme yol haritasıdır. Çıkış tarihi, kesin kapsam ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="nfc-premium-roadmap-grid">{cards}</div><div class="premium-plus-note-group"><p class="premium-plus-note"><strong>Premium Plus mevcut paket özelliklerini yeniden paketlemez.</strong> Uzaktan yönetim tüm Standart Restoran paketlerinin mevcut kapsamındadır. Premium Plus'ın farkı doğrudan masa siparişi, sipariş notları, Misafir CRM, sadakat, VIP tanıma, segmentasyon, rezervasyon / bekleme listesi, AI upsell ve AI yönetici zekâsıdır.</p><p class="premium-plus-release-note">Çıkış tarihi, kesin özellik kapsamı ve fiyatlandırma tamamlandığında BG Studio tarafından duyurulacaktır.</p></div><div class="nfc-page-cta"><h3>Premium Plus gelişmelerini takip et.</h3><a class="secondary-cta" href="../../nfc-qr/">NFC + QR ana sayfasına dön ↗</a></div></section>'''
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
    # v3.3.41 — NFC taraması / menü açılışı / feedback / Google yönlendirmesi yalnızca NFC + QR projelerine ait.
    if _project_kind(item) != 'nfc':
        return []
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
    collection_schema={
        '@context':'https://schema.org','@type':'CollectionPage','@id':BASE_URL+'/projeler/#collection',
        'name':'BG Studio 3D Projeler','description':'BG Studio 3D sahadan işler, kurumsal üretim, NFC + QR ve prototip proje arşivi.',
        'url':BASE_URL+'/projeler/','isPartOf':{'@id':BASE_URL+'/#website'},'publisher':{'@id':BASE_URL+'/#organization'},
        'mainEntity':{'@type':'ItemList','itemListElement':[
            {'@type':'ListItem','position':pos,'name':str(row.get('headline') or row.get('name') or 'BG Studio 3D Projesi'),'url':BASE_URL+'/projeler/'+_project_slug(row)+'/'}
            for pos,row in enumerate(project_items,1)
        ]}
    }
    collection_json=json.dumps(collection_schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json" data-schema="project-collection">{collection_json}</script><section class="project-index-hero"><div class="shell project-index-hero-grid"><div><p class="eyebrow">SAHADAN İŞLER</p><h1>Gerçek ihtiyaçlar.<br>Gerçek teslimler.</h1><p class="lead">Restoranlardan kurumsal üretime, NFC sistemlerinden teknik parçalara kadar tamamlanan BG Studio işlerini tek proje arşivinde incele.</p></div><div class="project-index-stat"><span>Tamamlanan proje</span><strong>{len(project_items)}</strong><small>Panel ve veri tabanlı saha kayıtlarından üretilir.</small></div></div></section><section class="section-pad shell"><div class="project-filterbar" aria-label="Proje filtreleri">{''.join(filters)}<div class="project-result-count"><strong data-project-count>{len(project_items)}</strong> proje gösteriliyor</div></div><div class="project-index-grid" data-project-grid>{''.join(cards)}</div><div class="project-empty" data-project-empty hidden>Bu filtrede yayınlanmış proje bulunmuyor.</div></section><section class="project-index-cta"><div class="shell"><div><p class="eyebrow">SIRADAKİ PROJE</p><h2>Senin işletmen veya parçan olabilir.</h2><p>Kurumsal üretim, özel parça, prototip veya NFC + QR sistemi için kapsamı gönder.</p></div><a class="primary-cta" href="../teklif/" data-project-index-quote>Teklif Al ↗</a></div></section>'''
    return _project_page_shell('Projeler – Kuşadası 3D Baskı ve NFC İşleri | BG Studio 3D','BG Studio 3D proje arşivi: Kuşadası ve çevresinde sahadan işler, kurumsal üretimler, NFC + QR kurulumları ve prototip parça çalışmaları.','/projeler/',body,'../')


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
    media=_project_media(item,'../../','project-detail-media',eager=True)
    kind=_project_kind(item)
    service={'nfc':'../../nfc-qr/','prototype':'../../prototip-parca/','corporate':'../../kurumsal/'}.get(kind,'../../kurumsal/')
    offer={'nfc':'../../teklif/?tur=nfc','prototype':'../../teklif/?tur=prototip','corporate':'../../teklif/?tur=kurumsal'}.get(kind,'../../teklif/')
    same_kind=[x for x in project_items if _project_slug(x)!=slug and _project_kind(x)==kind]
    other_kind=[x for x in project_items if _project_slug(x)!=slug and _project_kind(x)!=kind]
    related=(same_kind+other_kind)[:3]
    related_html=''.join(f'<a class="project-related-card" data-project-related href="../{esc(_project_slug(x))}/">{_project_media(x,"../../","project-related-media")}<span>{esc(_project_kind_label(x))}</span><strong>{esc(x.get("name") or x.get("headline") or "Proje")}</strong></a>' for x in related)
    project_url=BASE_URL+'/projeler/'+slug+'/'
    service_url={'nfc':BASE_URL+'/nfc-qr/','prototype':BASE_URL+'/prototip-parca/','corporate':BASE_URL+'/kurumsal/'}.get(kind,BASE_URL+'/kurumsal/')
    schema={'@context':'https://schema.org','@type':'CreativeWork','@id':project_url+'#project','name':headline,'description':description,'creator':{'@id':BASE_URL+'/#organization'},'publisher':{'@id':BASE_URL+'/#organization'},'url':project_url,'mainEntityOfPage':{'@type':'WebPage','@id':project_url},'isPartOf':{'@id':BASE_URL+'/projeler/#collection'},'about':{'@type':'Service','name':kind_label,'url':service_url}}
    if sector: schema['keywords']=', '.join([sector]+[str(x) for x in (item.get('tags') or [])[:6]])
    if item.get('image'): schema['image']=BASE_URL+'/'+str(item.get('image')).lstrip('/')
    breadcrumb_schema={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Ana Sayfa','item':BASE_URL+'/'},{'@type':'ListItem','position':2,'name':'Projeler','item':BASE_URL+'/projeler/'},{'@type':'ListItem','position':3,'name':name,'item':project_url}]}
    schema_json=json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    breadcrumb_json=json.dumps(breadcrumb_schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json" data-schema="project">{schema_json}</script><script type="application/ld+json" data-schema="breadcrumb">{breadcrumb_json}</script><section class="project-detail-hero" data-project-detail data-project-slug="{esc(slug)}" data-project-kind="{esc(kind)}" data-project-name="{esc(name)}"><div class="shell project-detail-grid"><div class="project-detail-copy"><nav class="project-breadcrumb" aria-label="İçerik yolu"><a href="../../projeler/">Projeler</a><span>/</span><b>{esc(name)}</b></nav><p class="eyebrow">{esc(kind_label)} · {esc(sector)}</p><h1>{esc(headline)}</h1><p class="lead">{esc(description)}</p><div class="hero-actions"><a class="primary-cta" data-project-quote href="{offer}">Benzer proje için teklif al ↗</a><a class="secondary-cta" data-project-service href="{service}">İlgili hizmeti incele ↗</a></div></div>{media}</div></section><section class="project-facts-wrap"><div class="shell project-facts">{facts_html}</div></section><section class="section-pad shell"><div class="project-story-grid">{story_html}</div>{('<div class="project-scope"><p class="eyebrow">UYGULAMA KAPSAMI</p><div class="project-scope-tags">'+tags+'</div></div>') if tags else ''}</section>{metrics_html}<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">BENZER PROJELER</p><h2>Aynı üretim alanından başka işler.</h2></div><a class="ghost-cta" href="../../projeler/">Tüm projeler ↗</a></div><div class="project-related-grid">{related_html}</div></section><section class="project-detail-cta"><div class="shell"><div><p class="eyebrow">BENZER BİR İHTİYAÇ MI VAR?</p><h2>Kapsamı gönder, üretim yolunu netleştirelim.</h2></div><a class="primary-cta" data-project-quote href="{offer}">Teklif Al ↗</a></div></section>'''
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
# V3.3.19 · SERVICE SEO FOUNDATION
# ==============================================================

def _service_schema_v3319(name, service_type, path, description):
    data = {
        '@context': 'https://schema.org',
        '@type': 'Service',
        '@id': f'{BASE_URL}{path}#service',
        'name': name,
        'serviceType': service_type,
        'description': description,
        'url': f'{BASE_URL}{path}',
        'provider': {'@id': BASE_URL + '/#organization'},
        'areaServed': [
            {'@type': 'City', 'name': 'Kuşadası'},
            {'@type': 'AdministrativeArea', 'name': 'Aydın'},
            {'@type': 'Country', 'name': 'Türkiye'},
        ],
    }
    return '<script type="application/ld+json" data-schema="service">' + json.dumps(
        data, ensure_ascii=False, separators=(',', ':')
    ).replace('</', '<\\/') + '</script>'


def _faq_schema_v3319(items):
    data = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': question,
                'acceptedAnswer': {'@type': 'Answer', 'text': answer},
            }
            for question, answer in items
        ],
    }
    return '<script type="application/ld+json" data-schema="faq">' + json.dumps(
        data, ensure_ascii=False, separators=(',', ':')
    ).replace('</', '<\\/') + '</script>'


def _service_pathways_v3319(current):
    rows = [
        ('custom', 'Kişiye Özel Üretim', 'Fotoğraf, ölçü, fikir veya kişiselleştirme üzerinden üretim.', '../ozel-uretim/'),
        ('prototype', 'Prototip & Parça', 'Yedek parça, teknik uyum ve işlev odaklı 3D parça üretimi.', '../prototip-parca/'),
        ('corporate', 'Kurumsal Üretim', 'Markalı, adetli ve işletmeye özel fiziksel üretim.', '../kurumsal/'),
        ('local', 'Kuşadası 3D Baskı', 'Kuşadası ve Aydın için yerel 3D baskı hizmeti.', '../kusadasi-3d-baski/'),
    ]
    cards = []
    for key, title, desc, href in rows:
        if key == current:
            continue
        cards.append(
            f'<article><span>{len(cards)+1:02d}</span><h3>{esc(title)}</h3>'
            f'<p>{esc(desc)}</p><a class="text-cta" href="{esc(href)}">İncele ↗</a></article>'
        )
    return (
        '<section class="section-pad shell"><div class="split-title"><div>'
        '<p class="eyebrow">İLGİLİ ÜRETİM YOLLARI</p><h2>İhtiyaca göre doğru üretim sayfasına geç.</h2>'
        '</div><p>Özel üretim, teknik parça ve kurumsal üretim birbirinden farklı ihtiyaçlara göre ele alınır.</p>'
        f'</div><div class="v3169-about-grid">{"".join(cards)}</div></section>'
    )


def _personalized_examples_v3319(products):
    candidates = [p for p in (products or []) if p.get('active', True) and catalog_personalizable(p)]
    cards = []
    for product in candidates[:3]:
        slug = str(product.get('slug') or '').strip('/')
        name = str(product.get('name') or 'Kişiye özel ürün').strip()
        if not slug:
            continue
        media = (
            '<div class="project-related-media">'
            + render_home_product_picture(product, '../', eager=False, sizes='(max-width:700px) 100vw, 33vw')
            + '</div>'
        )
        cards.append(
            f'<a class="project-related-card" href="../urunler/{esc(slug)}/">{media}'
            f'<span>Kişiselleştirilebilir ürün</span><strong>{esc(name)}</strong></a>'
        )
    if not cards:
        return ''
    return (
        '<section class="section-pad-sm shell" data-service-seo-v3319="examples">'
        '<div class="split-title"><div><p class="eyebrow">GERÇEK ÜRÜN ÖRNEKLERİ</p>'
        '<h2>Kişiselleştirmeye açık ürünlerden örnekler.</h2></div>'
        '<p>İsim, renk veya ölçüye göre kişiselleştirebileceğiniz ürünlerimiz.</p>'
        '</div><div class="project-related-grid">'
        + ''.join(cards)
        + '</div></section>'
    )


def sync_custom_service_seo_v3319(products):
    path = ROOT / 'ozel-uretim/index.html'
    if not path.exists():
        return {'updated': False, 'reason': 'ozel-uretim missing'}
    text = path.read_text(encoding='utf-8')

    service_schema = _service_schema_v3319(
        'Kişiye Özel 3D Baskı Üretimi',
        'Kişiye özel 3D baskı ve özel üretim',
        '/ozel-uretim/',
        'Fotoğraf, ölçü, eskiz, mevcut ürün veya fikir üzerinden kişiye özel 3D baskı ve özel üretim değerlendirmesi.'
    )
    text = re.sub(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>\s*\{.*?\"@type\"\s*:\s*\"Service\".*?</script>",
        service_schema,
        text,
        count=1,
        flags=re.I | re.S,
    )

    wrong = 'Ölçü değişikliği, isim, renk veya uygun tasarımlarda logo gibi kişiselleştirmeler üretim öncesinde birlikte netleştirilir.'
    correct = 'Uygun parçalarda mevcut örnek, fotoğraf ve ölçüler üzerinden yeniden modelleme ve 3D baskı üretilebilirliği değerlendirilebilir. Uyum, yük, sıcaklık ve kullanım koşulları üretim kararını etkiler.'
    text = text.replace(wrong, correct)

    text = re.sub(
        r'<!-- BGSTUDIO:SERVICE_SEO_V3319_START -->.*?<!-- BGSTUDIO:SERVICE_SEO_V3319_END -->',
        '',
        text,
        flags=re.I | re.S,
    )
    insertion = (
        '<!-- BGSTUDIO:SERVICE_SEO_V3319_START -->'
        + _personalized_examples_v3319(products)
        + _service_pathways_v3319('custom')
        + '<!-- BGSTUDIO:SERVICE_SEO_V3319_END -->'
    )
    faq_marker = '<section class="section-pad-sm shell reveal"><div class="split-title"><h2>Sık sorulanlar.</h2>'
    if faq_marker in text:
        text = text.replace(faq_marker, insertion + faq_marker, 1)
    else:
        text = text.replace('</main>', insertion + '</main>', 1)

    path.write_text(text, encoding='utf-8')
    return {
        'updated': True,
        'personalizable_examples': len([p for p in (products or []) if p.get('active', True) and catalog_personalizable(p)][:3]),
    }


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
    # V3.2.01-R1: the Corporate marquee mirrors the exact records already
    # visible in the Corporate case grid. Some NFC-backed field jobs are
    # intentionally published on /kurumsal/ as corporate work, so filtering
    # them out here made the rail collapse to the single native corporate row.
    corporate_marquee_items = list(items or [])
    corporate_marquee = render_contextual_business_marquee(
        corporate_marquee_items,
        'KURUMSAL REFERANSLAR',
        'Kurumsal üretim yaptığımız işletmeler.',
        'Kurumsal üretim yaptığımız işletmelerden bazıları.',
        prefix='../',
        context='corporate',
    )
    body=f'''<section class="v3169-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-sector-cloud"><small>ÇALIŞTIĞIMIZ İHTİYAÇ TİPLERİ</small>{sector_html}</div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">SÜREÇ</p><h2>İhtiyaçtan teslimata.</h2></div><p>Kurumsal işlerde ürün biçimi hazır kalıba göre değil, nasıl kullanılacağına göre netleşir.</p></div><div class="v3169-process"><article><span>01</span><h3>İhtiyaç</h3><p>Adet, kullanım noktası, ölçü ve marka gereksinimini netleştiririz.</p></article><article><span>02</span><h3>Tasarım</h3><p>Ürünü marka kimliği ve üretim koşullarına göre geliştiririz.</p></article><article><span>03</span><h3>Üretim</h3><p>Onaylanan modeli 3D baskı üretime alırız.</p></article><article><span>04</span><h3>Teslim</h3><p>Kontrol, paketleme ve teslim / kargo adımıyla işi tamamlarız.</p></article></div></section><section class="section-pad shell v3169-reference-section"><div class="split-title"><div><p class="eyebrow">SAHADAN KURUMSAL İŞLER</p><h2>Farklı sektörler. Tek üretim disiplini.</h2></div><p>Kurumsal üretim ve NFC kurulumlarından seçili işler. Ayrıntısı olan işlerin proje sayfasına geçebilirsiniz.</p></div><div class="case-grid">{cards}</div></section>{corporate_marquee}<section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">TOPLU ÜRETİM</p><h2>Adedi ve ihtiyacı gönder.</h2><p>Kurumsal anahtarlık, masaüstü ürün, stand veya işletmeye özel parça için kapsamı birlikte netleştirelim.</p></div><a class="primary-cta" href="../teklif/?tur=kurumsal">Toplu sipariş için teklif al ↗</a></div></section>'''
    corp_faq = [
        ('Kurumsal 3D baskıda kaç adet üretim yapılabilir?', 'Adet, ürün geometrisi ve üretim süresine göre değerlendirilir. Tek numuneden küçük ve daha yüksek adetli serilere kadar uygun üretim planı proje kapsamında netleştirilir.'),
        ('Logo veya marka bilgisi ürüne eklenebilir mi?', 'Uygun tasarımlarda logo, marka adı, renk ve benzeri kurumsal detaylar üretim öncesinde tasarıma dahil edilebilir.'),
        ('Toplu üretim öncesi numune yapılabilir mi?', 'Uygun projelerde seri üretim öncesinde tasarım ve kullanım kontrolü için numune veya prototip üretim değerlendirilebilir.'),
    ]
    body = (
        _service_schema_v3319(
            'Kurumsal 3D Baskı ve Toplu Üretim',
            'Kurumsal 3D baskı, markalı ürün ve toplu üretim',
            '/kurumsal/',
            'İşletmelere özel markalı ürün, promosyon, masaüstü çözüm, küçük seri ve toplu 3D baskı üretimi.'
        )
        + _faq_schema_v3319(corp_faq)
        + body
        + '<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">KURUMSAL 3D BASKI</p><h2>Numuneden adetli üretime.</h2></div><p>Kurumsal üretimde adet, marka uygulaması, kullanım noktası ve tekrar üretilebilirlik birlikte değerlendirilir. Kuşadası merkezli üretim altyapısıyla Aydın çevresi ve Türkiye geneli talepler ele alınır.</p></div></section>'
        + '<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">SIK SORULANLAR</p><h2>Kurumsal üretim hakkında.</h2></div></div><div class="faq">'
        + ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q,a in corp_faq)
        + '</div></section>'
        + _service_pathways_v3319('corporate')
    )
    return _editorial_page_shell('Kurumsal 3D Üretim | BG Studio 3D','İşletmelere özel kurumsal 3D baskı, promosyon, masaüstü ürün ve saha üretimleri. Kuşadası BG Studio 3D.','/kurumsal/',body,'corporate')


def render_prototype_page_v3169(items):
    page_copy = read_site_content_v3175()['prototype']
    # V3.1.78: prototype cards must resolve the same prefixed project slug that
    # collect_project_items/build_project_pages uses. Without this marker the
    # card linked to /projeler/<slug>/ while the detail page was generated as
    # /projeler/prototip-<slug>/, producing a 404.
    prototype_cards = [{**item, '_project_kind': 'prototype'} for item in items]
    cards=''.join(render_managed_case(item, '../') for item in prototype_cards)
    body=f'''<section class="v3169-hero v3169-tech-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-tech-flow"><span>SORUN</span><i>↓</i><span>MODEL / CAD</span><i>↓</i><span>3D BASKI</span><i>↓</i><span>ÇALIŞAN PARÇA</span></div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">TEKNİK AKIŞ</p><h2>Ölçü. Model. Test. Üretim.</h2></div><p>Parçanın görevi, temas ettiği yüzeyler ve tolerans ihtiyacı üretim kararını belirler.</p></div><div class="v3169-process"><article><span>01</span><h3>İnceleme</h3><p>Mevcut parça, ölçü, fotoğraf veya teknik dosya üzerinden ihtiyaç belirlenir.</p></article><article><span>02</span><h3>Model</h3><p>Gerekirse model revize edilir veya üretime uygun geometri hazırlanır.</p></article><article><span>03</span><h3>3D Baskı</h3><p>Parçanın kullanımına uygun baskı yönü, malzeme ve üretim ayarları seçilir.</p></article><article><span>04</span><h3>Kontrol</h3><p>Uyum ve kullanım amacı kontrol edilerek teslim edilir.</p></article></div></section><section class="section-pad shell v3169-reference-section"><div class="split-title"><div><p class="eyebrow">TEKNİK ÖRNEKLER</p><h2>Çalışan çözümler.</h2></div><p>Ürettiğimiz prototip ve yedek parça işlerinden örnekler.</p></div><div class="case-grid">{cards}</div></section><section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">DOSYAN HAZIR MI?</p><h2>STL, 3MF, STEP, PDF veya görselle başlayabiliriz.</h2><p>Ölçü ve kullanım bilgisini ekle. Üretim yolunu birlikte netleştirelim.</p></div><a class="primary-cta" href="../teklif/?tur=prototip">Teknik üretim teklifi al ↗</a></div></section>'''
    proto_faq = [
        ('3D model olmadan parça üretimi yapılabilir mi?', 'Uygun parçalarda fotoğraf, mevcut örnek, ölçü veya teknik çizim üzerinden modelleme ve üretilebilirlik değerlendirmesi yapılabilir.'),
        ('Kırık veya bulunamayan yedek parça yeniden üretilebilir mi?', 'Geometri ölçülebiliyor ve kullanım koşulları 3D baskıya uygunsa yeniden üretim değerlendirilebilir. Yük, sıcaklık, tolerans ve bağlantı biçimi ayrıca kontrol edilir.'),
        ('STL, 3MF veya STEP dosyam varsa kullanabilir misiniz?', 'Dosya üretime uygunluk açısından kontrol edilir. Gerekirse baskı yönü, tolerans veya geometri için revizyon ihtiyacı değerlendirilir.'),
    ]
    body = (
        _service_schema_v3319(
            'Prototip ve 3D Parça Üretimi',
            'Prototip, yedek parça ve teknik 3D parça üretimi',
            '/prototip-parca/',
            'Kırık, bulunamayan veya geliştirilmesi gereken parçalar için prototip, yedek parça ve teknik 3D baskı üretimi.'
        )
        + _faq_schema_v3319(proto_faq)
        + body
        + '<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">3D PARÇA ÜRETİMİ</p><h2>Yedek parça, prototip ve teknik uyum.</h2></div><p>Buradaki odak dekoratif görünümden önce işlevdir. Ölçü, bağlantı noktaları, tolerans, kullanım yükü ve ortam koşulları parçanın üretilebilirliğini belirler.</p></div></section>'
        + '<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">SIK SORULANLAR</p><h2>Prototip ve parça üretimi hakkında.</h2></div></div><div class="faq">'
        + ''.join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q,a in proto_faq)
        + '</div></section>'
        + _service_pathways_v3319('prototype')
    )
    return _editorial_page_shell('Prototip ve Parça Üretimi | BG Studio 3D','Prototip, yedek parça ve teknik 3D baskı üretimi. Model, ölçü ve kullanım ihtiyacına göre Kuşadası BG Studio 3D.','/prototip-parca/',body,'prototype')


MAKET_FAQ_V3373 = [('Maket ne kadar sürede hazır olur?', 'Süre, maketin boyutuna, ölçeğine ve parça sayısına göre değişir. Dosyanızı gördükten sonra net bir teslim tarihi veririz; jüri veya sunum tarihiniz varsa ona göre planlarız.'), ('Fiyat nasıl belirleniyor?', 'Fiyatı malzeme miktarı, baskı süresi ve montaj işçiliği belirler. STL Stüdyo’da dosyanızın tahmini malzeme miktarını görebilir, kesin fiyat için bize WhatsApp’tan ulaşabilirsiniz.'), ('Maketler hangi renkte basılıyor?', 'Mimari maketlerde en çok mat beyaz ve açık gri tercih edilir. Peyzaj, cam veya vurgu yüzeyleri için farklı renkler de kullanılabilir.'), ('Büyük bir projeyi tek parça basabilir misiniz?', 'Yazıcının baskı alanından büyük maketleri parçalara böler, baskıdan sonra birleştiririz. Birleşim çizgilerini maketin kurgusuna uygun yerlere yerleştiririz.'), ('Dosyam baskıya hazır değilse ne olur?', 'Açık yüzeyler, çok ince duvarlar veya baskıda kırılabilecek detaylar varsa dosyayı birlikte düzenler, baskıya uygun hale getiririz.')]
MAKET_BODY_V3373 = '<section class="maket-hero">\n  <div class="shell maket-hero-grid">\n    <div>\n      <p class="eyebrow">MİMARİ MAKET 3D BASKI</p>\n      <h1>Projeniz masada, ölçeğinde.</h1>\n      <p class="lead">Bir mimarın kurduğu stüdyoda, dosyanızdan kütle, cephe ve vaziyet maketleri basıyoruz. Jüri, müşteri sunumu ve satış ofisi için; Kuşadası’ndan Ege’nin her yerine.</p>\n      <div class="hero-actions"><a class="primary-cta" href="../teklif/#stl-studyo">Dosyanı yükle, ölçüsünü gör ↗</a><a class="secondary-cta" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20mimari%20maket%20i%C3%A7in%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp’tan sor ↗</a></div>\n      <div class="maket-trust"><span>Mimar kurucu</span><span>STL · 3MF · OBJ</span><span>Kuşadası elden teslim</span></div>\n    </div>\n    <div class="maket-stage" aria-hidden="true">\n      <svg viewBox="0 0 440 440">\n        <g class="mk-grid"><line x1="40" y1="300" x2="220" y2="404"/><line x1="220" y1="404" x2="400" y2="300"/><line x1="80" y1="277" x2="260" y2="381"/><line x1="120" y1="254" x2="300" y2="358"/><line x1="160" y1="231" x2="340" y2="335"/><line x1="200" y1="208" x2="380" y2="312"/></g>\n        <path class="mk-base" d="M40 300 220 404 400 300v14L220 418 40 314z"/>\n        <path class="mk-base-top" d="M40 300 220 196 400 300 220 404z"/>\n        <g class="mk-block mk-b1"><path class="l" d="M110 280 150 303v-60l-40-23z"/><path class="r" d="M150 303 200 274v-60l-50 29z"/><path class="t" d="M110 220 160 191l40 23-50 29z"/></g>\n        <g class="mk-block mk-b2"><path class="l" d="M190 250 230 273V143l-40-23z"/><path class="r" d="M230 273 270 250V120l-40 23z"/><path class="t" d="M190 120 230 97l40 23-40 23z"/><path class="mk-win" d="M236 150h4v100h-4zM248 143h4v100h-4zM260 136h4v100h-4z"/></g>\n        <g class="mk-block mk-b3"><path class="l" d="M262 300 302 323v-46l-40-23z"/><path class="r" d="M302 323 352 294v-46l-50 29z"/><path class="t" d="M262 254 312 225l40 23-50 29z"/></g>\n        <g class="mk-block mk-b4"><path class="l" d="M150 340 180 357v-30l-30-17z"/><path class="r" d="M180 357 214 337v-30l-34 20z"/><path class="t" d="M150 310 184 290l30 17-34 20z"/></g>\n        <g class="mk-block mk-b5"><circle class="mk-tree" cx="320" cy="350" r="9"/><circle class="mk-tree" cx="340" cy="338" r="7"/><circle class="mk-tree" cx="96" cy="320" r="8"/></g>\n        <g class="mk-head" transform="translate(220 60)"><rect x="-12" y="-14" width="24" height="14" rx="4"/><path d="M-4 0h8l-4 6z"/></g>\n        <path class="mk-scale" d="M54 360h70M54 354v12M124 354v12"/>\n        <text class="mk-label" x="54" y="384">1:200</text>\n      </svg>\n    </div>\n  </div>\n</section>\n\n<section class="section-pad shell">\n  <div class="split-title"><div><p class="eyebrow">NELER BASIYORUZ?</p><h2>Konseptten sunum maketine.</h2></div><p>Tasarımın hangi aşamasındaysanız, anlatmak istediğiniz şeye uygun maketi birlikte seçeriz. Maket, mimari çizimin dilini bilen biri tarafından hazırlanır.</p></div>\n  <div class="capability-grid">\n    <article class="cap-card"><span class="cap-no">01</span><h3>Kütle maketi</h3><p>Yapının hacmini, yüksekliğini ve çevresiyle ilişkisini ilk bakışta anlatan sade maket.</p></article>\n    <article class="cap-card"><span class="cap-no">02</span><h3>Cephe ve detay</h3><p>Pencere, saçak ve doku gibi cephe kararlarını gösteren daha ayrıntılı ölçekler.</p></article>\n    <article class="cap-card"><span class="cap-no">03</span><h3>Vaziyet ve topoğrafya</h3><p>Arazi eğimi, yollar ve komşu yapılarla birlikte projenin yerleşimi.</p></article>\n    <article class="cap-card"><span class="cap-no">04</span><h3>İç mekân kesiti</h3><p>Plan ve kesit kararlarını açan, içine bakılabilen kesitli maket.</p></article>\n    <article class="cap-card"><span class="cap-no">05</span><h3>Peyzaj ve çevre</h3><p>Ağaç, bitki ve dış mekân öğeleriyle projeyi yaşayan bir sahneye dönüştüren parçalar.</p></article>\n    <article class="cap-card"><span class="cap-no">06</span><h3>Sunum tabanı</h3><p>Proje adı ve künyesiyle birlikte maketi taşıyan, ölçüye özel üretilmiş taban.</p></article>\n  </div>\n</section>\n\n<section class="section-pad-sm shell">\n  <div class="split-title"><div><p class="eyebrow">ÖLÇEK</p><h2>Doğru ölçek, doğru anlatım.</h2></div><p>Ölçeği maketin nerede ve kime gösterileceğine göre birlikte belirleriz. Büyük maketler parçalara bölünerek basılır ve birleştirilir.</p></div>\n  <div class="maket-scales">\n    <div class="maket-scale"><b>1:500</b><strong>Vaziyet</strong><p>Parsel, yollar ve çevre yapılarla genel yerleşim.</p><span class="bar" style="width:30%"></span></div>\n    <div class="maket-scale"><b>1:200</b><strong>Kütle</strong><p>Hacim, kat sayısı ve yapı grupları arasındaki ilişki.</p><span class="bar" style="width:52%"></span></div>\n    <div class="maket-scale"><b>1:100</b><strong>Cephe</strong><p>Pencere düzeni, saçaklar ve cephe ritmi.</p><span class="bar" style="width:76%"></span></div>\n    <div class="maket-scale"><b>1:50</b><strong>İç mekân</strong><p>Kesitler, iç mekân kurgusu ve detay kararları.</p><span class="bar" style="width:100%"></span></div>\n  </div>\n</section>\n\n<section class="section-pad-sm shell">\n  <div class="maket-architect">\n    <span class="mono"><img src="../assets/brand/bgstudio3d-monogram.webp" alt="" width="128" height="128"></span>\n    <div><p class="eyebrow">BİR MİMARIN STÜDYOSU</p><h2>Maketi, projeyi okuyabilen biri hazırlar.</h2><p>BG Studio, Mimar Berkant Gökbel tarafından kuruldu. Ölçek, kesit ve cephe kararlarının maket üzerinde nasıl okunacağını mimari çizimin dilinden biliyoruz; dosyanız baskıya hazır değilse birlikte hazırlarız. Mimarlık ve 3D görselleştirme çalışmalarımız için <a href="https://bgstudio.com.tr" rel="noopener" target="_blank">bgstudio.com.tr</a>.</p></div>\n  </div>\n</section>\n\n<section class="section-pad-sm shell">\n  <div class="split-title"><div><p class="eyebrow">DOSYA</p><h2>Elinizdeki dosyayla başlayın.</h2></div><p>SketchUp, Rhino, Revit veya ArchiCAD’den dışa aktardığınız dosya yeterli. Dosyanızı STL Stüdyo’ya bırakarak ölçüsünü ve tahmini malzeme miktarını hemen görebilirsiniz.</p></div>\n  <div class="maket-files"><span>STL <small>en yaygın</small></span><span>3MF <small>Bambu / Prusa</small></span><span>OBJ</span><span>SKP · 3DM · RVT <small>dışa aktarımla</small></span></div>\n  <div class="flow-grid" style="margin-top:28px">\n    <article class="flow-card"><span>01</span><h3>Gönder</h3><p>Dosyanızı ve maketin kullanılacağı yeri paylaşın.</p></article>\n    <article class="flow-card"><span>02</span><h3>Netleştir</h3><p>Ölçek, parçalama ve renk kararlarını birlikte veririz.</p></article>\n    <article class="flow-card"><span>03</span><h3>Üret</h3><p>Maket katman katman basılır, parçalar temizlenir.</p></article>\n    <article class="flow-card"><span>04</span><h3>Teslim</h3><p>Birleştirilmiş maket elden ya da kargoyla teslim edilir.</p></article>\n  </div>\n</section>\n\n<section class="section-pad-sm shell">\n  <div class="split-title"><div><p class="eyebrow">SIK SORULANLAR</p><h2>Mimari maket hakkında.</h2></div></div>\n  <div class="faq">\n    <details><summary>Maket ne kadar sürede hazır olur?</summary><p>Süre, maketin boyutuna, ölçeğine ve parça sayısına göre değişir. Dosyanızı gördükten sonra net bir teslim tarihi veririz; jüri veya sunum tarihiniz varsa ona göre planlarız.</p></details>\n    <details><summary>Fiyat nasıl belirleniyor?</summary><p>Fiyatı malzeme miktarı, baskı süresi ve montaj işçiliği belirler. STL Stüdyo’da dosyanızın tahmini malzeme miktarını görebilir, kesin fiyat için bize WhatsApp’tan ulaşabilirsiniz.</p></details>\n    <details><summary>Maketler hangi renkte basılıyor?</summary><p>Mimari maketlerde en çok mat beyaz ve açık gri tercih edilir. Peyzaj, cam veya vurgu yüzeyleri için farklı renkler de kullanılabilir.</p></details>\n    <details><summary>Büyük bir projeyi tek parça basabilir misiniz?</summary><p>Yazıcının baskı alanından büyük maketleri parçalara böler, baskıdan sonra birleştiririz. Birleşim çizgilerini maketin kurgusuna uygun yerlere yerleştiririz.</p></details>\n    <details><summary>Dosyam baskıya hazır değilse ne olur?</summary><p>Açık yüzeyler, çok ince duvarlar veya baskıda kırılabilecek detaylar varsa dosyayı birlikte düzenler, baskıya uygun hale getiririz.</p></details>\n  </div>\n</section>\n\n<section class="section-pad-sm shell">\n  <div class="maket-final"><h2>Projenizi masaya koyalım.</h2><div class="hero-actions"><a class="primary-cta" href="../teklif/#stl-studyo">Dosyanı yükle ↗</a><a class="secondary-cta" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20mimari%20maket%20i%C3%A7in%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp’tan yaz ↗</a></div></div>\n</section>'


def render_maket_page_v3373():
    service = {
        '@context': 'https://schema.org', '@type': 'Service',
        'name': 'Mimari Maket 3D Baskı', 'serviceType': 'Mimari maket üretimi',
        'description': 'STL, 3MF veya OBJ dosyasından kütle, cephe, vaziyet ve iç mekân maketlerinin 3D baskı ile üretimi.',
        'provider': {'@id': BASE_URL + '/#organization'},
        'areaServed': [{'@type': 'City', 'name': c} for c in ('Kuşadası', 'İzmir', 'Aydın', 'Bodrum', 'Didim', 'Söke', 'Selçuk')] + [{'@type': 'Country', 'name': 'Türkiye'}],
        'url': BASE_URL + '/mimari-maket-3d-baski/',
    }
    schema = '<script type="application/ld+json" data-schema="service">' + json.dumps(service, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '</script>'
    body = '<div class="maket-page">' + MAKET_BODY_V3373 + '</div>' + _faq_schema_v3319(MAKET_FAQ_V3373) + schema
    return _editorial_page_shell('Mimari Maket 3D Baskı – Kuşadası, İzmir, Aydın | BG Studio 3D',
        'Mimari maket 3D baskı: STL, 3MF veya OBJ dosyanızdan kütle, cephe, vaziyet ve iç mekân maketleri. Mimar kurucu, Kuşadası merkezli, Ege geneline teslim.',
        '/mimari-maket-3d-baski/', body, 'maket')


def render_about_page_v3169():
    page_copy = read_site_content_v3175()['about']
    body=f'''<section class="v3169-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p><div class="hero-actions"><a class="primary-cta" href="{esc(page_copy["primary_url"])}">{esc(page_copy["primary_label"])}</a><a class="secondary-cta" href="{esc(page_copy["secondary_url"])}">{esc(page_copy["secondary_label"])}</a></div></div><div class="v3169-brand-panel"><span>TASARIM</span><span>3D ÜRETİM</span><span>PROTOTİP</span><span>İŞLETME SİSTEMLERİ</span></div></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">YAKLAŞIM</p><h2>Önce kullanım. Sonra biçim.</h2></div><p>Ürünün nasıl görüneceği kadar nerede, kim tarafından ve hangi üretim koşullarında kullanılacağı da tasarım kararının parçasıdır.</p></div><div class="v3169-about-grid"><article><span>01</span><h3>BG Studio nedir?</h3><p>Fiziksel ürün ve işletme çözümlerini tasarım, 3D üretim ve dijital sistemlerle bir araya getiren bağımsız üretim markası.</p></article><article><span>02</span><h3>Tasarım yaklaşımı</h3><p>Gereksiz form yerine işlev, temiz detay, üretilebilirlik ve marka bütünlüğüne odaklanırız.</p></article><article><span>03</span><h3>Üretim süreci</h3><p>Model, baskı hazırlığı, üretim, kontrol, paketleme ve teslim adımlarını tek akışta yürütürüz.</p></article><article><span>04</span><h3>Atölye mantığı</h3><p>Tek seferlik özel işten tekrar üretilecek kurumsal parçaya kadar ölçeklenebilen çalışma biçimi.</p></article></div></section><section class="section-pad shell"><div class="split-title"><div><p class="eyebrow">ÜRETİM HATTI</p><h2>Modelden teslimata.</h2></div></div><div class="v3169-process"><article><span>01</span><h3>Model</h3><p>Ürün veya parçanın dijital modeli hazırlanır ya da mevcut dosya kontrol edilir.</p></article><article><span>02</span><h3>Baskı hazırlığı</h3><p>Yön, destek, malzeme, renk ve üretim parametreleri belirlenir.</p></article><article><span>03</span><h3>Üretim</h3><p>3D yazıcıda üretim alınır ve parça kontrol edilir.</p></article><article><span>04</span><h3>Paketleme & teslim</h3><p>Kuşadası elden teslim veya Türkiye geneli kargoyla gönderilir.</p></article></div></section><section class="v3169-architecture arch-showcase-v3353" aria-labelledby="arch-showcase-title"><div class="shell arch-showcase-grid"><div class="arch-copy"><p class="eyebrow">DİĞER İŞ KOLU</p><h2 id="arch-showcase-title">BG Studio Architecture</h2><p>Mimarlık, 3D görselleştirme ve proje çalışmalarımız ayrı marka kolunda devam eder.</p><a class="arch-link" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span class="arch-link-domain">bgstudio.com.tr</span><span class="arch-link-arrow"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 17 17 7M9 7h8v8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="sr-only"> Architecture sitesine geç</span></a></div><div class="arch-browser"><span class="arch-browser-bar" aria-hidden="true"><i></i><i></i><i></i><span>bgstudio.com.tr</span></span><span class="arch-browser-view"><iframe data-arch-frame src="https://bgstudio.com.tr" title="BG Studio Architecture giriş sayfası önizlemesi" loading="lazy" tabindex="-1" scrolling="no"></iframe></span><a class="arch-browser-hit" href="https://bgstudio.com.tr" rel="noopener" target="_blank" aria-label="BG Studio Architecture sitesini yeni sekmede aç"></a></div></div></section>'''
    return _editorial_page_shell('Hakkımızda – Kuşadası 3D Baskı Stüdyosu | BG Studio 3D','BG Studio 3D; Kuşadası merkezli 3D baskı, özel üretim, prototip, kurumsal ürün ve NFC + QR işletme sistemleri stüdyosu.','/hakkimizda/',body,'about')


def render_contact_page_v3169():
    page_copy = read_site_content_v3175()['contact']
    body=f'''<section class="v3169-hero v3169-contact-hero"><div class="shell v3169-hero-grid"><div><p class="eyebrow">{esc(page_copy["hero_eyebrow"])}</p><h1>{esc(page_copy["hero_title"])}</h1><p class="lead">{esc(page_copy["hero_lead"])}</p></div><div class="v3169-contact-primary"><a href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><small>EN HIZLI İLETİŞİM</small><strong>WhatsApp</strong><span>Mesaj gönder ↗</span></a><a href="https://instagram.com/bgstudio.3dtr" rel="noopener" target="_blank"><small>SOSYAL MEDYA</small><strong>@bgstudio.3dtr</strong><span>Instagram'a git ↗</span></a></div></div></section><section class="section-pad shell"><div class="v3169-contact-grid"><article><span>01</span><h2>Kuşadası</h2><p>BG Studio 3D üretim ve elden teslim süreci Kuşadası merkezlidir.</p></article><article><span>02</span><h2>Elden teslim</h2><p>Uygun siparişlerde Kuşadası elden teslim seçeneği bulunur.</p></article><article><span>03</span><h2>Türkiye geneli kargo</h2><p>Gönderime uygun ürün ve üretimler Türkiye geneline kargolanır.</p></article><article><span>04</span><h2>Teklif</h2><p>Özel üretim ve işletme projelerinde kapsamı form üzerinden düzenli şekilde iletebilirsin.</p><a class="text-cta" href="../teklif/">Teklif formuna geç ↗</a></article></div></section><section class="v3169-dark-cta"><div class="shell"><div><p class="eyebrow">İLK MESAJDA</p><h2>İşi hızlı netleştirelim.</h2><p>Ürün / parça türü, adet, yaklaşık ölçü, renk ve varsa görsel veya dosya bilgisini paylaşman teklif sürecini hızlandırır.</p></div><a class="primary-cta" href="../teklif/">Teklif talebi gönder ↗</a></div></section>'''
    return _editorial_page_shell('İletişim – Kuşadası 3D Baskı ve Özel Üretim | BG Studio 3D','BG Studio 3D iletişim. Kuşadası elden teslim, Türkiye geneli kargo, WhatsApp ve Instagram üzerinden 3D baskı ve özel üretim talepleri.','/iletisim/',body,'contact')

# ==============================================================
# V3.1.70 + V3.1.72 COMBINED FINAL EXPERIENCE
# Scenario quote center + SEO/performance/mobile/a11y/footer/legal pass.
# ==============================================================

def render_global_footer(prefix=''):
    return f'''<footer class="footer footer-dark footer-v3202">
<div class="shell footer-v3202-shell">
  <section class="footer-v3202-cta" aria-labelledby="footer-v3202-title">
    <div>
      <p class="eyebrow">BİR FİKRİN Mİ VAR?</p>
      <h2 id="footer-v3202-title">Fikri konuşalım.<br>Üretime dönüştürelim.</h2>
    </div>
    <div class="footer-v3202-cta-actions">
      <a class="footer-v3202-primary" href="{prefix}teklif/">Teklif Al <span aria-hidden="true">↗</span></a>
      <a class="footer-v3202-secondary" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D" rel="noopener" target="_blank">WhatsApp <span aria-hidden="true">↗</span></a>
    </div>
  </section>
  <div class="footer-v3202-divider"></div>
  <section class="footer-v3202-brandline" aria-label="BG Studio 3D">
    <div class="footer-v3202-brandcopy">
      <a class="brand footer-brand" href="{prefix}" aria-label="BG Studio 3D ana sayfa">
        <span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span>
      </a>
      <p>Kuşadası merkezli 3D baskı, özel üretim, prototip, kurumsal üretim ve NFC + QR işletme sistemleri.</p>
    </div>
    <div class="footer-v3202-location"><span class="footer-v3202-live-dot" aria-hidden="true"></span><div><small>ÜRETİM MERKEZİ</small><strong>Kuşadası, Aydın</strong></div></div>
  </section>
  <div class="footer-v3202-grid" aria-label="Alt site haritası">
    <nav aria-label="Ürünler"><strong>ÜRÜNLER</strong><a href="{prefix}urunler/">Tüm Ürünler</a><a href="{prefix}urunler/?sirala=newest">Yeni Ürünler</a><a href="{prefix}urunler/?one-cikan=1">Öne Çıkanlar</a></nav>
    <nav aria-label="Üretim"><strong>ÜRETİM</strong><a href="{prefix}ozel-uretim/">Özel Üretim</a><a href="{prefix}prototip-parca/">Prototip &amp; Parça</a><a href="{prefix}kurumsal/">Kurumsal Üretim</a><a href="{prefix}kusadasi-3d-baski/">Kuşadası 3D Baskı</a></nav>
    <nav aria-label="İşletmeler"><strong>İŞLETMELER</strong><a href="{prefix}nfc-qr/">NFC + QR Sistemleri</a><a href="{prefix}nfc-qr/restoran/">Restoran Sistemleri</a><a href="{prefix}nfc-qr/hizli-baglanti/">Hızlı Bağlantı</a><a href="{prefix}nfc-qr/feedback/">Değerlendirme Standları</a></nav>
    <nav aria-label="BG Studio"><strong>BG STUDIO</strong><a href="{prefix}projeler/">Projeler</a><a href="{prefix}hakkimizda/">Hakkımızda</a><a href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture ↗</a><a href="{prefix}iletisim/">İletişim</a></nav>
    <nav aria-label="Destek"><strong>DESTEK</strong><a href="{prefix}siparis-bilgilendirme/">Sipariş Bilgilendirme</a><a href="{prefix}teslimat-iade/">Teslimat / İade</a><a href="{prefix}kisiye-ozel-urun-kosullari/">Kişiye Özel Ürün Koşulları</a><a href="{prefix}gizlilik/">Gizlilik</a><a href="{prefix}kvkk/">KVKK</a></nav>
  </div>
  <div class="footer-v3202-socialrow">
    <div class="footer-v3202-socials" aria-label="Sosyal medya bağlantıları"><a href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank">Instagram <span>↗</span></a><a href="https://www.facebook.com/bgstudio.3dtr" rel="me noopener" target="_blank">Facebook <span>↗</span></a><a href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D" rel="noopener" target="_blank">WhatsApp <span>↗</span></a></div>
    <button class="footer-consent-button footer-v3202-consent" type="button">Çerez tercihleri</button>
  </div>
  <div class="footer-v3202-wordmark" aria-hidden="true"><span>BG STUDIO</span><strong>3D</strong></div>
  <div class="footer-v3202-bottom"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır.</p><p>Türkiye geneli kargo · Kuşadası elden teslim</p><p>BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div>
</div>
</footer>'''


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


STL_STUDIO_HTML_V3357 = '''<section class="stl-studio" id="stl-studyo" data-stl-studio aria-labelledby="stl-studio-title"><div class="shell stl-studio-grid">
<div class="stl-studio-copy"><p class="eyebrow">STL STÜDYO</p><h2 id="stl-studio-title">Dosyanı bırak, modelini hemen gör.</h2><p>STL, 3MF ya da OBJ dosyanı yükle; ölçüsünü, tahmini malzeme miktarını ve baskı süresini anında hesaplayalım. Dosyan cihazından çıkmaz, inceleme tamamen tarayıcında yapılır.</p>
<ul class="stl-studio-points"><li>Parmakla ya da fareyle döndür, yakınlaştır</li><li>PLA veya PETG için tahmini gram</li><li>Bilgiler hazır, tek dokunuşla WhatsApp teklifi</li></ul></div>
<div class="stl-studio-stage">
<div class="stl-drop" data-stl-drop role="button" tabindex="0" aria-label="STL veya 3MF dosyası seç veya buraya bırak"><input type="file" accept=".stl,.3mf,.obj" data-stl-input hidden><span class="stl-drop-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/></svg></span><strong>STL, 3MF veya OBJ dosyanı buraya bırak</strong><small>ya da dokunup seç · en fazla 60 MB</small></div>
<div class="stl-viewer" data-stl-viewer aria-label="3D model önizlemesi"></div>
<p class="stl-status" data-stl-status role="status" aria-live="polite"></p>
</div>
<div class="stl-result" data-stl-result hidden>
<div class="stl-result-head"><strong data-stl-name></strong><button type="button" class="stl-reset" data-stl-reset>Başka dosya</button></div>
<dl class="stl-metrics"><div><dt>Ölçü</dt><dd data-stl-size></dd></div><div><dt>Hacim</dt><dd data-stl-volume></dd></div><div><dt>Tahmini malzeme</dt><dd data-stl-weight></dd></div><div><dt>Tahmini baskı süresi</dt><dd data-stl-time></dd></div></dl>
<p class="stl-fit" data-stl-fit></p>
<div class="stl-controls"><div class="stl-material" role="group" aria-label="Malzeme"><button type="button" data-stl-material="PLA" aria-pressed="true">PLA</button><button type="button" data-stl-material="PETG" aria-pressed="false">PETG</button></div>
<label class="stl-field">Adet<input type="number" min="1" max="9999" value="1" inputmode="numeric" data-stl-qty></label>
<label class="stl-field">Birim<select data-stl-unit><option value="1">mm</option><option value="10">cm</option><option value="25.4">inç</option></select></label></div>
<a class="primary-cta stl-whatsapp" data-stl-whatsapp href="https://wa.me/905302466903" rel="noopener" target="_blank">WhatsApp’tan teklif iste ↗</a>
<p class="stl-note">Değerler tahminidir; kesin fiyat ve süreyi dosyana bakıp birkaç saat içinde iletiriz.</p>
</div></div></section>'''


def render_quote_center_v3170():
    pricing = active_nfc_pricing()
    package_options, duo_options, year = _quote_package_options(pricing)
    qr = _nfc_money(pricing.get('qr_unit'))
    menu = _nfc_money(pricing.get('menu_design'))
    logo = _nfc_money(pricing.get('logo_design'))
    desc = 'Özel üretim, kurumsal çalışma, prototip ve NFC + QR sistemleri için senaryoya göre değişen BG Studio 3D teklif formu.'
    quote_pricing_payload = {
        'year': year,
        'qr_unit': pricing.get('qr_unit'),
        'menu_design': pricing.get('menu_design'),
        'logo_design': pricing.get('logo_design'),
        'packages': pricing.get('packages') or {},
        'feedback_duo_packages': pricing.get('feedback_duo_packages') or {},
        'special_restaurant_packages': pricing.get('special_restaurant_packages') or {},
    }
    quote_pricing_json = json.dumps(quote_pricing_payload, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    canonical = BASE_URL + '/teklif/'
    body = f'''<section class="quote-hero"><div class="shell quote-hero-grid"><div><p class="eyebrow">TEKLİF MERKEZİ</p><h1>İhtiyacını seç.<br>Doğru detayları gönder.</h1><p class="lead">Form, seçtiğin çalışma tipine göre yalnız gereken alanları gösterir. Gönderim sonunda düzenli bir WhatsApp özeti hazırlanır.</p></div><div class="quote-hero-note"><strong>Hızlı başlangıç</strong><span>01 · Çalışma tipini seç</span><span>02 · Detayları doldur</span><span>03 · Özeti WhatsApp'tan gönder</span></div></div></section>{STL_STUDIO_HTML_V3357}<section class="section-pad shell quote-center" aria-labelledby="quote-type-title"><div class="quote-section-head"><p class="eyebrow">01 · ÇALIŞMA TİPİ</p><h2 id="quote-type-title">Ne için teklif istiyorsunuz?</h2></div><form class="quote-form quote-form-v3170" data-quote-form novalidate><select class="sr-only" name="talep_turu" aria-label="Talep türü" required><option value="kisiye-ozel">Özel Üretim</option><option value="kurumsal">Kurumsal</option><option value="prototip">Prototip / Parça</option><option value="nfc">NFC &amp; QR</option><option value="diger">Diğer</option></select><div class="quote-type-grid" role="group" aria-label="Teklif türü"><button class="quote-type-card" type="button" data-quote-type="kisiye-ozel" aria-pressed="false"><span>01</span><strong>Özel Üretim</strong><small>Fikir, görsel, ölçü veya mevcut üründen üretim.</small></button><button class="quote-type-card" type="button" data-quote-type="kurumsal" aria-pressed="false"><span>02</span><strong>Kurumsal</strong><small>Toplu üretim, markalama ve işletmeye özel ürün.</small></button><button class="quote-type-card" type="button" data-quote-type="prototip" aria-pressed="false"><span>03</span><strong>Prototip / Parça</strong><small>STL, 3MF, STEP, PDF veya ölçüyle teknik üretim.</small></button><button class="quote-type-card" type="button" data-quote-type="nfc" aria-pressed="false"><span>04</span><strong>NFC &amp; QR</strong><small>Restoran, hızlı stand ve feedback çözümleri.</small></button><button class="quote-type-card" type="button" data-quote-type="diger" aria-pressed="false"><span>05</span><strong>Diğer</strong><small>Kapsamı farklı olan talepler.</small></button></div><div class="quote-dynamic" data-quote-dynamic><div class="quote-section-head compact"><p class="eyebrow">02 · DETAYLAR</p><h2>Teklif için gereken bilgiler.</h2></div><div class="quote-form-grid"><div class="field"><label for="quote-name">Ad / Soyad</label><input id="quote-name" name="ad" autocomplete="name" required maxlength="100" placeholder="Adınız"></div><div class="field" data-quote-scope="kurumsal prototip nfc diger"><label for="quote-business">İşletme / Marka</label><input id="quote-business" name="isletme" autocomplete="organization" maxlength="120" placeholder="Varsa işletme veya marka adı"></div><div class="field"><label for="quote-city">Şehir</label><input id="quote-city" name="sehir" autocomplete="address-level2" maxlength="80" placeholder="Örn. Kuşadası"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal prototip"><label for="quote-qty">Adet</label><input id="quote-qty" name="adet" inputmode="numeric" min="1" type="number" placeholder="Örn. 50"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal prototip"><label for="quote-size">Yaklaşık ölçü / ebat</label><input id="quote-size" name="olcu" maxlength="100" placeholder="Örn. 120 × 80 × 30 mm"></div><div class="field" data-quote-scope="kisiye-ozel kurumsal"><label for="quote-color">Renk / malzeme tercihi</label><input id="quote-color" name="renk" maxlength="120" placeholder="Örn. Siyah PETG / fark etmez"></div><div class="field field-wide" data-quote-scope="kisiye-ozel"><label for="quote-product-type">Ürün tipi</label><input id="quote-product-type" name="urun_tipi" maxlength="140" placeholder="Örn. masaüstü stand, dekor, aparat, kişiye özel ürün"></div><div class="field" data-quote-scope="kurumsal"><label for="quote-corporate-use">Kullanım / sektör</label><input id="quote-corporate-use" name="kurumsal_kullanim" maxlength="140" placeholder="Örn. promosyon, mağaza, restoran, teknik kullanım"></div><div class="field" data-quote-scope="kurumsal"><label for="quote-branding">Logo / markalama</label><input id="quote-branding" name="kurumsal_markalama" maxlength="140" placeholder="Logo, isim, renk veya ambalaj talebi"></div><div class="field" data-quote-scope="prototip"><label for="quote-prototype-job">Parçanın görevi</label><input id="quote-prototype-job" name="prototip_gorev" maxlength="180" placeholder="Nereye bağlanıyor, ne işe yarıyor?"></div><div class="field" data-quote-scope="prototip"><label for="quote-prototype-material">Tercih edilen malzeme</label><select id="quote-prototype-material" name="prototip_malzeme"><option value="">Seçiniz</option><option value="PLA">PLA</option><option value="PETG">PETG</option><option value="Kararsızım">Kararsızım, siz önerin</option></select></div></div><section class="quote-nfc-config" data-nfc-quote-config hidden data-quote-scope="nfc"><div class="quote-nfc-head"><div><p class="eyebrow">NFC + QR SİSTEMİ</p><h3>Paket ve kapsam seçimi</h3></div><small>{year} web fiyat yapısı</small></div><div class="quote-form-grid"><div class="field field-wide"><label for="quote-nfc-package">Sistem / paket</label><select id="quote-nfc-package" name="nfc_paket" required>{package_options}</select></div><div class="field" data-feedback-capacity-wrap hidden><label for="quote-feedback-capacity">Feedback Duo kapasitesi</label><select id="quote-feedback-capacity" name="feedback_duo_capacity">{duo_options}</select></div></div><div class="quote-package-summary" data-nfc-package-summary hidden><div><small>SEÇİLİ ÇÖZÜM</small><strong data-nfc-package-title>Çözüm seç</strong><span data-nfc-package-capacity></span></div><div><small data-nfc-price-year>{year} BAŞLANGIÇ</small><strong data-nfc-package-price>Özel teklif</strong><span data-nfc-package-renewal></span></div></div><div class="quote-options"><label><input type="checkbox" name="nfc_qr" data-nfc-option><span><strong>QR sistemi</strong><small data-nfc-qr-copy>{qr} / QR</small></span></label><label><input type="checkbox" name="nfc_menu_design" data-nfc-option><span><strong>Menü Tasarımı</strong><small data-nfc-menu-price-copy>+{menu}</small></span></label><label><input type="checkbox" name="nfc_logo_design" data-nfc-option><span><strong>Logo Tasarımı</strong><small data-nfc-logo-price-copy>+{logo}</small></span></label></div><div class="quote-total" data-nfc-quote-total hidden><span>Seçili toplam</span><strong data-nfc-total-value></strong></div></section><section class="quote-files" data-quote-scope="kisiye-ozel kurumsal"><div><p class="eyebrow">DOSYA / GÖRSEL</p><h3>Referans ekle</h3><p>PNG, JPG, WEBP veya PDF. Her dosya en fazla 15 MB.</p></div><label class="quote-file-drop"><input type="file" data-quote-files accept=".png,.jpg,.jpeg,.webp,.pdf" multiple><span>Görsel veya PDF seç</span><small>Dosya adları teklife eklenir.</small></label></section><section class="quote-files" data-quote-scope="prototip"><div><p class="eyebrow">TEKNİK DOSYA</p><h3>Dosyan varsa ekle</h3><p>STL, 3MF, STEP, STP, PDF veya görsel. Her dosya en fazla 15 MB.</p></div><label class="quote-file-drop"><input type="file" data-quote-files accept=".stl,.3mf,.step,.stp,.pdf,.png,.jpg,.jpeg,.webp" multiple><span>Teknik dosya seç</span><small>Dosyalar web sunucusuna yüklenmez.</small></label></section><input type="hidden" name="dosya_ozeti"><ul class="quote-file-list" data-quote-file-list hidden></ul><p class="quote-security-note">🔒 Dosyalar bu sayfadan sunucuya gönderilmez. WhatsApp açıldığında seçtiğin dosyaları sohbete ayrıca ekle.</p><div class="field field-wide quote-detail-field"><label for="quote-detail">Talebini anlat</label><textarea id="quote-detail" name="detay" rows="6" required maxlength="1800" placeholder="Kullanım amacı, ölçü, adet ve önemli detayları yazın…"></textarea></div><div class="quote-status" role="status" aria-live="polite" data-quote-status></div><button class="primary-cta quote-submit" type="submit" data-quote-submit>Teklif özetini WhatsApp'ta aç ↗</button></div></form></section><section class="quote-trust"><div class="shell"><article><strong>Kuşadası</strong><span>Elden teslim</span></article><article><strong>Türkiye geneli</strong><span>Kargo</span></article><article><strong>Özel üretim</strong><span>İhtiyaca göre teklif</span></article><article><strong>NFC + QR</strong><span>Paket seçimine bağlı canlı hesap</span></article></div></section>'''
    org = {'@context':'https://schema.org','@type':'Service','name':'BG Studio 3D Teklif Merkezi','provider':{'@id':BASE_URL + '/#organization'},'areaServed':'Türkiye','url':canonical}
    schema = json.dumps(org,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Teklif Al – 3D Baskı, Kurumsal ve NFC | BG Studio 3D</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="Teklif Al – 3D Baskı, Kurumsal ve NFC | BG Studio 3D"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><meta name="robots" content="index,follow"><meta name="theme-color" content="#ffffff"><link rel="icon" href="../favicon.ico" sizes="any"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"><link rel="stylesheet" href="../assets/css/styles.css?v={SITE_ASSET_VERSION}"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header('../','')}<main id="main-content" class="quote-page-v3170">{body}</main><script type="application/json" id="quote-pricing-data">{quote_pricing_json}</script>{render_global_footer('../')}<script defer src="../assets/js/consent.js"></script><script defer src="../assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/main.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/quote-center.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/stl-studio.js?v={SITE_ASSET_VERSION}"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D" rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div></body></html>'''


def render_legal_page_v3171(slug, title, intro, sections, indexable=True):
    canonical = f'{BASE_URL}/{slug}/'
    blocks = ''.join(f'<article><h2>{esc(head)}</h2><p>{esc(text)}</p></article>' for head,text in sections)
    robots = 'index,follow' if indexable else 'noindex,follow'
    body = f'''<section class="legal-hero"><div class="shell"><p class="eyebrow">BİLGİLENDİRME</p><h1>{esc(title)}</h1><p class="lead">{esc(intro)}</p></div></section><section class="section-pad shell legal-layout"><div class="legal-content">{blocks}</div><aside class="legal-aside" role="none"><strong>BG Studio 3D</strong><p>Kuşadası merkezli 3D baskı ve özel üretim.</p><a class="text-cta" href="../iletisim/">İletişime geç ↗</a></aside></section>'''
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | BG Studio 3D</title><meta name="description" content="{esc(clip_seo_text(intro,160))}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="tr_TR"><meta property="og:site_name" content="BG Studio 3D"><meta property="og:title" content="{esc(title)} | BG Studio 3D"><meta property="og:description" content="{esc(clip_seo_text(intro,160))}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><meta name="robots" content="{robots}"><link rel="stylesheet" href="../assets/css/styles.css?v={SITE_ASSET_VERSION}"></head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>{render_site_header('../','')}<main id="main-content" class="legal-page-v3171">{body}</main>{render_global_footer('../')}<script defer src="../assets/js/consent.js"></script><script defer src="../assets/js/navigation.js?v={SITE_ASSET_VERSION}"></script><script defer src="../assets/js/main.js?v={SITE_ASSET_VERSION}"></script></body></html>'''


def build_legal_pages_v3171():
    pages = {
        'kvkk': ('KVKK Aydınlatma', 'Web sitesi ve teklif iletişimi kapsamında paylaşılan kişisel verilerin hangi amaçlarla işlendiğine ilişkin temel bilgilendirme.', [
            ('Toplanan bilgiler', 'İletişim veya teklif talebi sırasında ad, iletişim bilgisi, işletme bilgisi ve talebin kapsamı paylaşılabilir. Kart bilgisi bu web sitesinde tutulmaz.'),
            ('İşleme amacı', 'Paylaşılan bilgiler talebi yanıtlamak, üretim veya hizmet kapsamını netleştirmek, teslim ve iletişim sürecini yürütmek amacıyla değerlendirilir.'),
            ('Veri minimizasyonu', 'BG Studio 3D teklif ve sipariş süreci için gerekli olmayan kişisel bilgileri istememeyi hedefler. Web sitesinde çevrimiçi ödeme altyapısı devrede değildir.'),
            ('Başvuru ve iletişim', 'Kişisel verilerle ilgili talepler için BG Studio 3D iletişim kanalları üzerinden başvuru yapılabilir. Yasal saklama yükümlülükleri bulunan kayıtlar ayrı değerlendirilir.'),
        ]),
        # v3.3.42 — Shopier dükkan ayarlarıyla aynı kurallar: 1–3 iş günü üretim, kargo ücreti teslimatta alıcıdan,
        # hasarlı/hatalı üründe değişim veya iade, kişiye özel ürünler iade dışı.
        'teslimat-iade': ('Teslimat / İade', 'Ürünler sipariş üzerine üretilir; teslim, kargo ve iade kuralları aşağıdadır.', [
            ('Üretim süresi', 'Ürünler sipariş onayından sonra 1–3 iş günü içinde PLA veya PETG malzemeden üretilir, ardından kargoya verilir. Toplu ve kurumsal siparişlerde süre sipariş öncesinde ayrıca paylaşılır.'),
            ('Kargo', 'Türkiye geneline kargo ile gönderilir. Kargo ücreti teslimat sırasında alıcı tarafından ödenir. Uygun siparişlerde Kuşadası’nda elden teslim seçeneği vardır.'),
            ('Hasarlı veya hatalı ürün', 'Kargo kaynaklı hasar veya üretim hatası olursa paketin ve ürünün fotoğraflarıyla WhatsApp (0530 246 69 03) ya da bgstudio.3dtr@gmail.com üzerinden bize ulaşın; değişim ya da iade yapıyoruz.'),
            ('Kişiye özel ürünler', 'İsim, logo, ölçü veya müşteriye özgü başka bir detayla kişiselleştirilen ürünler iade kapsamında değildir. Bu nedenle üretim öncesinde kişiselleştirme bilgilerinin doğru onaylanması önemlidir.'),
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



def _bg_entity_schema_v3317():
    """Canonical BG Studio 3D identity. Never infer ratings, reviews, street address or third-party category."""
    return {
        '@context': 'https://schema.org',
        '@type': ['Organization', 'LocalBusiness'],
        '@id': BASE_URL + '/#organization',
        'name': 'BG Studio 3D',
        'url': BASE_URL + '/',
        'description': 'Kuşadası merkezli 3D baskı, özel üretim, prototip ve parça üretimi, kurumsal toplu üretim ve NFC + QR işletme çözümleri.',
        'logo': BASE_URL + '/assets/brand/bgstudio3d-logo.png',
        'image': BASE_URL + '/assets/brand/og-bgstudio3d-share-v2.jpg',
        'telephone': '+90 530 246 69 03',
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': 'Kuşadası',
            'addressRegion': 'Aydın',
            'addressCountry': 'TR',
        },
        'areaServed': [
            {'@type': 'City', 'name': 'Kuşadası'},
            {'@type': 'AdministrativeArea', 'name': 'Aydın'},
            {'@type': 'Country', 'name': 'Türkiye'},
        ],
        # V3.3.36: tie the site entity to its Google Business Profile. The profile
        # is a service-area listing (no public street address, map pin is the
        # Aydın region centre), so no geo/address beyond the city is added.
        'hasMap': GOOGLE_REVIEWS_URL_V3328,
        'sameAs': [
            'https://instagram.com/bgstudio.3dtr',
            'https://www.facebook.com/bgstudio.3dtr',
            GOOGLE_REVIEWS_URL_V3328,
        ],
        # Hours as published on the Google Business Profile (every day 10:00-19:00).
        'openingHoursSpecification': [{
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'opens': '10:00',
            'closes': '19:00',
        }],
        'founder': {'@type': 'Person', 'name': 'Berkant Gökbel'},
        'contactPoint': {
            '@type': 'ContactPoint',
            'contactType': 'customer service',
            'telephone': '+90 530 246 69 03',
            'availableLanguage': ['Turkish'],
        },
    }


def _bg_website_schema_v3317():
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        '@id': BASE_URL + '/#website',
        'name': 'BG Studio 3D',
        'url': BASE_URL + '/',
        'inLanguage': 'tr-TR',
        'publisher': {'@id': BASE_URL + '/#organization'},
        'potentialAction': {
            '@type': 'SearchAction',
            'target': BASE_URL + '/urunler/?q={search_term_string}',
            'query-input': 'required name=search_term_string',
        },
    }


def _strip_legacy_identity_schema_v3317(text, is_home=False):
    # Remove prior auto-generated entity scripts while preserving page-specific Product/FAQ/Service data.
    text = re.sub(
        r'<script\b[^>]*data-schema=["\'](?:organization|website|local-business|entity)["\'][^>]*>.*?</script>',
        '', text, flags=re.I | re.S
    )
    if is_home:
        # Remove the two historical unmarked homepage identity blocks only.
        text = re.sub(
            r'<script\s+type=["\']application/ld\+json["\']>\s*\{(?:(?!</script>).)*?"@type"\s*:\s*"LocalBusiness"(?:(?!</script>).)*?"name"\s*:\s*"BG Studio 3D"(?:(?!</script>).)*?</script>',
            '', text, count=1, flags=re.I | re.S
        )
        text = re.sub(
            r'<script\s+type=["\']application/ld\+json["\']>\s*\{(?:(?!</script>).)*?"@type"\s*:\s*"WebSite"(?:(?!</script>).)*?"name"\s*:\s*"BG Studio 3D"(?:(?!</script>).)*?</script>',
            '', text, count=1, flags=re.I | re.S
        )
    return text


def _schema_script(data, marker):
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'<script type="application/ld+json" data-schema="{marker}">{payload}</script>'


# ============================================================
# V3.3.12 · PERFORMANCE & LAUNCH AUDIT
# ============================================================

def _minify_css_v3312(source):
    """Conservative CSS minifier.

    Removes comments and collapses whitespace only outside quoted strings.
    It deliberately keeps spaces around +/- so calc() arithmetic stays valid.
    """
    out = []
    i = 0
    n = len(source)
    quote = None
    pending_space = False
    prev = ''
    no_space_before = set('}:;,>~)')
    no_space_after = set('{:;,>~(')

    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ''

        if quote:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(source[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            prev = ch
            continue

        if ch in ('"', "'"):
            if pending_space:
                if out and out[-1] not in no_space_after:
                    out.append(' ')
                pending_space = False
            quote = ch
            out.append(ch)
            prev = ch
            i += 1
            continue

        if ch == '/' and nxt == '*':
            end = source.find('*/', i + 2)
            if end < 0:
                break
            i = end + 2
            pending_space = True
            continue

        if ch.isspace():
            pending_space = True
            i += 1
            continue

        if pending_space:
            last = out[-1] if out else ''
            if last and last not in no_space_after and ch not in no_space_before:
                out.append(' ')
            pending_space = False

        # Trim an already emitted space before punctuation where it is safe.
        if ch in no_space_before and out and out[-1] == ' ':
            out.pop()
        out.append(ch)
        prev = ch
        i += 1

    return ''.join(out).strip()


def write_minified_css_v3312():
    source_path = ROOT / 'assets/css/styles.css'
    target_path = ROOT / 'assets/css/styles.min.css'
    if not source_path.exists():
        return {'written': False, 'reason': 'styles.css missing'}
    source = source_path.read_text(encoding='utf-8')
    minified = _minify_css_v3312(source)
    target_path.write_text(minified + '\n', encoding='utf-8')
    before = len(source.encode('utf-8'))
    after = len((minified + '\n').encode('utf-8'))
    return {
        'written': True,
        'source_bytes': before,
        'minified_bytes': after,
        'saved_bytes': max(0, before - after),
        'saved_percent': round(((before - after) / before * 100), 1) if before else 0,
    }


def _local_image_dimensions_v3312(html_path, src, cache):
    if PILImage is None or not src:
        return None
    raw = html.unescape(str(src)).strip()
    if not raw or raw.startswith(('http://','https://','//','data:','blob:','#')):
        return None
    raw = raw.split('#', 1)[0].split('?', 1)[0]
    if not raw:
        return None
    try:
        candidate = (html_path.parent / raw).resolve()
        root = ROOT.resolve()
        if candidate != root and root not in candidate.parents:
            return None
        if candidate.suffix.lower() == '.svg' or not candidate.is_file():
            return None
        key = str(candidate)
        if key in cache:
            return cache[key]
        with PILImage.open(candidate) as image:
            width, height = image.size
        value = (int(width), int(height)) if width and height else None
        cache[key] = value
        return value
    except Exception:
        return None


def audit_v3312_launch_readiness():
    result = {
        'pages': 0,
        'blocking_local_scripts': [],
        'images_missing_alt': [],
        'images_missing_dimensions': [],
        'mixed_content': [],
        'duplicate_ids': [],
        'entity_identity_issues': [],
        'broken_internal_links': [],
        'missing_local_assets': [],
        'unsafe_blank_targets': [],
        'stale_asset_versions': [],
        'forbidden_public_claims': [],
        'css': {},
    }
    source_css = ROOT / 'assets/css/styles.css'
    min_css = ROOT / 'assets/css/styles.min.css'
    if source_css.exists() and min_css.exists():
        before = source_css.stat().st_size
        after = min_css.stat().st_size
        result['css'] = {
            'source_bytes': before,
            'minified_bytes': after,
            'saved_bytes': max(0, before - after),
            'saved_percent': round(((before - after) / before * 100), 1) if before else 0,
        }

    def clean_local_url(value):
        raw = html.unescape(str(value or '')).strip()
        if not raw or raw.startswith(('#','mailto:','tel:','javascript:','data:','blob:')):
            return None
        if raw.startswith(('http://','https://','//')):
            return None
        return raw.split('#',1)[0].split('?',1)[0]

    def resolve_local(html_path, raw):
        local = clean_local_url(raw)
        if local is None:
            return None
        if local.startswith('/'):
            target = ROOT / local.lstrip('/')
        else:
            target = html_path.parent / local
        try:
            return target.resolve()
        except Exception:
            return None

    def link_exists(target):
        if target is None:
            return True
        try:
            root = ROOT.resolve()
            if target != root and root not in target.parents:
                return False
            if target.is_file():
                return True
            if target.is_dir() and (target / 'index.html').is_file():
                return True
            if not target.suffix and (target / 'index.html').is_file():
                return True
            return False
        except Exception:
            return False

    # These names are intentionally forbidden in generated public HTML until
    # Product Manager marks those modules as active again.
    forbidden = ('Garson Çağır', 'Hesap İste')

    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        rel = html_path.relative_to(ROOT).as_posix()
        result['pages'] += 1

        for tag in re.findall(r'<script\b[^>]*>', text, flags=re.I):
            if re.search(r'type=["\']application/(?:ld\+json|json)["\']', tag, flags=re.I):
                continue
            src_match = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, flags=re.I)
            if not src_match:
                continue
            src_value = src_match.group(1)
            local = not src_value.startswith(('http://','https://','//'))
            if local and not re.search(r'\b(?:defer|async)\b', tag, flags=re.I) and not re.search(r'type=["\']module["\']', tag, flags=re.I):
                result['blocking_local_scripts'].append(f'{rel}: {src_value}')

        if re.search(r'<img\b(?![^>]*\balt=)[^>]*>', text, flags=re.I):
            result['images_missing_alt'].append(rel)
        for tag in re.findall(r'<img\b[^>]*>', text, flags=re.I):
            if not ('width=' in tag.lower() and 'height=' in tag.lower()):
                result['images_missing_dimensions'].append(rel)
                break

        if re.search(r'(?:src|href)=["\']http://', text, flags=re.I):
            result['mixed_content'].append(rel)

        ids = re.findall(r'\bid=["\']([^"\']+)["\']', text, flags=re.I)
        seen = set()
        duplicates = sorted({value for value in ids if value in seen or seen.add(value)})
        if duplicates:
            result['duplicate_ids'].append({'page': rel, 'ids': duplicates[:8]})

        if rel == 'index.html':
            entity_count = len(re.findall(r'data-schema=["\']entity["\']', text, flags=re.I))
            website_count = len(re.findall(r'data-schema=["\']website["\']', text, flags=re.I))
            if entity_count != 1:
                result['entity_identity_issues'].append(f'index.html: canonical entity schema count {entity_count}, expected 1')
            if website_count != 1:
                result['entity_identity_issues'].append(f'index.html: canonical website schema count {website_count}, expected 1')
            if BASE_URL + '/#organization' not in text:
                result['entity_identity_issues'].append('index.html: canonical #organization @id missing')

        for href in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I):
            target = resolve_local(html_path, href)
            if target is not None and not link_exists(target):
                result['broken_internal_links'].append(f'{rel}: {href}')

        asset_values = []
        asset_values += re.findall(r'<(?:img|script|source)\b[^>]*\bsrc=["\']([^"\']+)["\']', text, flags=re.I)
        asset_values += re.findall(r'<link\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I)
        for value in asset_values:
            target = resolve_local(html_path, value)
            if target is not None and not target.is_file():
                result['missing_local_assets'].append(f'{rel}: {value}')

        for tag in re.findall(r'<a\b[^>]*\btarget=["\']_blank["\'][^>]*>', text, flags=re.I):
            rel_match = re.search(r'\brel=["\']([^"\']*)["\']', tag, flags=re.I)
            rel_tokens = set((rel_match.group(1).lower().split() if rel_match else []))
            if 'noopener' not in rel_tokens:
                href_match = re.search(r'\bhref=["\']([^"\']*)["\']', tag, flags=re.I)
                result['unsafe_blank_targets'].append(f'{rel}: {(href_match.group(1) if href_match else "unknown")[:180]}')

        for version in re.findall(r'(?:assets/(?:css|js)/[^"\']+\?v=)([^&"\']+)', text, flags=re.I):
            if version != SITE_ASSET_VERSION:
                result['stale_asset_versions'].append(f'{rel}: {version}')

        for phrase in forbidden:
            if phrase in text:
                result['forbidden_public_claims'].append(f'{rel}: {phrase}')

    for key in (
        'blocking_local_scripts','images_missing_alt','images_missing_dimensions','mixed_content',
        'broken_internal_links','missing_local_assets','unsafe_blank_targets','stale_asset_versions',
        'forbidden_public_claims','entity_identity_issues'
    ):
        result[key] = list(dict.fromkeys(result[key]))[:30]
    result['duplicate_ids'] = result['duplicate_ids'][:20]
    result['ready'] = not any(result[key] for key in (
        'blocking_local_scripts','images_missing_alt','broken_internal_links','missing_local_assets',
        'mixed_content','unsafe_blank_targets','stale_asset_versions','forbidden_public_claims','entity_identity_issues'
    ))
    return result

def sync_seo_accessibility_performance_v3171():
    scanned=changed=0
    heading_warnings=[]
    image_dimension_cache={}
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
            updated=updated.replace('</head>','<meta name="theme-color" content="#ffffff"></head>',1)
        if 'name="twitter:card"' not in updated:
            card='summary_large_image' if 'property="og:image"' in updated else 'summary'
            og_image_match=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',updated,re.I)
            if not og_image_match:
                og_image_match=re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',updated,re.I)
            twitter=f'<meta name="twitter:card" content="{card}"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(clip_seo_text(desc,160))}">'
            if og_image_match:
                twitter += f'<meta name="twitter:image" content="{esc(og_image_match.group(1))}">'
            updated=updated.replace('</head>',twitter+'</head>',1)
        is_home = html_path == ROOT/'index.html'
        updated = _strip_legacy_identity_schema_v3317(updated, is_home=is_home)
        updated=updated.replace('</head>',_schema_script(_bg_entity_schema_v3317(),'entity')+'</head>',1)
        if is_home:
            updated=updated.replace('</head>',_schema_script(_bg_website_schema_v3317(),'website')+'</head>',1)
        if route != '/' and 'data-schema="breadcrumb"' not in updated:
            label_map={'urunler':'Ürünler','ozel-uretim':'Özel Üretim','kurumsal':'Kurumsal','nfc-qr':'NFC & QR','restoran':'Restoran Sistemleri','hizli-baglanti':'Hızlı Bağlantı','feedback':'Premium Feedback','premium-plus':'Premium Plus','prototip-parca':'Prototip & Parça','mimari-maket-3d-baski':'Mimari Maket','projeler':'Projeler','hakkimizda':'Hakkımızda','iletisim':'İletişim','teklif':'Teklif','gizlilik':'Gizlilik','kvkk':'KVKK','teslimat-iade':'Teslimat / İade','kisiye-ozel-urun-kosullari':'Kişiye Özel Ürün Koşulları'}
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

            # V3.3.12: local intrinsic dimensions reduce layout shift without
            # changing the responsive CSS size. Remote/data/SVG assets are skipped.
            if not ('width=' in tag.lower() and 'height=' in tag.lower()):
                src_match=re.search(r'\bsrc=["\']([^"\']+)["\']',tag,re.I)
                dims=_local_image_dimensions_v3312(html_path,src_match.group(1),image_dimension_cache) if src_match else None
                if dims:
                    width,height=dims
                    if 'width=' not in tag.lower(): tag=add_attr(tag,f'width="{width}"')
                    if 'height=' not in tag.lower(): tag=add_attr(tag,f'height="{height}"')
            return tag
        updated=re.sub(r'<img\b[^>]*>',tune_img,updated,flags=re.I)
        h1_count=len(re.findall(r'<h1\b',updated,re.I))
        if h1_count != 1:
            heading_warnings.append({'page':html_path.relative_to(ROOT).as_posix(),'h1':h1_count})
        if updated != text:
            html_path.write_text(updated,encoding='utf-8'); changed += 1
    robots=('User-agent: *\nAllow: /\nDisallow: /tools/\nDisallow: /data/\nDisallow: /cloudflare/\nDisallow: /launcher/\nSitemap: '+BASE_URL+'/sitemap.xml\n')
    (ROOT/'robots.txt').write_text(robots,encoding='utf-8')
    return {'scanned':scanned,'changed':changed,'heading_warnings':heading_warnings[:20]}



# ============================================================
# V3.3.21 · TECHNICAL SEO FOUNDATION
# ============================================================

def _expected_canonical_v3321(html_path):
    rel = html_path.relative_to(ROOT).as_posix()
    if rel == 'index.html':
        return BASE_URL + '/'
    if rel == '404.html':
        return BASE_URL + '/404.html'
    if rel.endswith('/index.html'):
        return BASE_URL + '/' + rel[:-len('index.html')]
    return BASE_URL + '/' + rel


def _meta_content_v3321(text, key, value):
    pattern = re.compile(r'<meta\b[^>]*>', flags=re.I)
    key = key.casefold(); value = value.casefold()
    for match in pattern.finditer(text):
        tag = match.group(0)
        attr = re.search(rf'\b{re.escape(key)}=["\']([^"\']+)["\']', tag, flags=re.I)
        if not attr or attr.group(1).casefold() != value:
            continue
        content = re.search(r'\bcontent=["\']([^"\']*)["\']', tag, flags=re.I)
        return html.unescape(content.group(1)).strip() if content else ''
    return ''


def _canonical_href_v3321(text):
    for match in re.finditer(r'<link\b[^>]*>', text, flags=re.I):
        tag = match.group(0)
        rel = re.search(r'\brel=["\']([^"\']+)["\']', tag, flags=re.I)
        if not rel or 'canonical' not in rel.group(1).casefold().split():
            continue
        href = re.search(r'\bhref=["\']([^"\']+)["\']', tag, flags=re.I)
        return html.unescape(href.group(1)).strip() if href else ''
    return ''


def sync_canonical_integrity_v3321():
    """Enforce one clean self-canonical and matching og:url per generated page."""
    scanned = changed = 0
    quote_ok = False
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if '<head' not in text.lower():
            continue
        scanned += 1
        expected = _expected_canonical_v3321(html_path)
        updated = text

        # Remove all canonical tags first. Reinsert exactly one standardized tag.
        updated = re.sub(
            r'<link\b(?=[^>]*\brel=["\'][^"\']*\bcanonical\b[^"\']*["\'])[^>]*>',
            '', updated, flags=re.I
        )
        updated = updated.replace('</head>', f'<link rel="canonical" href="{esc(expected)}"></head>', 1)

        # Keep Open Graph URL aligned with the canonical URL when present.
        og_pattern = r'<meta\b(?=[^>]*\bproperty=["\']og:url["\'])[^>]*>'
        if re.search(og_pattern, updated, flags=re.I):
            updated = re.sub(og_pattern, f'<meta property="og:url" content="{esc(expected)}">', updated, count=1, flags=re.I)

        # 404 is never an index target. Its canonical is clean, but robots stays noindex.
        if html_path == ROOT/'404.html':
            robots_pattern = r'<meta\b(?=[^>]*\bname=["\']robots["\'])[^>]*>'
            if re.search(robots_pattern, updated, flags=re.I):
                updated = re.sub(robots_pattern, '<meta name="robots" content="noindex,follow">', updated, count=1, flags=re.I)
            else:
                updated = updated.replace('</head>', '<meta name="robots" content="noindex,follow"></head>', 1)

        if html_path == ROOT/'teklif'/'index.html':
            quote_ok = expected == BASE_URL + '/teklif/'

        if updated != text:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed, 'quote_canonical_ok': quote_ok}


def _sitemap_priority_v3321(url):
    path = url[len(BASE_URL):] if url.startswith(BASE_URL) else '/'
    exact = {
        '/': 1.0,
        '/kusadasi-3d-baski/': .95,
        '/nfc-qr/': .95,
        '/projeler/': .92,
        '/nfc-qr/restoran/': .92,
        '/kurumsal/': .90,
        '/prototip-parca/': .90,
        '/mimari-maket-3d-baski/': .90,
        '/ozel-uretim/': .90,
        '/urunler/': .90,
        '/nfc-qr/feedback/': .90,
        '/nfc-qr/hizli-baglanti/': .88,
        '/teklif/': .85,
        '/iletisim/': .80,
        '/nfc-qr/premium-plus/': .72,
    }
    if path in exact:
        return exact[path]
    if path.startswith('/projeler/'):
        return .72
    if path.startswith('/urunler/'):
        return .70
    if path in ('/gizlilik/','/hakkimizda/','/siparis-bilgilendirme/'):
        return .60
    if path in ('/kvkk/','/teslimat-iade/'):
        return .50
    if path == '/kisiye-ozel-urun-kosullari/':
        return .45
    return .60


def build_canonical_sitemap_v3321():
    """Build sitemap from generated indexable self-canonical pages, not a hand-maintained list."""
    canonical_to_page = {}
    excluded_noindex = []
    duplicate_canonicals = []
    invalid_canonicals = []

    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        rel = html_path.relative_to(ROOT).as_posix()
        robots = _meta_content_v3321(text, 'name', 'robots').casefold()
        canonical = _canonical_href_v3321(text)
        if 'noindex' in robots:
            excluded_noindex.append(rel)
            continue
        if not canonical.startswith(BASE_URL + '/'):
            invalid_canonicals.append(rel)
            continue
        if '/index.html' in canonical or '?' in canonical or '#' in canonical:
            invalid_canonicals.append(rel)
            continue
        if canonical in canonical_to_page:
            duplicate_canonicals.append({'canonical': canonical, 'pages': [canonical_to_page[canonical], rel]})
            continue
        canonical_to_page[canonical] = rel

    urls = sorted(canonical_to_page, key=lambda u: (u != BASE_URL+'/', u))
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        priority = _sitemap_priority_v3321(url)
        lines.append(
            f'  <url><loc>{url}</loc><lastmod>{today}</lastmod>'
            f'<changefreq>monthly</changefreq><priority>{priority}</priority></url>'
        )
    lines.append('</urlset>')
    (ROOT/'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {
        'urls': len(urls),
        'excluded_noindex': excluded_noindex,
        'duplicate_canonicals': duplicate_canonicals,
        'invalid_canonicals': invalid_canonicals,
    }


# ============================================================
# V3.3.22 · SEARCH CONSOLE / INDEXABILITY DIAGNOSTIC
# ============================================================

def _route_from_html_v3322(html_path):
    rel = html_path.relative_to(ROOT).as_posix()
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel


def build_indexability_manifest_v3322():
    """Create a deterministic local mirror of the indexability signals we control.

    This cannot replace Google's URL Inspection data. It answers the site-side part:
    canonical, robots, sitemap membership, physical index.html aliases and expected
    treatment of those aliases. Search Console example URLs can then be compared to
    this manifest instead of guessing from a page count.
    """
    reports_dir = ROOT / 'tools' / 'product_manager' / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    sitemap_text = (ROOT/'sitemap.xml').read_text(encoding='utf-8', errors='ignore') if (ROOT/'sitemap.xml').exists() else ''
    sitemap_urls = set(re.findall(r'<loc>(.*?)</loc>', sitemap_text, flags=re.I | re.S))
    pages = []
    aliases = []
    canonical_seen = {}

    for html_path in sorted(ROOT.rglob('*.html')):
        rel_parts = html_path.relative_to(ROOT).parts
        if 'tools' in rel_parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        rel = html_path.relative_to(ROOT).as_posix()
        route = _route_from_html_v3322(html_path)
        canonical = _canonical_href_v3321(text)
        robots = _meta_content_v3321(text, 'name', 'robots').strip() or 'index,follow'
        noindex = 'noindex' in robots.casefold()
        in_sitemap = canonical in sitemap_urls
        expected = 'noindex' if noindex else ('canonical-indexable' if in_sitemap else 'indexable-not-in-sitemap')
        pages.append({
            'file': rel,
            'route': route,
            'url': BASE_URL + route,
            'canonical': canonical,
            'robots': robots,
            'indexable': not noindex,
            'in_sitemap': in_sitemap,
            'expected_treatment': expected,
        })
        canonical_seen.setdefault(canonical, []).append(rel)

        # Every directory index has a technically reachable /index.html variant on
        # static hosting. That URL is not a second content target; it points to the
        # slash canonical and may legitimately appear in GSC as an alternate page.
        if rel == 'index.html':
            alias_url = BASE_URL + '/index.html'
        elif rel.endswith('/index.html'):
            alias_url = BASE_URL + '/' + rel
        else:
            alias_url = ''
        if alias_url and canonical and alias_url != canonical:
            aliases.append({
                'url': alias_url,
                'canonical': canonical,
                'source_file': rel,
                'expected_google_treatment': 'alternate-canonical-or-redirect',
            })

    duplicate_canonicals = [
        {'canonical': key, 'files': value}
        for key, value in sorted(canonical_seen.items())
        if key and len(value) > 1
    ]
    noindex_pages = [row for row in pages if not row['indexable']]
    orphan_indexable = [row for row in pages if row['indexable'] and not row['in_sitemap']]
    canonical_indexable = [row for row in pages if row['indexable'] and row['in_sitemap']]

    payload = {
        'site': BASE_URL + '/',
        'asset_version': SITE_ASSET_VERSION,
        'generated_at': date.today().isoformat(),
        'summary': {
            'physical_html_pages': len(pages),
            'canonical_indexable_pages': len(canonical_indexable),
            'noindex_pages': len(noindex_pages),
            'index_html_aliases': len(aliases),
            'sitemap_urls': len(sitemap_urls),
            'indexable_not_in_sitemap': len(orphan_indexable),
            'duplicate_canonicals': len(duplicate_canonicals),
        },
        'pages': pages,
        'aliases': aliases,
        'noindex_pages': noindex_pages,
        'indexable_not_in_sitemap': orphan_indexable,
        'duplicate_canonicals': duplicate_canonicals,
    }
    json_path = reports_dir / 'indexability-manifest.json'
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    md = [
        '# BG Studio 3D · Indexability Manifest',
        '',
        f'- Asset version: **{SITE_ASSET_VERSION}**',
        f'- Physical HTML: **{len(pages)}**',
        f'- Canonical + indexable + sitemap: **{len(canonical_indexable)}**',
        f'- Noindex: **{len(noindex_pages)}**',
        f'- `/index.html` aliases: **{len(aliases)}**',
        f'- Indexable but sitemap dışında: **{len(orphan_indexable)}**',
        f'- Duplicate canonical: **{len(duplicate_canonicals)}**',
        '',
        '## Noindex sayfalar',
    ]
    if noindex_pages:
        md.extend(f"- `{row['url']}` → `{row['canonical']}` ({row['robots']})" for row in noindex_pages)
    else:
        md.append('- Yok')
    md += [
        '',
        '## Nasıl yorumlanır?',
        '',
        '- `alternate-canonical-or-redirect`: `/index.html` gibi ikinci bir URL keşfedilmiş olabilir. Doğru canonical slash URL ise bunun Google dizinine ayrıca girmemesi normaldir.',
        '- `canonical-indexable`: bizim tarafta indexlenebilir, sitemapte ve temiz canonical ile yayınlanır.',
        '- `noindex`: bilinçli olarak Google dizini dışında tutulur.',
        '- `indexable-not-in-sitemap`: teknik hata adayıdır ve release öncesi incelenmelidir.',
        '',
        '> Bu rapor Search Console kararını tahmin etmez. “Keşfedildi” veya “Tarandı ama dizine eklenmedi” nedeninin kesin URL örneği GSC’den alınmalı ve bu manifestle karşılaştırılmalıdır.',
    ]
    md_path = reports_dir / 'indexability-manifest.md'
    md_path.write_text('\n'.join(md) + '\n', encoding='utf-8')
    return {
        'json': json_path.relative_to(ROOT).as_posix(),
        'markdown': md_path.relative_to(ROOT).as_posix(),
        **payload['summary'],
    }


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


def _project_media(item, prefix='../', css_class='', eager=False):
    image = str(item.get('project_cover_image') or item.get('image') or '').strip().replace('\\','/').lstrip('/')
    name = esc(item.get('project_client') or item.get('name') or item.get('project_title') or item.get('headline') or 'BG Studio projesi')
    klass = f' {css_class}' if css_class else ''
    if image:
        dims = _asset_dimensions_v3324(image) or (1600, 900)
        srcset = _responsive_srcset_for_asset_v3324(image, prefix, widths=(640, 1200))
        if css_class == 'project-detail-media':
            sizes = '(max-width:760px) calc(100vw - 24px), (max-width:1100px) 52vw, 48vw'
        else:
            sizes = '(max-width:760px) calc(100vw - 24px), (max-width:1100px) 50vw, 33vw'
        srcset_attr = f' srcset="{esc(srcset)}" sizes="{sizes}"' if srcset else ''
        loading = 'eager' if eager else 'lazy'
        priority = ' fetchpriority="high"' if eager else ''
        return f'<div class="project-media{klass}"><img src="{esc(prefix + image)}" alt="{name}" width="{dims[0]}" height="{dims[1]}" loading="{loading}" decoding="async"{priority}{srcset_attr}></div>'
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
    # v3.3.41 — NFC taraması / menü açılışı / feedback / Google yönlendirmesi yalnızca NFC + QR projelerine ait.
    if _project_kind(item) != 'nfc':
        return []
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
    collection_schema={'@context':'https://schema.org','@type':'CollectionPage','@id':BASE_URL+'/projeler/#collection','name':'BG Studio 3D Projeler','description':'BG Studio 3D sahadan işler, kurumsal üretim, NFC + QR ve prototip proje arşivi.','url':BASE_URL+'/projeler/','isPartOf':{'@id':BASE_URL+'/#website'},'publisher':{'@id':BASE_URL+'/#organization'},'mainEntity':{'@type':'ItemList','itemListElement':[{'@type':'ListItem','position':pos,'name':str(row.get('project_title') or row.get('headline') or row.get('project_client') or row.get('name') or 'BG Studio 3D Projesi'),'url':BASE_URL+'/projeler/'+_project_slug(row)+'/'} for pos,row in enumerate(project_items,1)]}}
    collection_json=json.dumps(collection_schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json" data-schema="project-collection">{collection_json}</script><section class="project-index-hero"><div class="shell project-index-hero-grid"><div><p class="eyebrow">SAHADAN İŞLER</p><h1>Gerçek ihtiyaçlar.<br>Gerçek teslimler.</h1><p class="lead">Restoranlardan kurumsal üretime, NFC sistemlerinden teknik parçalara kadar tamamlanan BG Studio işlerini tek proje arşivinde incele.</p></div><div class="project-index-stat"><span>Tamamlanan proje</span><strong>{len(project_items)}</strong><small>Restoran, kurumsal ve prototip işlerinden oluşan arşiv.</small></div></div></section><section class="section-pad shell"><div class="project-filterbar" aria-label="Proje filtreleri">{''.join(filters)}<div class="project-result-count"><strong data-project-count>{len(project_items)}</strong> proje gösteriliyor</div></div><div class="project-index-grid" data-project-grid>{''.join(cards)}</div><div class="project-empty" data-project-empty hidden>Bu filtrede yayınlanmış proje bulunmuyor.</div></section><section class="project-index-cta"><div class="shell"><div><p class="eyebrow">SIRADAKİ PROJE</p><h2>Senin işletmen veya parçan olabilir.</h2><p>Kurumsal üretim, özel parça, prototip veya NFC + QR sistemi için kapsamı gönder.</p></div><a class="primary-cta" href="../teklif/" data-project-index-quote>Teklif Al ↗</a></div></section>'''
    return _project_page_shell('Projeler – Kuşadası 3D Baskı ve NFC İşleri | BG Studio 3D','BG Studio 3D proje arşivi: Kuşadası ve çevresinde sahadan işler, kurumsal üretimler, NFC + QR kurulumları ve prototip parça çalışmaları.','/projeler/',body,'../')


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
    if _project_kind(item) == 'nfc':
        need = solution = ''  # v3.3.41 — İhtiyaç / çözüm anlatımı NFC + QR projelerinde gösterilmez.
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
    media=_project_media(item,'../../','project-detail-media',eager=True)
    gallery=_project_gallery(item)
    gallery_html=''
    if gallery:
        gallery_cards=''.join(f'<button class="project-gallery-item zoomable-media" type="button" aria-label="{esc(name)} proje görselini büyüt"><img src="../../{esc(src)}" alt="{esc(name)} proje görseli {idx}" loading="lazy" decoding="async"></button>' for idx,src in enumerate(gallery,1))
        gallery_html=f'<section class="section-pad-sm shell project-gallery-section"><div class="split-title"><div><p class="eyebrow">PROJE GÖRSELLERİ</p><h2>Uygulamadan detaylar.</h2></div></div><div class="project-gallery-grid">{gallery_cards}</div></section>'
    kind=_project_kind(item)
    service={'nfc':'../../nfc-qr/','prototype':'../../prototip-parca/','corporate':'../../kurumsal/'}.get(kind,'../../kurumsal/')
    offer={'nfc':'../../teklif/?tur=nfc','prototype':'../../teklif/?tur=prototip','corporate':'../../teklif/?tur=kurumsal'}.get(kind,'../../teklif/')
    same_kind=[x for x in project_items if _project_slug(x)!=slug and _project_kind(x)==kind]
    other_kind=[x for x in project_items if _project_slug(x)!=slug and _project_kind(x)!=kind]
    related=(same_kind+other_kind)[:3]
    related_html=''.join(f'<a class="project-related-card" data-project-related href="../{esc(_project_slug(x))}/">{_project_media(x,"../../","project-related-media")}<span>{esc(_project_kind_label(x))}</span><strong>{esc(x.get("project_client") or x.get("name") or x.get("project_title") or x.get("headline") or "Proje")}</strong></a>' for x in related)
    project_url=BASE_URL+'/projeler/'+slug+'/'
    service_url={'nfc':BASE_URL+'/nfc-qr/','prototype':BASE_URL+'/prototip-parca/','corporate':BASE_URL+'/kurumsal/'}.get(kind,BASE_URL+'/kurumsal/')
    schema={'@context':'https://schema.org','@type':'CreativeWork','@id':project_url+'#project','name':headline,'description':description,'creator':{'@id':BASE_URL+'/#organization'},'publisher':{'@id':BASE_URL+'/#organization'},'url':project_url,'mainEntityOfPage':{'@type':'WebPage','@id':project_url},'isPartOf':{'@id':BASE_URL+'/projeler/#collection'},'about':{'@type':'Service','name':kind_label,'url':service_url}}
    if sector: schema['keywords']=', '.join([sector]+[str(x) for x in _project_tags(item)[:6]])
    cover=str(item.get('project_cover_image') or item.get('image') or '').strip()
    if cover:
        schema['image']=BASE_URL+'/'+cover.lstrip('/')
    breadcrumb_schema={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Ana Sayfa','item':BASE_URL+'/'},{'@type':'ListItem','position':2,'name':'Projeler','item':BASE_URL+'/projeler/'},{'@type':'ListItem','position':3,'name':name,'item':project_url}]}
    schema_json=json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    breadcrumb_json=json.dumps(breadcrumb_schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    body=f'''<script type="application/ld+json" data-schema="project">{schema_json}</script><script type="application/ld+json" data-schema="breadcrumb">{breadcrumb_json}</script><section class="project-detail-hero" data-project-detail data-project-slug="{esc(slug)}" data-project-kind="{esc(kind)}" data-project-name="{esc(name)}"><div class="shell project-detail-grid"><div class="project-detail-copy"><nav class="project-breadcrumb" aria-label="İçerik yolu"><a href="../../projeler/">Projeler</a><span>/</span><b>{esc(name)}</b></nav><p class="eyebrow">{esc(kind_label)} · {esc(sector)}</p><h1>{esc(headline)}</h1><p class="lead">{esc(description)}</p><div class="hero-actions"><a class="primary-cta" data-project-quote href="{offer}">Benzer proje için teklif al ↗</a><a class="secondary-cta" data-project-service href="{service}">İlgili hizmeti incele ↗</a></div></div>{media}</div></section><section class="project-facts-wrap"><div class="shell project-facts">{facts_html}</div></section><section class="section-pad shell"><div class="project-story-grid">{story_html}</div>{('<div class="project-scope"><p class="eyebrow">UYGULAMA KAPSAMI</p><div class="project-scope-tags">'+tags+'</div></div>') if tags else ''}</section>{gallery_html}{metrics_html}<section class="section-pad-sm shell"><div class="split-title"><div><p class="eyebrow">BENZER PROJELER</p><h2>Aynı üretim alanından başka işler.</h2></div><a class="ghost-cta" href="../../projeler/">Tüm projeler ↗</a></div><div class="project-related-grid">{related_html}</div></section><section class="project-detail-cta"><div class="shell"><div><p class="eyebrow">BENZER BİR İHTİYAÇ MI VAR?</p><h2>Kapsamı gönder, üretim yolunu netleştirelim.</h2></div><a class="primary-cta" data-project-quote href="{offer}">Teklif Al ↗</a></div></section>'''
    project_title_context={'nfc':'NFC + QR Projesi','prototype':'Prototip + Parça','corporate':'Kurumsal Üretim'}.get(kind,'Proje')
    seo_title=str(item.get('project_seo_title') or compact_serp_title(name, project_title_context)).strip()
    seo_description=clip_seo_text(item.get('project_seo_description') or description,160)
    return _project_page_shell(seo_title,seo_description,f'/projeler/{slug}/',body,'../../')



def release_candidate_summary_v3314(launch_audit, shell_verify, seo_audit):
    """Compact production-readiness status for Product Manager output."""
    launch = launch_audit if isinstance(launch_audit, dict) else {}
    shell = shell_verify if isinstance(shell_verify, dict) else {}
    seo = seo_audit if isinstance(seo_audit, dict) else {}
    critical_keys = (
        'blocking_local_scripts', 'images_missing_alt', 'broken_internal_links',
        'missing_local_assets', 'mixed_content', 'unsafe_blank_targets',
        'stale_asset_versions', 'forbidden_public_claims'
    )
    critical_count = sum(len(launch.get(key) or []) for key in critical_keys)
    seo_count = sum(len(seo.get(key) or []) for key in (
        'missing_title','missing_description','missing_canonical','missing_main','missing_alt'
    ))
    ready = bool(launch.get('ready')) and bool(shell.get('ok')) and critical_count == 0 and seo_count == 0
    return {
        'name': RELEASE_CANDIDATE,
        'channel': RELEASE_CHANNEL,
        'asset_version': SITE_ASSET_VERSION,
        'ready': ready,
        'critical_issue_count': critical_count,
        'seo_issue_count': seo_count,
        'shell_ok': bool(shell.get('ok')),
        'next_step': 'STABLE baseline kilitli' if ready else 'launch_audit / SEO uyarılarını temizle',
    }


def enforce_strict_release_v3314(release_summary):
    """Optional CI/release gate.

    Normal Product Manager builds stay non-blocking. Set BG_STUDIO_STRICT_RELEASE=1
    in CI or before a production release to make critical RC failures stop the build.
    """
    strict = str(os.environ.get('BG_STUDIO_STRICT_RELEASE') or '').strip().lower() in ('1','true','yes','on')
    if strict and not bool((release_summary or {}).get('ready')):
        raise RuntimeError(
            'V3.3.15 STABLE release gate başarısız: production audit temiz değil. '
            'Build JSON içindeki release_candidate ve launch_audit alanlarını kontrol et.'
        )
    return {'strict': strict, 'passed': (not strict) or bool((release_summary or {}).get('ready'))}


def sync_kusadasi_local_seo_v3317(project_items):
    """Populate local proof from real Product Manager project records and keep Service schema tied to canonical entity."""
    path = ROOT / 'kusadasi-3d-baski' / 'index.html'
    if not path.exists():
        return {'ok': False, 'changed': False, 'reason': 'page missing', 'projects': 0}
    text = path.read_text(encoding='utf-8')
    original = text
    preferred = ['kusadasi-asansor', 'luckyland-kusadasi', 'kabalci-hukuk-burosu']
    by_slug = {_project_slug(item): item for item in (project_items or [])}
    selected = [by_slug[slug] for slug in preferred if slug in by_slug]

    cards = []
    for item in selected:
        slug = _project_slug(item)
        client = str(item.get('project_client') or item.get('name') or 'BG Studio 3D').strip()
        headline = str(item.get('project_title') or item.get('headline') or client).strip()
        sector = _project_sector(item) or '3D baskı üretimi'
        media = _project_media(item, '../', 'project-related-media')
        cards.append(
            f'<a class="project-related-card" href="../projeler/{esc(slug)}/" aria-label="{esc(client)} projesini incele">'
            f'{media}<span>{esc(sector)}</span><strong>{esc(headline)}</strong></a>'
        )

    proof = (
        '<section class="section-pad shell reveal" aria-labelledby="kusadasi-real-work-title">'
        '<div class="split-title"><div><p class="eyebrow">KUŞADASI’NDAN GERÇEK ÜRETİMLER</p>'
        '<h2 id="kusadasi-real-work-title">Yerelde ürettiğimiz gerçek işler.</h2></div>'
        '<p>Kuşadası merkezli üretim altyapısıyla Aydın çevresindeki özel ve kurumsal talepleri değerlendiriyor; '
        'uygun ürünleri Türkiye geneline gönderiyoruz. Aşağıda Kuşadası ve çevresinde tamamladığımız işlerden örnekler var.</p></div>'
        f'<div class="project-related-grid">{"".join(cards)}</div>'
        '<div class="hero-actions local-seo-link">'
        '<a class="text-cta" href="../kurumsal/">Kurumsal üretimi incele ↗</a>'
        '<a class="text-cta" href="../prototip-parca/">Prototip &amp; parça üretimini incele ↗</a>'
        '<a class="text-cta" href="../ozel-uretim/">Kişiye özel üretimi incele ↗</a>'
        '</div></section>'
    )
    start='<!-- BGSTUDIO:LOCAL_PROOF_START -->'
    end='<!-- BGSTUDIO:LOCAL_PROOF_END -->'
    if start in text and end in text:
        text = replace_between(text, start, end, proof)
    else:
        faq_marker='<section class="section-pad-sm shell reveal"><div class="split-title"><h2>Kuşadası 3D baskı hakkında sık sorulanlar.</h2>'
        if faq_marker not in text:
            return {'ok': False, 'changed': False, 'reason': 'FAQ insertion point missing', 'projects': len(selected)}
        text = text.replace(faq_marker, start + '\n' + proof + '\n' + end + '\n' + faq_marker, 1)

    text = re.sub(
        r'"provider":\{"@type":"LocalBusiness","name":"BG Studio 3D","url":"https://3d\.bgstudio\.com\.tr/","address":\{"@type":"PostalAddress","addressLocality":"Kuşadası","addressRegion":"Aydın","addressCountry":"TR"\}\}',
        '"provider":{"@id":"https://3d.bgstudio.com.tr/#organization"}', text, count=1
    )
    text = text.replace(
        '"areaServed":{"@type":"City","name":"Kuşadası"}',
        '"areaServed":[{"@type":"City","name":"Kuşadası"},{"@type":"AdministrativeArea","name":"Aydın"}]', 1
    )
    if text != original:
        path.write_text(text, encoding='utf-8')
    return {'ok': True, 'changed': text != original, 'projects': len(selected), 'slugs': [_project_slug(x) for x in selected]}


# ============================================================
# V3.3.26 · SEO + ACCESSIBILITY AUDIT FIXES
# Final idempotent pass over every public page. Covers markup that comes
# from hand-maintained pages or several templates at once.
# ============================================================
DEFAULT_OG_IMAGE_V3326 = BASE_URL + '/assets/brand/og-bgstudio3d-share-v2.jpg'


def _matching_div_end_v3326(text, start):
    """Index just past the </div> that closes the <div> opened at `start`."""
    depth = 0
    for m in re.compile(r'<div\b|</div>', re.I).finditer(text, start):
        depth += 1 if m.group(0).lower() == '<div' else -1
        if depth == 0:
            return m.end()
    return -1


def _page_og_image_v3326(html_path, text):
    """Project pages share their own hero photo; everything else the brand card."""
    if html_path.relative_to(ROOT).as_posix().startswith('projeler/') and html_path.parent.name != 'projeler':
        main = text[text.find('<main'):] if '<main' in text else text
        m = re.search(r'<img\b[^>]*\bsrc="([^"]+\.(?:jpe?g|png|webp))"', main, re.I)
        if m:
            candidate = (html_path.parent / html.unescape(m.group(1))).resolve()
            if candidate.is_file() and ROOT.resolve() in candidate.parents:
                return BASE_URL + '/' + candidate.relative_to(ROOT.resolve()).as_posix(), None
    return DEFAULT_OG_IMAGE_V3326, (1200, 630)


def sync_audit_fixes_v3326():
    scanned = changed = 0
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        scanned += 1
        updated = text

        # Share preview: every page gets an og:image (WhatsApp/Instagram/Facebook cards).
        if 'property="og:image"' not in updated and '</head>' in updated:
            image, size = _page_og_image_v3326(html_path, updated)
            tags = f'<meta property="og:image" content="{esc(image)}">'
            if size:
                tags += f'<meta property="og:image:width" content="{size[0]}"><meta property="og:image:height" content="{size[1]}">'
            if 'name="twitter:image"' not in updated:
                tags += f'<meta name="twitter:image" content="{esc(image)}">'
            updated = updated.replace('</head>', tags + '</head>', 1)
            updated = re.sub(r'(<meta name="twitter:card" content=")summary(")', r'\1summary_large_image\2', updated, count=1)

        # Duplicated marquee copies are aria-hidden; inert also removes their links from Tab order.
        updated = re.sub(r'(<div class="home-client-marquee-group-v3199r1" aria-hidden="true")(?! inert)>', r'\1 inert>', updated)

        # Horizontally scrollable flow strip must be reachable by keyboard.
        updated = re.sub(r'<div class="nfc-digital-flow"(?![^>]*tabindex)', '<div class="nfc-digital-flow" role="region" tabindex="0"', updated)

        # Side panels nested inside <main> are layout, not complementary landmarks.
        updated = re.sub(r'<aside class="(info-panel[^"]*|legal-aside)"(?![^>]*\brole=)', r'<aside class="\1" role="none"', updated)
        updated = updated.replace('<aside><strong>BG NFC</strong>', '<aside role="none"><strong>BG NFC</strong>')

        # Floating launchers sit outside every landmark; make the group its own one.
        start = updated.find('<div aria-label="Hızlı işlemler" class="floating-actions">')
        if start >= 0:
            end = _matching_div_end_v3326(updated, start)
            if end > 0:
                block = updated[start:end]
                block = '<aside' + block[4:-6] + '</aside>'
                updated = updated[:start] + block + updated[end:]

        # Catalog cards use <h3>; give the grid the missing <h2> level.
        if html_path == ROOT / 'urunler' / 'index.html' and 'id="catalog-grid-title"' not in updated:
            updated = updated.replace(
                '<div class="product-grid catalog-grid" id="catalog-grid">',
                '<h2 class="sr-only" id="catalog-grid-title">Tüm ürünler</h2><div class="product-grid catalog-grid" id="catalog-grid">', 1)

        if updated != text:
            html_path.write_text(updated, encoding='utf-8')
            changed += 1
    return {'scanned': scanned, 'changed': changed}


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
    # v3.3.47 — öne çıkanların panelde sürükle-bırak ile verilen kendi sırası (featured_order); sırası olmayanlar
    # katalog sırasına göre sona dizilir. Ana sayfanın üst bölümü ve vitrin şeridi bu sırayı izler.
    def _featured_key(product):
        try:
            return (0, int(product.get('featured_order')), 0)
        except (TypeError, ValueError):
            return (1, 0, int(product.get('sort_order') or 9999))
    featured.sort(key=_featured_key)
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

    maket_path = ROOT / 'mimari-maket-3d-baski/index.html'
    maket_path.parent.mkdir(parents=True, exist_ok=True)
    maket_path.write_text(render_maket_page_v3373(), encoding='utf-8')

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
    local_seo_sync = sync_kusadasi_local_seo_v3317(project_items)
    service_seo_sync = sync_custom_service_seo_v3319(active)

    for p in products:
        folder = ROOT / 'urunler' / p['slug']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(render_product_page(p, choose_related(products, p)), encoding='utf-8')

    # V3.1.78: 404 is served at the originally requested nested URL, so
    # relative assets need a root base before global header/footer rewrites.
    error_page_sync = ensure_404_root_base()
    # V3.2.03-R1: canonical Rich Navigation, footer, SEO, accessibility and performance pass.
    nav_sync = sync_site_header_navigation()
    footer_sync = sync_global_footer()
    assistant_sync = sync_bg_assistant_widget()
    css_minify = write_minified_css_v3312()
    seo_a11y_sync = sync_seo_accessibility_performance_v3171()
    canonical_sync = sync_canonical_integrity_v3321()
    audit_fixes = sync_audit_fixes_v3326()
    site_content_state = read_site_content_v3175()
    sitemap_sync = build_canonical_sitemap_v3321()
    indexability_sync = build_indexability_manifest_v3322()
    asset_sync = sync_site_asset_versions()
    shell_verify = verify_v3164_public_shell()
    seo_audit = audit_v3171_public_pages()
    launch_audit = audit_v3312_launch_readiness()
    release_candidate = release_candidate_summary_v3314(launch_audit, shell_verify, seo_audit)
    release_gate = enforce_strict_release_v3314(release_candidate)
    return {'error_page_sync': error_page_sync, 'navigation_sync': nav_sync, 'footer_sync': footer_sync, 'assistant_sync': assistant_sync, 'seo_a11y_sync': seo_a11y_sync, 'canonical_sync': canonical_sync, 'audit_fixes': audit_fixes, 'css_minify': css_minify, 'site_content': site_content_state, 'sitemap_sync': sitemap_sync, 'indexability_sync': indexability_sync, 'asset_sync': asset_sync, 'shell_verify': shell_verify, 'audit': seo_audit, 'launch_audit': launch_audit, 'release_candidate': release_candidate, 'release_gate': release_gate, 'legal_pages': legal_pages, 'products': len(products), 'active': len(active), 'featured': len(featured), 'nfc_references': len(nfc_items), 'nfc_subpages': nfc_subpages, 'projects': project_build, 'local_seo_sync': local_seo_sync, 'service_seo_sync': service_seo_sync, 'corporate_references': len(corporate_items), 'prototypes': len(prototype_items), 'sitemap_urls': sitemap_sync.get('urls', 0)}


if __name__ == '__main__':
    print(json.dumps(build_site(), ensure_ascii=False, indent=2))
