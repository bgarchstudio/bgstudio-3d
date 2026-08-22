# 3d.bgstudio.com.tr yayın planı

## 1. GitHub
1. GitHub'da `bgstudio-3d` isimli yeni repo oluştur.
2. v0.9 klasörünün **içeriğini** repo köküne yükle. Klasörün kendisini bir üst klasör olarak yükleme.
3. `main` branch kullan.
4. Settings → Pages → Deploy from a branch → `main` / `/root`.
5. Önce GitHub Pages'in geçici adresinde ana sayfa, ürün, teklif, kurumsal ve NFC sayfalarını kontrol et.

## 2. Subdomain DNS
1. `bgstudio.com.tr` alan adının DNS panelini aç.
2. `3d` host/adı için bir CNAME kaydı oluştur.
3. Hedefi GitHub Pages hesabının verdiği host adına yönlendir.
4. Ana `bgstudio.com.tr` kayıtlarını değiştirme veya silme.

## 3. Custom domain
1. GitHub repo → Settings → Pages → Custom domain alanına `3d.bgstudio.com.tr` yaz.
2. DNS doğrulamasını bekle.
3. GitHub seçeneği aktif hale geldiğinde `Enforce HTTPS` aç.
4. Repodaki `CNAME` dosyası zaten `3d.bgstudio.com.tr` içerir.

## 4. Yayın sonrası
1. `https://3d.bgstudio.com.tr` üzerinden tüm ana navigasyonu kontrol et.
2. En az 3 ürün sayfasında WhatsApp sipariş akışını test et.
3. Google Search Console'a `https://3d.bgstudio.com.tr` property ekle.
4. `https://3d.bgstudio.com.tr/sitemap.xml` gönder.
5. BG Studio Architecture sitesine `BG Studio 3D ↗` geçişi ekle.

DNS ve GitHub adımlarını uygularken bu dosyayı körlemesine takip etmek yerine ekrandaki güncel değerleri birlikte kontrol etmek daha güvenlidir.
