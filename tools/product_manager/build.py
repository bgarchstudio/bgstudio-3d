from pathlib import Path
import json, re, html
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data' / 'products.json'
BASE_URL = 'https://3d.bgstudio.com.tr'
CATEGORY_LABELS = {
    'dekoratif': 'Dekoratif',
    'aydinlatma': 'Aydınlatma',
    'fonksiyonel': 'Fonksiyonel',
    'kisiye-ozel': 'Kişiye Özel',
}
FAQ = [
    ('Renk seçebilir miyim?', 'Mevcut filament seçenekleri ürüne göre değişir. Sipariş öncesinde uygun renkleri WhatsApp üzerinden birlikte netleştiriyoruz.'),
    ('Üretim ve teslim süresi ne kadar?', 'Süre; ürün, adet ve atölye yoğunluğuna göre değişebilir. Güncel üretim ve teslim bilgisini sipariş öncesinde paylaşıyoruz.'),
    ('3D baskı katman izleri normal mi?', 'Evet. Katman dokusu 3D baskı üretim yönteminin doğal karakteridir. Ürünler doğrudan baskı kalitesini koruyacak şekilde hazırlanır.'),
]


def esc(v):
    return html.escape(str(v or ''), quote=True)


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
    data = json.loads(DATA.read_text(encoding='utf-8'))
    return sorted(data, key=lambda p: (int(p.get('sort_order') or 9999), p.get('name', '').casefold()))


def category_label(p):
    return CATEGORY_LABELS.get(p.get('category'), p.get('category', '').replace('-', ' ').title())


def render_card(p, prefix=''):
    name = esc(p['name'])
    label = esc(category_label(p))
    price = esc(p.get('price_text') or 'Fiyat için iletişim')
    desc = esc(p.get('card_description') or p.get('description') or '')
    img = esc(prefix + p['main_image'])
    href = esc(prefix + 'urunler/' + p['slug'] + '/')
    if prefix == '../':
        href = esc('../urunler/' + p['slug'] + '/')
    search = ' '.join([label, price, name, desc, 'Ürünü incele']).casefold()
    w = int(p.get('main_image_width') or 1000)
    h = int(p.get('main_image_height') or 760)
    return (
        f'<article class="product-card" data-category="{esc(p.get("category"))}" data-search="{esc(search)}">\n'
        f'<a class="product-image" href="{href}"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{img}" width="{w}"/></a>\n'
        f'<div class="product-card-body"><div class="product-topline"><span>{label}</span><strong>{price}</strong></div>\n'
        f'<h3><a href="{href}">{name}</a></h3><p>{desc}</p>\n'
        f'<a class="product-link" href="{href}">Ürünü incele ↗</a>\n</div>\n</article>'
    )


def replace_between(text, start_marker, end_marker, content):
    pattern = re.compile(re.escape(start_marker) + r'.*?' + re.escape(end_marker), re.S)
    replacement = start_marker + '\n' + content + '\n' + end_marker
    if not pattern.search(text):
        raise RuntimeError(f'İşaret bulunamadı: {start_marker}')
    return pattern.sub(lambda _m: replacement, text, count=1)


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
    if p.get('price_value') not in (None, ''):
        obj['offers'] = {
            '@type': 'Offer',
            'priceCurrency': 'TRY',
            'price': str(p['price_value']),
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
    price = esc(p.get('price_text') or 'Fiyat için iletişim')
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

    options = p.get('options') or ['Standart / WhatsApp’ta netleştir']
    options_html = ''.join(f'<option value="{esc(o)}">{esc(o)}</option>' for o in options)
    tags = ''.join(
        f'<button class="option-choice{" selected" if i == 0 else ""}" data-order-choice="{esc(o)}" type="button">{esc(o)}</button>'
        for i, o in enumerate(options)
    )
    feats = ''.join(f'<li>{esc(x)}</li>' for x in (p.get('features') or ['3D baskı üretim', 'Sipariş öncesi detaylandırma']))
    related_html = ''.join(
        f'<a class="related-card" href="../{esc(r["slug"])}/">'
        f'<img alt="{esc(r["name"])}" decoding="async" height="{int(r.get("main_image_height") or 760)}" loading="lazy" '
        f'src="../../{esc(r["main_image"])}" width="{int(r.get("main_image_width") or 1000)}"/>'
        f'<div><h3>{esc(r["name"])}</h3><span>{esc(r.get("price_text") or "Fiyat için iletişim")}</span></div></a>'
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
<link href="https://fonts.googleapis.com" rel="preconnect"/><link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&amp;family=Playfair+Display:wght@500;600&amp;display=swap" rel="stylesheet"/><link href="../../assets/css/styles.css" rel="stylesheet"/>
<script type="application/ld+json">{render_schema(p)}</script><script data-schema="breadcrumb" type="application/ld+json">{breadcrumb}</script><script data-schema="faq" type="application/ld+json">{faq}</script>
<meta content="{robots}" name="robots"/><meta content="strict-origin-when-cross-origin" name="referrer"/><meta content="{w}" property="og:image:width"/><meta content="{h}" property="og:image:height"/><meta content="light" name="color-scheme"/>

</head><body><a class="skip-link" href="#main-content">İçeriğe geç</a>
<header class="site-header" id="top"><div class="shell nav-shell"><a aria-label="BG Studio 3D ana sayfa" class="brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><button aria-controls="primary-navigation" aria-expanded="false" aria-label="Menüyü aç" class="menu-toggle" type="button"><span></span><span></span></button><nav aria-label="Ana menü" class="main-nav" id="primary-navigation"><a aria-current="page" class="is-active" href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../hakkimizda/">Hakkımızda</a><a href="../../iletisim/">İletişim</a><a class="arch-link" href="https://bgstudio.com.tr" rel="noopener" target="_blank">Architecture ↗</a><a class="nav-cta" href="https://wa.me/905302466903" rel="noopener" target="_blank">WhatsApp</a></nav></div></header>
{notice}
<main id="main-content"><section class="product-detail shell"><div class="breadcrumb"><a href="../../">Ana Sayfa</a><span>/</span><a href="../">Ürünler</a><span>/</span><span>{name}</span></div><div class="product-detail-grid"><div class="product-gallery"><div aria-label="Seçili ürün görselini büyüt" class="gallery-stage zoomable-media" data-gallery-stage="" role="button" tabindex="0"><img alt="{name}" data-gallery-main="" decoding="async" height="{h}" src="{esc(main_rel)}" width="{w}"/></div><div aria-label="Ürün görselleri" class="gallery-thumbs"><button aria-label="Ürün görselini göster" aria-pressed="true" class="gallery-thumb active" data-gallery-alt="{name}" data-gallery-src="{esc(main_rel)}" type="button"><img alt="{name}" decoding="async" height="{h}" loading="lazy" src="{esc(main_rel)}" width="{w}"/><span>Ürün</span></button>{poster_thumb}{gallery_thumbs}</div><p class="gallery-hint">Görseli büyütmek için ana görsele tıkla.</p></div>
<div class="product-info"><p class="eyebrow">{label.upper()}</p><h1>{name}</h1><p class="product-lead">{desc}</p><div class="price-block"><small>Fiyat</small><strong>{price}</strong></div><div class="order-configurator" data-order-config="" data-product-name="{name}" data-product-price="{price}"><div class="order-config-head"><strong>Siparişini hazırla</strong><span>Seçimini yap, mesajı hazır gönder.</span></div><div class="order-controls"><label class="order-field"><span>Seçenek</span><select aria-label="Ürün seçeneği" data-order-option="">{options_html}</select></label><div class="order-field"><span>Adet</span><div class="qty-stepper"><button aria-label="Adedi azalt" data-qty-minus="" type="button">−</button><input aria-label="Adet" data-order-qty="" max="99" min="1" type="number" value="1"/><button aria-label="Adedi artır" data-qty-plus="" type="button">+</button></div></div></div><label class="order-field order-note-field"><span>Not (isteğe bağlı)</span><input data-order-note="" maxlength="160" placeholder="Örn. siyah renk, hediye olacak…" type="text"/></label><div class="order-summary"><span>Seçim:</span><strong data-order-summary="">{esc(options[0])} • 1 adet</strong></div><a class="primary-cta wide-cta smart-order-whatsapp" data-order-whatsapp="" href="#" rel="noopener" target="_blank">Seçimi WhatsApp’tan gönder ↗</a><p class="order-local-note">Seçimin site üzerinde kaydedilmez; yalnızca WhatsApp mesajını hazırlamak için kullanılır.</p></div><div class="product-action-row share-only-row"><button class="secondary-cta share-product" data-share-title="{name}" type="button">Ürün linkini paylaş</button></div><div class="detail-note">📍 Kuşadası elden teslim   •   📦 Türkiye geneli kargo</div><div class="product-facts"><div><small>Üretim</small><strong>3D baskı</strong></div><div><small>Teslim</small><strong>Kuşadası / kargo</strong></div><div><small>Seçenek</small><strong>Ürüne göre</strong></div><div><small>Sipariş</small><strong>WhatsApp</strong></div></div><div class="detail-section"><h2>Öne çıkan özellikler</h2><ul>{feats}</ul></div><div class="detail-section"><h2>Renk / seçenekler</h2><div class="option-tags">{tags}</div></div><div class="detail-section"><h2>Üretim notu</h2><p>{production}</p></div></div></div><div class="assurance-strip"><div><strong>Kuşadası</strong><span>Elden teslim</span></div><div><strong>Türkiye</strong><span>Kargo seçeneği</span></div><div><strong>Atölye</strong><span>3D baskı üretim</span></div><div><strong>Sipariş</strong><span>WhatsApp üzerinden</span></div></div></section>
<section class="order-process shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ SÜRECİ</p><h2>Nasıl ilerliyoruz?</h2></div></div><div class="order-steps"><article class="order-step"><span>01</span><h3>Ürünü seç</h3><p>Renk, adet ve varsa kişiselleştirme isteğini bize ilet.</p></article><article class="order-step"><span>02</span><h3>Detayları netleştir</h3><p>Üretim seçeneği ve teslim/kargo detaylarını sipariş öncesi netleştir.</p></article><article class="order-step"><span>03</span><h3>Üretim</h3><p>Ürün atölyede 3D baskı ile hazırlanır ve kontrol edilir.</p></article><article class="order-step"><span>04</span><h3>Teslim</h3><p>Kuşadası elden teslim veya uygun kargo seçeneğiyle gönderim.</p></article></div></section>
<section class="product-faq shell"><div class="section-title"><div><p class="eyebrow">SİPARİŞ ÖNCESİ</p><h2>Bilmen gerekenler.</h2></div></div><div class="faq">{faq_html}</div></section>
<section class="related-products shell"><div class="section-title"><div><p class="eyebrow">BUNLAR DA İLGİNİ ÇEKEBİLİR</p><h2>Atölyeden başka seçenekler.</h2></div></div><div class="related-grid">{related_html}</div></section><section class="detail-back shell"><a class="text-cta" href="../">← Tüm ürünlere dön</a></section></main>
<footer class="footer footer-dark"><div class="shell footer-inner"><div class="footer-topline"><a class="brand footer-brand" href="../../"><span class="brand-monogram">BG</span><span class="brand-text"><strong>STUDIO</strong><small>3DTR</small></span></a><p class="footer-tagline">Fikirden fiziksel ürüne. Kuşadası merkezli 3D baskı ve özel üretim.</p></div><div aria-label="BG Studio 3D sosyal ve marka bağlantıları" class="footer-socials"><a class="footer-social icon-instagram" href="https://instagram.com/bgstudio.3dtr" rel="noopener" target="_blank"><span>bgstudio.3dtr</span></a><a class="footer-social icon-facebook" href="https://www.facebook.com/bgstudio.3dtr" rel="noopener" target="_blank"><span>bgstudio.3dtr</span></a><a class="footer-social icon-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank"><span>WhatsApp</span></a><a class="footer-social icon-architecture" href="https://bgstudio.com.tr" rel="noopener" target="_blank"><span>bgstudio.com.tr</span></a></div><nav aria-label="Alt menü" class="footer-links"><a href="../../urunler/">Ürünler</a><a href="../../ozel-uretim/">Özel Üretim</a><a href="../../kurumsal/">Kurumsal</a><a href="../../nfc-qr/">NFC &amp; QR</a><a href="../../kusadasi-3d-baski/">Kuşadası 3D Baskı</a><a href="../../iletisim/">İletişim</a><a href="../../gizlilik/">Gizlilik</a><a href="../../siparis-bilgilendirme/">Sipariş Bilgilendirme</a></nav><div class="footer-legal"><p>BG STUDIO 3D © <span data-current-year="">2026</span>. Tüm hakları saklıdır. | 3D baskı, özel üretim ve kurumsal çözümler.</p><p class="footer-credit">BG Studio tarafından tasarlanmış ve geliştirilmiştir.</p></div></div></footer>
<script defer="" src="../../assets/js/consent.js"></script><script defer="" src="../../assets/js/main.js"></script><div aria-label="Hızlı işlemler" class="floating-actions"><a aria-label="WhatsApp üzerinden iletişime geç" class="floating-whatsapp" href="https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum." rel="noopener" target="_blank">WhatsApp</a><button aria-label="Sayfanın başına dön" class="back-to-top" type="button">↑</button></div><div class="mobile-product-cta"><div><strong>{name}</strong><span>{price}</span></div><a data-mobile-order-whatsapp="" href="#" rel="noopener" target="_blank">Siparişi hazırla</a></div></body></html>'''


def build_site():
    products = load_products()
    active = [p for p in products if p.get('active', True)]

    cat_path = ROOT / 'urunler/index.html'
    cat = cat_path.read_text(encoding='utf-8')
    cards = '\n'.join(render_card(p, '../') for p in active)
    cat = replace_between(cat, '<!-- PRODUCT_MANAGER:CATALOG_START -->', '<!-- PRODUCT_MANAGER:CATALOG_END -->', cards)
    cat = re.sub(r'(<p[^>]*id="catalog-count"[^>]*>)[^<]*(</p>)', lambda m: m.group(1) + f'{len(active)} ürün' + m.group(2), cat, count=1)
    cat_path.write_text(cat, encoding='utf-8')

    home_path = ROOT / 'index.html'
    home = home_path.read_text(encoding='utf-8')
    featured = [p for p in active if p.get('featured')][:8]
    homecards = '\n'.join(render_card(p, '') for p in featured)
    home = replace_between(home, '<!-- PRODUCT_MANAGER:FEATURED_START -->', '<!-- PRODUCT_MANAGER:FEATURED_END -->', homecards)
    home_path.write_text(home, encoding='utf-8')

    for p in products:
        folder = ROOT / 'urunler' / p['slug']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(render_product_page(p, choose_related(products, p)), encoding='utf-8')

    today = date.today().isoformat()
    static = [
        ('/', 1.0), ('/gizlilik/', .6), ('/hakkimizda/', .6), ('/iletisim/', .8),
        ('/kurumsal/', .9), ('/kusadasi-3d-baski/', .95), ('/nfc-qr/', .9), ('/ozel-uretim/', .9),
        ('/siparis-bilgilendirme/', .6), ('/teklif/', .8), ('/urunler/', .9),
    ]
    urls = [(BASE_URL + path, prio) for path, prio in static] + [(f"{BASE_URL}/urunler/{p['slug']}/", .7) for p in active]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, prio in urls:
        lines.append(f'  <url><loc>{url}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{prio}</priority></url>')
    lines.append('</urlset>')
    (ROOT / 'sitemap.xml').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'products': len(products), 'active': len(active), 'featured': len(featured), 'sitemap_urls': len(urls)}


if __name__ == '__main__':
    print(json.dumps(build_site(), ensure_ascii=False, indent=2))
