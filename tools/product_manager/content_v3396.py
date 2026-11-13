"""v3.3.96 · Content for the pages that were under 300 words.

Only facts already stated elsewhere on the site, in the panel data or by the owner:
PLA + PETG only, 1–3 business days production, ~1 week cargo, 14-day return for
non-personalised items, personalised items not returnable, WhatsApp 0530 246 69 03,
bgstudio.3dtr@gmail.com, Kuşadası based, founder Mimar Berkant Gökbel.
Project sections describe how that kind of job runs, never invented project details.
"""
from html import escape as _e

WA = 'https://wa.me/905302466903?text=Merhaba%20BG%20Studio%203D%2C%20web%20sitenizden%20yaz%C4%B1yorum.'
MAIL = 'bgstudio.3dtr@gmail.com'


def esc(v):
    return _e(str(v), quote=True)


def cards(eyebrow, title, intro, items, extra_class=''):
    """items: (title, text) — rendered as the site's cap-card grid."""
    cards_html = ''.join(
        f'<article class="cap-card"><span class="cap-no">{i:02d}</span><h3>{esc(t)}</h3><p>{esc(p)}</p></article>'
        for i, (t, p) in enumerate(items, 1))
    intro_html = f'<p>{esc(intro)}</p>' if intro else ''
    return (f'<section class="section-pad-sm shell content-v3396 {extra_class}"><div class="split-title"><div><p class="eyebrow">{esc(eyebrow)}</p>'
            f'<h2>{esc(title)}</h2></div>{intro_html}</div><div class="capability-grid">{cards_html}</div></section>')


def qa(eyebrow, title, items):
    """Always-open questions and answers (no accordion)."""
    rows = ''.join(f'<article><h3>{esc(q)}</h3><p>{esc(a)}</p></article>' for q, a in items)
    return (f'<section class="section-pad-sm shell content-v3396"><div class="split-title"><div><p class="eyebrow">{esc(eyebrow)}</p>'
            f'<h2>{esc(title)}</h2></div></div><div class="qa-v3396">{rows}</div></section>')


# ---------------------------------------------------------------- Hakkımızda
ABOUT_FOUNDER = (
    '<section class="section-pad-sm shell content-v3396"><div class="maket-architect">'
    '<span class="mono"><img src="../assets/brand/bgstudio3d-monogram.webp" alt="" width="128" height="128" loading="lazy" decoding="async"></span>'
    '<div><p class="eyebrow">KURUCU</p><h2>Bir mimarın kurduğu üretim stüdyosu.</h2>'
    '<p>BG Studio, Mimar Berkant Gökbel tarafından Kuşadası’nda kuruldu. Mimarlıktan gelen ölçek, detay ve üretilebilirlik bakışı '
    'stüdyonun yaptığı her işe taşınır: bir anahtarlıktaki logonun küçük boyutta okunup okunmadığından, bir restoran masasındaki '
    'standın misafirin elinin altına nasıl yerleşeceğine kadar.</p>'
    '<p>Mimari projeler ve 3D görselleştirme <a href="https://bgstudio.com.tr" rel="noopener" target="_blank">BG Studio Architecture</a> '
    'çatısı altında, fiziksel ürün, özel üretim ve işletme sistemleri BG Studio 3D’de yürür. İki iş kolu aynı stüdyodan çıkar.</p>'
    '</div></div></section>'
)

ABOUT_WORK = [
    ('Hazır ürünler', 'Katalogdaki dekor, aksesuar ve kullanım ürünleri sipariş üzerine basılır. Stokta bekleyen ürün yerine siparişe göre üretim yapılır.'),
    ('Kişiye özel ürünler', 'İsim, logo, ölçü veya renk seçimiyle kişiselleştirilen hediyelik ve kullanım ürünleri. Tasarım üretimden önce onaylanır.'),
    ('Kurumsal üretim', 'Logolu anahtarlık, telefon standı gibi promosyon ürünleri. 30, 50 ve 100 adetlik kurumsal işler projeler sayfasında.'),
    ('Prototip ve yedek parça', 'Bulunamayan ya da kırılan parçalar ölçüye göre modellenip üretilir: bir bot pompası ara parçası, bir çikolata şelalesi spiral aksamı gibi.'),
    ('Mimari maket', 'STL, 3MF veya OBJ dosyasından kütle, cephe ve vaziyet maketleri. Ölçek ve parçalama kararları mimari çizim bilgisiyle verilir.'),
    ('NFC + QR işletme sistemleri', 'Restoran masa standları, hızlı bağlantı standları ve yorum kartları. Bağlantılar panelden yönetilir, stand yeniden üretilmez.'),
]

ABOUT_MATERIAL = [
    ('PLA', 'İç mekân dekoru, hediyelik ürünler, maket ve sunum parçaları için. Temiz yüzey, canlı renk seçeneği ve keskin detay verir.'),
    ('PETG', 'Daha dayanıklı ve esnek bir malzeme. Darbeye, neme ve sıcaklığa karşı daha toleranslı olduğu için fonksiyonel parçalarda tercih edilir.'),
    ('Çok renkli baskı', 'Logo ve yazılar boya ya da etiketle değil, baskı sırasında farklı renkte filamentle ürünün kendisine işlenir.'),
]

ABOUT_AREA = [
    ('Kuşadası', 'Üretim ve elden teslim Kuşadası’nda. Uygun siparişler elden teslim edilebilir.'),
    ('Ege bölgesi', 'İzmir, Aydın, Söke, Selçuk, Didim ve Bodrum’daki işletmeler ve mimarlarla çalışıyoruz.'),
    ('Türkiye geneli', 'Gönderime uygun ürünler Türkiye’nin her yerine kargoyla ulaşır; kargo genellikle 1 hafta içinde teslim edilir.'),
]


def about_extra():
    return (ABOUT_FOUNDER
            + cards('NELER YAPIYORUZ', 'Altı iş, tek üretim hattı.', 'Aynı atölyede, aynı tasarım ve kontrol süreciyle yürüyen işler.', ABOUT_WORK)
            + cards('MALZEME', 'İki malzeme, doğru yerde.', 'Yalnızca PLA ve PETG ile çalışıyoruz. Hangisinin uygun olduğunu ürünün nerede kullanılacağına göre birlikte seçeriz.', ABOUT_MATERIAL)
            + cards('HİZMET BÖLGESİ', 'Kuşadası’ndan Türkiye’ye.', '', ABOUT_AREA))


# ---------------------------------------------------------------- İletişim
CONTACT_CHANNELS = (
    '<section class="section-pad-sm shell content-v3396"><div class="split-title"><div><p class="eyebrow">İLETİŞİM BİLGİLERİ</p>'
    '<h2>Bize buradan ulaşabilirsiniz.</h2></div><p>Sipariş ve teklif talepleri WhatsApp üzerinden en hızlı şekilde netleşir. '
    'Dosya ve uzun açıklamalar için e-posta veya teklif formu da kullanılabilir.</p></div>'
    '<div class="contact-list-v3396">'
    f'<a href="{WA}" rel="noopener" target="_blank"><small>WhatsApp</small><strong>0530 246 69 03</strong></a>'
    f'<a href="mailto:{MAIL}"><small>E-posta</small><strong>{MAIL}</strong></a>'
    '<a href="https://instagram.com/bgstudio.3dtr" rel="noopener" target="_blank"><small>Instagram</small><strong>@bgstudio.3dtr</strong></a>'
    '<div><small>Konum</small><strong>Kuşadası, Aydın</strong></div>'
    '</div></section>'
)

CONTACT_BRIEF = [
    ('Hazır ürün siparişi', 'Ürünün adı veya bağlantısı, renk, adet ve teslim edilecek şehir. Kuşadası’ndaysanız elden teslim isteyip istemediğinizi belirtin.'),
    ('Kişiye özel ürün', 'Yazılacak isim veya metin, logo dosyası (mümkünse SVG ya da PDF), renk tercihi ve adet.'),
    ('Kurumsal ve toplu iş', 'Adet, logo, kullanım amacı ve ihtiyaç tarihi. Toplu işlerde gerekirse önce test baskısı alınır.'),
    ('Prototip ve yedek parça', 'Parçanın birkaç açıdan fotoğrafı, ölçüleri ve nerede kullanılacağı. Kırık parça elinizdeyse onu da belirtin.'),
    ('Mimari maket', 'STL, 3MF veya OBJ dosyası, istenen ölçek ve sunum ya da jüri tarihi.'),
    ('NFC + QR sistemi', 'İşletme türü, masa veya stand sayısı ve yönlendirmek istediğiniz hesaplar: Google, Instagram, WhatsApp, menü.'),
]

CONTACT_QA = [
    ('Dosyamı nasıl gönderirim?', 'Teklif formundaki dosya alanına yükleyebilirsiniz; dosyalar talebinizle birlikte bize ulaşır. Dilerseniz WhatsApp veya e-posta ile de gönderebilirsiniz.'),
    ('Kuşadası dışından sipariş verebilir miyim?', 'Evet. Gönderime uygun ürünler Türkiye geneline kargoyla gönderilir. Kargo ücreti teslimat sırasında alıcı tarafından ödenir.'),
    ('Fiyatı önceden öğrenebilir miyim?', 'Katalogdaki ürünlerin fiyatı ürün sayfasında yazar. Özel üretim, toplu iş ve maketlerde fiyatı kapsamı gördükten sonra netleştiririz.'),
]


def contact_extra():
    return (CONTACT_CHANNELS
            + cards('TALEBE GÖRE', 'İlk mesajda neyi paylaşmalısınız?', 'Bu bilgilerle gelen talepler ilk yanıtta netleşir.', CONTACT_BRIEF)
            + qa('SIK SORULANLAR', 'İletişim ve sipariş.', CONTACT_QA))


# ---------------------------------------------------------------- Hızlı Bağlantı Standı
QUICK_HOW = [
    ('Dokun', 'Müşteri NFC’si açık telefonunu standdaki noktaya yaklaştırır. Uygulama gerekmez; bağlantı doğrudan tarayıcıda açılır.'),
    ('Okut', 'QR seçeneği eklendiyse NFC’si olmayan telefonlar da kameradan okutarak aynı hedefe ulaşır.'),
    ('Yönet', 'Hedef bağlantılar BG Studio NFC panelinden değiştirilir. Instagram hesabı ya da kampanya sayfası değişse bile stand yeniden üretilmez.'),
]

QUICK_FOR = [
    ('Kafe ve pastane', 'Kasa veya masa üzerinde Google yorumu, Instagram ve WhatsApp sipariş hattı tek noktada.'),
    ('Petshop ve mağaza', 'Bankoda duran stand ile müşteriler sosyal medya ve iletişim kanallarına hızlıca geçer. Örnek: Koala Petshop.'),
    ('Kuaför ve güzellik salonu', 'Randevu için WhatsApp, çalışmalar için Instagram, memnuniyet için Google yorumu.'),
    ('Ofis ve büro', 'Resepsiyonda web sitesi, konum ve iletişim bağlantılarını bir arada sunar.'),
]

QUICK_QA = [
    ('Hangi telefonlar dokunarak açar?', 'NFC özelliği olan Android telefonlar ve iPhone XS ile sonraki iPhone modelleri. NFC’si kapalı veya olmayan telefonlar için standa QR eklenebilir.'),
    ('Müşterinin bir uygulama indirmesi gerekir mi?', 'Hayır. Bağlantı telefonun kendi tarayıcısında açılır.'),
    ('Bağlantıları sonradan değiştirebilir miyim?', 'Evet. Standdaki üç hedef panelden güncellenir; fiziksel ürün olduğu gibi kalır.'),
    ('Hangi bağlantının ne kadar kullanıldığını görebilir miyim?', 'Evet. BG Studio NFC panelinde her bağlantının kaç kez açıldığı görünür.'),
]


def quick_extra():
    return (cards('NASIL ÇALIŞIR', 'Dokun, okut, yönet.', '', QUICK_HOW)
            + cards('KİMLER İÇİN', 'Bankoda, kasada, masada.', 'Hızlı Bağlantı Standı tek noktadan birkaç kanala yönlendirmek isteyen her işletmeye uyar.', QUICK_FOR)
            + qa('SIK SORULANLAR', 'Hızlı Bağlantı Standı hakkında.', QUICK_QA))


# ---------------------------------------------------------------- Proje sayfaları
PROJECT_PROCESS = {
    'corporate': ('BU TÜR İŞ NASIL İLERLER', 'Logodan seri üretime.', 'Kurumsal ve promosyon ürünlerinde izlediğimiz yol.', [
        ('Kapsam', 'Adet, ürün tipi, renkler ve ürünün nasıl dağıtılacağı netleştirilir. İşletme logosunu paylaşır.'),
        ('Baskıya uyarlama', 'Logo çok renkli 3D baskıda küçük boyutta da okunacak şekilde hazırlanır; ince çizgi ve küçük yazılar kontrol edilir.'),
        ('Onay ve test', 'Tasarım işletmeye onaya sunulur. Toplu işlerde gerekirse seri üretimden önce test baskısı alınır.'),
        ('Seri üretim ve teslim', 'Ürünler basılır, halka gibi parçaları takılır, kontrol edilip paketlenir. Kuşadası’nda elden, diğer şehirlere kargoyla teslim edilir.'),
    ]),
    'nfc': ('BU TÜR İŞ NASIL İLERLER', 'Planlamadan panele.', 'NFC ve QR işletme sistemlerinde izlediğimiz yol.', [
        ('Kurulum planı', 'Masa veya stand sayısı ve misafirin yönlendirileceği hesaplar belirlenir: Google, Tripadvisor, Instagram, WhatsApp, menü.'),
        ('Tasarım', 'Stand ya da kart işletmenin logosu ve renkleriyle tasarlanır; QR ve NFC noktaları misafirin kolay ulaşacağı yere yerleştirilir.'),
        ('Üretim ve bağlantı', 'Ürünler 3D baskıyla üretilir. Her NFC ve QR noktası işletmenin hedef bağlantısına tanımlanır.'),
        ('Teslim ve panel', 'Kurulumdan sonra hedefler BG Studio NFC panelinden güncellenebilir ve hangi bağlantının ne kadar açıldığı izlenebilir.'),
    ]),
    'prototype': ('BU TÜR İŞ NASIL İLERLER', 'Ölçüden çalışan parçaya.', 'Prototip ve yedek parça işlerinde izlediğimiz yol.', [
        ('Parça bilgisi', 'Parçanın fotoğrafları, ölçüleri ve nerede çalışacağı paylaşılır. Kırık parça varsa ölçü için o da kullanılır.'),
        ('Modelleme', 'Parça ölçülere göre dijital olarak modellenir; bağlantı noktaları ve toleranslar kullanım yerine göre ayarlanır.'),
        ('Deneme', 'İlk baskı yerine takılarak denenir. Oturmayan veya zorlanan noktalar varsa model düzeltilip yeniden basılır.'),
        ('Malzeme ve teslim', 'Kullanım koşuluna göre PLA veya PETG seçilir. Çalışan parça teslim edilir; model gerektiğinde tekrar üretim için saklanır.'),
    ]),
}


def project_extra(kind):
    eyebrow, title, intro, steps = PROJECT_PROCESS.get(kind) or PROJECT_PROCESS['corporate']
    return cards(eyebrow, title, intro, steps, 'project-process-v3396')


# ---------------------------------------------------------------- Yasal sayfalar
# (head, text) — text may be a list: first item a paragraph, the rest bullet points.
LEGAL_PAGES = {
    'kvkk': ('KVKK Aydınlatma Metni', '6698 sayılı Kişisel Verilerin Korunması Kanunu kapsamında; web sitesi, teklif, sipariş ve iletişim süreçlerinde paylaştığınız kişisel verilerin nasıl işlendiğine ilişkin bilgilendirme.', [
        ('Veri sorumlusu', f'BG Studio 3D (Kurucu: Mimar Berkant Gökbel), Kuşadası / Aydın. İletişim: {MAIL} · WhatsApp 0530 246 69 03.'),
        ('İşlenen kişisel veriler', ['Talebinize ve kullandığınız kanala göre aşağıdaki veriler işlenebilir:',
            'Kimlik ve iletişim bilgileri: ad soyad, telefon numarası, e-posta adresi.',
            'İşletme bilgileri: işletme adı, sektörü ve kurulum bilgileri (NFC + QR ve kurumsal işlerde).',
            'Talep ve sipariş bilgileri: ürün, adet, renk, kişiselleştirme içeriği ve notlar.',
            'Teslimat bilgileri: kargo için teslimat adresi.',
            'Teklif formuyla yüklediğiniz dosyalar: görsel, logo, STL, 3MF veya OBJ dosyaları.',
            'Site asistanına yazdığınız mesajlar.',
            'Çerez ve kullanım verileri: yalnızca analitiğe izin verdiğinizde.']),
        ('İşleme amaçları', ['Kişisel veriler şu amaçlarla işlenir:',
            'Teklif ve sipariş taleplerini yanıtlamak, üretim kapsamını netleştirmek.',
            'Kişiye özel ve kurumsal ürünleri tasarlamak, üretmek ve teslim etmek.',
            'Teslimat, iade ve değişim süreçlerini yürütmek.',
            'Yasal yükümlülükleri yerine getirmek.',
            'İzin verdiğiniz durumda site kullanımını ölçüp siteyi geliştirmek.']),
        ('Hukuki sebepler', 'Veriler, Kanun’un 5. maddesinin 2. fıkrasındaki sözleşmenin kurulması ve ifası, hukuki yükümlülüğün yerine getirilmesi ve veri sorumlusunun meşru menfaati sebeplerine dayanılarak işlenir. Analitik çerezler yalnızca açık rızanızla çalışır.'),
        ('Aktarım', ['Veriler yalnızca hizmetin gerektirdiği ölçüde şu taraflarla paylaşılır:',
            'Kargo firmaları: teslimat için ad, telefon ve adres.',
            'Shopier: Shopier mağazamızdan verilen siparişlerde ödeme ve sipariş bilgileri Shopier tarafından işlenir; kart bilgileriniz bize iletilmez.',
            'Google: teklif formu dosyalarının saklandığı Google Drive, e-posta ve izin verdiyseniz Google Analytics.',
            'WhatsApp (Meta): WhatsApp üzerinden yazıştığınızda.',
            'Yasal zorunluluk hâlinde yetkili kamu kurumları.',
            'Bu hizmet sağlayıcıların sunucuları yurt dışında bulunabilir.']),
        ('Saklama süresi', 'Veriler işlendikleri amacın gerektirdiği süre boyunca saklanır. Fatura ve ticari kayıtlar ilgili mevzuatta öngörülen süreler boyunca tutulur; süre sona erdiğinde veriler silinir veya anonim hâle getirilir.'),
        ('Haklarınız', ['Kanun’un 11. maddesi uyarınca şu haklara sahipsiniz:',
            'Kişisel verilerinizin işlenip işlenmediğini öğrenme ve işlendiyse bilgi talep etme.',
            'İşlenme amacını ve amacına uygun kullanılıp kullanılmadığını öğrenme.',
            'Yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri bilme.',
            'Eksik veya yanlış işlenmişse düzeltilmesini isteme.',
            'Kanun’daki şartlar çerçevesinde silinmesini veya yok edilmesini isteme ve bu işlemlerin aktarılan üçüncü kişilere bildirilmesini isteme.',
            'Otomatik sistemlerle analiz edilmesi sonucu aleyhinize bir sonuç çıkmasına itiraz etme.',
            'Kanuna aykırı işleme nedeniyle zarara uğramanız hâlinde zararın giderilmesini talep etme.']),
        ('Başvuru', f'Haklarınızla ilgili taleplerinizi {MAIL} adresine e-posta ile iletebilirsiniz. Başvurular en geç 30 gün içinde ücretsiz olarak yanıtlanır.'),
    ]),
    'teslimat-iade': ('Teslimat / İade', 'Ürünler sipariş üzerine üretilir; teslim, kargo, cayma ve iade kuralları aşağıdadır.', [
        ('Üretim süresi', 'Ürünler sipariş onayından sonra 1–3 iş günü içinde PLA veya PETG malzemeden üretilir, ardından kargoya verilir. Toplu ve kurumsal siparişlerde süre sipariş öncesinde ayrıca paylaşılır.'),
        ('Kargo', 'Türkiye geneline kargo ile gönderilir; kargoya verilen ürün genellikle 1 hafta içinde teslim edilir. Kargo ücreti teslimat sırasında alıcı tarafından ödenir. Uygun siparişlerde Kuşadası’nda elden teslim seçeneği vardır.'),
        ('Teslim alırken', 'Paketi kargo görevlisinin yanında kontrol edin. Pakette ezilme, yırtılma veya ıslanma varsa görevliye hasar tespit tutanağı tutturun; bu tutanak hasarlı ürün sürecini hızlandırır.'),
        ('Hasarlı veya hatalı ürün', 'Kargo kaynaklı hasar veya üretim hatası olursa paketin ve ürünün fotoğraflarıyla WhatsApp (0530 246 69 03) ya da bgstudio.3dtr@gmail.com üzerinden bize ulaşın; değişim ya da iade yapıyoruz.'),
        ('14 gün içinde iade', 'Kişiselleştirilmemiş ürünlerde, ürünü teslim aldığınız günden itibaren 14 gün içinde gerekçe göstermeden iade talebinde bulunabilirsiniz. Ürünün olağan incelemenin ötesinde kullanılmamış ve hasarsız olması gerekir. İade gönderiminin kargo ücreti alıcıya aittir.'),
        ('İade nasıl yapılır', ['İade süreci üç adımda ilerler:',
            'WhatsApp veya e-posta ile sipariş bilgilerinizi ve iade talebinizi iletin.',
            'Ürünü, size bildireceğimiz adrese kargoyla gönderin.',
            'Ürün bize ulaşıp kontrol edildikten sonra ödemeniz en geç 14 gün içinde ödediğiniz yöntemle iade edilir.']),
        ('Kişiye özel ürünler', 'İsim, logo, ölçü veya müşteriye özgü başka bir detayla kişiselleştirilen ürünler, Mesafeli Sözleşmeler Yönetmeliği gereği cayma hakkı ve iade kapsamında değildir. Bu nedenle üretim öncesinde kişiselleştirme bilgilerinin doğru onaylanması önemlidir. Hasarlı veya hatalı ürün hakkınız kişiye özel ürünlerde de geçerlidir.'),
    ]),
    'kisiye-ozel-urun-kosullari': ('Kişiye Özel Ürün Koşulları', 'İsim, logo, ölçü, renk veya işletmeye özgü tasarımla hazırlanan işlerde onaylanan üretim kapsamı esas alınır.', [
        ('Onay', 'Üretim öncesinde isim, logo, ölçü, renk, adet ve diğer kişiselleştirme detaylarının doğru iletilmesi müşterinin sorumluluğundadır. Gerekli işlerde üretimden önce tasarım görseli onayınıza sunulur; üretim bu onaydan sonra başlar.'),
        ('Logo ve dosyalar', 'Logolar için SVG, PDF veya AI gibi vektör dosyalar en iyi sonucu verir. Yalnızca görsel varsa yüksek çözünürlüklü PNG gönderin. Çok ince çizgiler ve küçük yazılar 3D baskıda okunacak şekilde sadeleştirilebilir.'),
        ('Kullanım hakkı', 'Gönderdiğiniz logo, marka veya görselin kullanım hakkının size ait olduğu ya da kullanım için izin aldığınız kabul edilir.'),
        ('3D baskı yüzeyi', 'Katman izleri 3D baskı üretim yönteminin doğal bir parçasıdır. Ürünün malzeme ve yüzey karakteri sipariş öncesinde değerlendirilebilir.'),
        ('Renk ve ölçü', 'Ekranda gördüğünüz renk ile filament rengi arasında küçük farklar olabilir. Ölçülerde de üretim yöntemine bağlı küçük farklılıklar oluşabilir; ölçünün kritik olduğu işleri sipariş öncesinde belirtin.'),
        ('Revizyon', 'Üretim başladıktan sonra tasarım, ölçü veya kişiselleştirme değişiklikleri yeniden üretim gerektirebilir ve ayrıca fiyatlandırılabilir.'),
        ('İade', 'Kişiye özel ürünler cayma hakkı ve iade kapsamında değildir. Kargo hasarı veya üretim hatası durumunda değişim ya da iade yapılır; ayrıntılar Teslimat / İade sayfasındadır.'),
    ]),
}
