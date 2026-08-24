# BG Studio 3D v3.1.17 — NFC Reference Jump Fix

## Düzeltilen sorun
- Ana sayfadaki **İşi incele** bağlantılarından **NFC & QR** sayfasına giderken
  özellikle **İstavrit Restaurant** ve **Koala Petshop** kartları doğru şekilde
  hedeflenmiyor, sayfa sadece bölümün başına gidiyordu.
- Hedef kart bazen sticky header altında kısmen yukarıda kalıyordu.

## Yapılan düzeltmeler
- Referans deep-link sistemi daha güçlü hale getirildi.
- Tıklanan kartın `reference id` bilgisi sessionStorage + URL query ile taşınıyor.
- Hedef sayfada kart çözümleme artık `data-reference-id`, `id`, isim ve başlık fallback'leriyle yapılıyor.
- Native anchor scroll etkisi nötrlenip ardından kart tekrar tekrar **merkeze alınarak** hizalanıyor.
- Yüklenme, resim gecikmesi ve layout kaymalarına karşı ek yeniden konumlandırma pass'leri eklendi.
- `hashchange`, `pageshow`, `load` ve `DOMContentLoaded` senaryoları kapsandı.
- `main.js` sürümü `3.1.17` yapılarak cache kırıldı.

## Değişen dosyalar
- `assets/js/main.js`
- cache-bust için tüm HTML dosyalarında `main.js?v=3.1.17`
