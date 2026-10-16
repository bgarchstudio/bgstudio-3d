from pathlib import Path
import re
import html

ROOT = Path(__file__).resolve().parents[2]

def attr(tag, name):
    m = re.search(rf'\b{re.escape(name)}=["\']([^"\']*)["\']', tag, flags=re.I)
    return html.unescape(m.group(1)).strip() if m else ''

pages = images = dimensions = lazy = eager = high = responsive = 0
issues = []
for path in sorted(ROOT.rglob('*.html')):
    if 'tools' in path.relative_to(ROOT).parts:
        continue
    pages += 1
    text = path.read_text(encoding='utf-8', errors='replace')
    tags = re.findall(r'<img\b[^>]*>', text, flags=re.I)
    images += len(tags)
    for tag in tags:
        if attr(tag,'width') and attr(tag,'height'): dimensions += 1
        else: issues.append(f'{path.relative_to(ROOT)}: intrinsic dimensions missing')
        if attr(tag,'loading').casefold() == 'lazy': lazy += 1
        if attr(tag,'loading').casefold() == 'eager': eager += 1
        if attr(tag,'fetchpriority').casefold() == 'high': high += 1
        if attr(tag,'srcset'): responsive += 1

print('BG Studio 3D Image / CWV Report')
print(f'Pages: {pages}')
print(f'Images: {images}')
print(f'Intrinsic dimensions: {dimensions}/{images}')
print(f'Lazy: {lazy} | Eager: {eager} | High priority: {high}')
print(f'Responsive srcset images: {responsive}')
print(f'Image layout issues: {len(issues)}')
for issue in issues[:20]:
    print('WARN:', issue)
