/**
 * BG Studio 3D — Teklif dosyalarını Google Drive'a kaydeden web uygulaması (Google Apps Script)
 * Hesap: bgstudio.3dtr@gmail.com
 *
 * KURULUM (bir kez, ~5 dk) — bgstudio.3dtr@gmail.com ile giriş yapılmış olmalı:
 *  1. Google Drive'da bir klasör aç: "BG Studio Teklif Dosyaları".
 *     Klasörü aç; adres çubuğundaki .../folders/XXXXXXXX kısmındaki XXXXXXXX = KLASÖR KİMLİĞİ.
 *  2. https://script.google.com → "Yeni proje" → bu dosyanın tamamını yapıştır.
 *  3. Aşağıdaki FOLDER_ID değerine klasör kimliğini yaz → Kaydet.
 *  4. "Dağıt" → "Yeni dağıtım" → tür: "Web uygulaması"
 *        Şu kullanıcı olarak çalıştır: "Ben"
 *        Erişimi olanlar: "Herkes"
 *     → "Dağıt" → Google izin ister (Drive + Gmail): "İzin ver".
 *  5. Çıkan "Web uygulaması URL'si"ni (…/exec ile biter) gönder; siteye bağlanır.
 *
 * Her teklif talebi müşterinin adıyla kendi klasörüne kaydedilir:
 *   "Ayşe Yılmaz · 2026-11-09 · K7QF"
 * Klasör herkese açık paylaşılmaz; WhatsApp mesajındaki bağlantıyı yalnızca
 * bgstudio.3dtr@gmail.com hesabı açabilir. Talep başına tek bildirim e-postası gelir.
 */

const FOLDER_ID = '1k29hXH90zXfCEPczat2Gx5yWx-NcAA3C';
const NOTIFY_EMAIL = 'bgstudio.3dtr@gmail.com';
const MAX_BYTES = 15 * 1024 * 1024;
const ALLOWED_EXT = ['png', 'jpg', 'jpeg', 'webp', 'pdf', 'stl', '3mf', 'step', 'stp', 'obj'];

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    const name = String(body.name || 'dosya').slice(0, 120).replace(/[\\/:*?"<>|]+/g, '-');
    const ext = name.split('.').pop().toLowerCase();
    if (ALLOWED_EXT.indexOf(ext) === -1) return reply_({ error: 'Bu dosya türü desteklenmiyor.' });
    const bytes = Utilities.base64Decode(String(body.data || ''));
    if (!bytes.length) return reply_({ error: 'Dosya boş.' });
    if (bytes.length > MAX_BYTES) return reply_({ error: 'Dosya 15 MB sınırını aşıyor.' });

    const ref = String(body.ref || '').replace(/[^a-zA-Z0-9]/g, '').slice(0, 12) || 'TALEP';
    const customer = String(body.customer || '').replace(/[\\/:*?"<>|]+/g, ' ')
      .replace(/\s+/g, ' ').trim().slice(0, 60) || 'Müşteri';
    const day = Utilities.formatDate(new Date(), 'Europe/Istanbul', 'yyyy-MM-dd');
    const folderName = customer + ' · ' + day + ' · ' + ref;

    // Aynı talebin dosyaları aynı klasöre: klasörü bulma/açma işlemi kilitli yapılır.
    lock.waitLock(20000);
    const root = DriveApp.getFolderById(FOLDER_ID);
    const existing = root.getFoldersByName(folderName);
    const folder = existing.hasNext() ? existing.next() : root.createFolder(folderName);
    lock.releaseLock();

    const blob = Utilities.newBlob(bytes, String(body.type || 'application/octet-stream'), name);
    const file = folder.createFile(blob);

    // Talep başına tek e-posta: son dosya kaydedildiğinde gönderilir.
    if (body.last) {
      const files = folder.getFiles();
      const list = [];
      while (files.hasNext()) {
        const f = files.next();
        list.push('• <a href="' + f.getUrl() + '">' + escape_(f.getName()) + '</a> (' + Math.ceil(f.getSize() / 1024) + ' KB)');
      }
      MailApp.sendEmail({
        to: NOTIFY_EMAIL,
        subject: 'Teklif dosyaları: ' + customer + ' (' + list.length + ' dosya)',
        htmlBody: '<b>' + escape_(customer) + '</b> web sitesindeki teklif formundan dosya gönderdi.<br>' +
          'Talep kodu: <b>' + ref + '</b><br><br>' + list.join('<br>') + '<br><br>' +
          '<a href="' + folder.getUrl() + '"><b>Müşterinin klasörünü Drive\'da aç →</b></a>'
      });
    }
    return reply_({ ok: true, folder: folder.getUrl(), url: file.getUrl(), name: name, size: bytes.length });
  } catch (err) {
    return reply_({ error: 'Yükleme başarısız: ' + err });
  } finally {
    try { lock.releaseLock(); } catch (ignore) {}
  }
}

function doGet() {
  return reply_({ ok: true, service: 'BG Studio 3D teklif dosyaları' });
}

function escape_(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
  });
}

function reply_(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
