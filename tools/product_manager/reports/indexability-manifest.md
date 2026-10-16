# BG Studio 3D · Indexability Manifest

- Asset version: **3.3.24**
- Physical HTML: **77**
- Canonical + indexable + sitemap: **74**
- Noindex: **3**
- `/index.html` aliases: **76**
- Indexable but sitemap dışında: **0**
- Duplicate canonical: **0**

## Noindex sayfalar
- `https://3d.bgstudio.com.tr/404.html` → `https://3d.bgstudio.com.tr/404.html` (noindex,follow)
- `https://3d.bgstudio.com.tr/mesafeli-satis/` → `https://3d.bgstudio.com.tr/mesafeli-satis/` (noindex,follow)
- `https://3d.bgstudio.com.tr/on-bilgilendirme/` → `https://3d.bgstudio.com.tr/on-bilgilendirme/` (noindex,follow)

## Nasıl yorumlanır?

- `alternate-canonical-or-redirect`: `/index.html` gibi ikinci bir URL keşfedilmiş olabilir. Doğru canonical slash URL ise bunun Google dizinine ayrıca girmemesi normaldir.
- `canonical-indexable`: bizim tarafta indexlenebilir, sitemapte ve temiz canonical ile yayınlanır.
- `noindex`: bilinçli olarak Google dizini dışında tutulur.
- `indexable-not-in-sitemap`: teknik hata adayıdır ve release öncesi incelenmelidir.

> Bu rapor Search Console kararını tahmin etmez. “Keşfedildi” veya “Tarandı ama dizine eklenmedi” nedeninin kesin URL örneği GSC’den alınmalı ve bu manifestle karşılaştırılmalıdır.
