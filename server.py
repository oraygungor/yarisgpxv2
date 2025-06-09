# Dosya Adı: server.py

from flask import Flask, request, redirect, render_template, jsonify
import requests
import os
import traceback # Hata dökümü için

# Flask'e HTML dosyasının bu betikle aynı klasörde olduğunu söylüyoruz.
app = Flask(__name__, template_folder='.')

# --- GÜVENLİ AYARLAR ---
# Hassas bilgiler, uygulamanın çalışacağı sunucudaki Ortam Değişkenleri'nden okunur.
STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')


# Bu fonksiyonları @app.route('/') ve @app.route('/login') arasına ekleyebilirsin.
# Sırası önemli değil, sadece var olmaları yeterli.

@app.route('/simulator')
def simulator_page():
    return render_template('yarissimulasyonu.html')

@app.route('/analyzer')
def analyzer_page():
    return render_template('yarisanalizi.html')

@app.route('/')
def index():
    # Projenin ana klasöründeki 'index.html' dosyasını sunar.
    return render_template('index.html')

@app.route('/login')
def login():
    # Kullanıcıyı Strava'ya yönlendirir.
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
    per_page = 100
    
    # WORKER TIMEOUT hatasını önlemek için döngüye sınır koyuyoruz.
    MAX_PAGES = 5 
    
    print(f"Strava API'ye istek gönderiliyor... Maksimum {MAX_PAGES} sayfa çekilecek.")
    
    try:
        for current_page in range(1, MAX_PAGES + 1):
            params = {'per_page': per_page, 'page': current_page}
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
        print("Hata: Strava API'den yanıt 10 saniye içinde gelmedi (Request Timeout).")
        return jsonify({"error": "Strava'dan zamanında yanıt alınamadı."}), 504

    except Exception as e:
        print(f"Sunucu içinde /get_activities endpoint'inde beklenmedik bir hata oluştu: {e}")
        traceback.print_exc()
        return jsonify({"error": "Sunucuda beklenmedik bir hata oluştu."}), 500

# --- SADECE TEK VE DOĞRU /GET_GPX FONKSİYONU ---
@app.route('/get_gpx/<activity_id>')
def get_gpx(activity_id):
    # Seçilen tek bir aktivitenin detaylı veri akışını (stream) çeker.
    print(f"--- /get_gpx isteği alındı, Activity ID: {activity_id} ---")
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or "Bearer " not in auth_header:
        print("HATA: Authorization başlığı eksik.")
        return jsonify({"error": "Authorization başlığı eksik veya hatalı"}), 401
        
    token = auth_header.split("Bearer ")[1]
    
    stream_url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {'Authorization': f'Bearer {token}'}
    
    # İSTEDİĞİMİZ TÜM ANAHTARLARI BURAYA YAZALIM
    stream_keys = 'time,latlng,altitude'
    params = {'keys': stream_keys, 'key_by_type': 'true'}
    
    print(f"Strava'ya istek gönderiliyor. URL: {stream_url}, Keys: {stream_keys}")

    try:
        response = requests.get(stream_url, headers=headers, params=params, timeout=20)

        print(f"Strava'dan yanıt alındı. Durum Kodu: {response.status_code}")

        # Eğer yanıt başarılı değilse, hatayı logla ve geri dön
        if response.status_code != 200:
            print(f"HATA: Strava API'si başarısız yanıt döndü. İçerik: {response.text}")
            return jsonify({"error": f"Strava API hatası: {response.text}"}), response.status_code
        
        # Yanıt başarılıysa, gelen verinin anahtarlarını loglayalım
        data = response.json()
        print(f"Başarıyla parse edilen JSON'un anahtarları: {list(data.keys())}")
        
        # Eğer 'altitude' anahtarı yoksa, bunu özel olarak loglayalım
        if 'altitude' not in data:
            print("DİKKAT: Strava'dan gelen yanıtta 'altitude' verisi bulunmuyor!")

        return jsonify(data)

    except requests.exceptions.Timeout:
        print("HATA: Strava'dan 20 saniye içinde yanıt gelmedi (Request Timeout).")
        return jsonify({"error": "Strava'dan zamanında yanıt alınamadı."}), 504

    except Exception as e:
        print(f"Sunucu içinde /get_gpx endpoint'inde beklenmedik bir hata oluştu: {e}")
        traceback.print_exc()
        return jsonify({"error": "Sunucuda beklenmedik bir hata oluştu."}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # debug=False, canlıya çıkarken güvenlik için önemlidir.
    app.run(host='0.0.0.0', port=port, debug=False)
