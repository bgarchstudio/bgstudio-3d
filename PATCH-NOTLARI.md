# BG Studio 3D v2.3 — Safety + Analytics

Bu patch üç alanı güçlendirir:

1. Gizlilik / Analytics
- GA4 artık kullanıcı analitik izni vermeden yüklenmez.
- `Sadece gerekli` ve `Analitiğe izin ver` seçenekleri eklenmiştir.
- Footer'a `Çerez tercihleri` düğmesi otomatik eklenir.
- Reklam kişiselleştirme sinyalleri kapalı tutulur.
- Gizlilik sayfası yeni davranışı açıklar.

2. Dönüşüm ölçümü
- Genel WhatsApp tıklaması: `whatsapp_click` + `generate_lead`
- Ürün siparişi: `whatsapp_order` + `generate_lead`
- Hızlı WhatsApp paneli: `whatsapp_quick_contact` + `generate_lead`
- Teklif formu: `quote_request` + `generate_lead`
- Ürün detay görüntüleme: `view_item`

3. Ürün Yöneticisi güvenliği
- `Yayın kontrolü` ekranı eklendi.
- CNAME, sitemap, SEO, ürün dosyaları ve slug çakışmaları kontrol edilir.
- Manuel tam yedek alınabilir.
- Yedek listesi ve geri yükleme sistemi eklendi.
- Kalıcı ürün silme öncesinde otomatik tam yedek alınır.

Not: Patch CNAME içermez. `data/backups/` GitHub'a gönderilmez.
