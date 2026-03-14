import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import os
import json
import sys
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import project modules (absolute imports)
from src.rag_engine import rag_engine
from src.database import init_db, get_setting, save_setting, get_saved_trips, save_trip
from src.utils import get_weather, get_city_info_from_wikipedia
from src.quick_responses import get_quick_response
from src.context_manager import (
    extract_context_from_history, 
    build_contextual_query,
    detect_places_in_text)

# Initialize App
app = FastAPI(title="TripEase API", description="Backend for TripEase Travel Companion")
# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)

import asyncio
@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 Triggering background model loading...")
    asyncio.create_task(asyncio.to_thread(rag_engine.load_model))

# Models
class Message(BaseModel):
    role: str
    content: str
class ChatRequest(BaseModel):
    message: str
    messages: Optional[List[dict]] = [] # History of messages
    city: Optional[str] = None
class SettingRequest(BaseModel):
    key: str
    value: str
class TripRequest(BaseModel):
    username: Optional[str] = None
    city: str
    trip_name: str
    start_date: str
    end_date: str
    itinerary_data: Dict[str, Any]

# Endpoints
@app.get("/")
def read_root():return {"message": "TripEase API is running"}
@app.get("/health")
def health_check():return {"status": "ok"}
# --- CHAT ---
@app.post("/chat")
def chat(request: ChatRequest):
    print(f"\n[BACKEND] User Query Received: '{request.message}'")
    try:
        # 1. Try Quick Response first (Latency < 50ms)
        quick_resp, detected_city, detected_days = get_quick_response(
            request.message, 
            request.city, 
            request.messages )
        if quick_resp:
            print(f"[BACKEND] Handled by Quick Response")
            return { "response": quick_resp,
                "dataset_source": "quick_response", # For debugging/frontend info
                "detected_city": detected_city,
                "detected_days": detected_days,
                "detected_mode": "trip_planning" if detected_days else None # Quick response usually implies planning if days present
}
        # 2. Use RAG Engine (Latency ~2-5s)
        # Attempt to inject context if available
        enhanced_prompt = request.message
        detected_mode = None
        if request.messages:
            context = extract_context_from_history(request.messages)
            enhanced_prompt = build_contextual_query(request.message, context)
            # Context Fallback for UI: If quick response didn't detect city, use context!
            if not detected_city and context.get('city'):
                 detected_city = context.get('city')
            # Capture last intent as mode
            detected_mode = context.get('last_intent')
        print(f"[BACKEND] Processing Enhanced Query: '{enhanced_prompt}'")
        # We will pass the ENHANCED query and HISTORY.
        response = rag_engine.query(enhanced_prompt, history=request.messages)
        # Detect specific places mentioned in the FINAL response for imagery
        detected_places = detect_places_in_text(response)
        return {"response": response,
            "dataset_source": "rag_engine",
            "detected_city": detected_city, 
            "detected_days": detected_days, 
            "detected_mode": detected_mode,
            "detected_places": detected_places}
    except Exception as e:
        print(f"Chat Error: {e}") # Log it
        # Return a graceful error so frontend doesn't break
        return {"response": "I'm encountering a technical issue right now. Please try again in a moment.",
            "error": True,
            "message": str(e)}

# --- INFO & DATA ---
@app.get("/cities/{city_name}")
def get_city_info(city_name: str):
    try:
        info = get_city_info_from_wikipedia(city_name)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weather/{city_name}")
def get_city_weather(city_name: str):
    try:
        weather = get_weather(city_name)
        if not weather:
            raise HTTPException(status_code=404, detail="Weather data not found")
        return weather
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/places")
def get_places(city_id: Optional[int] = None):
    try:
        if not city_id:
            return [] # Don't return all places if no city specified
        df = pd.read_csv('data/places.csv', encoding='latin-1')
        # Filter by city_id
        df = df[df['city_id'] == city_id]
        # Replace NaN with None/null for JSON compatibility
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hotels")
def get_hotels(city_id: Optional[int] = None):
    try:
        if not city_id:
            return []
        df = pd.read_csv('data/hotels.csv', encoding='utf-8')
        # Filter by city_id
        df = df[df['city_id'] == city_id]
        # Replace NaN with None/null for JSON compatibility
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/restaurants")
def get_restaurants(city_id: Optional[int] = None):
    try:
        if not city_id:
            return []
        df = pd.read_csv('data/Restaurent.csv', encoding='utf-8')
        # Filter by city_id
        df = df[df['city_id'] == city_id]
        # Normalise column names to snake_case for consistent frontend access
        df = df.rename(columns={'Restaurant Name': 'restaurant_name',
            'Country': 'country',
            'Description': 'description',
            'Rating': 'rating'})   
        # Replace NaN with empty string for JSON compatibility
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cities_list")
def get_cities_list():
    try:
        df = pd.read_csv('data/cities.csv', encoding='latin-1')
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
# --- SETTINGS ---
@app.get("/settings/{key}")
def read_setting(key: str, default: str = "dark"):
    return {"value": get_setting(key, default)}

@app.post("/settings")
def write_setting(request: SettingRequest):
    save_setting(request.key, request.value)
    return {"status": "success"}
# --- TRIPS ---
@app.get("/trips")
def read_trips(username: Optional[str] = None):
    return get_saved_trips(username)

@app.post("/trips")
def save_new_trip(request: TripRequest):
    save_trip(request.city, request.trip_name, request.start_date, request.end_date, request.itinerary_data, username=request.username)
    return {"status": "success"}

if __name__ == "__main__":
    # Run from project root: python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
