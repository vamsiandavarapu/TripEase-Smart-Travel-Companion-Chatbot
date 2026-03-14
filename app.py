import streamlit as st
import warnings
import base64
import os
import pandas as pd
import folium
import time
from streamlit_folium import st_folium
from folium.features import DivIcon

# Import authentication manager
import auth_manager
# Suppress pkg_resources deprecation warnings from third-party libraries
warnings.filterwarnings("ignore", category=UserWarning, module="google.rpc")
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

from ui_components import (get_custom_css, render_place_card, get_category_image,format_entry_fee)
from utils import get_route_geometry
from api_client import ApiClient
from season_utils import (get_current_season, get_season_emoji, get_time_of_day_emoji, get_day_of_week)
from optimization_utils import optimize_itinerary

# Page Config (Must be first)
st.set_page_config(page_title="TripEase", layout="wide", initial_sidebar_state="expanded")
# --- AUTH HELPERS ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        print(f"Error encoding image: {e}")
        return ""

def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# --- UI HELPERS ---
def render_glass_card(title, icon="📍"):
    """Renders a standard glassmorphism card header."""
    st.markdown(f"""
    <div class="theme-card">
        <h3 style="margin-top: 0;">{icon} {title}</h3>
    </div>
    """, unsafe_allow_html=True)

def render_activity_card(activity):
    """Renders a standard activity item for itineraries."""
    st.markdown(f"**{activity.get('name', 'Activity')}**")
    st.caption(f"{activity.get('category', 'General')}")
    if activity.get('famous_for'):
        st.success(f"🌟 {activity['famous_for']}")
    st.write(f"⭐ {activity.get('rating', 'N/A')}/5")
    st.write(f"💰 {activity.get('entry_fee', 'Free')}")
    st.markdown("---")

def render_login_page():
    # Get base64 background
    bg_img_path = os.path.join(os.getcwd(), 'Auth_System', 'FrontBackground.png')
    bin_str = get_base64_of_bin_file(bg_img_path)
    # Custom CSS for Premium Look
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;700&display=swap');
    .stApp {{
        background-image: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.8)), url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Raleway', sans-serif !important; }}
    
    .auth-title {{
        font-size: 80px !important;
        font-weight: 700 !important;
        color: white !important;
        text-align: center !important;
        margin-bottom: 0px !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5) !important;
        letter-spacing: 5px !important;
    }}
    
    .auth-subtitle {{
        font-size: 24px !important;
        color: #e0e0e0 !important;
        text-align: center !important;
        margin-bottom: 50px !important;
        font-weight: 300 !important;
    }}
    
    .glass-container {{
        /* Background and border removed as requested */
        background: transparent !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        border: none !important;
        border-radius: 20px;
        padding: 20px !important;
        max-width: 500px !important;
        margin: auto !important;
    }}
    
    /* Input Styling */
    .stTextInput>div>div>input {{
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #1a237e !important;
        border-radius: 10px !important;
        border: 2px solid #1e88e5 !important;
        height: 50px !important;
    }}
    
    /* Button Styling */
    .stButton>button {{
        border-radius: 25px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        height: 50px !important;
    }}
    
    .primary-btn button {{
        background-color: #1e88e5 !important;
        color: white !important;
    }}
    
    div[data-testid="stForm"] {{
        border: none !important;
        padding: 0 !important;
    }}
    
    label {{
        color: white !important;
        font-weight: 600 !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    if st.session_state.auth_page == 'home':
        st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
        st.markdown('<h1 class="auth-title">TripEase</h1>', unsafe_allow_html=True)
        st.markdown('<p class="auth-subtitle">Your Smart Travel Companion</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            if st.button("🔑 LOGIN", width='stretch', type="primary"):
                st.session_state.auth_page = 'login'
                st.rerun()
            st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
            if st.button("📝 REGISTER", width='stretch'):
                st.session_state.auth_page = 'register'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.auth_page == 'login':
        st.markdown('<h1 class="auth-title" style="font-size: 50px !important;">Login</h1>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            with st.form("login_form"):
                user = st.text_input("Username", placeholder="Enter your username")
                pw = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("Log In", width='stretch')    
                if submit:
                    if user and pw:
                        success, msg = auth_manager.login_user(user, pw)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.username = user
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill in all fields")
            if st.button("← Back to Home", width='stretch'):
                st.session_state.auth_page = 'home'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.auth_page == 'register':
        st.markdown('<h1 class="auth-title" style="font-size: 50px !important;">Register</h1>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="glass-container">', unsafe_allow_html=True)
            with st.form("register_form"):
                new_user = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email (Optional)", placeholder="Enter your email")
                new_pw = st.text_input("Password", type="password", placeholder="Create a password")
                confirm_pw = st.text_input("Confirm Password", type="password")
                reg_submit = st.form_submit_button("Create Account", width='stretch')
                if reg_submit:
                    if new_user and new_pw:
                        if new_pw == confirm_pw:
                            success, msg = auth_manager.register_user(new_user, new_pw, new_email)
                            if success:
                                st.success(msg)
                                time.sleep(1)
                                st.session_state.auth_page = 'login'
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.error("Passwords do not match")
                    else:
                        st.warning("Username and password are required")
            if st.button("← Back to Home", width='stretch'):
                st.session_state.auth_page = 'home'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- INITIALIZATION ---
auth_manager.init_db()
# Initialize API Client
api_client = ApiClient()
# Check backend connection with retry logic
if not api_client.health_check():
    with st.spinner("🚀 Starting TripEase Backend (loading AI models)... Please wait a moment."):
        retry_count = 0
        max_retries = 30  # Wait up to 60 seconds
        while retry_count < max_retries:
            time.sleep(2)
            if api_client.health_check():
                st.success("✅ Connected to Backend!")
                time.sleep(1) # Show success briefly
                st.rerun()
            retry_count += 1
    st.error("⚠️ Cannot connect to TripEase Backend. Please ensure the server is running using `start_both_servers.ps1`.")
    st.stop()

# Helper to get city_id
@st.cache_data(ttl=60) # Cache for 60 seconds to allow retries if backend was down
def get_cities_data():
    data = api_client.get_cities_list()
    if not data:
        st.cache_data.clear() # Clear cache if data is empty so we retry immediately next time
        return []
    return data

def get_city_id(city_name):
    try:
        cities = get_cities_data()
        if not cities:
            return None
        # Look for city in the list
        for city in cities:
            if city.get('city_name', '').lower() == city_name.lower():
                return city.get('city_id')
    except Exception:
        pass
    return None

def generate_day_by_day_itinerary(city, days, places_df):
    """Generates intelligent day-by-day itinerary with seasonal awareness. 
    Args:
        city: City name
        days: Number of days
        places_df: DataFrame with places data
    Returns:
        Dict with day-by-day itinerary including contextual information """
    if places_df.empty:
        return generate_fallback_itinerary(city, days)
    # Use new optimization logic
    # This returns a dictionary of days with slots filled
    try:
        optimized_itinerary = optimize_itinerary(days, places_df)
    except Exception as e:
        print(f"Optimization failed: {e}")
        optimized_itinerary = {}
    # If optimization failed or returned empty, use the main fallback itinerary
    if not optimized_itinerary:
        return generate_fallback_itinerary(city, days)
    # Process the optimized itinerary (add names, emojis, and fill empty slots)
    for day, data in optimized_itinerary.items():
        if 'day_info' in data:
            data['day_info']['day_name'] = get_day_of_week(day_offset=day-1)
            data['day_info']['season_emoji'] = get_season_emoji(data['day_info']['season'])
        # Fill empty slots with fallback activities
        for slot in ['morning', 'afternoon', 'evening']:
            if not data.get(slot):
                data[slot] = [generate_fallback_activity(slot, city)]           
    return optimized_itinerary
def generate_fallback_activity(time_slot, city):
    """Generates fallback activity when we run out of places."""
    activities = {'morning': {
            'name': 'Local Breakfast Experience','category': 'Food & Culture',
            'description': f'Explore local cafes and try authentic {city} breakfast specialties',
            'rating': 4.2,'entry_fee': 'Varies','famous_for': 'Local cuisine and street food',
            'why_now': 'Fresh morning preparation • Authentic experience','time_emoji': '🌅','is_preferred_time': True},
        'afternoon': {
            'name': 'Local Market & Shopping','category': 'Shopping',
            'description': f'Visit traditional markets and shopping districts of {city}',
            'rating': 4.0, 'entry_fee': 'Free','famous_for': 'Local crafts and souvenirs',
            'why_now': 'Markets in full swing • Variety of goods',
            'time_emoji': '☀️','is_preferred_time': True  },
        'evening': {
            'name': 'Sunset & Leisure Time','category': 'Relaxation',
            'description': f'Relax and enjoy the evening atmosphere of {city}',
            'rating': 4.3,'entry_fee': 'Free','famous_for': 'Evening ambiance and city views',
            'why_now': 'Perfect for unwinding • Evening views',
            'time_emoji': '🌆','is_preferred_time': True}}
    return activities.get(time_slot, activities['afternoon'])

def generate_fallback_itinerary(city, days):
    """Generates basic itinerary when no places data available."""
    current_season = get_current_season()
    season_emoji = get_season_emoji(current_season)
    itinerary = {}
    for day in range(1, days + 1):
        day_name = get_day_of_week(day_offset=day-1)
        itinerary[day] = {'day_info': {
                'day_number': day,
                'day_name': day_name,
                'season': current_season,
                'season_emoji': season_emoji},
            'morning': [generate_fallback_activity('morning', city)],
            'afternoon': [generate_fallback_activity('afternoon', city)],
            'evening': [generate_fallback_activity('evening', city)]}
    return itinerary

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi there! I'm Nidhi, your dedicated travel expert. 🌍✨\n\nI can help you plan complete itineraries, find top-rated hotels, or check the weather for your next destination.\n\nWhere are you dreaming of going today?"} ]
if "selected_city" not in st.session_state:
    # Get first city from database instead of hardcoded default
    cities_data = get_cities_data()
    default_city = cities_data[0]['city_name'] if cities_data else "Hyderabad"
    st.session_state.selected_city = default_city
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "🏠 Home"
if "theme" not in st.session_state:
    st.session_state.theme = api_client.get_setting("theme", "dark")
# --- AUTH SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'home'
if "chat_display_mode" not in st.session_state:
    st.session_state.chat_display_mode = None  # What to show in center (hotels, places, trip, etc.)
if "trip_days" not in st.session_state:
    st.session_state.trip_days = 3
if "booked_hotels" not in st.session_state:
    st.session_state.booked_hotels = []

# --- AUTH GUARD ---
if not st.session_state.logged_in:
    render_login_page()
    st.stop()

# Dynamic CSS based on theme
# Inject Custom CSS
st.markdown(get_custom_css(st.session_state.theme), unsafe_allow_html=True)
# Remove automatic top padding in sidebar
empty = st.sidebar.empty()
empty.markdown("")
# --- SIDEBAR HEADER ---
# Display Logo centered with minimal spacing
logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
if os.path.exists(logo_path):
    # Center the logo using columns
    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
        st.image(logo_path, width='stretch')
else:
    # Fallback to text if logo not found
    st.sidebar.markdown("### 🌴 TripEase")
    st.sidebar.markdown("Your Smart Travel Companion ✨")

# Theme Toggle
theme_btn_label = "☀️ Switch to Light Mode" if st.session_state.theme == "dark" else "🌙 Switch to Dark Mode"
if st.sidebar.button(theme_btn_label, width='stretch'):
    new_theme = "light" if st.session_state.theme == "dark" else "dark"
    st.session_state.theme = new_theme
    api_client.save_setting("theme", new_theme)
    st.rerun()

# Reset Chat Button
if st.sidebar.button("🔄 Reset Chat", width='stretch', help="Clear all conversation history"):
    st.session_state.messages = []
    st.session_state.chat_display_mode = None
    st.session_state.selected_page = "🏠 Home"
    st.rerun()
# Logout Button
if st.sidebar.button("🚪 Logout", width='stretch'):
    logout_user()
st.sidebar.markdown("---")
# --- NAVIGATION MENU ---
nav_items = [ "🏠 Home","🗺️ Plan Trip","🧭 Explore",
    "🏨 Hotels","🍽️ Restaurants","📅 Itinerary",
    "🛫 Saved Trips","💰 Budget","☁️ Weather","⚙️ Settings"]
for item in nav_items:
    if st.sidebar.button(item, width='stretch'):
        st.session_state.selected_page = item
        st.session_state.chat_display_mode = None
        st.rerun()
st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ for your perfect journey")

# -----------------------------
# MAIN LAYOUT
# -----------------------------
col_center, col_chat = st.columns([0.70, 0.30], gap="large")
# -----------------------------
# CENTER MAIN CONTENT
# -----------------------------
with col_center:
    selected_page = st.session_state.selected_page
    # Check if chat triggered content display
    if st.session_state.chat_display_mode == "city_info":
        # Show city information from Wikipedia
        st.title(f"About {st.session_state.selected_city}")
        city_info = api_client.get_city_info(st.session_state.selected_city)
        if city_info and city_info.get('summary'):
            # Wikipedia data available
            if city_info.get('image'):
                st.image(city_info['image'], width='stretch', caption=city_info.get('title', st.session_state.selected_city))
            else:
                # Fallback image
                st.image(f"https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&w=1600&q=80&q={st.session_state.selected_city}", 
                        width='stretch', caption=st.session_state.selected_city)
            
            st.markdown(f"### 📖 {city_info.get('title', st.session_state.selected_city)}")
            st.write(city_info['summary'])
            
            if city_info.get('latitude') and city_info.get('longitude'):
                st.info(f"📍 Coordinates: {city_info['latitude']:.4f}, {city_info['longitude']:.4f}")
        else:
            # Wikipedia failed - show fallback content
            st.image(f"https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=1600&q=80&q={st.session_state.selected_city}", 
                    width='stretch', caption=st.session_state.selected_city)
            st.markdown(f"### 📖 {st.session_state.selected_city}")
            st.write(f"""
            {st.session_state.selected_city} is a vibrant destination with rich culture, history, and modern attractions. 
            Known for its unique blend of tradition and innovation, this city offers visitors an unforgettable experience.
            From historic landmarks to contemporary entertainment, {st.session_state.selected_city} has something for everyone.
            Explore the local cuisine, visit famous monuments, and immerse yourself in the local culture.
            """)  
            st.info("💡 For more detailed information, try asking about specific places, hotels, or weather!")
            # Show some quick stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏛️ Places", "100+")
            with col2:
                st.metric("🏨 Hotels", "50+")
            with col3:
                st.metric("⭐ Avg Rating", "4.5/5")
    
    elif st.session_state.chat_display_mode == "trip_planning":
        # Show complete trip plan on ONE page
        st.title(f"🗺️ Planning Trip to {st.session_state.selected_city}")
        # City Tourism Perspective (Wikipedia intro)
        city_info = api_client.get_city_info(st.session_state.selected_city)
        if city_info:
            st.markdown(f"## 📍 {city_info.get('title', st.session_state.selected_city)} - Tourism Perspective")
            if city_info.get('image'):
                st.image(city_info['image'], width='stretch', caption=f"Welcome to {city_info.get('title', 'City')}")
            # Show tourism-focused summary
            st.markdown(f"### About {city_info['title']}")
            st.write(city_info['summary'])
            if city_info['latitude'] and city_info['longitude']:
                st.info(f"📍 Location: {city_info['latitude']:.4f}°N, {city_info['longitude']:.4f}°E")
        
        st.markdown("---")
        # Top 3 Places to Visit
        st.markdown(f"## 🏛️ Top Places to Visit in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            # Use API to get places
            places_data = api_client.get_places(city_id)
            # Convert list of dicts to DataFrame for nlargest logic or just sort list
            places_df = pd.DataFrame(places_data)
            if not places_df.empty:
                top_places = places_df.nlargest(3, 'rating')
                for idx, place in top_places.iterrows():
                    render_place_card(place)
        
        except Exception as e:
            st.warning("Loading sample places...")
        # Top 3 Hotels
        st.markdown(f"## 🏨 Recommended Hotels in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            hotels_data = api_client.get_hotels(city_id)
            hotels_df = pd.DataFrame(hotels_data)
            if not hotels_df.empty:
                top_hotels = hotels_df.nlargest(3, 'rating')
            else:
                top_hotels = pd.DataFrame() # Handle empty

            for idx, hotel in top_hotels.iterrows():
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"### {hotel.get('hotel_name', 'Hotel')}")
                    st.write(f"**Description:** {hotel.get('description', 'Comfortable accommodation awaits!')}")
                    st.write(f"**Amenities:** {hotel.get('amenities', 'WiFi, Parking, Restaurant')}")
                with col2:
                    st.metric("⭐ Rating", f"{hotel.get('rating', 'N/A')}/5")
                    st.metric("💰 Price", f"₹{hotel.get('price', 'N/A')}/night")
                    if st.button("📞 Book", key=f"book_hotel_{idx}"):
                        st.success("Booking feature coming soon!")        
                st.markdown("---")
        except Exception as e:
            st.warning("Loading sample hotels...")
        
        # Top 3 Restaurants
        st.markdown(f"## 🍽️ Top Restaurants in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            restaurants_data = api_client.get_restaurants(city_id)
            restaurants_df = pd.DataFrame(restaurants_data)
            if not restaurants_df.empty:
                restaurants_df['rating'] = pd.to_numeric(restaurants_df['rating'], errors='coerce').fillna(0)
                top_restaurants = restaurants_df.nlargest(3, 'rating')
                for idx, rest in top_restaurants.iterrows():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"### {rest.get('restaurant_name', 'Restaurant')}")
                        st.write(f"**Description:** {rest.get('description', 'A wonderful dining experience!')}")
                    with col2:
                        st.metric("⭐ Rating", f"{rest.get('rating', 'N/A')}/5")
                    st.markdown("---")
        except Exception as e:
            st.warning("Loading sample restaurants...")
        # Dynamic Day Itinerary
        st.markdown(f"## 📅 {st.session_state.trip_days}-Day Itinerary for {st.session_state.selected_city}")
        try:
             city_id = get_city_id(st.session_state.selected_city)
             places_data = api_client.get_places(city_id)
             places_df = pd.DataFrame(places_data)
        except:
             places_df = pd.DataFrame()

        # Generate based on session state days
        itinerary_data = generate_day_by_day_itinerary(
            st.session_state.selected_city, 
            st.session_state.trip_days, 
            places_df
        )
        for day, day_data in itinerary_data.items():
            # Get day info
            day_info = day_data.get('day_info', {})
            day_name = day_info.get('day_name', 'Day')
            season = day_info.get('season', '')
            season_emoji = day_info.get('season_emoji', '🌍')
            with st.expander(
                f"📅 Day {day} - {day_name} ({season} {season_emoji})", 
                expanded=(day==1)
            ):
                col1, col2, col3 = st.columns(3)   
                with col1:
                    st.markdown("### 🌅 Morning")
                    for activity in day_data.get('morning', []):
                        # Show activity image
                        place_name = activity.get('name')
                        city_name = st.session_state.selected_city
                        img_url = get_category_image(activity.get('category'), place_name, city_name)
                        st.image(img_url, width='stretch')
                        st.markdown(f"**{activity.get('time_emoji', '⏰')} {activity['name']}**")
                        if activity.get('famous_for'):
                            st.info(f"🌟 {activity['famous_for']}")
                        if activity.get('why_now'):
                            st.success(f"✨ {activity['why_now']}")
                        st.write(f"⭐ Rating: {activity.get('rating', 'N/A')}")
                        st.write(f"💰 Entry: {format_entry_fee(activity.get('entry_fee'))}")
                        st.markdown("---")
                with col2:
                    st.markdown("### ☀️ Afternoon")
                    for activity in day_data.get('afternoon', []):
                        # Show activity image
                        place_name = activity.get('name')
                        city_name = st.session_state.selected_city
                        img_url = get_category_image(activity.get('category'), place_name, city_name)
                        st.image(img_url, width='stretch')
                        st.markdown(f"**{activity.get('time_emoji', '⏰')} {activity['name']}**")
                        if activity.get('famous_for'):
                            st.info(f"🌟 {activity['famous_for']}")
                        if activity.get('why_now'):
                            st.success(f"✨ {activity['why_now']}")
                        st.write(f"⭐ Rating: {activity.get('rating', 'N/A')}")
                        st.write(f"💰 Entry: {format_entry_fee(activity.get('entry_fee'))}")
                        st.markdown("---")    
                with col3:
                    st.markdown("### 🌆 Evening")
                    for activity in day_data.get('evening', []):
                        # Show activity image
                        place_name = activity.get('name')
                        city_name = st.session_state.selected_city
                        img_url = get_category_image(activity.get('category'), place_name, city_name)
                        st.image(img_url, width='stretch')
                        st.markdown(f"**{activity.get('time_emoji', '⏰')} {activity['name']}**")
                        if activity.get('famous_for'):
                            st.info(f"🌟 {activity['famous_for']}")
                        if activity.get('why_now'):
                            st.success(f"✨ {activity['why_now']}")
                        st.write(f"⭐ Rating: {activity.get('rating', 'N/A')}")
                        st.write(f"💰 Entry: {format_entry_fee(activity.get('entry_fee'))}")
                        st.markdown("---")
        
        # Save Trip Button
        if st.button("💾 Save this Trip", type="primary", width='stretch'):
            # Use session state dates if available, otherwise fallback to placeholders
            start_dt = st.session_state.get('trip_start_date', "2025-06-01")
            duration = st.session_state.get('trip_days', 3)
            end_dt = (pd.to_datetime(start_dt) + pd.Timedelta(days=duration)).strftime("%Y-%m-%d") if isinstance(start_dt, str) else (start_dt + pd.Timedelta(days=duration)).strftime("%Y-%m-%d")
            success = api_client.save_trip(
                st.session_state.selected_city,
                f"Trip into {st.session_state.selected_city}",
                str(start_dt), str(end_dt),
                itinerary_data,
                username=st.session_state.get('username')
            )
            if success:
                st.success("Trip saved successfully! Check 'Saved Trips'.")
            else:
                st.error("Failed to save trip.")
        st.markdown("---")
        # Interactive Map
        st.markdown(f"## 🗺️ Interactive Map - {st.session_state.selected_city}")
        # Day Selector for Map
        days_avail = list(itinerary_data.keys())
        day_options = ["All Days"] + [f"Day {d}" for d in days_avail]
        selected_map_day = st.radio("Select View:", day_options, horizontal=True, key="map_day_selector")
        
        try:
            city_id = get_city_id(st.session_state.selected_city)
            places_data = api_client.get_places(city_id)
            hotels_data = api_client.get_hotels(city_id)
            places_df = pd.DataFrame(places_data)
            hotels_df = pd.DataFrame(hotels_data)
            # Determine which days to show
            days_to_plot = []
            if selected_map_day == "All Days":
                days_to_plot = days_avail
            else:
                day_num = int(selected_map_day.split(" ")[1])
                days_to_plot = [day_num]
            # Collect all coordinates for centering
            all_lats = []
            all_lons = []
            if not places_df.empty:
                all_lats.extend(places_df['latitude'].dropna().tolist())
                all_lons.extend(places_df['longitude'].dropna().tolist())
            if not hotels_df.empty:
                all_lats.extend(hotels_df['latitude'].dropna().tolist())
                all_lons.extend(hotels_df['longitude'].dropna().tolist())
            center_lat = sum(all_lats) / len(all_lats) if all_lats else 20.0
            center_lon = sum(all_lons) / len(all_lons) if all_lons else 78.0
            
            # Create map
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            # Colors for different days
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
            # Add place markers and routes
            for day in days_to_plot:
                day_data = itinerary_data.get(day, {})
                day_color = colors[(day - 1) % len(colors)]
                # Combine all slots in order for the route
                all_activities = day_data.get('morning', []) + day_data.get('afternoon', []) + day_data.get('evening', [])
                # Collect route points
                route_points = []
                for idx, activity in enumerate(all_activities):
                    lat = activity.get('latitude')
                    lon = activity.get('longitude')
                    if lat and lon:
                        point = [lat, lon]
                        route_points.append(point)
                        # Custom Numbered Marker
                        # Using DivIcon to show number (1, 2, 3...)
                        icon_html = f""" <div style="
                                font-family: sans-serif;
                                color: white;
                                background-color: {day_color};
                                border-radius: 50%;
                                text-align: center;
                                width: 24px;
                                height: 24px;
                                line-height: 24px;
                                font-weight: bold;
                                border: 2px solid white;
                                box-shadow: 0 0 5px rgba(0,0,0,0.5);
                            ">
                                {idx + 1}
                            </div>"""
                        # Add Marker
                        folium.Marker(
                            location=point,
                            popup=folium.Popup(f"""
                                <b>Day {day} - Step {idx+1}</b><br>
                                <b>{activity.get('name', 'Place')}</b><br>
                                ⭐ {activity.get('rating', 'N/A')}/5<br>
                                🕐 {activity.get('time_emoji', '')}
                            """, max_width=250),
                            tooltip=f"Step {idx+1}: {activity.get('name', 'Place')}",
                            icon=DivIcon(
                                icon_size=(24, 24),
                                icon_anchor=(12, 12),
                                html=icon_html
                            )
                        ).add_to(m)
                
                # Draw Route Line if we have multiple points
                if len(route_points) > 1:
                    full_route_geometry = []
                    # Fetch road geometry pairwise between each stop
                    for i in range(len(route_points) - 1):
                        start = route_points[i]
                        end = route_points[i+1]
                        # Fetch geometry segment (Road following)
                        segment = get_route_geometry(start[0], start[1], end[0], end[1])
                        full_route_geometry.extend(segment)
                    if full_route_geometry:
                        # Use static PolyLine for a normal route look along the road
                        folium.PolyLine(
                            locations=full_route_geometry,
                            color=day_color,
                            weight=5,
                            opacity=0.8,
                            tooltip=f"Day {day} Road Path"
                        ).add_to(m)       
            if selected_map_day == "All Days" and not hotels_df.empty:
                top_hotels = hotels_df.nlargest(3, 'rating')
                for idx, hotel in top_hotels.iterrows():
                    folium.Marker(
                        location=[hotel['latitude'], hotel['longitude']],
                        popup=folium.Popup(f"""
                            <b>{hotel.get('hotel_name', 'Hotel')}</b><br>
                            ⭐ {hotel.get('rating', 'N/A')}/5<br>
                            💰 ₹{hotel.get('price', 'N/A')}/day
                        """, max_width=250),
                        tooltip=hotel.get('hotel_name', 'Hotel'),
                        icon=folium.Icon(color='blue', icon='home')
                    ).add_to(m)

            # Calculate bounds dynamically to ensure map fits content
            bounds_points = []
            # Add Itinerary Points
            for day in days_to_plot:
                day_data = itinerary_data.get(day, {})
                for period in ['morning', 'afternoon', 'evening']:
                    for activity in day_data.get(period, []):
                        if activity.get('latitude') and activity.get('longitude'):
                            bounds_points.append([activity['latitude'], activity['longitude']])
            # Add Hotels if shown (All Days view)
            if selected_map_day == "All Days" and not hotels_df.empty:
                top_hotels_bounds = hotels_df.nlargest(3, 'rating')
                for _, hotel in top_hotels_bounds.iterrows():
                     if hotel['latitude'] and hotel['longitude']:
                        bounds_points.append([hotel['latitude'], hotel['longitude']])
            if bounds_points:
                m.fit_bounds(bounds_points)
            st_folium(m, width=None, height=600)
        except Exception as e:
            st.error(f"Map loading... {e}")
        st.markdown("---")
        st.success(f"✅ Complete trip plan for {st.session_state.selected_city} ready! Enjoy your journey! 🎉")
    
    elif st.session_state.chat_display_mode == "hotels":
        # Show hotels in center
        st.title(f"🏨 Hotels in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            hotels_data = api_client.get_hotels(city_id)
            hotels_df = pd.DataFrame(hotels_data)
            hotels_to_show = hotels_df.head(5)
            for idx, hotel in hotels_to_show.iterrows():
                render_glass_card(hotel.get('hotel_name', 'Hotel'), "🏨")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**Description:** {hotel.get('description', 'A comfortable stay awaits you!')}")
                    st.markdown(f"**Amenities:** {hotel.get('amenities', 'WiFi, Parking, Restaurant')}")
                with col2:
                    st.metric("⭐ Rating", f"{hotel.get('rating', 'N/A')}/5")
                    st.metric("💰 Price", f"₹{hotel.get('price', 'N/A')}/night")
                with col3:
                    if st.button(f"📞 Book Now", key=f"book_{idx}"):
                        st.success("Booking feature coming soon!")
                
                st.markdown("---")
        except Exception as e:
            st.error(f"Error loading hotels: {e}")
    elif st.session_state.chat_display_mode == "restaurants":
        # Show restaurants in center
        st.title(f"🍽️ Restaurants in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            restaurants_data = api_client.get_restaurants(city_id)
            restaurants_df = pd.DataFrame(restaurants_data)
            if not restaurants_df.empty:
                restaurants_df['rating'] = pd.to_numeric(restaurants_df['rating'], errors='coerce').fillna(0)
                restaurants_to_show = restaurants_df.nlargest(8, 'rating')
            else:
                restaurants_to_show = pd.DataFrame()
            if restaurants_to_show.empty:
                st.info(f"No restaurant data found for {st.session_state.selected_city}.")
            else:
                for idx, rest in restaurants_to_show.iterrows():
                    render_glass_card(rest.get('restaurant_name', 'Restaurant'), "🍽️")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Description:** {rest.get('description', 'A wonderful dining experience!')}")
                    with col2:
                        st.metric("⭐ Rating", f"{rest.get('rating', 'N/A')}/5")
                    st.markdown("---")
        except Exception as e:
            st.error(f"Error loading restaurants: {e}")
    
    elif st.session_state.chat_display_mode == "seasonal":
        # Show seasonal city recommendations
        if 'seasonal_info' in st.session_state:
            season = st.session_state.seasonal_info.get('season', 'this season')
            cities = st.session_state.seasonal_info.get('cities', [])
            st.title(f"☀️ Best Places for {season.capitalize()}")
            st.markdown(f"Based on our database, here are the top destinations to visit in **{season.capitalize()}**:")
            for city_name in cities:
                with st.expander(f"📍 {city_name}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        # Try to get a brief description if we can, or just a placeholder
                        st.write(f"Explore the beauty of {city_name} in the {season} months.")
                    with col2:
                        if st.button(f"Go to {city_name}", key=f"seasonal_go_{city_name}"):
                            st.session_state.selected_city = city_name
                            st.session_state.chat_display_mode = "city_info"
                            st.rerun()
            st.info("💡 Tip: Click on a city to see more details and plan your trip!")
        else:
            st.info("No seasonal recommendations loaded. Try asking 'where should I go in winter?'")
    elif st.session_state.chat_display_mode == "places":
        # Show places in center
        st.title(f"🗺️ Places to Visit in {st.session_state.selected_city}")
        try:
            city_id = get_city_id(st.session_state.selected_city)
            places_data = api_client.get_places(city_id)
            places_df = pd.DataFrame(places_data)
            places_to_show = places_df.head(5)
            for idx, place in places_to_show.iterrows():
                render_place_card(place)
        except Exception as e:
            st.error(f"Error loading places: {e}")
    
    elif st.session_state.chat_display_mode == "weather":
        # Show weather in center
        st.title(f"☁️ Weather in {st.session_state.selected_city}")
        weather = api_client.get_weather(st.session_state.selected_city)
        if weather:
            if "error" in weather:
                st.error(weather["error"])
            elif weather.get('is_mock'):
                st.warning("⚠️ OpenWeatherMap API key is missing. Add `OPENWEATHER_API_KEY` to your `.env` file for live data.")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🌡️ Temperature", f"{weather['temp']}°C")
            with col2:
                st.metric("🌤️ Condition", weather['description'].capitalize())
            with col3:
                st.metric("📍 Location", st.session_state.selected_city)
            st.markdown(f"""
            <div class="weather-widget">
                <h2>{st.session_state.selected_city}</h2>
                <h1>{weather['temp']}°C</h1>
                <p>{weather['description'].capitalize()}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Could not fetch weather data")
    
    elif selected_page == "🏠 Home":
        st.title("Welcome to TripEase 🌍")
        st.markdown("### Your AI-powered smart travel companion.")
        st.image("https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1600&q=80", width='stretch')
        st.markdown("---")
        st.markdown("### ✨ Features")
        feat_cols = st.columns(3)
        with feat_cols[0]:
            st.markdown("#### 🗺️ Smart Planning")
            st.write("AI-powered trip suggestions tailored to your preferences")
        with feat_cols[1]:
            st.markdown("#### 🏨 Best Hotels")
            st.write("Curated hotel recommendations with real-time pricing")
        with feat_cols[2]:
            st.markdown("#### ☁️ Weather Updates")
            st.write("Live weather forecasts for your destinations")
    
    elif selected_page == "🗺️ Plan Trip":
        st.title("🗺️ Plan Your Trip")
        st.markdown("### Let's create your perfect itinerary!")
        trip_col1, trip_col2 = st.columns(2)
        with trip_col1:
            # Default to session state values if available
            destination = st.text_input("🌍 Destination", value=st.session_state.selected_city, placeholder="e.g., Hyderabad, Mumbai, Delhi")
            default_start = st.session_state.get('trip_start_date', pd.to_datetime("today").date())
            start_date = st.date_input("📅 Start Date", value=default_start)
        with trip_col2:
            duration = st.number_input("⏱️ Duration (days)", min_value=1, max_value=15, value=st.session_state.trip_days)
            # Auto-calculate end date
            end_date = start_date + pd.Timedelta(days=duration)
            st.date_input("📅 End Date", value=end_date, disabled=True)
        if st.button("✨ Generate Trip Plan", type="primary", width='stretch'):
            with st.spinner(f"Creating your perfect {duration}-day itinerary for {destination}..."):
                # 1. Store inputs in session state
                st.session_state.selected_city = destination # Sync with global city selection
                st.session_state.trip_start_date = start_date
                st.session_state.trip_days = duration # Sync with global days
                # 2. Fetch data
                city_id = get_city_id(destination)
                places_data = api_client.get_places(city_id)
                places_df = pd.DataFrame(places_data)
                filtered_places = places_df # Use all places
                # 4. Generate Itinerary
                itinerary = generate_day_by_day_itinerary(destination, duration, filtered_places)
                st.session_state.generated_itinerary = itinerary
                # 5. Redirect to Itinerary Tab
                st.session_state.selected_page = "📅 Itinerary"
                st.success("Trip generated successfully! Redirecting...")
                time.sleep(1)
                st.rerun()
        
    elif selected_page == "🧭 Explore":
        st.title(f"Explore {st.session_state.selected_city}")
        # Fetch city info from Wikipedia
        city_info = api_client.get_city_info(st.session_state.selected_city)
        if city_info:
            st.markdown(f"### 📖 About {city_info.get('title', 'City')}")
            # Show Wikipedia image if available
            if city_info.get('image'):
                st.image(city_info['image'], width='stretch')
            # Show full description in center
            st.markdown(f"**{city_info.get('summary', '')}**")
            if city_info.get('latitude') and city_info.get('longitude'):
                st.info(f"📍 Coordinates: {city_info['latitude']:.4f}, {city_info['longitude']:.4f}")
        st.markdown("---")
        
        # Weather Overlay
        weather = api_client.get_weather(st.session_state.selected_city)
        if weather:
            if "error" in weather:
                st.error(f"Weather: {weather['error']}")
            elif weather.get('is_mock'):
                st.caption("⚠️ Using sample weather data")
            st.markdown(f"""
            <div class="weather-widget">
                <h3>{st.session_state.selected_city}</h3>
                <h1>{weather['temp']}°C</h1>
                <p>{weather['description'].capitalize()}</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")
        # Load places data
        try:
            city_id = get_city_id(st.session_state.selected_city)
            places_data = api_client.get_places(city_id)
            places_df = pd.DataFrame(places_data)
            places_to_show = places_df.head(10)  # Show more places
            st.markdown("### 📌 Popular Places")
            st.markdown(f"*Discover {len(places_to_show)} amazing destinations*")
            st.markdown("")
            # Display all places as cards (no expander, just vertical scroll)
            for idx, place in places_to_show.iterrows():
                render_place_card(place)
            # Map at the bottom
            st.markdown("### 🗺️ Interactive Map - All Locations")
            st.markdown("*Click on markers to see place details*")
            if len(places_to_show) > 0:
                center_lat = places_to_show['latitude'].mean()
                center_lon = places_to_show['longitude'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
                for idx, place in places_to_show.iterrows():
                    folium.Marker(
                        location=[place['latitude'], place['longitude']],
                        popup=folium.Popup(f"""
                            <b>{place.get('place_name', 'Place')}</b><br>
                            {place.get('category', 'N/A')}<br>
                            Rating: {place.get('rating', 'N/A')}/5<br>
                            Entry: {place.get('entry_fee', 'Free')}
                        """, max_width=250),
                        tooltip=place.get('place_name', 'Place'),
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(m)
                
                st_folium(m, width=None, height=600)
            else:
                st.info("No places data available")
                
        except Exception as e:
            st.error(f"Error loading places data: {e}")
            st.info(f"Sample data for {st.session_state.selected_city} could not be loaded. Please check your database connection.")
            st.markdown("---")
            st.markdown("### 🗺️ Map View")
            # Map fallback if needed
            st.info("Interactive map unavailable due to data load error.")
            # m = get_map() # Removed helper, use folium directly or another mechanism if critical
            # st_folium(m, width=700, height=400)

    elif selected_page == "🍽️ Restaurants":
        st.title(f"🍽️ Restaurants in {st.session_state.selected_city}")
        # Search and Filters
        search_query = st.text_input("🔍 Search Restaurants or jump to city (e.g. 'Mysore')", placeholder="Search by name or type a city name...")
        # Check if search query is a city name to jump context
        is_city_jump = False
        if search_query:
            new_city_id = get_city_id(search_query)
            if new_city_id:
                is_city_jump = True
                if search_query.lower() != st.session_state.selected_city.lower():
                    st.session_state.selected_city = search_query.title()
                    st.success(f"Switching context to {search_query.title()}...")
                    st.rerun()
        rating_filter = st.slider("⭐ Minimum Rating", 1.0, 5.0, 3.5, 0.5)
        st.markdown("---")
        
        try:
            city_id = get_city_id(st.session_state.selected_city)
            restaurants_data = api_client.get_restaurants(city_id)
            restaurants_df = pd.DataFrame(restaurants_data)
            if not restaurants_df.empty:
                restaurants_df['rating'] = pd.to_numeric(restaurants_df['rating'], errors='coerce').fillna(0)
                # Apply Search Filter (if not a city jump)
                if search_query and not is_city_jump:
                    search_query = search_query.lower()
                    restaurants_df = restaurants_df[
                        restaurants_df['restaurant_name'].str.lower().str.contains(search_query) |
                        restaurants_df['description'].str.lower().str.contains(search_query) ]
                # Filter by rating
                restaurants_df = restaurants_df[restaurants_df['rating'] >= rating_filter]
                # Default Sort: Rating (High to Low)
                restaurants_df = restaurants_df.sort_values('rating', ascending=False)
            if restaurants_df.empty:
                st.info(f"No restaurants found in {st.session_state.selected_city} matching your criteria.")
            else:
                st.markdown("### 🍽️ Available Restaurants")
                st.markdown(f"*Found {len(restaurants_df)} restaurants matching your criteria*")
                st.markdown("")
                for idx, rest in restaurants_df.iterrows():
                    render_glass_card(rest.get('restaurant_name', 'Restaurant'), "🍽️")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Description:** {rest.get('description', 'A wonderful dining experience awaits!')}")
                    with col2:
                        st.metric("⭐ Rating", f"{rest.get('rating', 'N/A')}/5")
                    st.markdown("---")
        except Exception as e:
            st.error(f"Error loading restaurants data: {e}")
    
    elif selected_page == "🏨 Hotels":
        st.title(f"Hotels in {st.session_state.selected_city}")
        # Search and Filters
        search_query = st.text_input("🔍 Search Hotels or jump to city (e.g. 'Goa')", placeholder="Search by name or type a city name...")
        # Check if search query is a city name to jump context
        is_city_jump = False
        if search_query:
            new_city_id = get_city_id(search_query)
            if new_city_id:
                is_city_jump = True
                if search_query.lower() != st.session_state.selected_city.lower():
                    st.session_state.selected_city = search_query.title()
                    st.success(f"Switching context to {search_query.title()}...")
                    st.rerun()
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            # Numeric range slider for actual prices
            price_range = st.slider("💰 Price Range (₹)", 0, 50000, (0, 30000), 500)
        with filter_col2:
            rating_filter = st.slider("⭐ Minimum Rating", 1.0, 5.0, 3.5, 0.5)
        st.markdown("---")
        
        # Load hotels data
        try:
            city_id = get_city_id(st.session_state.selected_city)
            hotels_data = api_client.get_hotels(city_id)
            if not hotels_data:
                st.info(f"No hotels found in {st.session_state.selected_city} matching your criteria. Try another city or adjust filters!")
                hotels_df = pd.DataFrame()
            else:
                hotels_df = pd.DataFrame(hotels_data)
                # 1. Standardize Numeric Columns with Safety
                if 'price' in hotels_df.columns:
                    hotels_df['price'] = pd.to_numeric(hotels_df['price'], errors='coerce').fillna(0)
                if 'rating' in hotels_df.columns:
                    hotels_df['rating'] = pd.to_numeric(hotels_df['rating'], errors='coerce').fillna(0)
                # 2. Apply Filters
                if not hotels_df.empty:
                    # Apply Search Filter (if not a city jump)
                    if search_query and not is_city_jump:
                        search_query = search_query.lower()
                        hotels_df = hotels_df[hotels_df['hotel_name'].str.lower().str.contains(search_query) |
                            hotels_df['description'].str.lower().str.contains(search_query) ]
                    # Filter by Price Range (Actual Numeric Price)
                    if 'price' in hotels_df.columns:
                        hotels_df = hotels_df[(hotels_df['price'] >= price_range[0]) & (hotels_df['price'] <= price_range[1])]
                    # Filter by Rating
                    if 'rating' in hotels_df.columns:
                        hotels_df = hotels_df[hotels_df['rating'] >= rating_filter]
                if hotels_df.empty:
                    st.info(f"No hotels found in {st.session_state.selected_city} matching your current filters.")
                else:
                    # Default Sort: Rating (High to Low)
                    if 'rating' in hotels_df.columns:
                        hotels_df = hotels_df.sort_values('rating', ascending=False)
                    hotels_to_show = hotels_df.head(10)
            
                st.markdown("### 🏨 Available Hotels")
                st.markdown(f"*Found {len(hotels_to_show)} hotels matching your criteria*")
                st.markdown("")
                # Display all hotels as cards
                for idx, hotel in hotels_to_show.iterrows():
                    render_glass_card(hotel.get('hotel_name', 'Hotel'), "🏨")
                    # Details in columns
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"**Description:** {hotel.get('description', 'A comfortable stay awaits you!')}")
                        st.markdown(f"**Amenities:** {hotel.get('amenities', 'WiFi, Parking, Restaurant')}")
                        st.markdown(f"**📍 Address:** {hotel.get('address', 'City Center')}")
                    with col2:
                        st.metric("⭐ Rating", f"{hotel.get('rating', 'N/A')}/5")
                        st.metric("💰 Price", f"₹{hotel.get('price', 'N/A')}/day") 
                    with col3:
                        if st.button(f"📞 Book Now", key=f"book_{idx}", width='stretch'):
                            # Initialize booking list if needed
                            if 'booked_hotels' not in st.session_state:
                                st.session_state.booked_hotels = []
                            # Add to booked list
                            booking_details = {
                                "hotel_name": hotel.get('hotel_name'),
                                "city": st.session_state.selected_city,
                                "price": hotel.get('price', 'N/A'),
                                "address": hotel.get('address', 'N/A'),
                                "rating": hotel.get('rating', 'N/A'),
                                "booked_on": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M") }
                            st.session_state.booked_hotels.append(booking_details)
                            st.success(f"✅ Booked {hotel.get('hotel_name')}!")
                            time.sleep(1)
                            st.rerun()    
                st.markdown("---")
            
                # Map at the bottom (only if coordinates exist)
                if 'latitude' in hotels_to_show.columns and 'longitude' in hotels_to_show.columns:
                    st.markdown("### 🗺️ Hotels Map - All Locations")
                    st.markdown("*Click on markers to see hotel details*")                
                    center_lat = hotels_to_show['latitude'].mean()
                    center_lon = hotels_to_show['longitude'].mean()              
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)        
                    for idx, hotel in hotels_to_show.iterrows():
                        folium.Marker(
                            location=[hotel['latitude'], hotel['longitude']],
                            popup=folium.Popup(f"""
                                <b>{hotel.get('hotel_name', 'Hotel')}</b><br>
                                Rating: {hotel.get('rating', 'N/A')}/5<br>
                                Price: ₹{hotel.get('price', 'N/A')}/night
                            """, max_width=250),
                            tooltip=hotel.get('hotel_name', 'Hotel'),
                            icon=folium.Icon(color='blue', icon='home')
                        ).add_to(m)
                    
                    st_folium(m, width=None, height=600)
                else:
                    st.info("Map view unavailable (coordinates missing)")
                
        except Exception as e:
            st.error(f"Error loading hotels data: {e}")
            st.info("Please ensure categories are correctly defined in your hotel data.")
    elif selected_page == "📅 Itinerary":
        st.title("📅 Your Itinerary")        
        if 'generated_itinerary' in st.session_state and st.session_state.generated_itinerary:
            dest = st.session_state.selected_city
            days = st.session_state.trip_days
            st.markdown(f"### Trip to {dest} ({days} Days)")
            # Create tabs for each day
            day_labels = [f"Day {i}" for i in range(1, days + 1)]
            day_tabs = st.tabs(day_labels)
            itinerary = st.session_state.generated_itinerary
            for idx, tab in enumerate(day_tabs):
                day_num = idx + 1
                with tab:
                    if day_num in itinerary:
                        day_data = itinerary[day_num]
                        day_info = day_data.get('day_info', {})
                        st.info(f"📅 {day_info.get('day_name', 'Day')} - {day_info.get('season', '')} {day_info.get('season_emoji', '')}")
                        col1, col2, col3 = st.columns(3)
                        # Morning
                        with col1:
                            st.markdown("### 🌅 Morning")
                            for activity in day_data.get('morning', []):
                                render_activity_card(activity)
                        # Afternoon
                        with col2:
                            st.markdown("### ☀️ Afternoon")
                            for activity in day_data.get('afternoon', []):
                                render_activity_card(activity)
                        # Evening
                        with col3:
                            st.markdown("### 🌆 Evening")
                            for activity in day_data.get('evening', []):
                                render_activity_card(activity)
                    else:
                        st.warning("No activities found for this day.")
            st.markdown("---")
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button("🔄 Plan New Trip", width='stretch'):
                    st.session_state.selected_page = "🗺️ Plan Trip"
                    st.rerun()
            with col_act2:
                if st.button("💾 Save Trip", type="primary", width='stretch'):
                    # Save logic
                    api_client.save_trip(dest, f"Trip to {dest}", str(st.session_state.trip_start_date), str(st.session_state.trip_start_date + pd.Timedelta(days=days)), itinerary)
                    st.success("Trip saved to 'Saved Trips'!")
        else:
            st.info("No trip planned yet. Go to the 'Plan Trip' page to create one!")
            if st.button("🗺️ Go to Plan Trip", type="primary"):
                st.session_state.selected_page = "🗺️ Plan Trip"
                st.rerun()
        
    elif selected_page == "☁️ Weather":
        st.title("☁️ Weather Forecast")   
        city_input = st.text_input("Enter city name", value=st.session_state.selected_city)
        if city_input:
            weather = api_client.get_weather(city_input)
            if weather:
                if "error" in weather:
                    st.error(weather["error"])
                else:
                    if weather.get('is_mock'):
                        st.warning("⚠️ Using Mock Data: Add `OPENWEATHER_API_KEY` to your `.env` for live weather.")
                    # Main metrics
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.metric("🌡️ Temperature", f"{weather.get('temp', 'N/A')}°C")
                        st.metric("💧 Humidity", f"{weather.get('humidity', 'N/A')}%")
                    with col2:
                        st.metric("🌤️ Condition", weather.get('description', 'Unknown').capitalize())
                        st.metric("💨 Wind", f"{weather.get('wind_speed', 'N/A')} m/s")
                
                st.caption(f"📍 Weather data for {city_input}")
            else:
                st.error("Could not fetch weather data. Please use a valid city name.")

    elif selected_page == "💰 Budget":
        st.title("💰 Trip Budget Planner")
        st.markdown("### Estimate your travel expenses")
        col1, col2 = st.columns(2)
        with col1:
            flights = st.number_input("✈️ Flights / Travel", min_value=0, value=5000)
            accommodation = st.number_input("🏨 Accommodation", min_value=0, value=10000)
            food = st.number_input("🍔 Food & Dining", min_value=0, value=5000)
        with col2:
            activities = st.number_input("🎫 Activities & Tours", min_value=0, value=3000)
            shopping = st.number_input("🛍️ Shopping & Souvenirs", min_value=0, value=2000)
            misc = st.number_input("🚕 Transport & Misc", min_value=0, value=1000)
        total_budget = flights + accommodation + food + activities + shopping + misc
        st.markdown("---")
        st.metric("💵 Total Estimated Budget", f"₹{total_budget:,.2f}")
        # Simple breakdown chart
        budget_data = pd.DataFrame({
            "Category": ["Flights", "Accommodation", "Food", "Activities", "Shopping", "Misc"],
            "Amount": [flights, accommodation, food, activities, shopping, misc]})
        st.bar_chart(budget_data.set_index("Category"))
    elif selected_page == "🛫 Saved Trips":
        st.title("🛫 Saved Trips")
        # --- SAVED ITINERARIES SECTION ---
        st.markdown("### 🗺️ Saved Itineraries")
        saved_trips = api_client.get_trips(username=st.session_state.get('username'))
        if not saved_trips:
            st.info("No saved trips yet. Plan a trip and save it!")
        else:
            for trip in saved_trips:
                with st.expander(f"🗺️ {trip.get('trip_name', 'Trip')} ({trip.get('city', 'City')}) - {trip.get('start_date', 'Date')}"):
                    st.write(f"**Dates:** {trip.get('start_date')} to {trip.get('end_date')}")
                    st.write(f"**Created:** {trip.get('created_at', '')}")    
                    if st.button("Load Itinerary", key=f"load_{trip.get('id', 'unknown')}"):
                        st.session_state.selected_city = trip.get('city')
                        st.session_state.trip_start_date = pd.to_datetime(trip.get('start_date')).date() if trip.get('start_date') else pd.to_datetime("today").date()
                        # Update trip planning state to reflect the loaded city
                        st.session_state.trip_days = len(trip.get('itinerary_data', {}))
                        st.success(f"Loaded trip context for {trip['city']}! Redirecting to Dashboard...")
                        time.sleep(1)
                        st.rerun()
    elif selected_page == "⚙️ Settings":
        st.title("⚙️ Settings")
        st.markdown("### 🎨 Preferences")
        # Theme Setting
        theme_toggle_label = "☀️ Switch to Light Mode" if st.session_state.theme == "dark" else "🌙 Switch to Dark Mode"
        if st.button(theme_toggle_label, width='stretch'):
             new_theme = "light" if st.session_state.theme == "dark" else "dark"
             st.session_state.theme = new_theme
             api_client.save_setting("theme", new_theme)
             st.rerun()
# -----------------------------
# RIGHT CHAT PANEL
# -----------------------------
with col_chat:
    st.markdown("### 💬 AI Assistant")
    st.caption("Quick summaries & travel tips")
    # Scrollable chat box
    chat_box = st.container(height=500)
    with chat_box:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                # Render detected place images if present (Assistant messages only)
                if msg["role"] == "assistant" and "detected_places" in msg:
                    places = msg["detected_places"]
                    if places:
                        # Use city context from state for more accurate images
                        city = st.session_state.get('selected_city', '') 
                        st.markdown("---")
                        # Beautiful horizontal scroll of images
                        cols = st.columns(min(len(places), 3))
                        for i, place in enumerate(places):
                            with cols[i % 3]:
                                img_url = get_category_image("landmark", place, city)
                                st.image(img_url, caption=place, width='stretch')
    # Input stays fixed
    user_input = st.chat_input("Ask me about your trip...")
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        # Generate Response (without displaying it here)
        with st.spinner("Thinking..."):
            # Call API for chat
            # Pass history so backend can do context management if needed
            response_data = api_client.chat(
                message=user_input, 
                messages=st.session_state.messages, 
                city=st.session_state.selected_city)
            # Check for error returned by updated api_client
            if response_data and response_data.get("error"):
                 response_text = f"⚠️ {response_data.get('message')}"
                 detected_city = None
                 detected_days = None
            else:
                response_text = response_data.get("response", "Sorry, I couldn't process that. (No response from server)")
                detected_city = response_data.get("detected_city")
                detected_days = response_data.get("detected_days")
                # Check for seasonal result marker from RAG engine
                if response_text.startswith("__SEASONAL__") and "|" in response_text:
                    parts = response_text.split("|")
                    if len(parts) >= 3:
                        season_tag = parts[0].replace("__SEASONAL__", "")
                        city_list_raw = parts[1]
                        response_text = parts[2]
                        # Store seasonal info for the dashboard
                        st.session_state.seasonal_info = {"season": season_tag,
                            "cities": [c.strip() for c in city_list_raw.split(",")]}
                        st.session_state.chat_display_mode = "seasonal"
                # Check for planning intercept (starts with ✨)
                elif response_text.startswith("✨") and "itinerary" in response_text.lower():
                    st.session_state.chat_display_mode = "trip_planning"
             # Add assistant response
            st.session_state.messages.append({ "role": "assistant", 
                "content": response_text,
                "detected_places": response_data.get("detected_places", []) })
            # 1. Update detected city
            if detected_city and detected_city != st.session_state.selected_city:
                 st.session_state.selected_city = detected_city
                 # Force a switch to city_info if no other mode is set and city just changed
                 if not st.session_state.chat_display_mode:
                     st.session_state.chat_display_mode = "city_info"
            # 2. Update detected duration (days) or special mode sentinel
            if detected_days:
                if detected_days == "restaurants":
                    # Restaurant intent sentinel from quick_responses
                    st.session_state.chat_display_mode = "restaurants"
                else:
                    try:
                        days = int(detected_days)
                        if 1 <= days <= 30:
                            st.session_state.trip_days = days
                            # If days are mentioned, we usually want to see the trip planning dashboard
                            st.session_state.chat_display_mode = "trip_planning"
                    except:
                        pass
            # 3. Update display mode from API (highest priority)
            detected_mode = response_data.get("detected_mode")
            if detected_mode:
                # Map backend intents to frontend display modes
                mode_map = {"trip_planning": "trip_planning",
                    "hotels": "hotels",
                    "places": "places",
                    "weather": "weather",
                    "city_info": "city_info"}
                if detected_mode in mode_map:
                    st.session_state.chat_display_mode = mode_map[detected_mode]
            # 4. Fallback Keyword Detection (if API didn't provide a mode)
            elif not detected_mode:
                query_lower = user_input.lower()
                if any(word in query_lower for word in ['plan trip', 'trip plan', 'itinerary']):
                    st.session_state.chat_display_mode = "trip_planning"
                elif any(word in query_lower for word in ['hotel', 'stay']):
                    st.session_state.chat_display_mode = "hotels"
                elif any(word in query_lower for word in ['restaurant', 'dining', 'where to eat', 'food places']):
                    st.session_state.chat_display_mode = "restaurants"
                elif any(word in query_lower for word in ['place', 'visit', 'attraction']):
                    st.session_state.chat_display_mode = "places"
                elif any(word in query_lower for word in ['weather']):
                    st.session_state.chat_display_mode = "weather"
                elif any(word in query_lower for word in ['about', 'info']):
                    st.session_state.chat_display_mode = "city_info"
            # Rerun to display the new messages and update dashboard
            st.rerun()