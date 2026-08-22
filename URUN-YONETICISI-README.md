# BG Studio 3D v2.0 — Ürün Yöneticisi

Bu sürümde ürün eklemek veya mevcut ürün bilgisini değiştirmek için HTML dosyası düzenlemeniz gerekmez.

## Kullanım
1. GitHub Desktop'ta kullandığınız `bgstudio-3d` repo klasörünün içine bu sürümün dosyalarını kopyalayın.
2. Repo kökündeki `URUN-YONETICI.bat` dosyasına çift tıklayın.
3. Tarayıcıda `BG Studio 3D Ürün Yöneticisi` açılır.
4. `Yeni ürün ekle` seçeneğini kullanın veya soldaki mevcut ürüne tıklayıp düzenleyin.
5. `Ürünü kaydet ve siteyi hazırla` deyin.
6. GitHub Desktop otomatik olarak değişen dosyaları gösterecektir.
7. Commit ve `Push origin` yapın. GitHub Pages otomatik yayınlar.

## Panel otomatik olarak ne yapar?
- Ana ürün görselini 1000×760 WebP'ye hazırlar.
- Afişi 1254×1254 WebP'ye hazırlar.
- `data/products.json` ürün verisini günceller.
- Ürün detay sayfasını üretir.
- Ürün kataloğunu günceller.
- Ana sayfadaki öne çıkan ürünleri günceller.
- Benzer ürünleri otomatik seçer.
- Product / Breadcrumb / FAQ SEO şemalarını üretir.
- `sitemap.xml` dosyasını günceller.
- Temiz `/urunler/urun-slug/` URL yapısını korur.

## URL kuralı
Mevcut bir ürün yayına girdikten sonra URL slug'ını değiştirmeyin. Panel mevcut ürünlerde bu alanı kilitler.

## Güvenli alanlar
Panel `CNAME`, DNS, GitHub Pages, Analytics ölçüm kimliği veya Cloudflare ayarlarını değiştirmez.
