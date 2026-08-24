from __future__ import annotations

from pathlib import Path
from datetime import datetime
import os
import json
import sqlite3
import shutil
import zipfile
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]

_local = os.environ.get('LOCALAPPDATA')
if _local:
    APP_HOME = Path(_local) / 'BGStudio3D'
else:
    APP_HOME = Path.home() / 'AppData' / 'Local' / 'BGStudio3D'

DB_FILE = APP_HOME / 'bgstudio3d.db'
MEDIA_ROOT = APP_HOME / 'media'
BACKUPS_ROOT = APP_HOME / 'backups'
META_FILE = APP_HOME / 'storage-info.json'
SCHEMA_VERSION = 4

COLLECTIONS = {
    'products': ROOT / 'data' / 'products.json',
    'colors': ROOT / 'data' / 'colors.json',
    'nfc': ROOT / 'data' / 'nfc_references.json',
    'corporate': ROOT / 'data' / 'corporate_references.json',
    'prototype': ROOT / 'data' / 'prototypes.json',
}

MUTABLE_MEDIA_PREFIXES = (
    'assets/images/products/',
    'assets/images/posters/',
    'assets/images/references/',
    'assets/images/prototypes/',
)


# V3.1 product taxonomy migration. Legacy values stay readable in older backups,
# but the persistent manager store is upgraded once without deleting any product.
LEGACY_CATEGORY_MAP = {
    'dekoratif': 'dekoratif-duvar',
    'aydinlatma': 'aydinlatma',
    'fonksiyonel': 'pratik-fonksiyonel',
    'kisiye-ozel': 'hediye-kisiye-ozel',
}
SPECIAL_CATEGORY_MAP = {
    'arac-koku-difuzoru': 'pratik-fonksiyonel',
    'ataturk-imzasi': 'dekoratif-duvar',
    'cerceveli-dalga-lamba': 'aydinlatma',
    'dekoratif-kus-obje': 'dekoratif-duvar',
    'dekoratif-lale': 'dekoratif-duvar',
    'dekoratif-mirket-obje': 'dekoratif-duvar',
    'dekoratif-mumluk': 'dekoratif-duvar',
    'dekoratif-tavsan-obje': 'dekoratif-duvar',
    'havuz-icecek-tutucu': 'pratik-fonksiyonel',
    'heykel-bust-masa-lambasi': 'aydinlatma',
    'kask-askiligi': 'ev-duzen',
    'kisiye-ozel-miknatisli-acacak': 'hediye-kisiye-ozel',
    'renkli-masa-lambasi': 'aydinlatma',
    'spiral-masa-lambasi': 'aydinlatma',
    'kisiye-ozel-gaming-stand': 'gaming-masaustu',
    'iron-man-eli-masa-lambasi': 'aydinlatma',
}
SPECIAL_PRODUCT_TAGS = {
    'arac-koku-difuzoru': ['Araç', 'Pratik'],
    'ataturk-imzasi': ['Duvar Dekoru', 'Hediye'],
    'cerceveli-dalga-lamba': ['Masa Lambası', 'Masaüstü', 'Dekoratif'],
    'dekoratif-kus-obje': ['Dekoratif', 'Hediye'],
    'dekoratif-lale': ['Dekoratif', 'Hediye'],
    'dekoratif-mirket-obje': ['Dekoratif', 'Hediye'],
    'dekoratif-mumluk': ['Dekoratif', 'Ev'],
    'dekoratif-tavsan-obje': ['Dekoratif', 'Hediye'],
    'havuz-icecek-tutucu': ['Pratik', 'Yaz'],
    'heykel-bust-masa-lambasi': ['Masa Lambası', 'Dekoratif'],
    'kask-askiligi': ['Motosiklet', 'Duvar Düzeni', 'Pratik'],
    'kisiye-ozel-miknatisli-acacak': ['Kişiye Özel', 'Açacak', 'Mıknatıslı', 'Hediye', 'Adetli Üretim'],
    'renkli-masa-lambasi': ['Masa Lambası', 'Masaüstü', 'Dekoratif'],
    'spiral-masa-lambasi': ['Masa Lambası', 'Masaüstü', 'Dekoratif'],
    'kisiye-ozel-gaming-stand': ['Gaming', 'Kişiye Özel', 'PlayStation', 'Xbox', 'Masaüstü'],
    'iron-man-eli-masa-lambasi': ['Masa Lambası', 'Gaming', 'Dekoratif', 'Hediye'],
}


KUSADASI_ASANSOR_REFERENCE = {
    "slug": "kusadasi-asansor",
    "name": "Kuşadası Asansör",
    "headline": "100 Adet Logolu Kurumsal Anahtarlık",
    "description": "Kuşadası Asansör için işletmenin isteğine göre mavi-beyaz kurumsal renklerde, logolu 100 adet 3D baskı anahtarlık üretildi. Tasarım marka kimliğine göre hazırlanıp seri üretime alınarak teslim edildi.",
    "category": "Kurumsal üretim",
    "tags": ["100 Adet", "Kurumsal Anahtarlık", "Logolu Üretim", "Mavi & Beyaz", "Kuşadası"],
    "active": True,
    "sort_order": 40,
    "theme": "light",
    "image": "assets/images/references/kusadasi-asansor-100-anahtarlik.webp",
    "profile_image": "assets/images/references/kusadasi-asansor-profile.webp"
}

def _ensure_kusadasi_asansor_reference(con):
    """Restore the Kuşadası Asansör field reference without touching other records.

    The homepage field-work section is generated from the corporate collection.
    Older persistent stores predate this reference, so a rebuild could drop the
    card. Add/update this single record once during schema migration.
    """
    row = con.execute('SELECT json_text FROM collections WHERE name=?', ('corporate',)).fetchone()
    try:
        items = json.loads(row[0]) if row else []
    except Exception:
        items = []
    if not isinstance(items, list):
        items = []
    changed = False
    found = None
    for item in items:
        if isinstance(item, dict) and str(item.get('slug') or '').strip() == KUSADASI_ASANSOR_REFERENCE['slug']:
            found = item
            break
    if found is None:
        items.append(dict(KUSADASI_ASANSOR_REFERENCE))
        changed = True
    else:
        # One-time restoration: preserve user-edited copy but restore fields that
        # are required for rendering and make the missing card active again.
        for key in ('name','headline','description','category','tags','sort_order','theme','image','profile_image'):
            if not found.get(key):
                found[key] = KUSADASI_ASANSOR_REFERENCE[key]
                changed = True
        if found.get('active') is not True:
            found['active'] = True
            changed = True
    if changed:
        con.execute(
            'INSERT INTO collections(name,json_text,updated_at) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET json_text=excluded.json_text, updated_at=excluded.updated_at',
            ('corporate', json.dumps(items, ensure_ascii=False, indent=2), _now())
        )

    # Keep packaged reference media in the persistent media vault so later
    # export/build cycles cannot lose it. Never overwrite an existing user file.
    for rel in (KUSADASI_ASANSOR_REFERENCE['image'], KUSADASI_ASANSOR_REFERENCE['profile_image']):
        repo_file = ROOT / rel
        vault_file = MEDIA_ROOT / rel
        if repo_file.exists() and not vault_file.exists():
            vault_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo_file, vault_file)


NAZ_BALIK_NFC_FALLBACK = {
    "slug": "naz-balik-restaurant",
    "name": "Naz Balık Restaurant",
    "headline": "15 Masa İçin Google + Tripadvisor QR Yorum Kartı",
    "description": "Naz Balık Restaurant’ın 15 masası için Google Reviews ve Tripadvisor yorum yönlendirmesine özel toplam 15 adet masaüstü QR yorum kartı tasarlanıp uygulandı. Her kartta iki platform için ayrı QR yönlendirmeleri kurgulandı ve tasarım restoranın marka kimliğine özel olarak hazırlandı.",
    "category": "Restoran • QR Yorum Sistemi",
    "tags": ["15 Masa", "15 QR Yorum Kartı", "Google Reviews", "Tripadvisor", "QR Yorum Sistemi", "Restoran", "Kuşadası"],
    "active": True,
    "sort_order": 3,
    "profile_image": "assets/images/references/naz-balik-restaurant-profile.webp"
}


def _load_collection_json(con, name):
    row = con.execute('SELECT json_text FROM collections WHERE name=?', (name,)).fetchone()
    try:
        value = json.loads(row[0]) if row else []
    except Exception:
        value = []
    return value if isinstance(value, list) else []


def _save_collection_json(con, name, items):
    con.execute(
        'INSERT INTO collections(name,json_text,updated_at) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET json_text=excluded.json_text, updated_at=excluded.updated_at',
        (name, json.dumps(items, ensure_ascii=False, indent=2), _now())
    )


def _resequence_collection(items):
    """Keep each content collection on a clean 1..N position sequence."""
    clean_items = [x for x in items if isinstance(x, dict)]
    clean_items.sort(key=lambda x: (int(x.get('sort_order') or 999999), str(x.get('name') or x.get('slug') or '').casefold()))
    for index, item in enumerate(clean_items, 1):
        item['sort_order'] = index
    return clean_items


def _upgrade_references_v4(con):
    """Move Naz Balık to NFC & QR and make every NFC reference corporate-visible."""
    nfc = _load_collection_json(con, 'nfc')
    corporate = _load_collection_json(con, 'corporate')
    prototype = _load_collection_json(con, 'prototype')

    # Move the existing independent Naz Balık corporate record into NFC & QR.
    naz_corp = next((x for x in corporate if str(x.get('slug') or '') == 'naz-balik-restaurant' and not x.get('source_slug')), None)
    naz_nfc = next((x for x in nfc if str(x.get('slug') or '') == 'naz-balik-restaurant'), None)
    source = dict(NAZ_BALIK_NFC_FALLBACK)
    if naz_corp:
        for key in ('name','headline','description','category','tags','active','image','profile_image'):
            value = naz_corp.get(key)
            if value not in (None, '', []):
                source[key] = value
        # Corporate title historically had a shorter sentence; use the richer known NFC title.
        if source.get('headline') == 'QR yorum akışı ve işletmeye özel uygulama.':
            source['headline'] = NAZ_BALIK_NFC_FALLBACK['headline']
        if not source.get('category') or source.get('category') == 'Kurumsal üretim':
            source['category'] = NAZ_BALIK_NFC_FALLBACK['category']
    if naz_nfc:
        for key, value in source.items():
            if naz_nfc.get(key) in (None, '', []):
                naz_nfc[key] = value
    else:
        # Naz was historically corporate-only; append it after existing NFC cards
        # before normalizing the collection to 1..N.
        source['sort_order'] = max([int(x.get('sort_order') or 0) for x in nfc if isinstance(x, dict)] + [0]) + 1
        nfc.append(source)

    # Remove only the independent Naz copy; it will reappear as an NFC-synced corporate card.
    corporate = [x for x in corporate if not (str(x.get('slug') or '') == 'naz-balik-restaurant' and not x.get('source_slug'))]

    # Every NFC record gets exactly one linked corporate card. Existing theme/active choices are preserved.
    nfc_by_slug = {str(x.get('slug') or ''): x for x in nfc if x.get('slug')}
    linked = {}
    independent = []
    for item in corporate:
        if item.get('source_kind') == 'nfc' and item.get('source_slug'):
            slug = str(item.get('source_slug'))
            if slug in nfc_by_slug and slug not in linked:
                linked[slug] = item
            continue
        # If an older independent corporate card has the same slug as an NFC record, convert it to a link.
        slug = str(item.get('slug') or '')
        if slug in nfc_by_slug and slug not in linked:
            linked[slug] = {
                'slug': slug,
                'source_kind': 'nfc',
                'source_slug': slug,
                'theme': 'dark' if str(item.get('theme') or '').lower() == 'dark' else 'light',
                'active': bool(item.get('active', True)),
                'sort_order': int(item.get('sort_order') or 999),
            }
        else:
            independent.append(item)

    synced = []
    for idx, nfc_item in enumerate(_resequence_collection(nfc), 1):
        slug = str(nfc_item.get('slug') or '')
        card = linked.get(slug) or {
            'slug': slug,
            'source_kind': 'nfc',
            'source_slug': slug,
            'theme': 'dark' if idx % 2 else 'light',
            'active': bool(nfc_item.get('active', True)),
            'sort_order': idx,
        }
        card['slug'] = slug
        card['source_kind'] = 'nfc'
        card['source_slug'] = slug
        # On migration, mirror the NFC order first; corporate can be reordered later.
        card['sort_order'] = idx
        synced.append(card)

    # NFC cards first in their NFC order, then independent corporate jobs.
    corporate = _resequence_collection(synced + independent)
    prototype = _resequence_collection(prototype)

    _save_collection_json(con, 'nfc', nfc)
    _save_collection_json(con, 'corporate', corporate)
    _save_collection_json(con, 'prototype', prototype)

def _upgrade_products_v2(con):
    row = con.execute('SELECT json_text FROM collections WHERE name=?', ('products',)).fetchone()
    if not row:
        return
    try:
        products = json.loads(row[0])
    except Exception:
        return
    if not isinstance(products, list):
        return
    changed = False
    for product in products:
        if not isinstance(product, dict):
            continue
        slug = str(product.get('slug') or '')
        old_category = str(product.get('category') or '')
        new_category = SPECIAL_CATEGORY_MAP.get(slug, LEGACY_CATEGORY_MAP.get(old_category, old_category))
        if new_category and new_category != old_category:
            product['category'] = new_category
            changed = True
        if not isinstance(product.get('tags'), list):
            product['tags'] = list(SPECIAL_PRODUCT_TAGS.get(slug, []))
            changed = True
        elif not product.get('tags') and slug in SPECIAL_PRODUCT_TAGS:
            product['tags'] = list(SPECIAL_PRODUCT_TAGS[slug])
            changed = True
    if changed:
        con.execute(
            'UPDATE collections SET json_text=?, updated_at=? WHERE name=?',
            (json.dumps(products, ensure_ascii=False, indent=2), _now(), 'products')
        )

def _sync_smaller_repo_media():
    """Keep V3.1 optimized repo images in the persistent media vault.

    The vault is authoritative and normally exports over the repo on startup.
    During this one-time upgrade we only replace a vault file when the packaged
    repo counterpart is at least 25% smaller, which preserves user media while
    carrying forward lossless-looking image optimization.
    """
    for prefix in MUTABLE_MEDIA_PREFIXES:
        repo_dir = ROOT / prefix.rstrip('/')
        if not repo_dir.exists():
            continue
        for repo_file in repo_dir.rglob('*'):
            if not repo_file.is_file():
                continue
            rel = repo_file.relative_to(ROOT)
            vault_file = MEDIA_ROOT / rel
            if not vault_file.exists() or not vault_file.is_file():
                continue
            try:
                repo_size = repo_file.stat().st_size
                vault_size = vault_file.stat().st_size
            except OSError:
                continue
            if repo_size > 0 and vault_size > 0 and repo_size <= vault_size * 0.75:
                vault_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repo_file, vault_file)

def _upgrade_schema(con, old_version):
    if old_version < 2:
        _upgrade_products_v2(con)
        _sync_smaller_repo_media()
    if old_version < 3:
        _ensure_kusadasi_asansor_reference(con)
    if old_version < 4:
        _upgrade_references_v4(con)

_lock = threading.RLock()


def _now():
    return datetime.now().isoformat(timespec='seconds')


def _connect():
    APP_HOME.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE, timeout=15)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')
    con.execute('PRAGMA foreign_keys=ON')
    return con


def _create_schema(con):
    con.execute('''CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS collections (
        name TEXT PRIMARY KEY,
        json_text TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')
    con.commit()


def _meta_get(con, key, default=None):
    row = con.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
    return row[0] if row else default


def _meta_set(con, key, value):
    con.execute('INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))


def _read_repo_json(path, default):
    try:
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            return value
    except Exception:
        pass
    return default


def _copy_tree_contents(src: Path, dst: Path):
    if not src.exists():
        return
    for f in src.rglob('*'):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)


def _initial_import(con):
    defaults = {name: [] for name in COLLECTIONS}
    for name, repo_path in COLLECTIONS.items():
        data = _read_repo_json(repo_path, defaults[name])
        con.execute(
            'INSERT OR REPLACE INTO collections(name,json_text,updated_at) VALUES(?,?,?)',
            (name, json.dumps(data, ensure_ascii=False, indent=2), _now())
        )

    # Mevcut repo içindeki panel görsellerini kalıcı kasaya ilk kez kopyala.
    for prefix in MUTABLE_MEDIA_PREFIXES:
        src = ROOT / prefix.rstrip('/')
        dst = MEDIA_ROOT / prefix.rstrip('/')
        _copy_tree_contents(src, dst)

    # Eski panel yedeklerini de kaybetme.
    old_backups = ROOT / 'data' / 'backups'
    if old_backups.exists():
        BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
        for f in old_backups.iterdir():
            if f.is_file():
                target = BACKUPS_ROOT / f.name
                if not target.exists():
                    shutil.copy2(f, target)

    # Seed mandatory shipped references on a fresh install as well.
    _ensure_kusadasi_asansor_reference(con)
    _upgrade_references_v4(con)
    _meta_set(con, 'initialized', '1')
    _meta_set(con, 'schema_version', SCHEMA_VERSION)
    _meta_set(con, 'initialized_at', _now())
    _meta_set(con, 'migration_source_repo', str(ROOT))
    con.commit()


def ensure_initialized():
    with _lock:
        APP_HOME.mkdir(parents=True, exist_ok=True)
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
        with _connect() as con:
            _create_schema(con)
            if _meta_get(con, 'initialized') != '1':
                _initial_import(con)
            else:
                # Yeni sürümlerde yeni koleksiyon eklenirse eskileri bozmadan ekle.
                for name, repo_path in COLLECTIONS.items():
                    row = con.execute('SELECT 1 FROM collections WHERE name=?', (name,)).fetchone()
                    if not row:
                        data = _read_repo_json(repo_path, [])
                        con.execute('INSERT INTO collections(name,json_text,updated_at) VALUES(?,?,?)', (name, json.dumps(data, ensure_ascii=False, indent=2), _now()))
                try:
                    old_version = int(_meta_get(con, 'schema_version', '1') or 1)
                except Exception:
                    old_version = 1
                if old_version < SCHEMA_VERSION:
                    _upgrade_schema(con, old_version)
                _meta_set(con, 'schema_version', SCHEMA_VERSION)
                con.commit()
        write_info_file()


def write_info_file():
    info = {
        'app_home': str(APP_HOME),
        'database': str(DB_FILE),
        'media': str(MEDIA_ROOT),
        'backups': str(BACKUPS_ROOT),
        'schema_version': SCHEMA_VERSION,
        'note': 'Bu klasör repo/CMD dosyalarından bağımsız kalıcı BG Studio 3D yönetim verisidir.'
    }
    META_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')


def get_collection(name, default=None):
    ensure_initialized()
    if default is None:
        default = []
    with _lock, _connect() as con:
        row = con.execute('SELECT json_text FROM collections WHERE name=?', (name,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return default


def set_collection(name, value):
    ensure_initialized()
    text = json.dumps(value, ensure_ascii=False, indent=2)
    with _lock, _connect() as con:
        con.execute(
            'INSERT INTO collections(name,json_text,updated_at) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET json_text=excluded.json_text, updated_at=excluded.updated_at',
            (name, text, _now())
        )
        con.commit()


def media_path(rel):
    rel = str(rel or '').replace('\\', '/').lstrip('/')
    return MEDIA_ROOT / rel


def is_mutable_media(rel):
    rel = str(rel or '').replace('\\', '/').lstrip('/')
    return any(rel.startswith(prefix) for prefix in MUTABLE_MEDIA_PREFIXES)


def save_media(rel, raw: bytes):
    rel = str(rel or '').replace('\\', '/').lstrip('/')
    if not is_mutable_media(rel):
        return
    target = media_path(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def remove_media(rel):
    rel = str(rel or '').replace('\\', '/').lstrip('/')
    if not is_mutable_media(rel):
        return
    target = media_path(rel)
    if target.exists() and target.is_file():
        target.unlink()


def copy_media(src_rel, dst_rel):
    src_rel = str(src_rel or '').replace('\\', '/').lstrip('/')
    dst_rel = str(dst_rel or '').replace('\\', '/').lstrip('/')
    if not is_mutable_media(dst_rel):
        return False
    src = media_path(src_rel)
    if not src.exists():
        src = ROOT / src_rel
    if not src.exists() or not src.is_file():
        return False
    dst = media_path(dst_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    repo_dst = ROOT / dst_rel
    repo_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, repo_dst)
    return True


def export_to_repo():
    """Kalıcı kasayı GitHub repo çıktısına yansıtır. Repo veri kaynağı değildir."""
    ensure_initialized()
    with _lock:
        for name, repo_path in COLLECTIONS.items():
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            repo_path.write_text(json.dumps(get_collection(name, []), ensure_ascii=False, indent=2), encoding='utf-8')
        for prefix in MUTABLE_MEDIA_PREFIXES:
            src = MEDIA_ROOT / prefix.rstrip('/')
            dst = ROOT / prefix.rstrip('/')
            _copy_tree_contents(src, dst)


def create_db_backup(label='auto'):
    ensure_initialized()
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in str(label).lower()).strip('-') or 'auto'
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = BACKUPS_ROOT / f'data-{stamp}-{safe}.sqlite3'
    with _lock:
        src = _connect()
        try:
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    files = sorted(BACKUPS_ROOT.glob('data-*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[80:]:
        old.unlink(missing_ok=True)
    return target


def create_full_backup(label='manual'):
    ensure_initialized()
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in str(label).lower()).strip('-') or 'manual'
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    db_snapshot = create_db_backup('full-temp')
    target = BACKUPS_ROOT / f'bgstudio3d-{stamp}-{safe}.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(db_snapshot, 'bgstudio3d.db')
        if MEDIA_ROOT.exists():
            for f in MEDIA_ROOT.rglob('*'):
                if f.is_file():
                    z.write(f, Path('media') / f.relative_to(MEDIA_ROOT))
        z.writestr('backup-info.json', json.dumps({'created_at': _now(), 'schema_version': SCHEMA_VERSION}, ensure_ascii=False, indent=2))
    db_snapshot.unlink(missing_ok=True)
    files = sorted(BACKUPS_ROOT.glob('bgstudio3d-*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[20:]:
        old.unlink(missing_ok=True)
    return target


def list_backups(limit=40):
    ensure_initialized()
    files = sorted(
        [*BACKUPS_ROOT.glob('bgstudio3d-*.zip'), *BACKUPS_ROOT.glob('data-*.sqlite3')],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    out = []
    for f in files[:limit]:
        out.append({
            'name': f.name,
            'type': 'full' if f.suffix.lower() == '.zip' else 'database',
            'size': f.stat().st_size,
            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec='seconds')
        })
    return out


def _validate_restore_db(path: Path):
    con = sqlite3.connect(path)
    try:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'collections' not in names or 'meta' not in names:
            raise ValueError('Yedek BG Studio 3D veritabanı değil.')
    finally:
        con.close()


def restore_backup(name):
    ensure_initialized()
    file = (BACKUPS_ROOT / Path(str(name)).name).resolve()
    if BACKUPS_ROOT.resolve() not in file.parents or not file.exists():
        raise ValueError('Yedek bulunamadı.')
    create_full_backup('before-restore')
    with _lock:
        if file.suffix.lower() == '.sqlite3':
            _validate_restore_db(file)
            shutil.copy2(file, DB_FILE)
        elif file.suffix.lower() == '.zip':
            with tempfile.TemporaryDirectory(prefix='bgstudio3d-restore-') as td:
                temp = Path(td)
                with zipfile.ZipFile(file, 'r') as z:
                    for member in z.infolist():
                        target = (temp / member.filename).resolve()
                        if temp.resolve() not in target.parents and target != temp.resolve():
                            raise ValueError('Yedek içeriği güvenli değil.')
                    z.extractall(temp)
                restore_db = temp / 'bgstudio3d.db'
                if not restore_db.exists():
                    raise ValueError('Yedekte veritabanı bulunamadı.')
                _validate_restore_db(restore_db)
                shutil.copy2(restore_db, DB_FILE)
                restore_media = temp / 'media'
                if restore_media.exists():
                    if MEDIA_ROOT.exists():
                        shutil.rmtree(MEDIA_ROOT)
                    shutil.copytree(restore_media, MEDIA_ROOT)
        else:
            raise ValueError('Desteklenmeyen yedek türü.')
    export_to_repo()


def status():
    ensure_initialized()
    with _connect() as con:
        initialized_at = _meta_get(con, 'initialized_at', '')
        schema = _meta_get(con, 'schema_version', str(SCHEMA_VERSION))
    return {
        'app_home': str(APP_HOME),
        'database': str(DB_FILE),
        'media': str(MEDIA_ROOT),
        'backups': str(BACKUPS_ROOT),
        'initialized_at': initialized_at,
        'schema_version': schema,
        'persistent': True,
    }


ensure_initialized()
