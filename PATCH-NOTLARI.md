# BG Studio 3D v2.6 — Renk, Set ve Kurumsal Senkron

Bu patch kullanıcı tarafından düzenlenen `data/products.json`, `data/nfc_references.json` ve `data/prototypes.json` dosyalarını özellikle içermez. Mevcut ürün/set/saha verilerin korunur.

## Kurulum
1. Paneli tamamen kapat.
2. Bu patch klasörünün içindekileri repo köküne kopyala ve dosyaları değiştir.
3. Ürün Yöneticisini yeniden aç.
4. Bir kez `Siteyi yeniden oluştur` butonuna bas.
5. `Yayın kontrolü` yap.
6. GitHub Desktop: Commit + Push.

## Gelenler
- Tekli fiyat katalog ve ana ürün fiyatında ana fiyattır; set fiyatı tekli fiyatı ezmez.
- Set/adet kartları ürünlerin tamamında aynı tasarım/işleyişi kullanır.
- 2'li/3'lü/4'lü setlerde her fiziksel ürün için ayrı renk seçilebilir.
- WhatsApp mesajında her ürünün rengi ayrı satırda görünür.
- `Benim renklerim`: renk adı, swatch tonu, stok açık/kapalı ve isteğe bağlı stok adedi.
- Ürün düzenlerken global renkler swatch ile açık biçimde seçilir.
- Müşteriye yalnızca stokta olan ve üründe izin verilen renkler gösterilir.
- Kurumsal Referanslar paneli eklendi.
- NFC saha kaydına bağlı Kurumsal kart, aynı kaynak veriyi kullanır. İki kart metin/görsel olarak birbirinden kopmaz.
- Çikolata Şelalesi Spiral Aksamı Kurumsal kartlardan kaldırılır; Prototip & Parça bölümünde kalır.

`CNAME` patch içinde yoktur.
