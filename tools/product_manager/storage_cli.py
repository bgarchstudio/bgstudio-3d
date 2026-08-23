from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storage import ensure_initialized, export_to_repo, create_full_backup, status, get_collection


def counts():
    return {
        'products': len(get_collection('products', [])),
        'colors': len(get_collection('colors', [])),
        'nfc': len(get_collection('nfc', [])),
        'corporate': len(get_collection('corporate', [])),
        'prototype': len(get_collection('prototype', [])),
    }


def print_status(title='BG Studio 3D Kalıcı Veri Kasası'):
    st = status()
    c = counts()
    print('\n' + title)
    print('=' * len(title))
    print('Veri klasörü :', st['app_home'])
    print('Veritabanı   :', st['database'])
    print('Medya        :', st['media'])
    print('Yedekler     :', st['backups'])
    print('DB şeması    :', st['schema_version'])
    print('İlk kurulum  :', st['initialized_at'])
    print('Kayıtlar     :', f"{c['products']} ürün · {c['colors']} renk · {c['nfc']} NFC · {c['corporate']} kurumsal · {c['prototype']} prototip")
    return st


def main():
    cmd = (sys.argv[1] if len(sys.argv) > 1 else 'status').lower()
    ensure_initialized()
    if cmd in ('prepare', 'sync'):
        export_to_repo()
        print_status('BG Studio 3D · Kalıcı Veri Hazır')
        return 0
    if cmd in ('migrate', 'gecis'):
        export_to_repo()
        path = create_full_backup('ilk-kalici-veri-gecisi')
        print_status('BG Studio 3D · Kalıcı Veri Geçişi Tamamlandı')
        print('İlk güvenlik yedeği:', path)
        return 0
    if cmd in ('backup', 'yedek'):
        path = create_full_backup('cmd-manual')
        print_status('BG Studio 3D · Yedek Tamamlandı')
        print('Yedek:', path)
        return 0
    print_status()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
