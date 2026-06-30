import requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather(city_name):
    """
    Fetches weather data from OpenWeatherMap API.
    """
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "YOUR_API_KEY":
        # Deterministic mock data based on city name if no key is present
        hash_val = sum(ord(c) for c in city_name)
        temp = 15 + (hash_val % 20) # 15-35 range
        conditions = ["Sunny", "Cloudy", "Partly Cloudy", "Haze", "Clear Sky"]
        condition = conditions[hash_val % len(conditions)]
        return {
            "temp": temp, 
            "description": f"{condition} (Mock - API Key Required)", 
            "icon": "01d",
            "humidity": 40 + (hash_val % 30),
            "wind_speed": 2.0 + (hash_val % 5),
            "is_mock": True }
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_name,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"}
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        if response.status_code == 200:
            return {"temp": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "is_mock": False}
        else:
            error_msg = data.get('message', 'Unknown API Error')
            return {"error": f"OpenWeatherMap Error: {error_msg} (Status {response.status_code})", "is_mock": False}
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def get_city_info_from_wikipedia(city_name):
    """ Fetches city information from Wikipedia API (free, no API key needed).
    Returns a summary and image URL. """
    try:
        # Wikipedia API endpoint
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + city_name.replace(" ", "_")
        # Wikipedia requires a User-Agent header
        headers = { 'User-Agent': 'TripEase/1.0 (Educational Project; contact@tripease.com)' }
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            # Extract summary (remove COVID-19 mentions)
            summary = data.get('extract', 'No description available.')
            # Filter out COVID-19 content
            summary = summary.replace('COVID-19', '').replace('coronavirus', '').replace('pandemic', '')
            # Get thumbnail image
            thumbnail = data.get('thumbnail', {}).get('source', None)
            # Get coordinates if available
            coordinates = data.get('coordinates', {})
            lat = coordinates.get('lat', None)
            lon = coordinates.get('lon', None)            
            return {'summary': summary,
                'image': thumbnail,
                'latitude': lat,
                'longitude': lon,
                'title': data.get('title', city_name)  }
        else:
            print(f"Wikipedia API returned status {response.status_code} for {city_name}")
            return None
    except Exception as e:
        print(f"Error fetching Wikipedia data: {e}")
        return None

def get_route_geometry(start_lat, start_lon, end_lat, end_lon):
    """ Fetches route geometry from OSRM public API.
    Returns a list of [lat, lon] points for Folium.
    Falls back to straight line if API fails or no route found. """
    try:
        # OSRM requires {lon},{lat}
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        headers = {'User-Agent': 'TripEase-Capstone-Project/1.0'}
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and data.get("routes"):
                # Route found
                geometry = data["routes"][0]["geometry"]["coordinates"]
                # Convert [lon, lat] to [lat, lon]
                path = [[lat, lon] for lon, lat in geometry]
                return path
    except Exception as e:
        print(f"Routing Error: {e}")
    
    # Fallback to direct line
    return [[start_lat, start_lon], [end_lat, end_lon]]
