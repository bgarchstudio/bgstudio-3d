"""v3.3.97 · Müşteri yorumları.

Kaynak: müşterinin BG Studio 3D'ye gönderdiği gerçek memnuniyet mesajı (WhatsApp, Instagram,
e-posta, yüz yüze). Kurallar:
- Yalnızca müşterinin yayın izni olan (consent=True) ve yayında (active=True) yorumlar sitede görünür.
- Puan (rating 1–5) yalnızca müşteri kendisi verdiyse girilir; 0 = puan yok.
- Google'a giden Review / AggregateRating yalnızca puanlı yorumlardan üretilir. Puansız mesajlar
  sayfada alıntı olarak görünür, şemaya girmez.

Veri biçimi (storage koleksiyonu 'reviews', repo kopyası data/reviews.json):
  {"id": "r-20261113-ab12", "product_slug": "spiral-masa-lambasi", "author": "Ayşe K.",
   "text": "...", "rating": 5, "date": "2026-11-13", "source": "whatsapp",
   "consent": true, "active": true, "created_at": "2026-11-13T15:20:00"}
"""
import re
import secrets
from datetime import datetime
from html import escape as _e

SOURCES = {
    'whatsapp': 'WhatsApp mesajı',
    'instagram': 'Instagram mesajı',
    'eposta': 'E-posta',
    'yuz-yuze': 'Yüz yüze',
    'diger': 'Müşteri mesajı',
}
MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


def esc(v):
    return _e(str(v), quote=True)


def normalize(item):
    """Clean one review coming from the panel. Raises ValueError with a Turkish message."""
    item = dict(item or {})
    slug = str(item.get('product_slug') or '').strip()
    author = re.sub(r'\s+', ' ', str(item.get('author') or '')).strip()[:60]
    text = re.sub(r'[ \t]+', ' ', str(item.get('text') or '')).strip()[:1200]
    if not slug:
        raise ValueError('Yorumun ait olduğu ürünü seç.')
    if not text:
        raise ValueError('Müşterinin mesajını yaz.')
    if not author:
        raise ValueError('Sitede görünecek ismi yaz (örneğin “Ayşe K.”).')
    try:
        rating = int(item.get('rating') or 0)
    except (TypeError, ValueError):
        rating = 0
    rating = rating if 1 <= rating <= 5 else 0
    date = str(item.get('date') or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
        date = datetime.now().strftime('%Y-%m-%d')
    source = str(item.get('source') or 'whatsapp')
    if source not in SOURCES:
        source = 'diger'
    consent = bool(item.get('consent'))
    active = bool(item.get('active', True)) and consent
    rid = str(item.get('id') or '').strip() or f"r-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(2)}"
    return {
        'id': rid, 'product_slug': slug, 'author': author, 'text': text, 'rating': rating,
        'date': date, 'source': source, 'consent': consent, 'active': active,
        'created_at': str(item.get('created_at') or datetime.now().isoformat(timespec='seconds')),
    }


def published(reviews, slug):
    rows = [r for r in (reviews or []) if isinstance(r, dict) and r.get('product_slug') == slug
            and r.get('consent') and r.get('active', True) and str(r.get('text') or '').strip()]
    return sorted(rows, key=lambda r: str(r.get('date') or ''), reverse=True)


def _date_label(value):
    try:
        d = datetime.strptime(str(value), '%Y-%m-%d')
        return f'{MONTHS[d.month - 1]} {d.year}'
    except ValueError:
        return ''


def _stars(rating):
    full = '★' * rating + '☆' * (5 - rating)
    return f'<span class="review-stars-v3397" role="img" aria-label="5 üzerinden {rating} puan">{full}</span>'


def render_section(reviews):
    if not reviews:
        return ''
    rated = [r for r in reviews if int(r.get('rating') or 0) > 0]
    summary = ''
    if rated:
        avg = sum(int(r['rating']) for r in rated) / len(rated)
        summary = (f'<p class="review-summary-v3397"><strong>{avg:.1f}'.replace('.', ',') + '</strong>'
                   f'{_stars(round(avg))}<span>{len(rated)} puanlı değerlendirme</span></p>')
    cards = []
    for r in reviews:
        rating = int(r.get('rating') or 0)
        meta = ' · '.join(x for x in (SOURCES.get(r.get('source'), 'Müşteri mesajı'), _date_label(r.get('date'))) if x)
        cards.append(
            '<figure class="review-card-v3397">'
            + (_stars(rating) if rating else '')
            + f'<blockquote><p>{esc(r["text"])}</p></blockquote>'
            + f'<figcaption><strong>{esc(r["author"])}</strong><span>{esc(meta)}</span></figcaption></figure>')
    return ('<section class="product-reviews-v3397 shell" id="yorumlar"><div class="section-title"><div>'
            '<p class="eyebrow">MÜŞTERİ YORUMLARI</p><h2>Müşterilerimiz ne dedi?</h2></div>' + summary + '</div>'
            '<div class="review-grid-v3397">' + ''.join(cards) + '</div>'
            '<p class="review-note-v3397">Müşterilerimizin bize ilettiği mesajlardan, izinleriyle yayınlanmıştır.</p></section>')


def schema_fields(reviews):
    """Review + AggregateRating for Product schema, only from reviews the customer rated."""
    rated = [r for r in (reviews or []) if int(r.get('rating') or 0) > 0]
    if not rated:
        return {}
    avg = sum(int(r['rating']) for r in rated) / len(rated)
    return {
        'aggregateRating': {'@type': 'AggregateRating', 'ratingValue': f'{avg:.1f}', 'reviewCount': len(rated),
                            'bestRating': '5', 'worstRating': '1'},
        'review': [{
            '@type': 'Review',
            'author': {'@type': 'Person', 'name': r['author']},
            'datePublished': r['date'],
            'reviewBody': r['text'],
            'reviewRating': {'@type': 'Rating', 'ratingValue': str(int(r['rating'])), 'bestRating': '5', 'worstRating': '1'},
        } for r in rated[:10]],
    }
