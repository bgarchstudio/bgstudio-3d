# BG Studio 3D v1.3 Clean URL Patch

Bu patch dahili bağlantılardaki `index.html` parçalarını temiz URL yapısına çevirir.

Örnek:
- `/urunler/index.html` → `/urunler/`
- `/urunler/dekoratif-kus-obje/index.html` → `/urunler/dekoratif-kus-obje/`

Ayrıca eski `index.html` adresiyle açılan sayfalarda tarayıcı adresini sayfa yenilemeden temizleyen küçük bir uyumluluk kodu eklenmiştir.

CNAME dosyası bu patch içinde yoktur; mevcut repodaki CNAME korunmalıdır.
