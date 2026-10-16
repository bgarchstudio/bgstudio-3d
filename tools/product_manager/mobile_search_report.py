from pathlib import Path
import html
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]


def public_pages():
    for path in sorted(ROOT.rglob('*.html')):
        if 'tools' in path.relative_to(ROOT).parts:
            continue
        yield path


def tag_attr(tag, name):
    m = re.search(rf'\b{re.escape(name)}=["\']([^"\']*)["\']', tag, flags=re.I)
    return html.unescape(m.group(1)).strip() if m else ''


def meta_value(text, key, expected):
    for tag in re.findall(r'<meta\b[^>]*>', text, flags=re.I):
        if tag_attr(tag, key).casefold() == expected.casefold():
            return tag_attr(tag, 'content')
    return ''


def main():
    rows=[]
    for path in public_pages():
        text=path.read_text(encoding='utf-8', errors='replace')
        robots=meta_value(text,'name','robots').casefold()
        if 'noindex' in robots:
            continue
        title_match=re.search(r'<title>(.*?)</title>',text,flags=re.I|re.S)
        title=html.unescape(re.sub(r'\s+',' ',title_match.group(1)).strip()) if title_match else ''
        desc=meta_value(text,'name','description')
        viewport=meta_value(text,'name','viewport')
        rel=path.relative_to(ROOT).as_posix()
        rows.append({'path':rel,'title':title,'title_len':len(title),'desc_len':len(desc),'viewport':bool(viewport)})

    title_counts=Counter(row['title'] for row in rows if row['title'])
    long_titles=[row for row in rows if row['title_len']>62]
    very_long=[row for row in rows if row['title_len']>70]
    long_desc=[row for row in rows if row['desc_len']>160]
    duplicate_titles=[title for title,count in title_counts.items() if count>1]
    missing_viewport=[row for row in rows if not row['viewport']]

    print('BG Studio 3D Mobile Search Report')
    print(f'Indexable pages: {len(rows)}')
    print(f'Titles <= 62 chars: {sum(1 for r in rows if r["title_len"]<=62)}/{len(rows)}')
    print(f'Titles > 62 chars: {len(long_titles)}')
    print(f'Titles > 70 chars: {len(very_long)}')
    print(f'Descriptions > 160 chars: {len(long_desc)}')
    print(f'Duplicate titles: {len(duplicate_titles)}')
    print(f'Missing viewport: {len(missing_viewport)}')
    if long_titles:
        print('\nLong titles:')
        for row in sorted(long_titles,key=lambda r:r['title_len'],reverse=True):
            print(f'  {row["title_len"]:>3}  {row["path"]}  {row["title"]}')
    return 1 if very_long or long_desc or duplicate_titles or missing_viewport else 0


if __name__ == '__main__':
    raise SystemExit(main())
