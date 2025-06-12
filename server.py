# Dosya Adı: server.py (HTML'ler ana klasörde)

from flask import Flask, request, redirect, render_template, jsonify
import requests
import os
import traceback 

# DÜZELTME: Flask'e şablonların bu script ile aynı klasörde olduğunu söylüyoruz.
app = Flask(__name__, template_folder='.')

# --- Ortam Değişkenleri ---
STRAVA_CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulator')
def simulator_page():
    return render_template('yarissimulasyonu.html')

@app.route('/analyzer')
def analyzer_page():
    return render_template('yarisanalizi.html')


@app.route('/login')
def login():
    # Strava'nın istediği standart yetkilendirme akışı
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
    
    # Kullanıcıyı ana portala yönlendir. index.html bu token'ı yakalayıp kaydedecek.
    return redirect(f'/#access_token={access_token}')


# --- API Endpointleri ---
# server.py içindeki fonksiyon

@app.route('/api/get_activities', methods=['GET'])
def get_activities():
    auth_header = request.headers.get('Authorization')
    if not auth_header: return jsonify({"error": "Authorization başlığı eksik"}), 401
    
    try:
        headers = {'Authorization': auth_header}
        all_activities = []
        page = 1
        while page <= 5: 
            params = {'per_page': 100, 'page': page}
            response = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers, params=params, timeout=10)
            response.raise_for_status()
            activities = response.json()
            if not activities: break
            all_activities.extend(activities)
            page += 1

        # --- DEĞİŞİKLİK BURADA ---
        # Artık 'name' ve 'start_date' bilgilerini de ekliyoruz.
        runs_with_details = [
            {
                'id': act['id'], 
                'name': act.get('name', f"Aktivite {act['id']}"), # Aktivite adı yoksa ID'sini kullan
                'distance': act['distance'], 
                'sport_type': act.get('sport_type'),
                'start_date': act.get('start_date') # Başlangıç tarihini ekle
            }
            for act in all_activities if act.get('sport_type') in ['Run', 'TrailRun', 'VirtualRun']
        ]
        return jsonify(runs_with_details)
        # --- DEĞİŞİKLİK SONU ---

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/get_activity_streams', methods=['POST'])
def get_activity_streams():
    auth_header = request.headers.get('Authorization')
    if not auth_header: return jsonify({"error": "Authorization başlığı eksik"}), 401

    try:
        data = request.json
        activity_ids = data.get('activity_ids', [])
        headers = {'Authorization': auth_header}
        
        all_streams = []
        for act_id in activity_ids:
            keys = 'time,latlng,altitude,heartrate'
            params = {'keys': keys, 'key_by_type': True}
            response = requests.get(f"https://www.strava.com/api/v3/activities/{act_id}/streams", headers=headers, params=params, timeout=20)
            response.raise_for_status()
            all_streams.append(response.json())

        return jsonify(all_streams)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
