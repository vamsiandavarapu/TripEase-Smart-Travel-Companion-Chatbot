import requests
from typing import Dict, List, Any, Optional

class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url

    def _request(self, method: str, endpoint: str, **kwargs):
        timeout = kwargs.pop('timeout', 15)
        silent = kwargs.pop('silent', False)
        try:
            res = requests.request(method, f"{self.base_url}{endpoint}", timeout=timeout, **kwargs)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            if not silent or endpoint == "/health":
                print(f"DEBUG: Connection Error to {self.base_url}{endpoint}: {e}")
            return {}

    def health_check(self) -> bool: return self._request("GET", "/health", silent=True).get("status") == "ok"
    def chat(self, message: str, messages: List[Dict], city: str = None) -> Dict:
        return self._request("POST", "/chat", json={"message": message, "messages": messages, "city": city}, timeout=60) or {"response": "Connection error."}
    def get_city_info(self, city_name: str) -> Dict: return self._request("GET", f"/cities/{city_name}") or {}
    def get_weather(self, city_name: str) -> Dict: return self._request("GET", f"/weather/{city_name}")
    def get_places(self, city_id: Optional[int] = None) -> List[Dict]: return self._request("GET", "/places", params={"city_id": city_id} if city_id else {}) or []
    def get_hotels(self, city_id: Optional[int] = None) -> List[Dict]: return self._request("GET", "/hotels", params={"city_id": city_id} if city_id else {}) or []
    def get_restaurants(self, city_id: Optional[int] = None) -> List[Dict]: return self._request("GET", "/restaurants", params={"city_id": city_id} if city_id else {}) or []
    def get_cities_list(self) -> List[Dict]: return self._request("GET", "/cities_list") or []
    def get_setting(self, key: str, default: str = "dark") -> str: return self._request("GET", f"/settings/{key}", params={"default": default}).get("value", default)
    def save_setting(self, key: str, value: str) -> bool: return self._request("POST", "/settings", json={"key": key, "value": value}).get("status") == "success"
    def get_trips(self, username: Optional[str] = None) -> List[Dict]: return self._request("GET", "/trips", params={"username": username} if username else {}) or []
    def save_trip(self, city, trip_name, start_date, end_date, itinerary_data, username=None) -> bool:
        return self._request("POST", "/trips", json={"username": username, "city": city, "trip_name": trip_name, "start_date": start_date, "end_date": end_date, "itinerary_data": itinerary_data}).get("status") == "success"


