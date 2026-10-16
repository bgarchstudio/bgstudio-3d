from pathlib import Path
import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BUILD_PY = ROOT / 'tools/product_manager/build.py'
BASE_URL = 'https://3d.bgstudio.com.tr'


def expected_version():
    try:
        text = BUILD_PY.read_text(encoding='utf-8')
        match = re.search(r"SITE_ASSET_VERSION\s*=\s*['\"]([^'\"]+)", text)
        return match.group(1) if match else ''
    except Exception:
        return ''


def public_html_files():
    rows = []
    for path in ROOT.rglob('*.html'):
        if 'tools' in path.relative_to(ROOT).parts:
            continue
        rows.append(path)
    return sorted(rows)


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
    target = (ROOT / local.lstrip('/')) if local.startswith('/') else (html_path.parent / local)
    try:
        return target.resolve()
    except Exception:
        return None


def within_root(target):
    if target is None:
        return True
    try:
        root = ROOT.resolve()
        return target == root or root in target.parents
    except Exception:
        return False


def route_exists(target):
    if target is None:
        return True
    if not within_root(target):
        return False
    if target.is_file():
        return True
    if target.is_dir() and (target/'index.html').is_file():
        return True
    if not target.suffix and (target/'index.html').is_file():
        return True
    return False


def html_route(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel


def expected_canonical_for_page(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel == 'index.html':
        return BASE_URL + '/'
    if rel == '404.html':
        return BASE_URL + '/404.html'
    if rel.endswith('/index.html'):
        return BASE_URL + '/' + rel[:-len('index.html')]
    return BASE_URL + '/' + rel


def tag_attr(tag, name):
    match = re.search(rf'\b{re.escape(name)}=["\']([^"\']*)["\']', tag, flags=re.I)
    return html.unescape(match.group(1)).strip() if match else ''


def canonical_values(text):
    values = []
    for tag in re.findall(r'<link\b[^>]*>', text, flags=re.I):
        rel = tag_attr(tag, 'rel').casefold().split()
        if 'canonical' in rel:
            values.append(tag_attr(tag, 'href'))
    return values


def meta_value(text, key, expected):
    for tag in re.findall(r'<meta\b[^>]*>', text, flags=re.I):
        if tag_attr(tag, key).casefold() == expected.casefold():
            return tag_attr(tag, 'content')
    return ''


def check():
    version = expected_version()
    pages = public_html_files()
    report = {
        'version': version,
        'pages': len(pages),
        'critical': [],
        'warnings': [],
        'stats': {},
    }
    if not pages:
        report['critical'].append('Public HTML bulunamadı. Önce Product Manager build çalıştırılmalı.')
        report['ready'] = False
        return report

    forbidden = ('Garson Çağır', 'Hesap İste')
    generated_routes = {html_route(path) for path in pages}
    local_asset_refs = 0
    checked_links = 0
    indexable_canonicals = set()
    noindex_canonicals = set()

    for path in pages:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')

        # Core document metadata.
        for token,label in (
            ('<title>', 'title'), ('name="description"', 'description'),
            ('rel="canonical"', 'canonical'), ('name="viewport"', 'viewport'),
            ('id="main-content"', 'main-content')
        ):
            if token not in text:
                report['critical'].append(f'{rel}: {label} eksik')
        if version and f'name="bgstudio-build" content="{version}"' not in text:
            report['critical'].append(f'{rel}: bgstudio-build {version} meta değeri yok/eski')

        # V3.3.21 canonical integrity.
        expected_canonical = expected_canonical_for_page(path)
        canonicals = canonical_values(text)
        if len(canonicals) != 1:
            report['critical'].append(f'{rel}: canonical sayısı {len(canonicals)}, beklenen 1')
        canonical = canonicals[0] if canonicals else ''
        if canonical != expected_canonical:
            report['critical'].append(f'{rel}: canonical yanlış: {canonical or "eksik"} | beklenen {expected_canonical}')
        if '/index.html' in canonical or '?' in canonical or '#' in canonical:
            report['critical'].append(f'{rel}: canonical temiz URL değil: {canonical}')
        robots_value = meta_value(text, 'name', 'robots').casefold()
        if canonical:
            if 'noindex' in robots_value:
                noindex_canonicals.add(canonical)
            else:
                indexable_canonicals.add(canonical)
        og_url = meta_value(text, 'property', 'og:url')
        if og_url and og_url != canonical:
            report['critical'].append(f'{rel}: og:url canonical ile eşleşmiyor')
        if rel == 'teklif/index.html' and canonical != BASE_URL + '/teklif/':
            report['critical'].append('teklif/index.html canonical /teklif/ olmalı')
        if rel == '404.html' and 'noindex' not in robots_value:
            report['critical'].append('404.html noindex olmalı')

        # Structural IDs.
        ids = re.findall(r'\bid=["\']([^"\']+)["\']', text, flags=re.I)
        seen = set(); dup = []
        for value in ids:
            if value in seen and value not in dup: dup.append(value)
            seen.add(value)
        if dup:
            report['critical'].append(f'{rel}: duplicate id {", ".join(dup[:8])}')

        # Internal links.
        for href in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I):
            target = resolve_local(path, href)
            if target is not None:
                checked_links += 1
                if not route_exists(target):
                    report['critical'].append(f'{rel}: kırık link {href}')

        # Assets.
        refs = []
        refs += re.findall(r'<(?:img|script|source)\b[^>]*\bsrc=["\']([^"\']+)["\']', text, flags=re.I)
        refs += re.findall(r'<link\b[^>]*\bhref=["\']([^"\']+)["\']', text, flags=re.I)
        for value in refs:
            target = resolve_local(path, value)
            if target is not None:
                local_asset_refs += 1
                if not target.is_file():
                    report['critical'].append(f'{rel}: eksik asset {value}')

        # Scripts must not block parser.
        for tag in re.findall(r'<script\b[^>]*>', text, flags=re.I):
            if re.search(r'type=["\']application/(?:ld\+json|json)["\']', tag, flags=re.I):
                continue
            src = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, flags=re.I)
            if src and not src.group(1).startswith(('http://','https://','//')):
                if not re.search(r'\b(?:defer|async)\b', tag, flags=re.I) and not re.search(r'type=["\']module["\']', tag, flags=re.I):
                    report['critical'].append(f'{rel}: blocking script {src.group(1)}')

        # New-window security.
        for tag in re.findall(r'<a\b[^>]*\btarget=["\']_blank["\'][^>]*>', text, flags=re.I):
            rel_match = re.search(r'\brel=["\']([^"\']*)["\']', tag, flags=re.I)
            tokens = set(rel_match.group(1).lower().split()) if rel_match else set()
            if 'noopener' not in tokens:
                report['critical'].append(f'{rel}: target=_blank noopener eksik')

        # Asset versions.
        if version:
            for found in re.findall(r'assets/(?:css|js)/[^"\']+\?v=([^&"\']+)', text, flags=re.I):
                if found != version:
                    report['critical'].append(f'{rel}: eski asset version {found}, beklenen {version}')

        # Content guards.
        for phrase in forbidden:
            if phrase in text:
                report['critical'].append(f'{rel}: aktif olmayan özellik metni bulundu: {phrase}')
        if re.search(r'(?:src|href)=["\']http://', text, flags=re.I):
            report['critical'].append(f'{rel}: mixed content http:// bulundu')

        # Accessibility / layout warnings.
        if re.search(r'<img\b(?![^>]*\balt=)[^>]*>', text, flags=re.I):
            report['critical'].append(f'{rel}: alt eksik img')
        if re.search(r'<img\b(?!(?:[^>]*\bwidth=)(?=[^>]*\bheight=))[^>]*>', text, flags=re.I):
            report['warnings'].append(f'{rel}: width/height eksik img olabilir')
        h1 = len(re.findall(r'<h1\b', text, flags=re.I))
        if h1 != 1:
            report['warnings'].append(f'{rel}: h1 sayısı {h1}')

    # Rich Navigation runtime regression guard.
    runtime_js = ROOT/'assets/js/main.js'
    if not runtime_js.is_file():
        report['critical'].append('assets/js/main.js eksik')
    else:
        runtime_text = runtime_js.read_text(encoding='utf-8', errors='replace')
        for token, label in (
            ('Kuşadası 3D Baskı', 'runtime Kuşadası üretim linki'),
            ('nav-submenu-rich', 'runtime rich navigation'),
            ("HEADER_VERSION = 'v3.2.03'", 'runtime header version senkronu'),
        ):
            if token not in runtime_text:
                report['critical'].append(f'main.js: {label} eksik')

    # V3.3.20 priority product SEO regression checks.
    product_expectations = {
        'iron-man-eli-masa-lambasi': ('Iron Man Eli Masa Lambası', '3D Baskı'),
        'masa-alti-bardak-tutucu': ('Masa Altı Bardak Tutucu', 'Gaming'),
        'futbol-takimi-logolu-anahtarlik': ('Futbol Takımı Logolu Anahtarlık', '3D Baskı'),
    }
    for slug, expected in product_expectations.items():
        product_page = ROOT/'urunler'/slug/'index.html'
        if not product_page.is_file():
            report['critical'].append(f'ürün SEO hedefi eksik: {slug}')
            continue
        product_text = product_page.read_text(encoding='utf-8', errors='replace')
        title_match = re.search(r'<title>(.*?)</title>', product_text, flags=re.I|re.S)
        title_text = html.unescape(title_match.group(1)).strip() if title_match else ''
        if not all(token.casefold() in title_text.casefold() for token in expected):
            report['critical'].append(f'{slug}: SEO title hedefi eksik')
        if f'{BASE_URL if False else "https://3d.bgstudio.com.tr"}/urunler/{slug}/' not in product_text:
            report['critical'].append(f'{slug}: canonical ürün URL sinyali eksik')
        for token in ('#product', 'https://3d.bgstudio.com.tr/#organization', '../../kusadasi-3d-baski/'):
            if token not in product_text:
                report['critical'].append(f'{slug}: ürün SEO sinyali eksik: {token}')
        if 'aggregateRating' in product_text or '"review"' in product_text:
            report['critical'].append(f'{slug}: doğrulanmamış rating/review schema bulundu')

    # robots.txt
    robots = ROOT/'robots.txt'
    if not robots.is_file():
        report['critical'].append('robots.txt eksik')
    else:
        rt = robots.read_text(encoding='utf-8', errors='replace')
        if f'Sitemap: {BASE_URL}/sitemap.xml' not in rt:
            report['critical'].append('robots.txt sitemap satırı eksik/yanlış')
        for blocked in ('/tools/','/data/','/cloudflare/','/launcher/'):
            if f'Disallow: {blocked}' not in rt:
                report['critical'].append(f'robots.txt crawl guard eksik: {blocked}')

    # sitemap.xml must be an exact set of indexable canonical URLs.
    sitemap = ROOT/'sitemap.xml'
    sitemap_count = 0
    if not sitemap.is_file():
        report['critical'].append('sitemap.xml eksik')
    else:
        try:
            ns = {'sm':'http://www.sitemaps.org/schemas/sitemap/0.9'}
            tree = ET.parse(sitemap)
            locs = [node.text.strip() for node in tree.findall('.//sm:loc', ns) if node.text]
            sitemap_count = len(locs)
            sitemap_set = set(locs)
            if len(sitemap_set) != len(locs):
                report['critical'].append('sitemap.xml duplicate URL içeriyor')
            for url in locs:
                if not url.startswith(BASE_URL + '/'):
                    report['critical'].append(f'sitemap external/yanlış origin: {url}')
                if '/index.html' in url or '?' in url or '#' in url:
                    report['critical'].append(f'sitemap temiz canonical URL değil: {url}')
                if url in noindex_canonicals:
                    report['critical'].append(f'sitemap noindex URL içeriyor: {url}')
            missing = sorted(indexable_canonicals - sitemap_set)
            extra = sorted(sitemap_set - indexable_canonicals)
            for url in missing[:30]:
                report['critical'].append(f'sitemap indexable canonical eksik: {url}')
            for url in extra[:30]:
                report['critical'].append(f'sitemap canonical olmayan/ekstra URL: {url}')
        except Exception as exc:
            report['critical'].append(f'sitemap parse hatası: {exc}')

    # 404 nested-route safety.
    error_page = ROOT/'404.html'
    if not error_page.is_file():
        report['critical'].append('404.html eksik')
    elif '<base href="/">' not in error_page.read_text(encoding='utf-8', errors='replace'):
        report['critical'].append('404.html root <base href="/"> eksik')

    # CSS production artifact.
    source_css = ROOT/'assets/css/styles.css'
    min_css = ROOT/'assets/css/styles.min.css'
    if not source_css.is_file() or not min_css.is_file():
        report['critical'].append('styles.css / styles.min.css production asset eksik')
    else:
        before = source_css.stat().st_size; after = min_css.stat().st_size
        report['stats']['css_source_bytes'] = before
        report['stats']['css_minified_bytes'] = after
        if after >= before:
            report['warnings'].append('styles.min.css source CSS kadar veya daha büyük')

    report['stats']['internal_links_checked'] = checked_links
    report['stats']['local_assets_checked'] = local_asset_refs
    report['stats']['sitemap_urls'] = sitemap_count
    report['stats']['indexable_canonicals'] = len(indexable_canonicals)
    report['stats']['noindex_canonicals'] = len(noindex_canonicals)
    report['critical'] = list(dict.fromkeys(report['critical']))
    report['warnings'] = list(dict.fromkeys(report['warnings']))
    report['ready'] = len(report['critical']) == 0
    return report


def main():
    parser = argparse.ArgumentParser(description='BG Studio 3D production release checker')
    parser.add_argument('--json', action='store_true', help='JSON çıktı ver')
    parser.add_argument('--strict', action='store_true', help='critical hata varsa exit 1')
    args = parser.parse_args()
    report = check()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        state = 'READY ✅' if report['ready'] else 'NOT READY ❌'
        print(f"BG Studio 3D {report.get('version') or ''} Release Check: {state}")
        print(f"Pages: {report['pages']} | Critical: {len(report['critical'])} | Warnings: {len(report['warnings'])}")
        for item in report['critical'][:30]: print('CRITICAL:', item)
        for item in report['warnings'][:20]: print('WARN:', item)
    if args.strict and not report['ready']:
        sys.exit(1)
    if report['pages'] == 0:
        sys.exit(2)


if __name__ == '__main__':
    main()
