BG Studio 3D v2.8.4 - Kalici Launcher Kurulum Hotfix

Neden gerekli?
Onceki SAFE PATCH launcher sablon dosyasini icermiyordu ve masaustu yolu sabit %USERPROFILE%\Desktop kabul ediliyordu.
OneDrive / Windows klasor yonlendirmesinde kisayol olusmayabiliyordu.

Bu hotfix:
- gerekli launcher sablonunu beraberinde getirir,
- Windows'un gercek Masaustu klasorunu Shell API ile bulur,
- kisayol gercekten olustu mu kontrol eder,
- hata olursa sessizce gecmek yerine hatayi ekranda gosterir,
- kalici launcher'i %LOCALAPPDATA%\BGStudio3D\launcher altinda tutar.

Kurulum:
1) ZIP icerigini mevcut bgstudio-3d repo klasorunun uzerine kopyala.
2) KALICI-YONETICI-KUR.cmd dosyasini bir kez calistir.
3) Ekranda [OK] Masaustu kisayolu olusturuldu yazisini gor.
