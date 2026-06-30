"""Context Manager for TripEase Chat
Extracts and maintains conversation context from chat history."""
import re
from typing import Dict, List, Optional
from difflib import get_close_matches
import pandas as pd
import os

AFFIRMATIVE_WORDS = ["yes", "yeah", "ok", "sure", "absolutely", "definitely", "yep", "yup", "do it", "go ahead", "y"]
# Centralized City Mapping
CITY_ALIASES = {'vizag': 'Visakhapatnam','calcutta': 'Kolkata','madras': 'Chennai','bombay': 'Mumbai','banaras': 'Varanasi','bangalore': 'Bengaluru','goa': 'Goa','gaya': 'Gaya'}
# --- LOAD KNOWN ENTITIES ---
try:
    _csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/cities.csv"))
    if os.path.exists(_csv_path):
        _df = pd.read_csv(_csv_path, encoding='latin1')
        city_list = _df['city_name'].astype(str).str.lower().tolist()
        KNOWN_CITIES_SET = set(city_list)
        # Add parts of names in parentheses
        for city in city_list:
            if '(' in city:
                parts = re.findall(r'\((.*?)\)|([^(]+)', city)
                for part_tuple in parts:
                    for part in part_tuple:
                        if part:
                            clean_part = part.strip().lower()
                            if len(clean_part) > 2:
                                KNOWN_CITIES_SET.add(clean_part)
        # Add common aliases to the set
        KNOWN_CITIES_SET.update(CITY_ALIASES.keys())
    else:
        KNOWN_CITIES_SET = set()
except Exception:
    KNOWN_CITIES_SET = set()

# Load known places from CSV at module level
try:
    _places_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/places.csv"))
    if os.path.exists(_places_path):
        _p_df = pd.read_csv(_places_path, encoding='latin-1')
        place_list = _p_df['place_name'].astype(str).tolist()
        # Create a mapping of lower_case_name -> Original Name
        KNOWN_PLACES_MAP = {p.lower(): p for p in place_list}
    else:
        KNOWN_PLACES_MAP = {}
except Exception:
    KNOWN_PLACES_MAP = {}

def detect_city_in_query(query: str) -> Optional[str]:
    """ Detects city name in user query.
    Prioritizes destination cities over origin cities.
    Returns city name if found AND it exists in our database."""
    query_lower = query.lower()
    # Destination keywords (where user wants to GO)
    destination_keywords = ['visit', 'go to', 'going to', 'travel to', 'traveling to', 'travelling to',
        'trip to', 'plan', 'planning', 'explore', 'tour', 'vacation in',
        'holiday in', 'journey to', 'heading to', 'want to go', 'wanna go' ]
    # Origin keywords (where user is FROM/CURRENTLY)
    origin_keywords = ['from', 'living in', 'live in', 'currently in', 'based in','staying in', 'located in', 'residing in', 'in', 'at']
    # Find all cities in the query with their positions
    sorted_cities = sorted(list(KNOWN_CITIES_SET), key=len, reverse=True)
    found_cities = []
    
    for city in sorted_cities:
        pattern = r'\b' + re.escape(city) + r'\b'
        match = re.search(pattern, query_lower)
        if match:
            # Normalize city name using centralized aliases
            normalized_city = CITY_ALIASES.get(city, city)
            found_cities.append({
                'name': normalized_city.title(),
                'position': match.start(),
                'is_destination': False,
                'is_origin': False})
    
    # If no cities found, try pattern matching
    if not found_cities:
        # EXPANDED NLU: Covers wide range of natural language travel intents
        intent_verbs = r"(?:trip|tour|vacation|holiday|getaway|journey|visit|travel|explore|adventure|excursion|expedition|voyage|go|plan|show|guide)"
        patterns = [ # classic "trip to city"
            rf"{intent_verbs}.*?(?:to|in|at)\s+([a-zA-Z\s]+)",
            # "city trip"
            rf"([a-zA-Z\s]+)\s+{intent_verbs}",
            # "about city"
            r"(?:about|info|details|weather|hotels|places).*?(?:for|in|of|at)\s+([a-zA-Z\s]+)"]
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                captured = match.group(1).strip()
                # Remove leading prepositions that might have been captured
                for prep in ['in ', 'to ', 'at ', 'for ']:
                    if captured.lower().startswith(prep):
                        captured = captured[len(prep):].strip()
                candidate = captured.lower()
                # CRITICAL CHECK
                if candidate in KNOWN_CITIES_SET:
                    return candidate.title()
        
        # Try fuzzy matching as a last resort
        for word in query_lower.split():
            # Remove punctuation
            clean_word = re.sub(r'[^\w\s]', '', word)
            if len(clean_word) > 4:  # Only fuzzy match longer words to avoid false positives
                matches = get_close_matches(clean_word, list(KNOWN_CITIES_SET), n=1, cutoff=0.8)
                if matches:
                    matched_city = matches[0]
                    if matched_city in CITY_ALIASES:
                        return CITY_ALIASES[matched_city].title()
                    return matched_city.title()
        return None

    # Classify each city as destination or origin based on surrounding keywords
    for city_info in found_cities:
        city_pos = city_info['position']
        # Check text before the city (within 50 characters)
        text_before = query_lower[max(0, city_pos - 50):city_pos]
        # Check for destination keywords
        for keyword in destination_keywords:
            if keyword in text_before:
                city_info['is_destination'] = True
                break
        # Check for origin keywords
        for keyword in origin_keywords:
            if keyword in text_before:
                city_info['is_origin'] = True
                break
    
    # Prioritize destination cities
    destination_cities = [c for c in found_cities if c['is_destination']]
    if destination_cities:
        # Return the first destination city found
        return destination_cities[0]['name']
    # If no destination city found, return the last city mentioned
    # (usually in "from X to Y" patterns, Y is the destination)
    if len(found_cities) > 1:
        return found_cities[-1]['name']
    # Return the only city found
    if found_cities:
        return found_cities[0]['name']
    return None

def detect_unknown_city(query: str) -> Optional[str]:
    """ Detects if the user is asking about a city NOT in our database.
    This helps prevent 'sticky context' where the bot keeps talking about 
    the previous city because it doesn't recognize the new one.
    NOTE: Season words, time words, and common travel terms are explicitly
    excluded so they are never mistaken for unknown city names."""
    query_lower = query.lower()
    # ── Whitelist: words that look like locations in regex but are NOT cities ──
    SEASONAL_AND_TIME_WORDS = {# Seasons
        'winter', 'summer', 'monsoon', 'spring', 'autumn', 'fall', 'rainy',
        # Months
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
        # Travel/query words often captured by "in <X>" pattern
        'india', 'places', 'trip', 'tour', 'vacation', 'holiday', 'weekend',
        'budget', 'nature', 'beach', 'mountains', 'hills', 'rivers', 'forests',
        'heritage', 'culture', 'food', 'adventure', 'backpacking', 'solo',
        'family', 'couples', 'honeymoon', 'group', 'north', 'south', 'east', 'west',}
    # Common patterns that precede a location
    patterns = [r"(?:what about|how about)\s+([a-zA-Z\s]+)",
        r"(?:trip|tour|vacation|holiday|go|travel|visit|heading|journey)\s+to\s+([a-zA-Z\s]+)",
        r"(?:explore|in|at)\s+([a-zA-Z\s]+)",
        r"\babout\s+([a-zA-Z\s]+)"]
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            candidate = match.group(1).split()[0].strip()
            candidate = re.sub(r'[^\w\s]', '', candidate)
            # Skip known cities
            if candidate in KNOWN_CITIES_SET:
                continue
            # Skip season/time/generic travel words — THIS IS THE KEY BUG FIX
            if candidate in SEASONAL_AND_TIME_WORDS:
                continue
            # Skip very short or stopwords
            stopwords = {'a', 'an', 'the', 'my', 'his', 'her', 'our', 'some', 'any',
                'this', 'that', 'it', 'me', 'i', 'is', 'was', 'am', 'be'}
            if candidate in stopwords or len(candidate) < 3:
                continue
            return candidate.title()
    return None

def extract_days_from_query(query: str) -> Optional[int]:
    """Extracts number of days from query.
    Handles patterns like "6 days", "for 5 days", "7-day trip"
"""
    query_lower = query.lower()
    # Pattern 1: "X days" or "for X days"
    match = re.search(r'(?:for\s+)?(\d+)\s*days?', query_lower)
    if match:
        return int(match.group(1))
    # Pattern 2: "X-day trip"
    match = re.search(r'(\d+)-day', query_lower)
    if match:
        return int(match.group(1))
    # Pattern 3: Just a number (if query is very short like "6" or "for 6")
    if re.match(r'^\s*(?:for\s+)?(\d+)\s*$', query_lower):
        match = re.search(r'(\d+)', query_lower)
        if match:
            days = int(match.group(1))
            # Only return if it's a reasonable number of days (1-30)
            if 1 <= days <= 30:
                return days
    return None

def extract_context_from_history(messages: List[Dict]) -> Dict:
    """ Extracts context from ENTIRE conversation history.
    Args:
        messages: List of message dicts with 'role' and 'content'
    Returns:
        Dict with context: {
            'city': str or None,
            'days': int or None,
            'last_intent': str or None,
            'last_user_message': str or None } """
    context = {'city': None,
        'days': None,
        'last_intent': None,
        'last_user_message': None} 
    # Scan ALL messages to build context
    for msg in messages:
        content = msg['content']
        content_lower = content.lower()
        # Store last user message if it's from user
        if msg['role'] == 'user':
            context['last_user_message'] = content
        # Extract city from ANY message (Assistant suggestions count too!)
        city = detect_city_in_query(content)
        if city:
            context['city'] = city
        else:
            # Check if user mentioned an UNKNOWN city - if so, CLEAR the known city context
            # to avoid "sticky context" hallucinations
            if msg['role'] == 'user':
                unknown = detect_unknown_city(content)
                if unknown:
                    context['city'] = None # Clear sticky city
                    context['unknown_city'] = unknown
        
        # Extract days from User messages
        if msg['role'] == 'user':
            days = extract_days_from_query(content)
            if days:
                context['days'] = days
        
        # Detect intent from User messages
        if msg['role'] == 'user':
            if 'trip' in content_lower or 'plan' in content_lower or 'itinerary' in content_lower:
                context['last_intent'] = 'trip_planning'
            elif 'hotel' in content_lower:
                context['last_intent'] = 'hotels'
            elif 'place' in content_lower or 'visit' in content_lower or 'attraction' in content_lower:
                context['last_intent'] = 'places'
            elif 'weather' in content_lower:
                context['last_intent'] = 'weather'
    return context

def is_follow_up_question(query: str, context: Dict) -> bool:
    """Determines if the query is a follow-up question that needs context.
    Args:
        query: User's current query
        context: Extracted context from history
    Returns:
        True if this appears to be a follow-up question"""
    query_lower = query.lower().strip()
    # Pattern 1: Just a number of days (e.g., "6 days", "for 5 days", "7")
    if re.match(r'^\s*(?:for\s+)?(\d+)\s*(?:days?)?\s*$', query_lower):
        return True
    # Pattern 1.5: Affirmative responses
    if query_lower in AFFIRMATIVE_WORDS:
        return True
    # Pattern 2: "plan for X days" - duration change for existing trip
    if re.match(r'^plan\s+for\s+\d+\s*days?', query_lower) and context.get('city'):
        return True
    # Pattern 3: "city for X days" - city change with duration
    city_detected = detect_city_in_query(query)
    days_detected = extract_days_from_query(query)
    if city_detected and days_detected and context.get('last_intent') == 'trip_planning':
        return True
    # Pattern 4: Just a city name (if we have recent trip context)
    if city_detected and len(query_lower.split()) <= 2 and context.get('last_intent'):
        return True

    # Pattern 5: Modification requests without context
    modification_patterns = [r'^make it',r'^change to',r'^instead',
        r'^actually',r'^no,?\s*',r'^add',
        r'^include',r'^show me',r'^what about',
        r'^how about',r'^weather',r'^what\'?s\s+the\s+weather']
    for pattern in modification_patterns:
        if re.match(pattern, query_lower):
            # Only strictly valid if we have a city in context
            if context.get('city'):
                return True
    return False


def build_contextual_query(query: str, context: Dict) -> str:
    """Builds a complete query by adding context to follow-up questions.
    Args:
        query: User's current query
        context: Extracted context from history
    Returns:
        Enhanced query with context """
    query_lower = query.lower().strip() 
    # Pattern 0: Affirmative responses - convert to plan request
    if query_lower in AFFIRMATIVE_WORDS and context.get('city'):
        return f"plan a trip to {context['city']}"

    # Pattern 1: Just a number of days
    if re.match(r'^\s*(?:for\s+)?(\d+)\s*(?:days?)?\s*$', query_lower):
        days = extract_days_from_query(query)
        city = context.get('city')
        if not city:
            return query  # No city context available
        return f"plan a {days}-day trip to {city}"
    
    # Pattern 2: "plan for X days" - extract days and use context city
    if re.match(r'^plan\s+for\s+\d+\s*days?', query_lower):
        days = extract_days_from_query(query)
        city = context.get('city')
        if not city:
            return query  # No city context available
        return f"plan a {days}-day trip to {city}"
    
    # Pattern 3: "city for X days" - both city and duration specified
    city_detected = detect_city_in_query(query)
    days_detected = extract_days_from_query(query)
    if city_detected and days_detected:
        return f"plan a {days_detected}-day trip to {city_detected}"
    
    # Pattern 4: Just a city name - use context intent and days
    if city_detected and len(query_lower.split()) <= 2:
        if context.get('last_intent') == 'trip_planning':
            days = context.get('days') or 5  # Default to 5 days if not specified
            return f"plan a {days}-day trip to {city_detected}"
        elif context.get('last_intent') == 'hotels':
            return f"show hotels in {city_detected}"
        elif context.get('last_intent') == 'places':
            return f"places to visit in {city_detected}"
        else:
            # Default to trip planning
            return f"plan trip to {city_detected}"
    
    # Pattern 5: Modification requests
    if context.get('city'):
        city = context['city']
        if query_lower.startswith('make it') or query_lower.startswith('change to'):
            if 'day' in query_lower:
                return f"plan trip to {city} {query}"
            else:
                return query
        if query_lower.startswith('add') or query_lower.startswith('include'):
            return f"{query} in {city}"
        if query_lower.startswith('show me'):
            return f"{query} in {city}"
    return query

def detect_seasonal_intent(query: str) -> Optional[str]:
    """Detects if the user is asking about a specific season.
    Returns: 'winter', 'summer', 'monsoon', 'spring' or None """
    query_lower = query.lower()
    # 1. Direct Season Keywords
    seasons = ["winter", "summer", "monsoon", "spring", "autumn"]
    for s in seasons:
        if s in query_lower:
            # Map autumn to spring
            if s == "autumn": return "spring"
            return s 
    return None

def detect_places_in_text(text: str) -> List[str]:
    """Scans text for any known attraction names.
    Returns a list of unique original place names found."""
    if not text or not KNOWN_PLACES_MAP:
        return []
    found_places = []
    text_lower = text.lower()
    # Sort places by length (longest first) to avoid matching sub-strings prematurely
    # e.g., "Mysore Palace" should match before "Palace"
    sorted_places = sorted(KNOWN_PLACES_MAP.keys(), key=len, reverse=True)
    for place_lower in sorted_places:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(place_lower) + r'\b'
        if re.search(pattern, text_lower):
            original_name = KNOWN_PLACES_MAP[place_lower]
            if original_name not in found_places:
                found_places.append(original_name)
                # Once matched, we could mask it from text_lower to prevent double matching,
                # but unique list + longest-first should be sufficient.
    
    return found_places
