from pathlib import Path
import argparse
import csv
import html
import json
import re
import sys
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = 'https://3d.bgstudio.com.tr'
MANIFEST = ROOT/'tools/product_manager/reports/indexability-manifest.json'


def load_manifest():
    if not MANIFEST.exists():
        raise SystemExit('Indexability manifest bulunamadı. Önce: python tools/product_manager/build.py')
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def normalize_url(value):
    raw = html.unescape(str(value or '')).strip()
    if not raw:
        return ''
    if raw.startswith('/'):
        raw = BASE_URL + raw
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return raw
    path = parts.path or '/'
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, '', ''))


def classify(url, manifest):
    clean = normalize_url(url)
    pages_by_url = {normalize_url(row.get('url')): row for row in manifest.get('pages', [])}
    pages_by_canonical = {normalize_url(row.get('canonical')): row for row in manifest.get('pages', []) if row.get('canonical')}
    aliases = {normalize_url(row.get('url')): row for row in manifest.get('aliases', [])}

    if clean in aliases:
        row = aliases[clean]
        return {
            'url': clean,
            'classification': 'alternate-canonical-or-redirect',
            'canonical': row.get('canonical'),
            'action': 'Hata olmak zorunda değil. Google bu index.html varyantını ayrı dizine almamalı; canonical hedefini kullanmalı.',
        }
    row = pages_by_url.get(clean) or pages_by_canonical.get(clean)
    if row:
        if not row.get('indexable'):
            return {
                'url': clean,
                'classification': 'intentional-noindex',
                'canonical': row.get('canonical'),
                'action': 'Dizine girmemesi bekleniyor. robots=noindex bilinçli.',
            }
        if row.get('in_sitemap'):
            return {
                'url': clean,
                'classification': 'canonical-indexable',
                'canonical': row.get('canonical'),
                'action': 'Site tarafı temiz. GSC “keşfedildi/tarandı ama dizine eklenmedi” diyorsa içerik/önem sinyali ve Google yeniden taraması incelenmeli.',
            }
        return {
            'url': clean,
            'classification': 'indexable-not-in-sitemap',
            'canonical': row.get('canonical'),
            'action': 'Teknik hata adayı: indexlenebilir sayfa sitemap dışında.',
        }
    return {
        'url': clean,
        'classification': 'unknown-to-current-build',
        'canonical': '',
        'action': 'Bu URL güncel build manifestinde yok. Eski URL, yanlış yol veya kaldırılmış içerik olabilir.',
    }


def read_gsc_file(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f'GSC dosyası bulunamadı: {p}')
    text = p.read_text(encoding='utf-8-sig', errors='replace')
    rows = []
    # CSV/TSV exportları için url benzeri bütün hücreleri al. Yanındaki reason/status
    # hücresi varsa raporda koru; dosya formatına bağımlı sert kolon adı istemeyiz.
    delimiter = '\t' if text.count('\t') > text.count(',') else ','
    try:
        parsed = list(csv.reader(text.splitlines(), delimiter=delimiter))
    except Exception:
        parsed = []
    if parsed:
        for row in parsed:
            urls = [cell.strip() for cell in row if '3d.bgstudio.com.tr' in cell]
            if not urls:
                continue
            reason = next((cell.strip() for cell in row if cell.strip() and '3d.bgstudio.com.tr' not in cell), '')
            for url in urls:
                rows.append({'url': url, 'gsc_reason': reason})
    else:
        for line in text.splitlines():
            match = re.search(r'https?://3d\.bgstudio\.com\.tr/\S*', line)
            if match:
                rows.append({'url': match.group(0).rstrip(' ,;'), 'gsc_reason': line.replace(match.group(0),'').strip(' ,;:-')})
    return rows


def main():
    parser = argparse.ArgumentParser(description='BG Studio 3D Search Console / indexability bridge')
    parser.add_argument('--url', action='append', default=[], help='Tek bir GSC URL örneğini sınıflandır. Birden fazla kullanılabilir.')
    parser.add_argument('--gsc-file', help='GSC dışa aktarımı veya URL listesi CSV/TSV/TXT')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='indexable-not-in-sitemap varsa exit 1')
    args = parser.parse_args()
    manifest = load_manifest()
    inputs = [{'url': u, 'gsc_reason': ''} for u in args.url]
    if args.gsc_file:
        inputs.extend(read_gsc_file(args.gsc_file))

    if inputs:
        results = []
        for item in inputs:
            result = classify(item['url'], manifest)
            if item.get('gsc_reason'):
                result['gsc_reason'] = item['gsc_reason']
            results.append(result)
        payload = {'summary': manifest.get('summary', {}), 'results': results}
    else:
        payload = {
            'summary': manifest.get('summary', {}),
            'noindex_pages': manifest.get('noindex_pages', []),
            'sample_index_html_aliases': manifest.get('aliases', [])[:12],
            'message': 'GSC URL örneklerini --url veya --gsc-file ile verirsen her URL güncel build ile eşleştirilir.',
        }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        s = payload.get('summary', {})
        print('BG Studio 3D Indexability Report')
        print(f"Physical: {s.get('physical_html_pages',0)} | Canonical indexable: {s.get('canonical_indexable_pages',0)} | Noindex: {s.get('noindex_pages',0)} | Sitemap: {s.get('sitemap_urls',0)}")
        if inputs:
            for row in payload['results']:
                reason = f" | GSC: {row.get('gsc_reason')}" if row.get('gsc_reason') else ''
                print(f"{row['classification']}: {row['url']} -> {row.get('canonical') or '-'}{reason}")
                print('  ', row['action'])
        else:
            print(payload['message'])
            for row in payload.get('noindex_pages', []):
                print('NOINDEX:', row.get('url'), '->', row.get('canonical'))

    if args.strict:
        bad = manifest.get('indexable_not_in_sitemap') or []
        if bad:
            sys.exit(1)


if __name__ == '__main__':
    main()
