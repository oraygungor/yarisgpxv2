# Dosya Adı: server.py
# Bu versiyon, hassas bilgiler olmadan GitHub'a yüklenebilir.

from flask import Flask, request, redirect, render_template, jsonify
import requests
from datetime import datetime, timedelta
import os # Ortam değişkenlerini okumak için os modülü

# Flask'e HTML dosyasının bu betikle aynı klasörde olduğunu söylüyoruz.
app = Flask(__name__, template_folder='.')

# --- GÜVENLİ AYARLAR ---
# Hassas bilgiler, uygulamanın çalışacağı sunucudaki (Render gibi)
# Ortam Değişkenleri'nden (Environment Variables) okunur.
# Bu sayede gizli anahtarlar kodun içinde yer almaz.
STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')

# REDIRECT_URI, hem yerel testler hem de canlı sunucu için ayarlanabilir olmalı.
# Render gibi platformlarda bu da bir ortam değişkeni olarak ayarlanabilir.
# Varsayılan olarak yerel adresi kullanıyoruz.
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')


@app.route('/')
def index():
    # Projenin ana klasöründeki 'index.html' dosyasını sunar.
    # HTML dosyanızın adının 'index.html' olduğundan emin olun.
    return render_template('index.html')

@app.route('/login')
def login():
    # Kullanıcıyı Strava'ya yönlendirir.
    # scope=activity:read_all, kullanıcının tüm aktivitelerini okuma izni ister.
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={STRAVA_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=activity:read_all"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Strava, kullanıcı izin verdikten sonra bu adrese bir 'code' ile geri döner.
    code = request.args.get('code')
    if not code:
        return "Hata: Yetkilendirme kodu alınamadı.", 400

    # Alınan 'code' ve 'Client Secret' kullanılarak kalıcı bir 'access_token' alınır.
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload)
    
    if response.status_code != 200:
        return f"Hata: Erişim jetonu alınamadı. Strava yanıtı: {response.text}", 400

    access_token = response.json().get('access_token')
    
    # Jetonu tarayıcının yerel deposuna kaydetmek ve ana sayfaya yönlendirmek için JS kullanılır.
    return f"""
        <script>
            localStorage.setItem('strava_token', '{access_token}');
            window.location.href = '/';
        </script>
    """

@app.route('/get_activities')
def get_activities():
    print("--- /get_activities isteği alındı ---")
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or "Bearer " not in auth_header:
        print("Hata: Authorization başlığı eksik veya hatalı.")
        return jsonify({"error": "Authorization başlığı eksik veya hatalı"}), 401
    
    token = auth_header.split("Bearer ")[1]
    print(f"Alınan token (ilk 5 karakter): {token[:5]}...")

    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {token}'}
    all_activities = []
    page = 1
    per_page = 100
    
    # --- DEĞİŞİKLİK: DÖNGÜYE SINIR KOYUYORUZ ---
    # En fazla 5 sayfa (500 aktivite) çek. Bu, çoğu durum için timeout'u önler.
    MAX_PAGES = 5 
    
    print(f"Strava API'ye istek gönderiliyor... Maksimum {MAX_PAGES} sayfa çekilecek.")
    
    try:
        # while True yerine for döngüsü kullanarak sınırı uyguluyoruz
        for current_page in range(1, MAX_PAGES + 1):
            params = {'per_page': per_page, 'page': current_page}
            
            # DEĞİŞİKLİK: Her isteğe bir timeout ekleyelim.
            # 10 saniye içinde yanıt gelmezse hata verir.
            response = requests.get(activities_url, headers=headers, params=params, timeout=10)
            
            print(f"Strava'dan yanıt alındı. Sayfa: {current_page}, Durum Kodu: {response.status_code}")

            if response.status_code != 200:
                print(f"Strava API Hatası! Yanıt İçeriği: {response.text}")
                return jsonify({"error": f"Strava API hatası: {response.text}"}), response.status_code
                
            activities = response.json()
            if not activities:
                print("Daha fazla aktivite bulunamadı. Döngü sonlandırılıyor.")
                break
                
            all_activities.extend(activities)
            print(f"Toplam {len(all_activities)} aktivite çekildi.")
            
            if len(activities) < per_page:
                print("Son sayfaya ulaşıldı. Döngü sonlandırılıyor.")
                break

        print("--- /get_activities isteği başarıyla tamamlandı ---")
        return jsonify(all_activities)

    except requests.exceptions.Timeout:
        # requests'in kendi timeout hatasını yakala
        print("Hata: Strava API'den yanıt 10 saniye içinde gelmedi (Request Timeout).")
        return jsonify({"error": "Strava'dan zamanında yanıt alınamadı."}), 504 # Gateway Timeout

    except Exception as e:
        print(f"Sunucu içinde beklenmedik bir hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Sunucuda beklenmedik bir hata oluştu."}), 500

@app.route('/get_gpx/<activity_id>')
def get_gpx(activity_id):
    # Seçilen tek bir aktivitenin detaylı veri akışını (stream) çeker.
    auth_header = request.headers.get('Authorization')
    if not auth_header or "Bearer " not in auth_header:
        return jsonify({"error": "Authorization başlığı eksik veya hatalı"}), 401
        
    token = auth_header.split("Bearer ")[1]
    
    stream_url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {'Authorization': f'Bearer {token}'}
    params = {'keys': 'time,latlng,altitude', 'key_by_type': 'true'}
    response = requests.get(stream_url, headers=headers, params=params)

    return jsonify(response.json())


# Bu blok, dosya 'python server.py' ile çalıştırıldığında devreye girer.
# Gunicorn gibi profesyonel bir sunucu bu bloğu kullanmaz.
if __name__ == '__main__':
    # '0.0.0.0' host'u, uygulamanın ağdaki diğer cihazlar tarafından erişilebilir olmasını sağlar.
    # Render gibi platformlar bunu gerektirir.
    # debug=False, canlıya çıkarken güvenlik için önemlidir.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
