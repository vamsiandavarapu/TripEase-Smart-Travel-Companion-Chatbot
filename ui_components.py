import streamlit as st
from season_utils import infer_best_time
from image_service import search_unsplash_image

def get_custom_css(theme="dark"):
    # Define color system for a premium feel
    if theme == "dark":
        # Night Mode: Deep Sea/Charcoal Palette
        bg_color = "#0B1120"
        sidebar_bg = "#111827"
        card_bg = "#1F2937"
        card_border = "#374151"
        accent_color = "#6366F1"  # Indigo
        accent_secondary = "#8B5CF6" # Violet
        text_primary = "#F9FAFB"
        text_secondary = "#9CA3AF"
        bot_msg_bg = "#1F2937"
        glass_bg = "rgba(31, 41, 55, 0.7)"
        input_bg = "#111827"
    else:
        # Day Mode: Clean/Soft White Palette
        bg_color = "#F8F9FA"
        sidebar_bg = "#FFFFFF"
        card_bg = "#FFFFFF"
        card_border = "#E5E7EB"
        accent_color = "#2563EB" # Royal Blue
        accent_secondary = "#3B82F6" # Blue
        text_primary = "#111827"
        text_secondary = "#4B5563"
        bot_msg_bg = "#F3F4F6"
        glass_bg = "rgba(255, 255, 255, 0.7)"
        input_bg = "#FFFFFF"

    return f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    /* Global Transitions and Typography */
    * {{
        transition: background-color 0.4s ease, border-color 0.4s ease, box-shadow 0.4s ease;
        font-family: 'Outfit', sans-serif;
    }}

    /* Main View */
    [data-testid="stAppViewContainer"] {{
        background-color: {bg_color};
        color: {text_primary};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        border-right: 1px solid {card_border};
    }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {text_primary} !important;
        font-weight: 600;
    }}

    /* Glass Effect Containers */
    .glass-card {{
        background: {glass_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}

    /* Theme Card (Used in Hotels/Places) */
    .theme-card {{
        background-color: {card_bg};
        border: 1px solid {card_border};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }}
    .theme-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px {accent_color}22; /* Low opacity accent shadow */
        border-color: {accent_color}44;
    }}

    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: {text_primary} !important;
        letter-spacing: -0.025em;
    }}
    
    /* Global Text */
    p, span, label, .stMetric div {{
        color: {text_secondary} !important;
    }}
    strong, b {{
        color: {text_primary} !important;
    }}

    /* Metric Styling */
    [data-testid="stMetricValue"] {{
        color: {accent_color} !important;
        font-weight: 700 !important;
    }}

    /* Buttons - Standard and Sidebar */
    .stButton > button, 
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] button {{
        border-radius: 10px !important;
        border: 1px solid {card_border} !important;
        background-color: {card_bg} !important;
        color: {text_primary} !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }}
    
    .stButton > button:hover,
    [data-testid="stSidebar"] button:hover,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
        border-color: {accent_color} !important;
        color: {accent_color} !important;
        background-color: {card_bg} !important;
        box-shadow: 0 0 10px {accent_color}33 !important;
    }}
    
    /* Primary Action Button */
    button[kind="primary"] {{
        background-color: {accent_color} !important;
        color: white !important;
        border: none !important;
    }}
    button[kind="primary"]:hover {{
        background-color: {accent_secondary} !important;
        color: white !important;
        transform: scale(1.02);
    }}

    /* Chat Messages */
    .stChatMessage {{
        background-color: transparent !important;
    }}
    
    [data-testid="stChatMessageContent"] {{
        background-color: {bot_msg_bg} !important;
        border: 1px solid {card_border} !important;
        color: {text_primary} !important;
        border-radius: 15px !important;
        margin-bottom: 15px !important; /* Distance between messages */
        padding: 12px !important;       /* Inner box space */
    }}
    /* User Message Override (if possible to distinguish) */
    /* Note: Streamlit doesn't give easy classes for user vs bot, 
       but we can style the internal content if we use custom divs in app.py */
    /* Weather Widget Refined */
    .weather-widget {{
        background: linear-gradient(135deg, {accent_color}, {accent_secondary});
        border-radius: 20px;
        padding: 30px;
        color: white !important;
        text-align: center;
        box-shadow: 0 10px 25px {accent_color}44;
    }}
    .weather-widget h1, .weather-widget h2, .weather-widget p {{
        color: white !important;
        margin: 5px 0;
    }}
    /* Hide Streamlit components for cleaner look */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{background: transparent !important;}}
    </style>"""

def render_place_card(place, image_url=None):
    """Renders a high-fidelity place card matching the 'Perfect Match' UI specs."""
    name = place.get('place_name', 'Unknown Place')
    category = place.get('category', 'N/A')
    description = place.get('description', 'A wonderful place to visit!')
    best_time = place.get('best_time_to_visit')
    if not best_time or str(best_time).lower() in ['nan', 'none', '']:
        best_time = infer_best_time(name, category)
    rating = place.get('rating', 'N/A')
    entry_fee = place.get('entry_fee', 0)
    lat = place.get('latitude', 'N/A')
    lon = place.get('longitude', 'N/A')
    if not image_url:
        image_url = get_category_image(category, name)
    # 1. Header Box
    st.markdown(f"""
    <div class="theme-card">
        <h2 style="margin: 0; font-size: 32px; font-weight: 700; display: flex; align-items: center;">
            <span style="margin-right: 15px; font-size: 28px;">📍</span> {name}
        </h2>
    </div>""", unsafe_allow_html=True)
    # 2. Image (Full Width)
    st.image(image_url, width='stretch')
    # 3. Details Row
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.8, 1, 1])
    with col1:
        st.markdown(f"<p style='margin-bottom: 8px;'><b>Category:</b> <span>{category}</span></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-bottom: 8px;'><b>Description:</b> <span>{description}</span></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin-bottom: 8px;'><b>Best Time to Visit:</b> <span>{best_time}</span></p>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: left; padding-left: 10px;">
            <div style="font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
                <span style="color: #fbbf24;">⭐</span> Rating
            </div>
            <div style="font-size: 42px; font-weight: 800; color: inherit; margin-top: 4px; line-height: 1;">
                {rating}/5
            </div>
            <div style="margin-top: 28px;">
                <div style="font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">💰</span> Entry Fee
                </div>
                <div style="font-size: 32px; font-weight: 700; color: inherit; margin-top: 4px;">
                    {format_entry_fee(entry_fee)}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Handle Latitude/Longitude formatting
        try:
            lat_str = f"{float(lat):.4f}" if lat != 'N/A' else 'N/A'
            lon_str = f"{float(lon):.4f}" if lon != 'N/A' else 'N/A'
        except:
            lat_str, lon_str = str(lat), str(lon)

        st.markdown(f"""
        <div style="text-align: left; padding-left: 10px;">
            <div style="font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
                <span style="color: #ec4899;">📍</span> Latitude
            </div>
            <div style="font-size: 42px; font-weight: 800; color: inherit; margin-top: 4px; line-height: 1;">
                {lat_str}
            </div>
            <div style="margin-top: 28px;">
                <div style="font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #ec4899; font-size: 16px;">📍</span> Longitude
                </div>
                <div style="font-size: 32px; font-weight: 700; color: inherit; margin-top: 4px;">
                    {lon_str}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True) 
    st.markdown("<div style='margin-bottom: 50px;'></div>", unsafe_allow_html=True)
    st.markdown("---")

def get_category_image(category, place_name="", city_context=""):
    """Returns a high-quality Unsplash image URL.
    1. Tries Dynamic Search via Unsplash API (if key exists)
    2. Fallback to specific reliable photo IDs based on category/name """
    # 1. Try Dynamic API Search
    if place_name:
        # Use city_context to narrow down the search (e.g., "Palace Mysore")
        dynamic_url = search_unsplash_image(place_name, city_context)
        if dynamic_url:
            return dynamic_url
    # 2. Fallback to Curated Static Logic
    cat_lower = category.lower() if category else ""
    name_lower = place_name.lower() if place_name else ""
    
    # Specific keywords in name
    if 'mall' in name_lower or 'market' in name_lower:
        return "https://images.unsplash.com/photo-1472851294608-415105022054?auto=format&fit=crop&w=800&q=80" # Busy market
    if 'temple' in name_lower or 'shrine' in name_lower:
        return "https://images.unsplash.com/photo-1582510003544-bea4db4d303f?auto=format&fit=crop&w=800&q=80" # Temple
    if 'palace' in name_lower or 'fort' in name_lower:
        return "https://images.unsplash.com/photo-1599661046289-e31897b12408?auto=format&fit=crop&w=800&q=80" # Mysore Palace or similar grand structure
    if 'beach' in name_lower:
        return "https://images.unsplash.com/photo-1473116763249-56381a35deaa?auto=format&fit=crop&w=800&q=80" # Beach
    if 'museum' in name_lower:
        return "https://images.unsplash.com/photo-1566127444979-b3d2b654e3d7?auto=format&fit=crop&w=800&q=80" # Museum
    if 'park' in name_lower or 'garden' in name_lower:
        return "https://images.unsplash.com/photo-1496070242169-caeb40a13d09?auto=format&fit=crop&w=800&q=80" # Park
    if 'lake' in name_lower:
        return "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=800&q=80" # Lake/Nature
    
    # Categories
    if 'adventure' in cat_lower:
        return "https://images.unsplash.com/photo-1533692328991-08159e79439a?auto=format&fit=crop&w=800&q=80" # Adventure/Trekking
    if 'history' in cat_lower or 'heritage' in cat_lower:
        return "https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=800&q=80" # Historic Fort
    if 'nature' in cat_lower or 'scenic' in cat_lower:
        return "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=800&q=80" # Nature/Landscape
    if 'worship' in cat_lower or 'religious' in cat_lower:
         return "https://images.unsplash.com/photo-1582510003544-bea4db4d303f?auto=format&fit=crop&w=800&q=80"
    if 'shopping' in cat_lower:
         return "https://images.unsplash.com/photo-1472851294608-415105022054?auto=format&fit=crop&w=800&q=80"

    # Default fallback (Travel/Map theme)
    return "https://images.unsplash.com/photo-1524850011238-e3d235c7d4c9?auto=format&fit=crop&w=800&q=80"

def format_entry_fee(fee):
    """Formats entry fee to be user-friendly."""
    try:
        val = float(fee)
        if val == 0:
            return "Free"
        return f"₹{int(val)}"
    except:
        if str(fee).lower() in ['0', 'inf', 'nan', 'none', '']:
            return "Free"
        return str(fee)
