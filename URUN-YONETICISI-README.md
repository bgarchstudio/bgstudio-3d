# BG Studio 3D v2.2 PRO — Ürün Yöneticisi

Ürün eklemek, çoğaltmak, arşivlemek, sıralamak ve görselleri hazırlamak için HTML düzenlemeniz gerekmez.

## Hızlı kullanım
1. Repo kökündeki `URUN-YONETICI.bat` dosyasını açın.
2. Soldan mevcut ürünü seçin veya `Yeni ürün ekle` deyin.
3. Bilgileri/görselleri girin.
4. `Önizle` ile kaydetmeden önce görünümü kontrol edin.
5. `Ürünü kaydet ve siteyi hazırla` deyin.
6. GitHub Desktop'ta Commit + Push yapın.

## v2.2 PRO özellikleri
- Ürünü tek tıkla kopyalama. Kopya güvenlik için arşivde oluşur.
- Yayından kaldırma / tekrar yayına alma.
- Kalıcı silme için `SİL` doğrulaması.
- Soldaki listede sürükle-bırak katalog sıralaması.
- Yayında / Arşiv / Öne çıkan filtreleri.
- Yıldız butonuyla hızlı öne çıkarma.
- Kaydetmeden önce canlı ürün önizlemesi.
- Eksik alan kalite kontrolü.
- SEO karakter sayaçları ve otomatik SEO.
- Ana görsel + afiş + 12 adede kadar ek galeri görseli.
- Görselleri otomatik WebP optimizasyonu ve SEO uyumlu dosya adları.
- Ürün detay sayfası, katalog, ana sayfa, schema ve sitemap otomatik güncelleme.

## Sürükle-bırak sıralama
Sıralama yalnızca `Tümü` filtresinde ve arama kutusu boşken aktif olur. Bu sayede filtrelenmiş bir listede yanlışlıkla katalog sırası bozulmaz.

## URL kuralı
Mevcut ürün yayına girdikten sonra URL slug'ını değiştirmeyin. Panel mevcut ürünlerde bu alanı kilitler.

## Güvenli alanlar
Panel `CNAME`, DNS, GitHub Pages, Analytics ölçüm kimliği veya Cloudflare ayarlarını değiştirmez.

## v2.3 — Yayın güvenliği ve yedek merkezi
- Üst bardaki `Yayın kontrolü` düğmesi ürün verisi, slug, görsel/sayfa dosyaları, SEO, CNAME, sitemap ve öne çıkan sayısını kontrol eder.
- `Şimdi tam yedek al` ürün verisini ve ürün/poster görsellerini `data/backups/` altında ZIP olarak saklar.
- Ürün üzerinde yapılan değişikliklerde hafif JSON yedeği otomatik alınır.
- Bir ürün kalıcı silinmeden önce otomatik tam site yedeği alınır.
- Yedek geri yüklenmeden önce mevcut durum da otomatik tam yedeklenir.
- `data/backups/` `.gitignore` içinde olduğu için bu yerel yedekler GitHub'a gönderilmez.

## v2.5 — Set / adet fiyatlandırması
Tekli fiyatın yanında 2’li, 4’lü veya başka paket fiyatları olan ürünler için `Set / adet fiyatlandırması` alanını kullan. Paket adı, ürün adedi, fiyat ve kısa notu panelden yönetebilirsin. Canlı ürün sayfasındaki sipariş seçici ve WhatsApp mesajı bu bilgileri otomatik kullanır.

## v2.8.4 Kalıcı launcher
Paneli repo içindeki CMD yerine masaüstündeki kalıcı kısayoldan açmak için bir kez `KALICI-YONETICI-KUR.cmd` çalıştır. Launcher `%LOCALAPPDATA%\BGStudio3D\launcher` altına kurulur ve gelecekteki ZIP güncellemelerinden etkilenmez.
