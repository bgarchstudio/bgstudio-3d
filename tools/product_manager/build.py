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


def load_site_settings():
    data = get_collection('site_settings', {})
    return data if isinstance(data, dict) else {}


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
    }


def default_nfc_family_themes():
    return {
        'feedback_duo': 'dark',
        'restaurant_packages': 'light',
        'quick_stand': 'light',
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
    for key, fixed in fixed_paths.items():
        row = incoming.get(key) if isinstance(incoming.get(key), dict) else {}
        image = str(row.get('image') or '').replace('\\', '/').lstrip('/')
        # V3.1.48 self-heal: fixed uploaded file wins if the DB pointer was lost.
        if (ROOT / fixed).is_file():
            image = fixed
        elif not image or not (ROOT / image).is_file():
            image = ''
        default_theme = str((default_nfc_media_settings().get(key) or {}).get('theme') or 'light').lower()
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
    body = f'<div class="case-body"><span class="case-type">{kicker}</span><h3>{headline}</h3><p>{desc}</p><div class="case-meta">{tags}</div></div>'
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
    body = f'<div class="case-body">{identity}<h3>{name}</h3><p>{desc}</p><div class="case-meta">{tags}</div></div>'
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
    body = f'<div class="case-body">{identity}<h3>{headline}</h3><p>{desc}</p><div class="case-meta">{tags}</div></div>'
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
    link = home_case_link(item)
    target_key = link.split('#', 1)[1] if '#' in link else 'referans-' + reference_identity(item)
    ref_id = reference_identity(item, item.get('source_slug') if item.get('source_kind') == 'nfc' else item.get('slug'))
    return f'<article class="field-work-card{theme}" data-card-theme="{card_theme}" data-reference-target="{esc(target_key)}" data-reference-id="{esc(ref_id)}" data-reference-name="{esc(raw_name)}"><div class="field-work-top">{profile}<div><span class="field-work-no">{index:02d}</span><span class="field-work-type">{category}</span></div></div><h3>{headline}</h3><p>{desc}</p><div class="field-work-meta">{tags}</div><a class="field-work-link" href="{esc(link)}">İşi incele ↗</a></article>'

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


def render_card(p, prefix=''):
    name = esc(p['name'])
    label = esc(category_label(p))
    price = esc(active_price_text(p))
    price_markup = card_price_html(p)
    desc = esc(p.get('card_description') or p.get('description') or '')
    img = esc(prefix + p['main_image'])
    href = esc(prefix + 'urunler/' + p['slug'] + '/')
    if prefix == '../':
        href = esc('../urunler/' + p['slug'] + '/')
    search = ' '.join([label, price, name, desc, ' '.join(str(x) for x in (p.get('tags') or [])), 'Ürünü incele']).casefold()
    w = int(p.get('main_image_width') or 1000)
    h = int(p.get('main_image_height') or 760)
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
                'availability': 'https://schema.org/InStock',
                'eligibleQuantity': {'@type': 'QuantitativeValue', 'value': int(t.get('quantity') or 1), 'unitText': 'adet'},
            }
            for t in tiers if t.get('price_value') not in (None, '')
        ]
    elif active_price_value(p) not in (None, ''):
        obj['offers'] = {
            '@type': 'Offer',
            'priceCurrency': 'TRY',
            'price': str(active_price_value(p)),
            'availability': 'https://schema.org/InStock',
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

    return f'''<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8"/><meta content="width=device-width, initial-scale=1" name="viewport"/><meta content="#f5ede2" name="theme-color"/>
<title>{title}</title><meta content="{seo_desc}" name="description"/>
<link href="{canonical}" rel="canonical"/>
<meta content="product" property="og:type"/><meta content="tr_TR" property="og:locale"/><meta content="BG Studio 3D" property="og:site_name"/>
<meta content="{title}" property="og:title"/><meta content="{card_desc}" property="og:description"/><meta content="{canonical}" property="og:url"/><meta content="{main_abs}" property="og:image"/><meta content="{name} | BG Studio 3D" property="og:image:alt"/>
<meta content="summary_large_image" name="twitter:card"/><meta content="{title}" name="twitter:title"/><meta content="{card_desc}" name="twitter:description"/><meta content="{main_abs}" name="twitter:image"/>
<link href="../../favicon.ico" rel="icon" sizes="any"/><link href="../../assets/brand/favicon-32x32.png" rel="icon" sizes="32x32" type="image/png"/><link href="../../assets/brand/favicon-16x16.png" rel="icon" sizes="16x16" type="image/png"/><link href="../../apple-touch-icon.png" rel="apple-touch-icon" sizes="180x180"/><link href="../../site.webmanifest" rel="manifest"/>
<link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"/><link href="../../assets/css/styles.css?v=3.1.52" rel="stylesheet"/>
<script type="application/ld+json">{render_schema(p)}</script><script data-schema="breadcrumb" type="application/ld+json">{breadcrumb}</script><script data-schema="faq" type="application/ld+json">{faq}</script>
<meta content="{robots}" name="robots"/><meta content="strict-origin-when-cross-origin" name="referrer"/><meta content="{w}" property="og:image:width"/><meta content="{h}" property="og:image:height"/><meta content="light" name="color-scheme"/>

</head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>
<header class="site-header" id="top"><div class="shell nav-shell"><a aria-label="BG Studio 3D ana sayfa" class="brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><button aria-controls="primary-navigation" aria-expanded="false" aria-label="Menüyü aç" class="menu-toggle" type="button"><span></span><span></span></button><nav aria-label="Ana menü" class="main-nav" id="primary-navigation"><a aria-current="page" class="is-active" href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../prototip-parca/">Prototip &amp; Parça Üretim</a><a href="../../hakkimizda/">Hakkımızda</a><a href="../../iletisim/">İletişim</a><a class="arch-link" href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture ↗</a><a class="nav-cta" href="https://wa.me/905302466903" rel="noopener" target="_blank">WhatsApp</a></nav></div></header>
{notice}
<main id="main-content"><section class="product-detail shell"><div class="breadcrumb"><a href="../../">Ana Sayfa</a><span>/</span><a href="../">Ürünler</a><span>/</span><span>{name}</span></div><div class="product-detail-grid"><div class="product-gallery"><div aria-label="Seçili ürün görselini büyüt" class="gallery-stage zoomable-media" data-gallery-stage="" role="button" tabindex="0"><img alt="{name}" data-gallery-main="" decoding="async" fetchpriority="high" height="{h}" src="{esc(main_rel)}" width="{w}"/></div><div aria-label="Ürün görselleri" class="gallery-thumbs"><button aria-label="Ürün görselini göster" aria-pressed="true" class="gallery-thumb active" data-gallery-alt="{name}" data-gallery-src="{esc(main_rel)}" type="button"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{esc(main_rel)}" width="{w}"/><span>Ürün</span></button>{poster_thumb}{gallery_thumbs}</div><p class="gallery-hint">Görseli büyütmek için ana görsele tıkla.</p></div>
<div class="product-info"><p class="eyebrow">{label.upper()}</p><h1>{name}</h1><p class="product-lead">{desc}</p><div class="price-block{' has-discount' if sale_info else ''}"><small>Fiyat</small><div class="price-display-row">{price_list_html}<strong data-product-price-display="">{selected_display_price}</strong>{discount_badge_html}</div></div>{tier_cards_html}<div class="order-configurator" data-order-config="" data-product-name="{name}" data-product-price="{price}" data-product-base-price-value="{esc(active_base_value or '')}"><div class="order-config-head"><strong>Siparişini hazırla</strong><span>Seçimini yap, mesajı hazır gönder.</span></div><div class="order-controls{' has-tier' if pricing_tiers else ''}{' color-mode' if color_public else ''}">{option_field_html}{tier_field_html}<div class="order-field order-qty-field"><span>{'Set adedi' if pricing_tiers else 'Adet'}</span><div class="qty-stepper"><button aria-label="Adedi azalt" data-qty-minus="" type="button">−</button><input aria-label="Adet" data-order-qty="" max="12" min="1" type="number" value="1"/><button aria-label="Adedi artır" data-qty-plus="" type="button">+</button></div></div></div>{color_picker_html}{color_data_html}<label class="order-field order-note-field"><span>Not (isteğe bağlı)</span><input data-order-note="" maxlength="160" placeholder="Örn. hediye olacak, teslim notu…" type="text"/></label><div class="order-summary"><span>Seçim:</span><strong data-order-summary="">{esc(initial_summary)}</strong></div><a class="primary-cta wide-cta smart-order-whatsapp" data-order-whatsapp="" href="#" rel="noopener" target="_blank">Seçimi WhatsApp’tan gönder ↗</a><p class="order-local-note">Seçimin site üzerinde kaydedilmez; yalnızca WhatsApp mesajını hazırlamak için kullanılır.</p></div><div class="product-action-row share-only-row"><button class="secondary-cta share-product" data-share-title="{name}" type="button">Ürün linkini paylaş</button></div><div class="detail-note">📍 Kuşadası elden teslim   •   📦 Türkiye geneli kargo</div><div class="product-facts"><div><small>Üretim</small><strong>3D baskı</strong></div><div><small>Teslim</small><strong>Kuşadası / kargo</strong></div><div><small>Seçenek</small><strong>Ürüne göre</strong></div><div><small>Sipariş</small><strong>WhatsApp</strong></div></div><div class="detail-section"><h2>Öne çıkan özellikler</h2><ul>{feats}</ul></div><div class="detail-section"><h2>{detail_options_heading}</h2><div class="option-tags">{tags or '<span>WhatsApp üzerinden netleştirilir.</span>'}</div></div>{product_tag_section}<div class="detail-section"><h2>Üretim notu</h2><p>{production}</p></div></div></div><div class="assurance-strip"><div><strong>Kuşadası</strong><span>Elden teslim</span></div><div><strong>Türkiye</strong><span>Kargo seçeneği</span></div><div><strong>Atölye</strong><span>3D baskı üretim</span></div><div><strong>Sipariş</strong><span>WhatsApp üzerinden</span></div></div></section>
<section class="order-process shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ SÜRECİ</p><h2>Nasıl ilerliyoruz?</h2></div></div><div class="order-steps"><article class="order-step"><span>01</span><h3>Ürünü seç</h3><p>Renk, adet ve varsa kişiselleştirme isteğini bize ilet.</p></article><article class="order-step"><span>02</span><h3>Detayları netleştir</h3><p>Üretim seçeneği ve teslim/kargo detaylarını sipariş öncesi netleştir.</p></article><article class="order-step"><span>03</span><h3>Üretim</h3><p>Ürün atölyede 3D baskı ile hazırlanır ve kontrol edilir.</p></article><article class="order-step"><span>04</span><h3>Teslim</h3><p>Kuşadası elden teslim veya uygun kargo seçeneğiyle gönderim.</p></article></div></section>
<section class="product-faq shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ ÖNCESİ</p><h2>Bilmen gerekenler.</h2></div></div><div class="faq">{faq_html}</div></section>
<section class="related-products shell"><div class="section-title"><div><p class="eyebrow">BUNLAR DA İLGİNİ ÇEKEBİLİR</p><h2>Atölyeden başka seçenekler.</h2></div></div><div class="related-grid">{related_html}</div></section><section class="detail-back shell"><a class="text-cta" href="../">← Tüm ürünlere dön</a></section></main>
<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı ve özel üretim.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a aria-label="BG Studio 3D Instagram" class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>bgstudio.3dtr</span></a><a aria-label="BG Studio 3D Facebook" class="footer-social icon-facebook" href="https://www.facebook.com/bgstudio.3dtr" rel="me noopener" target="_blank"><span>Facebook · BG Studio 3D</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../prototip-parca/">Prototip &amp; Parça Üretim</a><a href="../../kusadasi-3d-baski/">Kuşadası 3D Baskı</a><a href="../../iletisim/">İletişim</a><a href="../../gizlilik/">Gizlilik</a><a href="../../siparis-bilgilendirme/">Sipariş Bilgilendirme</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır. | 3D baskı, özel üretim ve kurumsal çözümler.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>
<script defer="" src="../../assets/js/consent.js"></script><script defer="" src="../../assets/js/main.js?v=3.1.4"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div><div class="mobile-product-cta"><div><strong>{name}</strong><span class="mobile-price-wrap">{price_list_html}<b data-mobile-price="">{selected_display_price}</b></span></div><a data-mobile-order-whatsapp="" href="#" rel="noopener" target="_blank">Siparişi hazırla</a></div></body></html>'''



SITE_ASSET_VERSION = '3.1.56'

def sync_site_asset_versions():
    """Bump shared site CSS/JS query strings in-place without replacing page content."""
    for html_path in ROOT.rglob('*.html'):
        if 'tools' in html_path.relative_to(ROOT).parts:
            continue
        try:
            text = html_path.read_text(encoding='utf-8')
        except Exception:
            continue
        updated = re.sub(r'((?:\.\./)*assets/css/styles\.css\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', text)
        updated = re.sub(r'((?:\.\./)*assets/js/main\.js\?v=)[^"\']+', rf'\g<1>{SITE_ASSET_VERSION}', updated)
        if updated != text:
            html_path.write_text(updated, encoding='utf-8')

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

    return f'''<!-- NFC_PLATFORM_V156_START -->
<!-- NFC_REFERENCE_SLOT -->
<section class="page-hero nfc-platform-hero"><div class="shell page-hero-grid reveal"><div><p class="eyebrow">BG STUDIO NFC İŞLETME PLATFORMU</p><h1>Bir etiketten fazlası. İşletmen için dijital altyapı.</h1><p class="lead">BG Studio NFC; işletmeye özel fiziksel standları, NFC ve isteğe bağlı QR erişimini, müşteri etkileşimlerini, dijital menüyü, değerlendirme akışını, analitikleri ve yönetim panelini tek altyapıda birleştirir.</p><div class="hero-actions"><a class="primary-cta" href="../teklif/?tur=nfc">İşletmen için teklif al ↗</a><a class="secondary-cta" href="#urun-aileleri">Çözümleri incele ↓</a></div></div><aside class="info-panel info-panel-dark nfc-platform-metrics"><p class="eyebrow">TEK SİSTEMDE</p><div class="metric-grid"><div class="metric"><strong>Fiziksel</strong><span>İşletmeye özel 3D stand</span></div><div class="metric"><strong>Dijital</strong><span>Menü, feedback ve bağlantılar</span></div><div class="metric"><strong>Panel</strong><span>İşletme müşteri paneli</span></div><div class="metric"><strong>Analitik</strong><span>Stand / masa bazlı performans</span></div></div></aside></div></section>
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

<div class="special-ready-card"><div class="special-ready-copy"><p class="eyebrow">ÖZEL RESTORAN HAZIR PAKETLERİ</p><h3>Yüksek kapasitede restoran altyapısı.</h3><p>20 masanın üzerindeki restoranlarda aynı Standart Restoran altyapısı işletmenin kapasitesine göre ölçeklenir. Masa sayını seç; NFC paket bedeli, QR hesabı ve ek tasarım hizmetleri sağdaki kartta anında hesaplansın.</p><div class="nfc-capacity-selector-head"><strong>Masa sayını seç</strong><span>Aşağıdaki kartlardan birine tıkla. Sağdaki hesap anında yenilenir.</span></div><div class="nfc-capacity-chips" role="group" aria-label="Özel Restoran hazır masa kapasitesi">{capacity_chips}</div></div><div class="special-ready-highlight" data-special-package-calculator data-qr-unit="{qr_unit}" data-menu-price="{menu_design}" data-logo-price="{logo_design}"><span class="package-kicker" data-special-title>GÜNCEL {special_default_key} MASA HAZIR PAKETİ</span><div class="special-ready-metrics"><span><b data-special-tables>{special_default_key}</b>Masa</span><span><b data-special-nfc>{special_qr_count}</b>NFC</span></div><div class="special-ready-price"><small data-special-price-year>{year} NFC hazır paket bedeli</small><strong data-special-base-price>{money(special_default.get('price'))}</strong><span data-special-renewal>Yıllık yenileme: {money(special_default.get('renewal'))}</span></div><div class="special-ready-options"><button type="button" data-special-option="qr" aria-pressed="false"><span>QR sistemi</span><b data-special-qr-cost>+{money(special_qr_cost)}</b><small data-special-qr-copy>{special_qr_count} QR × {money(qr_unit)} / QR</small></button><button type="button" data-special-option="menu" aria-pressed="false"><span>Menü Tasarımı</span><b data-special-menu-cost>+{money(menu_design)}</b><small>{esc(menu_scope_copy)}</small></button><button type="button" data-special-option="logo" aria-pressed="false"><span>Logo Tasarımı</span><b data-special-logo-cost>+{money(logo_design)}</b><small>İşletmeye özel logo · stand ve dijital menü kullanımına uyumlu</small></button></div><div class="special-ready-breakdown"><div><span>NFC hazır paket</span><b data-special-line-base>{money(special_default.get('price'))}</b></div><div><span>QR sistemi</span><b data-special-line-qr>Seçilmedi</b></div><div><span>Menü Tasarımı</span><b data-special-line-menu>Seçilmedi</b></div><div><span>Logo Tasarımı</span><b data-special-line-logo>Seçilmedi</b></div></div><div class="special-ready-total"><span>Seçili toplam</span><strong data-special-total>{money(special_default.get('price'))}</strong><small>NFC paket bedeli + seçtiğin ek hizmetler</small></div><a class="secondary-cta" data-special-offer href="../teklif/?tur=nfc&amp;paket=ozel-kapasite&amp;masa={special_default_key}">{special_default_key} masa için teklifi al</a></div></div>
</section>

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
<!-- NFC_PLATFORM_V156_END -->'''

def rebuild_nfc_platform_sections(html_text, theme_overrides=None):
    """Replace public NFC platform/package copy without touching field references."""
    rendered = render_nfc_platform_sections(theme_overrides=theme_overrides)
    marker_pattern = re.compile(
        r'<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156)_START\s*-->.*?<!--\s*NFC_PLATFORM_V(?:145|153|154|155|156)_END\s*-->',
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
        '<section class="section-pad custom-band nfc-reference-first"><div class="shell reveal">'
        '<div class="split-title"><h2>Sahada çalışan örnekler.</h2>'
        '<p>Kurulan her sistem işletmenin masa sayısı, hedef kanalları ve kullanım senaryosuna göre farklılaşır. '
        'Aşağıdaki örnekler sahada uygulanan kurulumlardan seçildi.</p></div>'
        '<div class="case-grid case-grid-managed"><!-- CONTENT_MANAGER:NFC_START -->\n'
        + cards_html +
        '\n<!-- CONTENT_MANAGER:NFC_END --></div></div></section>'
    )


def rebuild_nfc_reference_section(html_text, cards_html):
    """Rebuild public NFC field references as the first content block of the NFC page.

    V3.1.56 keeps proof-of-work as the first content block of the NFC page. The platform renderer
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

    hero_anchor = re.search(
        r'<section\b[^>]*class="[^"]*page-hero[^"]*nfc-platform-hero[^"]*"',
        html_text,
        flags=re.I,
    )
    if not hero_anchor:
        hero_anchor = re.search(r'<section\b[^>]*class="[^"]*page-hero[^"]*"', html_text, flags=re.I)
    if hero_anchor:
        return html_text[:hero_anchor.start()] + section + '\n' + html_text[hero_anchor.start():]

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
    cards = '\n'.join(render_card(p, '../') for p in active)
    cat = replace_between(cat, '<!-- PRODUCT_MANAGER:CATALOG_START -->', '<!-- PRODUCT_MANAGER:CATALOG_END -->', cards)
    # V3.1.3: show the complete product taxonomy even before the first item is added to a category.
    # This makes new shelves such as Pet Ürünleri visible immediately in the catalog UI.
    present_categories = list(CATEGORY_ORDER)
    # Include any future/custom valid category after the preferred order.
    present_categories += sorted({p.get('category') for p in active if p.get('category') and p.get('category') not in present_categories}, key=lambda c: category_label({'category': c}))
    filter_buttons = ['<button aria-pressed="true" class="filter-btn active" data-filter="all" type="button">Tümü</button>']
    filter_buttons += [f'<button aria-pressed="false" class="filter-btn" data-filter="{esc(c)}" type="button">{esc(category_label({"category": c}))}</button>' for c in present_categories]
    filter_html = '<div aria-label="Ürün kategorileri" class="filter-row" role="group">' + ''.join(filter_buttons) + '</div>'
    cat = re.sub(r'<div aria-label="Ürün kategorileri" class="filter-row" role="group">.*?</div>', filter_html, cat, count=1, flags=re.S)
    cat = re.sub(r'(<p[^>]*id="catalog-count"[^>]*>)[^<]*(</p>)', lambda m: m.group(1) + f'{len(active)} ürün' + m.group(2), cat, count=1)
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
    validate_nfc_reference_output(nfc_html, nfc_items)
    validate_reference_theme_output(nfc_html, nfc_items, 'NFC & QR')
    nfc_path.write_text(nfc_html, encoding='utf-8')

    # Corporate-page visibility is independent from NFC publication. Linked NFC
    # records may stay live on NFC & QR (and on the homepage proof area) while
    # being temporarily hidden from the Corporate References page.
    corporate_all_active = [x for x in resolve_corporate_items() if x.get('active', True)]
    corporate_items = [x for x in corporate_all_active if not (x.get('source_kind') == 'nfc' and not bool(x.get('show_in_corporate', True)))]
    corporate_path = ROOT / 'kurumsal/index.html'
    corporate_html = ensure_corporate_markers(corporate_path.read_text(encoding='utf-8'))
    corporate_cards = '\n'.join(render_corporate_case(x, '../') for x in corporate_items)
    corporate_html = replace_between(corporate_html, '<!-- CONTENT_MANAGER:CORPORATE_START -->', '<!-- CONTENT_MANAGER:CORPORATE_END -->', corporate_cards)
    validate_reference_theme_output(corporate_html, corporate_items, 'Kurumsal')
    corporate_path.write_text(corporate_html, encoding='utf-8')

    # Homepage Sahadan İşler remains independent from the Corporate-page mirror
    # switch, so hiding NFC cards from /kurumsal/ does not erase field proof.
    home_html = home_path.read_text(encoding='utf-8')
    if '<!-- CONTENT_MANAGER:HOME_FIELD_START -->' in home_html and '<!-- CONTENT_MANAGER:HOME_FIELD_END -->' in home_html:
        home_field_cards = '\n'.join(render_home_field_case(x, i + 1, '') for i, x in enumerate(corporate_all_active[:4]))
        home_html = replace_between(home_html, '<!-- CONTENT_MANAGER:HOME_FIELD_START -->', '<!-- CONTENT_MANAGER:HOME_FIELD_END -->', home_field_cards)
        home_path.write_text(home_html, encoding='utf-8')

    prototype_items = [x for x in load_managed_content(PROTOTYPE_DATA) if x.get('active', True)]
    prototype_path = ROOT / 'prototip-parca/index.html'
    prototype_html = prototype_path.read_text(encoding='utf-8')
    prototype_cards = '\n'.join(render_managed_case(x, '../') for x in prototype_items)
    prototype_html = replace_between(prototype_html, '<!-- CONTENT_MANAGER:PROTOTYPE_START -->', '<!-- CONTENT_MANAGER:PROTOTYPE_END -->', prototype_cards)
    validate_reference_theme_output(prototype_html, prototype_items, 'Prototip')
    prototype_path.write_text(prototype_html, encoding='utf-8')

    for p in products:
        folder = ROOT / 'urunler' / p['slug']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(render_product_page(p, choose_related(products, p)), encoding='utf-8')

    today = date.today().isoformat()
    static = [
        ('/', 1.0), ('/gizlilik/', .6), ('/hakkimizda/', .6), ('/iletisim/', .8),
        ('/kurumsal/', .9), ('/kusadasi-3d-baski/', .95), ('/nfc-qr/', .95), ('/prototip-parca/', .9), ('/ozel-uretim/', .9),
        ('/siparis-bilgilendirme/', .6), ('/teklif/', .8), ('/urunler/', .9),
    ]
    urls = [(BASE_URL + path, prio) for path, prio in static] + [(f"{BASE_URL}/urunler/{p['slug']}/", .7) for p in active]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, prio in urls:
        lines.append(f'  <url><loc>{url}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{prio}</priority></url>')
    lines.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    sync_site_asset_versions()
    return {'products': len(products), 'active': len(active), 'featured': len(featured), 'nfc_references': len(nfc_items), 'corporate_references': len(corporate_items), 'prototypes': len(prototype_items), 'sitemap_urls': len(urls)}


if __name__ == '__main__':
    print(json.dumps(build_site(), ensure_ascii=False, indent=2))
