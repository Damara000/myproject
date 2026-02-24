from flask import Flask, send_from_directory, jsonify, request
import os, requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# ---------- Basic Setup ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, '..', 'static')
app = Flask(__name__, static_folder=STATIC_DIR)

# SECRET_KEY for Flask (optional if using sessions)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')

# API Key for OpenWeather
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '044020aeb958d75f8f002c0adcf17980')


# ---------- Routes ----------
@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(STATIC_DIR, 'assets'), filename)


# ---------- Rule-based Crop Prediction ----------
@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    crop = data.get("crop_type", "").lower()
    temp = float(data.get("temperature", 25))       # Optional from frontend
    rainfall = float(data.get("rainfall", 50))     # Optional from frontend
    planting_date_str = data.get("planting_date")  # Optional from frontend

    # ---------- Step 1: Base yield per crop ----------
    base_yield = {
        "wheat": 4,
        "rice": 5,
        "maize": 4.5
    }
    yield_estimate = base_yield.get(crop, 3.5)

    # ---------- Step 2: Adjust for temperature ----------
    ideal_temp = {
        "wheat": (18, 25),
        "rice": (22, 30),
        "maize": (20, 28)
    }
    temp_min, temp_max = ideal_temp.get(crop, (20, 30))
    if temp < temp_min:
        yield_estimate -= (temp_min - temp) * 0.2
    elif temp > temp_max:
        yield_estimate -= (temp - temp_max) * 0.2

    # ---------- Step 3: Adjust for rainfall ----------
    optimal_rainfall = {
        "wheat": (40, 60),
        "rice": (80, 120),
        "maize": (50, 90)
    }
    rain_min, rain_max = optimal_rainfall.get(crop, (50, 100))
    if rainfall < rain_min:
        yield_estimate -= (rain_min - rainfall) * 0.1
    elif rainfall > rain_max:
        yield_estimate -= (rainfall - rain_max) * 0.1

    # ---------- Step 4: Adjust for planting date ----------
    if planting_date_str:
        try:
            planting_date = datetime.strptime(planting_date_str, "%d-%m-%Y")
            days_since_planting = (datetime.now() - planting_date).days
            if days_since_planting < 60:        # not matured
                yield_estimate *= 0.8
            elif days_since_planting > 180:     # harvest passed
                yield_estimate *= 0.9
        except:
            pass  # ignore invalid date formats

    # ---------- Step 5: Confidence ----------
    confidence = min(max(int(80 + (yield_estimate % 5)), 50), 95)

    # ---------- Step 6: Result ----------
    result = {
        "predicted_yield": round(yield_estimate, 2),
        "confidence": confidence,
        "tips": [
            f"Ideal soil for {crop.capitalize()} detected 🌱",
            f"Weather conditions suggest moderate growth potential"
        ]
    }

    return jsonify(result)


# ---------- Live Insights ----------
@app.route('/insights', methods=['POST'])
def insights():
    data = request.get_json() or {}
    lat = data.get("latitude")
    lon = data.get("longitude")

    if not lat or not lon:
        return jsonify({"error": "Latitude and longitude required"}), 400

    # Fetch live weather from OpenWeather
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    weather_data = requests.get(url).json()

    # 🌱 Dynamic Soil Calculation based on rainfall & humidity
    rainfall = weather_data.get("rain", {}).get("1h", 0)
    humidity = weather_data["main"]["humidity"]

    ph = round(6 + (rainfall / 50), 1)          # more rain → slightly higher pH
    carbon = round(1 + (humidity / 100), 1)     # higher humidity → more soil carbon %
    nitrogen = 40 + int(rainfall / 2)           # rainfall adds nitrogen mg/kg

    # 💧 Dynamic Irrigation Insights
    if rainfall > 30:
        status = "Good"
        efficiency = 90
        index = 0.85
    elif 10 < rainfall <= 30:
        status = "Moderate"
        efficiency = 75
        index = 0.7
    else:
        status = "Low"
        efficiency = 60
        index = 0.55

    insights = {
        "weather": {
            "temp": round(weather_data["main"]["temp"], 1),
            "rainfall": rainfall,
            "humidity": humidity
        },
        "soil": {
            "ph": ph,
            "carbon": carbon,
            "nitrogen": nitrogen
        },
        "irrigation": {
            "status": status,
            "efficiency": efficiency,
            "index": index
        }
    }

    return jsonify(insights)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
