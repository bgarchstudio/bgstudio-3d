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
SCHEMA_VERSION = 1

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
