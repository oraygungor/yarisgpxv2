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
    # JavaScript'ten gelen yetkilendirme başlığını alır.
    auth_header = request.headers.get('Authorization')
    if not auth_header or "Bearer " not in auth_header:
        return jsonify({"error": "Authorization başlığı eksik veya hatalı"}), 401
    
    token = auth_header.split("Bearer ")[1]
    
    # Tüm aktivite sayfalarını çekmek için döngü kullanır.
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {token}'}
    all_activities = []
    page = 1
    per_page = 100
    
    while True:
        params = {'per_page': per_page, 'page': page}
        response = requests.get(activities_url, headers=headers, params=params)
        
        if response.status_code != 200:
            return jsonify({"error": f"Strava API hatası: {response.text}"}), response.status_code
            
        activities = response.json()
        if not activities:
            break
            
        all_activities.extend(activities)
        page += 1
        if len(activities) < per_page:
            break

    return jsonify(all_activities)

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