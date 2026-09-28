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

    # robots.txt
    robots = ROOT/'robots.txt'
    if not robots.is_file():
        report['critical'].append('robots.txt eksik')
    else:
        rt = robots.read_text(encoding='utf-8', errors='replace')
        if f'Sitemap: {BASE_URL}/sitemap.xml' not in rt:
            report['critical'].append('robots.txt sitemap satırı eksik/yanlış')

    # sitemap.xml paths should have a generated route.
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
            for url in locs:
                if not url.startswith(BASE_URL):
                    report['critical'].append(f'sitemap external/yanlış origin: {url}')
                    continue
                route = url[len(BASE_URL):] or '/'
                if not route.endswith('/') and '.' not in route.rsplit('/',1)[-1]: route += '/'
                if route not in generated_routes and route != '/':
                    report['critical'].append(f'sitemap route üretilmemiş: {route}')
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
