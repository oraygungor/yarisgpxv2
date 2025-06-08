# server.py
from flask import Flask, request, redirect, render_template, jsonify
import requests

app = Flask(__name__, template_folder='.') # HTML dosyasını aynı klasörde aramasını sağlar

# Strava'dan aldığınız bilgileri buraya girin
STRAVA_CLIENT_ID = "SİZİN_CLIENT_ID"
STRAVA_CLIENT_SECRET = "SİZİN_CLIENT_SECRET"
REDIRECT_URI = "http://127.0.0.1:5000/callback" # Yerel test için

# 1. Ana sayfayı göster
@app.route('/')
def index():
    return render_template('index.html') # Bizim HTML dosyamızın adı

# 2. Kullanıcıyı Strava'ya yönlendir
@app.route('/login')
def login():
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=activity:read_all"
    return redirect(auth_url)

# 3. Strava'dan gelen kodu al ve jetonla değiştir
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload)
    access_token = response.json().get('access_token')
    
    # Jetonu tarayıcıya göndermek için basit bir sayfa
    return f"""
        <script>
            localStorage.setItem('strava_token', '{access_token}');
            window.location.href = '/';
        </script>
    """

# 4. Aktiviteleri listelemek için bir API uç noktası
@app.route('/get_activities')
def get_activities():
    token = request.headers.get('Authorization')
    if not token: return jsonify({"error": "Token eksik"}), 401
    
    activities_url = "https://www.strava.com/api/v3/athlete/activities?per_page=50" # Son 50 aktivite
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(activities_url, headers=headers)
    return jsonify(response.json())

# 5. Seçilen aktivitenin GPX verisini almak için bir API uç noktası
@app.route('/get_gpx/<activity_id>')
def get_gpx(activity_id):
    token = request.headers.get('Authorization')
    # Bu endpoint'in Strava'dan aktivite stream'ini alıp GPX'e çevirmesi gerekir.
    # Bu kısım daha detaylı implementasyon gerektirir.
    # Şimdilik temsili olarak bırakalım.
    stream_url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams?keys=latlng,altitude,time&key_by_type=true"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(stream_url, headers=headers)
    # Gelen stream verisini GPX formatına dönüştürmek için gpxpy kullanılabilir.
    # Bu örnekte doğrudan stream verisini döndürelim, Pyodide tarafında işleriz.
    return jsonify(response.json())


if __name__ == '__main__':
    app.run(port=5000, debug=True)
