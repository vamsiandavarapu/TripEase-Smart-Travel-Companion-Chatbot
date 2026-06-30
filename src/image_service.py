import os
import requests
import random
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Correctly load the access key from environment variable
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
BASE_URL = "https://api.unsplash.com"

# Cache results to save API calls (Unsplash Free Tier is 50/hour)
@st.cache_data(ttl=3600, show_spinner=False)
def search_unsplash_image(query: str, city_context: str = "") -> str:
    """Searches Unsplash for high-quality photos matching the query.
    Fetches 5 results and returns one at random for variety. """
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "your_key_here":
        # API Key missing or default
        return None
    # Improve search accuracy with city context
    search_query = f"{query} {city_context}".strip() if city_context else query
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "Accept-Version": "v1" }    
    # Get 5 results to allow for randomization
    params = {"query": search_query,
        "per_page": 5,
        "orientation": "landscape",
        "content_filter": "high"}

    try:
        response = requests.get(f"{BASE_URL}/search/photos", headers=headers, params=params, timeout=12)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                # Pick a random result from the fetched list
                chosen = random.choice(results)
                return chosen['urls']['regular']
        elif response.status_code == 403:
            # Rate limit exceeded or invalid key
            print(f"Unsplash API Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"Unsplash Connection Error: {e}")
        return None
        
    return None
