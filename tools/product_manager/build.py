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
            item = {**src, **{k:v for k,v in raw.items() if k in ('slug','source_kind','source_slug','theme','active','sort_order','home_link')}}
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
<link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"/><link href="../../assets/css/styles.css?v=3.1.4" rel="stylesheet"/>
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



SITE_ASSET_VERSION = '3.1.38'

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


def build_site():
    # V3.1.38: every reference page uses the same explicit card-tone source.
    ensure_explicit_reference_themes()
    # Kalıcı AppData kasasını her build öncesinde repo çıktısına yansıt.
    export_to_repo()
    products = load_products()
    active = [p for p in products if p.get('active', True)]

    cat_path = ROOT / 'urunler/index.html'
    cat = cat_path.read_text(encoding='utf-8')
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
    nfc_cards = '\n'.join(render_nfc_case(x, '../') for x in nfc_items)
    nfc_html = replace_between(nfc_html, '<!-- CONTENT_MANAGER:NFC_START -->', '<!-- CONTENT_MANAGER:NFC_END -->', nfc_cards)
    validate_reference_theme_output(nfc_html, nfc_items, 'NFC & QR')
    nfc_path.write_text(nfc_html, encoding='utf-8')

    corporate_items = [x for x in resolve_corporate_items() if x.get('active', True)]
    corporate_path = ROOT / 'kurumsal/index.html'
    corporate_html = ensure_corporate_markers(corporate_path.read_text(encoding='utf-8'))
    corporate_cards = '\n'.join(render_corporate_case(x, '../') for x in corporate_items)
    corporate_html = replace_between(corporate_html, '<!-- CONTENT_MANAGER:CORPORATE_START -->', '<!-- CONTENT_MANAGER:CORPORATE_END -->', corporate_cards)
    validate_reference_theme_output(corporate_html, corporate_items, 'Kurumsal')
    corporate_path.write_text(corporate_html, encoding='utf-8')

    # Keep the homepage real-work proof area synchronized with managed corporate references.
    home_html = home_path.read_text(encoding='utf-8')
    if '<!-- CONTENT_MANAGER:HOME_FIELD_START -->' in home_html and '<!-- CONTENT_MANAGER:HOME_FIELD_END -->' in home_html:
        home_field_cards = '\n'.join(render_home_field_case(x, i + 1, '') for i, x in enumerate(corporate_items[:4]))
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
