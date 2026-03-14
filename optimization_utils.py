import math
import re
import pandas as pd
from typing import List, Dict, Any, Tuple
from season_utils import infer_best_time, infer_famous_for, get_current_season, get_time_of_day_emoji, generate_why_now_explanation

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) using Haversine formula.
    Returns distance in kilometers."""
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def parse_time_slot_preference(place: Dict[str, Any]) -> str:
    """Determines the preferred time slot ('morning', 'afternoon', 'evening') for a place.
    Uses 'best_time_to_visit' if available, otherwise infers it."""
    # 1. Try explicit data
    best_time = place.get('best_time_to_visit', '')
    if best_time:
        if 'morning' in best_time.lower(): return 'morning'
        if 'afternoon' in best_time.lower(): return 'afternoon'
        if 'evening' in best_time.lower(): return 'evening'
    # 2. Infer if missing
    return infer_best_time(place.get('place_name', ''), place.get('category', ''))

def is_open_at_slot(place: Dict[str, Any], slot: str) -> bool:
    """Checks if a place is likely open during a specific time slot."""
    hours = place.get('operational_hours', '')
    if not hours or '24 hours' in hours.lower():
        return True
    hours = hours.lower().replace(u'\u2013', '-').replace(u'\u2014', '-') # Normalize dashes
    # regex to find time ranges like "10:00 am - 5:00 pm"
    # Capture groups: 1=Start, 2=End
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*[ap]m)\s*-\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', hours)
    if match:
        start_str = match.group(1)
        end_str = match.group(2)
        # Simple parsing to 24h float
        def parse_time(t_str):
            t_str = t_str.strip()
            is_pm = 'pm' in t_str
            t_str = t_str.replace('am','').replace('pm','').strip()
            parts = t_str.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if is_pm and h != 12: h += 12
            if not is_pm and h == 12: h = 0
            return h + m/60.0
        try:
            start_h = parse_time(start_str)
            end_h = parse_time(end_str)
            # Handle crossing midnight (e.g. 10pm - 2am)
            if end_h < start_h: 
                end_h += 24
# Define Slot Ranges # Morning: 9 - 12 # Afternoon: 12 - 17 # Evening: 17 - 21
            slot_ranges = {'morning': (9, 12),'afternoon': (12, 17),'evening': (17, 21) }
            s_start, s_end = slot_ranges.get(slot, (9, 17))
            # Check overlap
            # Range 1: start_h to end_h
            # Range 2: s_start to s_end
            # Overlap if max(start1, start2) < min(end1, end2)
            overlap_start = max(start_h, s_start)
            overlap_end = min(end_h, s_end)
            if overlap_end > overlap_start:
                 # Check if overlap is significant (e.g. at least 1.5 hours)
                 if (overlap_end - overlap_start) >= 1.5:
                     return True
                 else:
                     return False
            else:
                return False  
        except:
             return True # Fallback if parsing fails  
    return True # Default check strictness only if parsing works

def score_place(place: Dict[str, Any], 
                current_lat: float, 
                current_lon: float, 
                slot: str,
                visited_names: set) -> float:
    """
    Scores a place for a specific slot based on:
    - Distance from current location (Minimize)
    - Rating (Maximize)
    - Time Preference Match (Bonus)
    - Open Status (Hard constraint/Huge Penalty)
    """
    if place.get('place_name') in visited_names:
        return -1e9 # Already visited
    # 1. Check if open (Hard Constraint)
    if not is_open_at_slot(place, slot):
        return -1000 # Huge penalty but not impossible if forced
    # 2. Distance Score (Lower distance is better)
    # We invert distance: Score = 1 / (distance + epsilon)
    lat = place.get('latitude')
    lon = place.get('longitude')
    distance_km = 0
    if lat and lon and current_lat and current_lon:
        try:
            distance_km = haversine_distance(current_lat, current_lon, float(lat), float(lon))
        except:
            distance_km = 10 # Fallback max distance
    else:
        distance_km = 10 # Penalty for missing coords
        
    # Cap distance penalty to avoid skewing too much (e.g. max 20km penalty)
    dist_penalty = min(distance_km, 20) * 0.5 # 0.5 points per km
    # 3. Rating Score
    rating = float(place.get('rating', 0) or 0)
    rating_score = rating * 2 # Scale 0-5 to 0-10
    # 4. Time Preference Score
    ideal_slot = parse_time_slot_preference(place)
    time_bonus = 10 if ideal_slot == slot else 0
    # Total Score
    # We want max score. 
    # Score = Rating(0-10) + TimeBonus(0 or 5) - DistancePenalty(0-10)
    final_score = rating_score + time_bonus - dist_penalty
    return final_score

def optimize_itinerary(days: int, places_df_orig: Any) -> Dict[str, Any]:
    """ Generates an optimized itinerary."""
    if hasattr(places_df_orig, 'empty') and places_df_orig.empty:
        return {} # Should trigger fallback in caller
    # Convert to list of dicts for easier handling
    places = places_df_orig.to_dict('records')
    # Initial Location (City Center or average of all places)
    # For simplicity, let's start at the first top-rated place or average.
    lats = [float(p['latitude']) for p in places if p.get('latitude')]
    lons = [float(p['longitude']) for p in places if p.get('longitude')]
    current_lat = sum(lats)/len(lats) if lats else 20.0
    current_lon = sum(lons)/len(lons) if lons else 78.0
    visited = set()
    itinerary = {}
    current_season = get_current_season()
    slots = ['morning', 'afternoon', 'evening']
    for day in range(1, days + 1):
        day_plan = {
            'day_info': {
                'day_number': day,
                'season': current_season
            },
            'morning': [],'afternoon': [],'evening': [] }
        for slot in slots:
            best_place = None
            best_score = -float('inf')
            # Find best place for this slot
            for place in places:
                score = score_place(place, current_lat, current_lon, slot, visited)
                if score > best_score:
                    best_score = score
                    best_place = place
            if best_place and best_score > -100: # Ensure valid candidate
                visited.add(best_place['place_name'])
                # Update location to this place
                if best_place.get('latitude') and best_place.get('longitude'):
                    current_lat = float(best_place['latitude'])
                    current_lon = float(best_place['longitude'])
                
                # We duplicate some logic from app.py's `generate_day_by_day_itinerary`
                # to keep `optimize_itinerary` self-contained or we return raw objects.
                # Let's return the simplified dict expected by UI buffer.
                famous_for = best_place.get('famous_for') or infer_famous_for(
                    best_place.get('place_name', ''),
                    best_place.get('category', ''),
                    best_place.get('description', '')
                )
                ideal_slot = parse_time_slot_preference(best_place)
                is_preferred = (ideal_slot == slot)
                activity = {
                    'name': best_place.get('place_name', 'Attraction'),
                    'category': best_place.get('category', 'Sightseeing'),
                    'description': best_place.get('description', ''),
                    'rating': best_place.get('rating', 4.0),
                    'entry_fee': best_place.get('entry_fee', 'Free'),
                    'famous_for': famous_for,
                    'why_now': generate_why_now_explanation(
                        famous_for, current_season, slot, is_preferred
                    ),
                    'time_emoji': get_time_of_day_emoji(slot),
                    'is_preferred_time': is_preferred,
                    'latitude': best_place.get('latitude'),
                    'longitude': best_place.get('longitude')
                }
                day_plan[slot].append(activity)
        itinerary[day] = day_plan
    return itinerary
