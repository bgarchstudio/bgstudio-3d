# BG Studio 3D v2.6.2 — Profil Fotoğrafı Patch

Bu patch mevcut ürün, renk, NFC, kurumsal ve prototip JSON verilerini içermez; mevcut panel verilerinin üzerine yazmaz.

## Kurulum
1. Ürün yöneticisini ve açık Python/CMD penceresini kapat.
2. Bu klasörün içindekileri mevcut `bgstudio-3d` repo klasörünün üzerine kopyala.
3. Ürün yöneticisini yeniden aç.
4. `Saha & Prototip` bölümüne gir.
5. NFC veya bağımsız Kurumsal kayıtta `Profil fotoğrafı / işletme logosu` alanını kullan.
6. `Siteyi yeniden oluştur` çalıştır.
7. GitHub Desktop: Commit + Push.

## Davranış
- Profil fotoğrafı yüklenmezse BG Studio monogramı otomatik gösterilir.
- NFC kaydına bağlı Kurumsal kartlar profil fotoğrafını da NFC kaynağından devralır.
- `Varsayılan BG logosuna dön` ile yüklenmiş profil fotoğrafı kaldırılabilir.
- Prototip kartlarında profil fotoğrafı alanı gösterilmez.
