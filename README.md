
Proje Başlığı: Strava Koşu Performans Modeli ve Yarış Simülatörü
Ana Amaç: Kullanıcıların Strava koşu verilerini kullanarak kişisel bir "Eğim/Pace Performans Modeli" oluşturmalarını ve bu modeli kullanarak seçtikleri bir yarış parkurunun (GPX dosyası) simülasyonunu yapmalarını sağlayan tek sayfalık bir web uygulaması (SPA) geliştirmek.
Teknik Gereksinimler:
Frontend Teknolojisi: Tüm analiz ve görselleştirme işlemleri, sunucu yükünü minimumda tutmak için istemci tarafında (tarayıcıda) yapılacaktır. Bu amaçla Pyodide kullanılacak ve gerekli Python kütüphaneleri (gpxpy, numpy, pandas, plotly) tarayıcıda çalıştırılacaktır.
Backend Teknolojisi: Strava ile OAuth2 kimlik doğrulamasını yönetmek ve API'den veri çekmek için Python'da basit bir Flask sunucusu (server.py) oluşturulacaktır.
Güvenlik: Hiçbir hassas bilgi (Client ID, Secret Key) kodun içine yazılmayacaktır. Bu bilgiler, Render gibi hosting platformları için Ortam Değişkenleri (Environment Variables) üzerinden okunacak şekilde server.py yapılandırılmalıdır.
Uygulama Akışı ve Özellikleri (Adım Adım):
Adım 1: Kimlik Doğrulama ve Oturum Yönetimi
Uygulama açıldığında, kullanıcıya bir "Strava ile Bağlan" butonu gösterilecek.
Kullanıcı bağlandığında, access_token tarayıcının localStorage'ına kaydedilecek.
Hata Yönetimi: Eğer kaydedilmiş bir token varsa ama süresi dolmuşsa (API 401 Unauthorized hatası verirse), uygulama token'ı otomatik olarak silmeli, kullanıcıyı bilgilendirmeli ("Oturumunuzun süresi doldu, lütfen tekrar bağlanın.") ve giriş ekranına yönlendirmelidir.
Adım 2: Veri Yükleme ve Model Seçimi
Giriş yapıldıktan sonra, tüm koşu aktiviteleri (Run, TrailRun, VirtualRun) Strava'dan çekilecek.
Kullanıcı Deneyimi (Önbellek): Bu aktivite listesi, her sayfa yenilendiğinde tekrar çekilmemelidir. Liste ilk çekildiğinde tarayıcının sessionStorage'ına kaydedilmeli ve sonraki yüklemelerde oradan okunmalıdır. Kullanıcının listeyi tazeleyebilmesi için bir "Aktiviteleri Yenile" butonu bulunmalıdır.
Çekilen veriler, "Yol Koşuları" (Run, VirtualRun) ve "Patika Koşuları" (TrailRun) olarak ikiye ayrılacak. Kullanıcıya, hangi veri setinden model oluşturmak istediğini soran iki buton gösterilecek.
Adım 3: Performans Modeli Oluşturma ve Görselleştirme
Kullanıcı model tipini (Yol/Patika) seçtiğinde:
İlgili kategorideki 15-40 km arası en son 10 koşunun detaylı veri akışları (time, latlng, altitude) Strava'dan çekilecek.
Bu veriler birleştirilecek ve gpxpy kullanılarak analiz edilecek.
Yükseklik Verisi Düzeltme: Ham yükseklik verisindeki gürültüyü temizlemek için analizden önce gpx.smooth(vertical=True, remove_extremes=True) fonksiyonu uygulanmalıdır. Bu, toplam yükseklik kazancı hesabının daha doğru olmasını sağlar.
Veri, 50 metrelik segmentlere bölünecek ve her segmentin eğimi ile pace'i hesaplanacak.
Bu eğim/pace verisine 2. dereceden bir polinom regresyon (eğri uydurma) uygulanarak bir performans modeli (formül) oluşturulacak.
Görselleştirme:
Plotly kullanılarak, bu model interaktif bir grafikte gösterilecek. Grafik, ham veri noktalarını (scatter plot) ve üzerine oturtulmuş performans eğrisini (line plot) içerecek.
Grafiğin X ekseni (Eğim) -30% ile +30% arasında sabitlenecek.
Grafiğin Y ekseni (Pace) ters çevrilmiş olacak (yavaş pace'ler üstte) ve sınırlar, modelin -35% ve +%35 eğimlerdeki tahminlerine göre bir miktar tampon payı bırakılarak dinamik olarak ayarlanacak.
Modelin matematiksel formülü (Pace = a*x² + b*x + c) grafiğin altında gösterilecek.
Adım 4: Yarış Simülasyonu
Kullanıcıya bir GPX dosyası yükleme ve bir "yorgunluk faktörü" (örneğin: her 20km'de %5 performans düşüşü) girme imkanı verilecek.
Simülasyon Mantığı:
Yüklenen yarış GPX'i de gpx.smooth() ile yumuşatılacak.
Parkur, 20 metrelik kısa segmentlere bölünecek.
Her segmentin eğimi hesaplanacak.
Bu eğim değeri, 3. Adımda oluşturulan performans modeline sokularak o segmentteki baz pace tahmin edilecek.
Tahmin edilen pace, o ana kadar kat edilen mesafeye göre yorgunluk faktörü ile çarpılarak yavaşlatılacak.
Her segmentin süresi hesaplanıp toplanarak toplam yarış süresi bulunacak.
Sonuç Görselleştirmesi:
Tahmini toplam bitiş süresi (HH:MM:SS formatında) gösterilecek.
Plotly kullanılarak, yarışın yükseklik profilini ve yarış boyunca değişen tahmini pace'i gösteren ikinci bir grafik çizilecek.
Bu prompt, sadece ne yapılacağını değil, aynı zamanda neden ve nasıl yapılacağını da (hata yönetimi, önbellekleme, veri düzeltme gibi) detaylandırarak, geliştirme sürecinde karşılaşılabilecek hemen hemen tüm sorunları önceden ele alıyor ve tek seferde nihai ürüne ulaşmayı hedefliyor.
