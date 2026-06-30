"""
Fast response system for common travel queries.
Bypasses LLM for instant responses.
"""
import re
import pandas as pd
import os

# Unified NLU Imports
from src.context_manager import (
    detect_city_in_query, 
    detect_unknown_city,
    extract_context_from_history, 
    is_follow_up_question, 
    build_contextual_query,
    extract_days_from_query
)

# --- KEYWORD CONSTANTS ---
GREETING_KEYWORDS = ['hi', 'hello', 'hlo', 'hey', 'namaste', 'greeting']
RESTAURANT_KEYWORDS = ['restaurant', 'restaurants', 'where to eat', 'dining', 'food places', 'eatery', 'dine']
TRIP_INTENTS = ['plan', 'trip', 'visit', 'show', 'tell', 'weather', 'places', 'hotels', 'about', 'restaurants', 'food', 'eat', 'dining']

# NOTE: The logic for loading cities and advanced intent detection (vacation, tour, etc.)
# is now centralized in src/context_manager.py to ensure consistency across the app.

def get_quick_response(query, city_name=None, conversation_history=None):
    """Returns instant responses for common queries without using LLM.
    Now supports conversation history for context-aware responses.
    Args:
        query: User's current query
        city_name: Default city name
        conversation_history: List of previous messages for context
    Returns (response, detected_city) tuple.""" """
    Returns instant responses for common queries without using LLM.
    Now supports conversation history for context-aware responses. """

    # 🛑 PREEMPTIVE SAFETY CHECK:
    # If we detect an UNKNOWN city in the query, we should NOT return a quick response
    # that uses the context city. This prevents "7 days in America" from being 
    # answered with "7 days in Delhi".
    unknown_city = detect_unknown_city(query)
    if unknown_city:
        return (None, None, None) # Let RAG Engine handle it with its own safety intercept
    query_lower = query.lower()
    # Extract context from conversation history
    context = {}
    if conversation_history:
        context = extract_context_from_history(conversation_history)
        # Use context city if available
        if context.get('city'):
            city_name = context['city']
    
    # Check if this is a follow-up question
    if conversation_history and is_follow_up_question(query, context):
        # Build contextual query
        enhanced_query = build_contextual_query(query, context)
        # Handle specific follow-up patterns
        days = None
        if re.match(r'^\s*(?:for\s+)?(\d+)\s*(?:days?)?\s*$', query_lower):
            # User said just "6 days" or "for 6 days"
            days = extract_days_from_query(query)
            if context.get('city') and context.get('last_intent') == 'trip_planning':
                response = f"🗺️ Perfect! I've created a complete {days}-day trip plan for {context['city']}!\n\nCheck the center panel to see:\n✅ Tourism perspective & city intro\n✅ Top 3 places to visit\n✅ Top 3 recommended hotels\n✅ {days}-day detailed itinerary\n✅ Interactive map with all locations\n\nEverything is ONE scrollable page! ⬅️"
                return (response, context['city'], days)
        # If we enhanced the query and it's different, recursively call with enhanced query
        if enhanced_query != query:
            # Recursively call with enhanced query (but no history to avoid infinite loop)
            return get_quick_response(enhanced_query, city_name, conversation_history=None)
    # Try to detect city in current query
    detected_city = detect_city_in_query(query)
    if detected_city:
        city_name = detected_city
    # Detect days in current query
    detected_days = extract_days_from_query(query)

    # Check for specific patterns
    if any(greet in query_lower for greet in GREETING_KEYWORDS):
        if len(query_lower.split()) <= 2:
            return ("Hi there! I'm Nidhi, your AI travel buddy. 🌍✨ How can I help you explore India today?", detected_city, detected_days)
    if 'how are you' in query_lower or 'how r u' in query_lower:
        return ("I'm doing wonderful, thank you for asking! 😊 I'm excited to help you plan your next adventure.", detected_city, detected_days)
    if 'thank' in query_lower:
        return ("You're most welcome! It's my pleasure to assist you. Let me know if you need anything else! 🌟", detected_city, detected_days)
    if 'bye' in query_lower or 'goodbye' in query_lower:
        return ("Goodbye! Safe travels and have a fantastic journey! 🌍✈️", detected_city, detected_days)
        
    # === RESTAURANT QUERIES ===
    if any(kw in query_lower for kw in RESTAURANT_KEYWORDS) and (detected_city or city_name):
        effective_city = detected_city if detected_city else city_name
        response = (
            f"Great choice! 🍽️ Here are the top-rated restaurants in {effective_city}!\n\n"
            f"I've loaded the dining options in the center panel. You can browse by rating.\n\n"
            f"Enjoy your meal in {effective_city}! 😋"
        )
        return (response, effective_city, "restaurants")  # use "restaurants" as detected_days sentinel for mode

    # Valid patterns for generic trip planning
    is_trip_intent = any(intent in query_lower for intent in TRIP_INTENTS)
    
    # If we detected a city OR we have a city in context + days detected, return plan
    if (detected_city or (city_name and detected_days)) and is_trip_intent:
        effective_city = detected_city if detected_city else city_name
        days_text = f" {detected_days}-day" if detected_days else ""
        response = (
            f"I'd be delighted to help you plan your{days_text} trip to {effective_city}! 🌟\n\n"
            f"It's a fantastic destination. I've updated your dashboard with the best places to visit, "
            f"recommended hotels, and a suggested itinerary.\n\n"
            f"Check out the **center panel** for all the details! ⬅️\n\n"
            f"You can also ask me specific questions like 'weather in {effective_city}' or 'top hotels'.")
        return (response, effective_city, detected_days)
    return (None, detected_city, detected_days)

