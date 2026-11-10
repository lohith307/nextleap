"""
Zomato AI Restaurant Recommendation System - Streamlit Web Application
Combines structured catalog retrieval with grounded LLM reasoning for personalized recommendations.
Features the exact ultra-premium dark-mode design system, budget number pills, and interactive map split-view from ui/index.html.
"""
import os
import json
import streamlit as st
import streamlit.components.v1 as components
from domain.models import UserPreference, BudgetBand
from ingestion.repo import RestaurantRepo
from filters.candidate_filter import CandidateFilterEngine
from llm.client import LLMClient

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="ZomatoAI — AI-Powered Restaurant Discovery",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Custom Styling (Matches ui/index.html Dark Theme Exactly)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');

    :root {
      --bg:             #09090B;
      --bg-panel:       #121215;
      --bg-card:        #17171C;
      --bg-card-hover:  #1D1D23;
      --bg-input:       #19191F;
      --border-subtle:  rgba(255, 255, 255, 0.08);
      --border-strong:  rgba(255, 255, 255, 0.16);
      --brand:          #E23744;
      --brand-hover:    #FF3B4B;
      --brand-glow:     rgba(226, 55, 68, 0.35);
      --brand-tint:     rgba(226, 55, 68, 0.12);
      --ai-purple:      #A855F7;
      --ai-purple-tint: rgba(168, 85, 247, 0.12);
      --ai-purple-border: rgba(168, 85, 247, 0.32);
      --rating-green:   #22C55E;
      --rating-green-bg:rgba(34, 197, 94, 0.16);
      --text-1:         #F8FAFC;
      --text-2:         #94A3B8;
      --text-3:         #64748B;
      --radius-sm:      8px;
      --radius-md:      12px;
      --radius-lg:      18px;
      --font:           'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Protect Streamlit Material Symbols Icons from broken ligatures */
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="collapsedControl"] span,
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-symbols-outlined,
    [data-testid="stHeader"] span {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-smoothing: antialiased !important;
        font-feature-settings: 'liga' 1 !important;
    }

    /* Global Dark Background */
    .stApp {
        background-color: var(--bg) !important;
        color: var(--text-1) !important;
    }

    /* Apply Plus Jakarta Sans to text elements only */
    .stApp p, .stApp span:not([data-testid="stIconMaterial"]):not(.material-symbols-rounded), 
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label, .stApp input, .stApp button {
        font-family: var(--font) !important;
    }

    /* Sidebar Background & Border */
    [data-testid="stSidebar"] {
        background-color: var(--bg-panel) !important;
        border-right: 1px solid var(--border-subtle) !important;
        padding-top: 1rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: #26262F; border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: #383844; }

    /* Top Brand Navigation */
    .nav-bar {
        background: rgba(9, 9, 11, 0.92);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 12px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .nav-logo {
        font-size: 24px;
        font-weight: 900;
        color: var(--brand);
        letter-spacing: -0.6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .nav-ai-pill {
        background: rgba(226, 55, 68, 0.14);
        border: 1px solid rgba(226, 55, 68, 0.35);
        border-radius: 99px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 800;
        color: var(--brand);
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .nav-status {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.28);
        border-radius: 99px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 600;
        color: var(--rating-green);
    }
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--rating-green);
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.8);
        animation: pulse-dot 2s infinite ease-in-out;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Hero Banner */
    .hero-banner {
        text-align: center;
        padding: 36px 20px 26px;
        background: radial-gradient(circle at 50% -20%, #2b0207 0%, #170005 45%, var(--bg) 85%);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        margin-bottom: 24px;
    }
    .hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        background: rgba(226, 55, 68, 0.1);
        border: 1px solid rgba(226, 55, 68, 0.3);
        border-radius: 99px;
        padding: 4px 14px;
        font-size: 11px;
        font-weight: 700;
        color: #FFA5AB;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.8px;
        color: #FFFFFF;
        margin-bottom: 8px;
    }
    .gradient-text {
        background: linear-gradient(135deg, #FF4B5C 0%, #FF8591 45%, #FFAAA6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 14px;
        color: var(--text-2);
        max-width: 600px;
        margin: 0 auto 16px;
        line-height: 1.6;
    }
    .hero-badges {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #15151A;
        border: 1px solid var(--border-subtle);
        border-radius: 99px;
        padding: 5px 14px;
        font-size: 11.5px;
        font-weight: 600;
        color: var(--text-2);
    }

    /* Sidebar Header */
    .sidebar-header-box {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 14px;
        margin-bottom: 16px;
        border-bottom: 1px solid var(--border-subtle);
    }
    .sidebar-title {
        font-size: 13.5px;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 0.8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .red-sparkle {
        color: var(--brand);
        font-size: 14px;
    }
    .sidebar-pill {
        background: rgba(226, 55, 68, 0.12);
        border: 1px solid rgba(226, 55, 68, 0.3);
        border-radius: 99px;
        padding: 2px 8px;
        font-size: 9.5px;
        font-weight: 800;
        color: #FF7B84;
        letter-spacing: 0.6px;
    }

    /* Sidebar Field Labels */
    .sidebar-label {
        font-size: 10.5px;
        font-weight: 800;
        color: var(--text-3);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 14px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .sidebar-label .req {
        color: var(--brand);
    }

    /* Segmented Control Styling - 3 Equal-Width Horizontal Cards */
    div[data-testid="stSegmentedControl"] {
        width: 100% !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stSegmentedControl"] > div {
        width: 100% !important;
        display: flex !important;
        gap: 6px !important;
    }
    div[data-testid="stSegmentedControl"] button {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        background-color: #19191F !important;
        border: 1.5px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        padding: 10px 4px !important;
        color: #94A3B8 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-align: center !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
        white-space: nowrap !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        border-color: rgba(226, 55, 68, 0.4) !important;
        color: #FFFFFF !important;
        background-color: #202027 !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[data-checked="true"],
    div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
        background-color: rgba(226, 55, 68, 0.16) !important;
        border-color: #E23744 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 14px rgba(226, 55, 68, 0.3) !important;
    }

    /* Fallback Clean stRadio */
    div[data-testid="stRadio"] > label,
    div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
        display: none !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        width: 100% !important;
        flex-wrap: nowrap !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] > label {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        background: #19191F !important;
        border: 1.5px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 10px !important;
        padding: 8px 2px !important;
        text-align: center !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
        border-color: rgba(226, 55, 68, 0.4) !important;
        background: #202027 !important;
    }
    div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
        background: rgba(226, 55, 68, 0.14) !important;
        border-color: #E23744 !important;
        box-shadow: 0 0 14px rgba(226, 55, 68, 0.25) !important;
    }
    div[data-testid="stRadio"] input[type="radio"],
    div[data-testid="stRadio"] [role="radio"] > div:first-child,
    div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        position: absolute !important;
    }

    /* Sidebar Metadata Info Box */
    .sidebar-meta-box {
        background: #15151A;
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 14px;
        margin-top: 20px;
    }
    .sidebar-meta-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11.5px;
        color: var(--text-2);
        margin-bottom: 7px;
    }
    .sidebar-meta-row:last-child {
        margin-bottom: 0;
    }
    .sidebar-meta-val {
        color: #FFFFFF;
        font-weight: 700;
    }

    /* AI Overview Box */
    .ai-overview-box {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.12) 0%, rgba(226, 55, 68, 0.08) 100%);
        border: 1px solid var(--ai-purple-border);
        border-radius: var(--radius-lg);
        padding: 18px 22px;
        display: flex;
        align-items: flex-start;
        gap: 14px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(168, 85, 247, 0.08);
    }
    .ai-icon-box {
        width: 38px;
        height: 38px;
        border-radius: var(--radius-sm);
        background: var(--ai-purple-tint);
        border: 1px solid var(--ai-purple-border);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }
    .ai-overview-label {
        font-size: 10.5px;
        font-weight: 800;
        color: var(--ai-purple);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
    .ai-overview-text {
        font-size: 13.5px;
        color: #E2E8F0;
        line-height: 1.6;
    }

    /* Streamlit Form Control Overrides */
    div[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #E23744 0%, #C02734 100%) !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        font-size: 13.5px !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 20px rgba(226, 55, 68, 0.45) !important;
        border: none !important;
        margin-top: 12px !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 26px rgba(226, 55, 68, 0.6) !important;
    }

    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 10px !important;
        color: var(--text-1) !important;
    }
    div[data-baseweb="select"] > div:focus-within, div[data-baseweb="input"] > div:focus-within {
        border-color: var(--brand) !important;
        box-shadow: 0 0 0 2px var(--brand-glow) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Cached Service Initialization (Single memory instance)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Loading verified Zomato catalog and initializing AI engine...")
def load_app_services():
    """Initializes and caches the catalog repository, candidate filter, and LLM client."""
    repo = RestaurantRepo()
    filter_engine = CandidateFilterEngine(repo)
    llm_client = LLMClient()
    return repo, filter_engine, llm_client


repo, filter_engine, llm_client = load_app_services()

# Identify active engine
if llm_client.groq_api_key:
    active_engine = f"Groq Cloud ({llm_client.model})"
elif llm_client.openai_api_key:
    active_engine = f"OpenAI ({llm_client.model})"
elif llm_client.gemini_api_key:
    active_engine = "Google Gemini"
else:
    active_engine = "Grounded AI Reasoning Engine (Zero API Key)"


# ---------------------------------------------------------
# Top Navigation Bar (Matches ui/index.html)
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="nav-bar">
        <div class="nav-logo">
            <span>zomato</span><span class="nav-ai-pill">AI</span>
        </div>
        <div class="nav-status">
            <span class="status-dot"></span>
            <span>{len(repo.restaurants):,} Verified Catalog Restaurants • {active_engine}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Hero Banner (Matches ui/index.html)
# ---------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-banner">
        <div class="hero-eyebrow">✦ NEXT-GEN RESTAURANT DISCOVERY</div>
        <h1 class="hero-title">Find Your Next Craving with <span class="gradient-text">AI-Powered Reasoning</span></h1>
        <p class="hero-subtitle">
            Structured catalog filtering meets LLM intelligence. Every recommendation is fact-verified against
            real catalog ratings, costs, and locations with personalized reasoning.
        </p>
        <div class="hero-badges">
            <span class="hero-badge">⚡ {active_engine}</span>
            <span class="hero-badge">🔒 100% Zero-Hallucination Grounding</span>
            <span class="hero-badge">📍 {len(repo.get_locations())} Bengaluru Localities</span>
            <span class="hero-badge">🍲 {len(repo.get_cuisines())} Cuisines</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar: Preferences Form
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-header-box">
            <div class="sidebar-title">
                <span class="red-sparkle">✦</span> SEARCH &amp; FILTERS
            </div>
            <span class="sidebar-pill">CATALOG VERIFIED</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Location
    locations = repo.get_locations()
    default_loc_idx = 0
    for target in ["Banashankari", "Bangalore", "Koramangala", "Indiranagar", "Basavanagudi"]:
        if target in locations:
            default_loc_idx = locations.index(target)
            break

    st.markdown('<div class="sidebar-label">LOCATION <span class="req">*</span></div>', unsafe_allow_html=True)
    selected_location = st.selectbox(
        "Location",
        options=locations,
        index=default_loc_idx,
        label_visibility="collapsed",
    )

    # 2. Cuisine
    cuisines = repo.get_cuisines()
    default_cui_idx = 0
    for target in ["North Indian", "South Indian", "Chinese", "Italian", "Cafe"]:
        if target in cuisines:
            default_cui_idx = cuisines.index(target)
            break

    st.markdown('<div class="sidebar-label">CUISINE <span class="req">*</span></div>', unsafe_allow_html=True)
    selected_cuisine = st.selectbox(
        "Cuisine",
        options=cuisines,
        index=default_cui_idx,
        label_visibility="collapsed",
    )

    # 3. Budget Tier (Showing exact dynamic numbers)
    p33 = int(repo.p33_cost)
    p66 = int(repo.p66_cost)
    
    st.markdown(
        f'<div class="sidebar-label">BUDGET TIER <span style="font-weight: 500; font-size: 10px; color: #64748B;">'
        f'(Under ₹{p33} • ₹{p33}-₹{p66} • Above ₹{p66})</span></div>',
        unsafe_allow_html=True,
    )
    
    # Clearly show numbers on each option
    budget_card_map = {
        f"₹ < ₹{p33}": BudgetBand.LOW,
        f"₹₹ ₹{p33}-₹{p66}": BudgetBand.MEDIUM,
        f"₹₹₹ > ₹{p66}": BudgetBand.HIGH,
    }
    
    default_budget_label = f"₹₹ ₹{p33}-₹{p66}"
    
    if hasattr(st, "segmented_control"):
        budget_choice = st.segmented_control(
            "Budget Tier",
            options=list(budget_card_map.keys()),
            default=default_budget_label,
            label_visibility="collapsed",
            width="stretch",
        )
        if not budget_choice:
            budget_choice = default_budget_label
    else:
        budget_choice = st.radio(
            "Budget Tier",
            options=list(budget_card_map.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )
    selected_budget = budget_card_map[budget_choice]

    # 4. Minimum Rating Slider
    st.markdown(
        '<div class="sidebar-label">MINIMUM RATING <span class="req">*</span></div>',
        unsafe_allow_html=True,
    )
    selected_min_rating = st.slider(
        "Minimum Rating",
        min_value=3.0,
        max_value=5.0,
        value=3.8,
        step=0.1,
        label_visibility="collapsed",
    )

    # 5. Dietary Preference
    st.markdown('<div class="sidebar-label">DIETARY PREFERENCE</div>', unsafe_allow_html=True)
    dietary_preference = st.selectbox(
        "Dietary Preference",
        options=["Any", "Vegetarian / Pure Veg", "Non-Veg Friendly"],
        index=0,
        label_visibility="collapsed",
    )

    # 6. Occasion & Vibe
    st.markdown('<div class="sidebar-label">OCCASION &amp; VIBE</div>', unsafe_allow_html=True)
    ambiance_tags = st.multiselect(
        "Ambiance",
        options=[
            "Family Dining",
            "Romantic Date Night",
            "Rooftop & Outdoor",
            "Cozy Cafe Vibes",
            "Late Night Food",
            "Quick Bite & Fast Service",
            "Live Music & Cocktails",
        ],
        default=["Family Dining"],
        label_visibility="collapsed",
    )

    # 7. Custom Notes
    st.markdown('<div class="sidebar-label">CUSTOM CRAVINGS (OPTIONAL)</div>', unsafe_allow_html=True)
    additional_notes = st.text_input(
        "Custom Notes",
        value="",
        placeholder="e.g. authentic biryani, quiet corner, outdoor seating",
        label_visibility="collapsed",
    )

    # Submit Button
    search_submitted = st.button("🚀 GET RECOMMENDATIONS", use_container_width=True)

    # Sidebar Catalog Metadata Box
    st.markdown(
        f"""
        <div class="sidebar-meta-box">
            <div class="sidebar-meta-row">
                <span>Verified Catalog:</span>
                <span class="sidebar-meta-val">{len(repo.restaurants):,} Restaurants</span>
            </div>
            <div class="sidebar-meta-row">
                <span>Localities:</span>
                <span class="sidebar-meta-val">{len(locations)} Areas</span>
            </div>
            <div class="sidebar-meta-row">
                <span>Cuisines:</span>
                <span class="sidebar-meta-val">{len(cuisines)} Styles</span>
            </div>
            <div class="sidebar-meta-row">
                <span>Active Engine:</span>
                <span class="sidebar-meta-val" style="color: #FFA5AB;">{active_engine}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------
# Quick Preset Inspiration (1-Click)
# ---------------------------------------------------------
if not search_submitted and "preset_pref" not in st.session_state:
    st.markdown("##### 💡 Or tap a curated discovery shortcut:")
    col_p1, col_p2, col_p3 = st.columns(3)

    if col_p1.button("🍛 North Indian in Banashankari (Mid-Range)"):
        st.session_state["preset_pref"] = UserPreference(
            location="Banashankari",
            cuisine="North Indian",
            budget=BudgetBand.MEDIUM,
            min_rating=3.8,
            additional_preferences="family friendly, flavorful curries and naan",
        )
        st.rerun()

    if col_p2.button("☕ Cozy Cafe in Bangalore (Budget)"):
        st.session_state["preset_pref"] = UserPreference(
            location="Bangalore",
            cuisine="Cafe",
            budget=BudgetBand.LOW,
            min_rating=3.5,
            additional_preferences="cozy cafe vibes, great coffee and snacks",
        )
        st.rerun()

    if col_p3.button("🍕 Fine Dining Italian in Koramangala"):
        st.session_state["preset_pref"] = UserPreference(
            location="Bangalore",
            cuisine="Italian",
            budget=BudgetBand.HIGH,
            min_rating=4.0,
            additional_preferences="authentic wood-fired pizza and pasta, romantic date",
        )
        st.rerun()


# ---------------------------------------------------------
# Execute Recommendation Logic
# ---------------------------------------------------------
pref_to_run = None
if search_submitted:
    extra_prefs = []
    if dietary_preference and dietary_preference != "Any":
        extra_prefs.append(dietary_preference)
    if ambiance_tags:
        extra_prefs.extend(ambiance_tags)
    if additional_notes.strip():
        extra_prefs.append(additional_notes.strip())

    combined_notes = ", ".join(extra_prefs)

    pref_to_run = UserPreference(
        location=selected_location,
        cuisine=selected_cuisine,
        budget=selected_budget,
        min_rating=selected_min_rating,
        additional_preferences=combined_notes,
    )
elif "preset_pref" in st.session_state:
    pref_to_run = st.session_state.pop("preset_pref")

if pref_to_run:
    with st.spinner("Analyzing verified catalog & synthesizing AI explanations with Groq..."):
        # Step 1: Catalog Filtering
        candidates, is_relaxed = filter_engine.extract_candidates(pref_to_run, limit=15)

        # Step 2: Zero Match Handling
        if not candidates:
            st.error(
                f"❌ **No restaurants found matching '{pref_to_run.cuisine}' in '{pref_to_run.location}'.**\n\n"
                f"**Suggestions:**\n"
                f"- Choose a broader location (e.g. *Bangalore*, *Indiranagar*, or *Koramangala*).\n"
                f"- Lower the minimum rating threshold slightly.\n"
                f"- Switch to a broader cuisine (e.g. *North Indian*, *Chinese*, *Fast Food*)."
            )
        else:
            # Step 3: LLM Ranking & Explanation
            recommendations, summary = llm_client.rank_and_explain(pref_to_run, candidates)

            # Step 4: Display Relaxation Alert if criteria were broadened
            if is_relaxed:
                st.info(
                    f"ℹ️ **Expanded Search Active:** We broadened the rating or budget threshold slightly "
                    f"to ensure you get the best available verified recommendations for **{pref_to_run.cuisine}** "
                    f"in **{pref_to_run.location}**."
                )

            # Step 5: AI Contextual Summary Banner (Matches ui/index.html)
            if summary:
                st.markdown(
                    f"""
                    <div class="ai-overview-box">
                        <div class="ai-icon-box">✦</div>
                        <div class="ai-overview-content">
                            <div class="ai-overview-label">AI CURATION OVERVIEW • {active_engine}</div>
                            <div class="ai-overview-text">{summary}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Step 6: Build JSON Payload for Interactive Split-View Map & Cards
            recs_json_list = []
            cand_map = {c.id: c for c in candidates}
            for idx, rec in enumerate(recommendations, 1):
                cand = cand_map.get(rec.id)
                cand_loc = cand.location if cand else pref_to_run.location
                
                # Deterministic coordinate placement for Bengaluru area map canvas
                base_x = 24 + ((idx * 29 + 11) % 52)
                base_y = 20 + ((idx * 23 + 17) % 55)

                recs_json_list.append({
                    "rank": rec.rank,
                    "name": rec.name,
                    "cuisine": f"{rec.cuisine} • {cand_loc}",
                    "rating": float(rec.rating),
                    "estimated_cost": int(rec.estimated_cost),
                    "explanation": rec.explanation,
                    "dist": f"{(0.6 + idx * 0.4):.1f} km",
                    "online_order": (cand.online_order if cand and cand.online_order else "No"),
                    "table_booking": (cand.table_booking if cand and cand.table_booking else "No"),
                    "votes": (cand.votes if cand and cand.votes else 0),
                    "coords": {"x": base_x, "y": base_y},
                })

            recs_json_str = json.dumps(recs_json_list)
            loc_label = pref_to_run.location

            # Step 7: Render Interactive Split View (Cards on Left + Interactive Map on Right)
            split_view_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
              <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{
                  background: transparent;
                  color: #F8FAFC;
                  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                  overflow-x: hidden;
                }}
                .split-container {{
                  display: grid;
                  grid-template-columns: 1.15fr 0.95fr;
                  gap: 18px;
                  align-items: start;
                  width: 100%;
                }}
                @media (max-width: 900px) {{
                  .split-container {{ grid-template-columns: 1fr; }}
                }}
                
                /* Left Cards Stream */
                .cards-stream {{
                  display: flex;
                  flex-direction: column;
                  gap: 14px;
                  max-height: 640px;
                  overflow-y: auto;
                  padding-right: 6px;
                }}
                .cards-stream::-webkit-scrollbar {{ width: 5px; }}
                .cards-stream::-webkit-scrollbar-thumb {{ background: #26262F; border-radius: 99px; }}

                .rec-card {{
                  background: #121215;
                  border: 1.5px solid rgba(255, 255, 255, 0.08);
                  border-radius: 16px;
                  padding: 18px 20px;
                  transition: all 0.22s ease;
                  cursor: pointer;
                  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
                }}
                .rec-card:hover {{
                  border-color: rgba(226, 55, 68, 0.45);
                  background: #17171C;
                  transform: translateY(-2px);
                  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5), 0 0 16px rgba(226, 55, 68, 0.15);
                }}
                .rec-card.selected {{
                  border-color: #E23744;
                  background: #191418;
                  box-shadow: 0 0 0 1px #E23744, 0 8px 30px rgba(226, 55, 68, 0.22);
                }}
                .card-top {{
                  display: flex;
                  align-items: flex-start;
                  justify-content: space-between;
                  gap: 12px;
                  margin-bottom: 8px;
                }}
                .card-left-meta {{
                  display: flex;
                  align-items: center;
                  gap: 10px;
                  flex: 1;
                }}
                .card-rank {{
                  width: 32px;
                  height: 32px;
                  border-radius: 50%;
                  background: rgba(226, 55, 68, 0.15);
                  border: 1px solid rgba(226, 55, 68, 0.35);
                  color: #E23744;
                  font-size: 12px;
                  font-weight: 800;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  flex-shrink: 0;
                }}
                .card-name {{
                  font-size: 16px;
                  font-weight: 800;
                  color: #FFFFFF;
                  letter-spacing: -0.3px;
                }}
                .badge-map-link {{
                  background: rgba(226, 55, 68, 0.16);
                  border: 1px solid rgba(226, 55, 68, 0.35);
                  color: #FF7B84;
                  font-size: 9px;
                  font-weight: 800;
                  padding: 2px 7px;
                  border-radius: 99px;
                  letter-spacing: 0.5px;
                  text-transform: uppercase;
                  display: inline-flex;
                  align-items: center;
                  gap: 3px;
                  margin-left: 6px;
                }}
                .rating-badge-green {{
                  background: #22C55E;
                  color: #FFFFFF;
                  font-size: 12px;
                  font-weight: 800;
                  padding: 3px 8px;
                  border-radius: 6px;
                  display: inline-flex;
                  align-items: center;
                  gap: 4px;
                }}
                .card-subline {{
                  font-size: 12.5px;
                  color: #94A3B8;
                  margin-bottom: 8px;
                }}
                .card-meta-row {{
                  display: flex;
                  align-items: center;
                  gap: 10px;
                  flex-wrap: wrap;
                  font-size: 12px;
                  color: #94A3B8;
                  margin-bottom: 10px;
                }}
                .cost-highlight {{ color: #FFFFFF; font-weight: 700; }}
                .tag-chip {{
                  display: inline-block;
                  padding: 2px 8px;
                  background: #181820;
                  border: 1px solid rgba(255, 255, 255, 0.08);
                  border-radius: 99px;
                  color: #94A3B8;
                  font-size: 10.5px;
                  font-weight: 600;
                }}
                .card-reason-box {{
                  background: rgba(226, 55, 68, 0.06);
                  border: 1px solid rgba(226, 55, 68, 0.16);
                  border-left: 3px solid #E23744;
                  border-radius: 10px;
                  padding: 10px 14px;
                  margin-top: 8px;
                }}
                .reason-label {{
                  font-size: 10px;
                  font-weight: 800;
                  color: #E23744;
                  text-transform: uppercase;
                  letter-spacing: 0.6px;
                  margin-bottom: 4px;
                }}
                .reason-text {{
                  font-size: 12px;
                  color: #F1F5F9;
                  line-height: 1.5;
                }}

                /* Right Map Column */
                .map-column {{
                  position: sticky;
                  top: 0;
                  background: #111115;
                  border: 1.5px solid rgba(255, 255, 255, 0.08);
                  border-radius: 18px;
                  height: 640px;
                  display: flex;
                  flex-direction: column;
                  overflow: hidden;
                  position: relative;
                }}
                .map-header-overlay {{
                  position: absolute;
                  top: 14px;
                  left: 14px;
                  right: 14px;
                  z-index: 20;
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  pointer-events: none;
                }}
                .map-tag-left {{
                  background: rgba(18, 18, 22, 0.92);
                  backdrop-filter: blur(8px);
                  border: 1px solid rgba(255, 255, 255, 0.12);
                  border-radius: 99px;
                  padding: 5px 12px;
                  font-size: 11px;
                  font-weight: 700;
                  color: #F8FAFC;
                  display: flex;
                  align-items: center;
                  gap: 6px;
                  pointer-events: auto;
                }}
                .tag-red-dot {{
                  width: 6px;
                  height: 6px;
                  border-radius: 50%;
                  background: #E23744;
                }}
                .map-tag-right {{
                  background: rgba(18, 18, 22, 0.92);
                  backdrop-filter: blur(8px);
                  border: 1px solid rgba(255, 255, 255, 0.12);
                  border-radius: 99px;
                  padding: 5px 12px;
                  font-size: 11px;
                  font-weight: 600;
                  color: #94A3B8;
                  pointer-events: auto;
                }}

                /* Zoom Controls */
                .map-tools {{
                  position: absolute;
                  top: 54px;
                  right: 14px;
                  z-index: 20;
                  display: flex;
                  flex-direction: column;
                  gap: 6px;
                }}
                .map-tool-btn {{
                  width: 32px;
                  height: 32px;
                  border-radius: 8px;
                  background: rgba(23, 23, 28, 0.92);
                  border: 1px solid rgba(255, 255, 255, 0.12);
                  color: #F8FAFC;
                  font-size: 14px;
                  font-weight: 700;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  cursor: pointer;
                  transition: all 0.2s;
                }}
                .map-tool-btn:hover {{
                  background: #272732;
                  border-color: #E23744;
                }}

                /* SVG Canvas */
                .map-canvas-wrap {{
                  flex: 1;
                  width: 100%;
                  height: 100%;
                  position: relative;
                  background: #0E0E12;
                  overflow: hidden;
                }}
                #mapSvg {{
                  width: 100%;
                  height: 100%;
                  transition: transform 0.3s ease;
                }}

                /* Dynamic Pins */
                .map-pin {{
                  position: absolute;
                  transform: translate(-50%, -100%);
                  cursor: pointer;
                  z-index: 10;
                  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
                }}
                .map-pin:hover, .map-pin.active {{
                  transform: translate(-50%, -105%) scale(1.1);
                  z-index: 25;
                }}
                .pin-bubble {{
                  background: #1E1E26;
                  border: 1.5px solid rgba(255, 255, 255, 0.2);
                  border-radius: 99px;
                  padding: 4px 10px;
                  display: flex;
                  align-items: center;
                  gap: 6px;
                  font-size: 11px;
                  font-weight: 700;
                  color: #FFFFFF;
                  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6);
                  white-space: nowrap;
                }}
                .map-pin.active .pin-bubble {{
                  background: #E23744;
                  border-color: #FF7B84;
                  box-shadow: 0 0 24px rgba(226, 55, 68, 0.75);
                }}
                .pin-rank {{
                  font-weight: 900;
                  color: #E23744;
                }}
                .map-pin.active .pin-rank {{ color: #FFFFFF; }}
                .pin-rating {{
                  background: #22C55E;
                  color: #FFFFFF;
                  padding: 1px 5px;
                  border-radius: 4px;
                  font-size: 10px;
                }}
                .pin-pointer {{
                  width: 0;
                  height: 0;
                  border-left: 5px solid transparent;
                  border-right: 5px solid transparent;
                  border-top: 6px solid #1E1E26;
                  margin: 0 auto;
                }}
                .map-pin.active .pin-pointer {{
                  border-top-color: #E23744;
                }}

                /* Floating Focused Card on Map Bottom */
                .map-focus-card {{
                  position: absolute;
                  bottom: 14px;
                  left: 14px;
                  right: 14px;
                  z-index: 25;
                  background: rgba(18, 18, 24, 0.96);
                  backdrop-filter: blur(14px);
                  border: 1.5px solid rgba(255, 255, 255, 0.16);
                  border-radius: 14px;
                  padding: 14px 16px;
                  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.7);
                }}
                .map-focus-top {{
                  display: flex;
                  align-items: flex-start;
                  justify-content: space-between;
                  gap: 10px;
                }}
                .focus-title {{
                  font-size: 14px;
                  font-weight: 800;
                  color: #FFFFFF;
                  display: flex;
                  align-items: center;
                  gap: 6px;
                }}
                .focus-dist {{
                  background: rgba(34, 197, 94, 0.15);
                  color: #22C55E;
                  font-size: 10px;
                  font-weight: 700;
                  padding: 1px 6px;
                  border-radius: 4px;
                }}
                .focus-sub {{
                  font-size: 11px;
                  color: #94A3B8;
                  margin-top: 2px;
                }}
                .focus-snippet {{
                  margin-top: 8px;
                  padding-top: 8px;
                  border-top: 1px solid rgba(255, 255, 255, 0.08);
                  font-size: 11px;
                  color: #CBD5E1;
                  line-height: 1.5;
                  display: -webkit-box;
                  -webkit-line-clamp: 2;
                  -webkit-box-orient: vertical;
                  overflow: hidden;
                }}
                .map-action-row {{
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  margin-top: 10px;
                }}
                .btn-action-red {{
                  background: #E23744;
                  color: #FFFFFF;
                  font-size: 11px;
                  font-weight: 700;
                  border-radius: 99px;
                  padding: 6px 14px;
                  border: none;
                  cursor: pointer;
                  display: inline-flex;
                  align-items: center;
                  gap: 4px;
                  text-decoration: none;
                }}
                .btn-action-red:hover {{ background: #FF3B4B; }}
                .btn-action-dark {{
                  background: #24242F;
                  border: 1px solid rgba(255, 255, 255, 0.12);
                  color: #94A3B8;
                  font-size: 11px;
                  font-weight: 600;
                  border-radius: 99px;
                  padding: 6px 14px;
                  border: none;
                  cursor: pointer;
                }}
                .btn-action-dark:hover {{ color: #FFFFFF; background: #2E2E3A; }}
              </style>
            </head>
            <body>
              <div class="split-container">
                <!-- Left: Cards Stream -->
                <div class="cards-stream" id="cardsStream"></div>

                <!-- Right: Interactive Styled Map Widget -->
                <div class="map-column" id="mapColumn">
                  <!-- Header Overlay -->
                  <div class="map-header-overlay">
                    <div class="map-tag-left">
                      <span class="tag-red-dot"></span>
                      <span id="mapCounter">Showing {len(recommendations)} Recommendations</span>
                    </div>
                    <div class="map-tag-right">📍 {loc_label}</div>
                  </div>

                  <!-- Zoom Tools -->
                  <div class="map-tools">
                    <button type="button" class="map-tool-btn" id="mapZoomIn" title="Zoom in">+</button>
                    <button type="button" class="map-tool-btn" id="mapZoomOut" title="Zoom out">&minus;</button>
                    <button type="button" class="map-tool-btn" id="mapRecenter" title="Recenter location">⌖</button>
                  </div>

                  <!-- SVG Dark Map Canvas -->
                  <div class="map-canvas-wrap" id="mapCanvasWrap">
                    <svg id="mapSvg" viewBox="0 0 800 900" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="roadGlow" x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stop-color="#22222E" />
                          <stop offset="100%" stop-color="#2E2E3E" />
                        </linearGradient>
                        <filter id="glowFilter">
                          <feGaussianBlur stdDeviation="3" result="blur" />
                          <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                      </defs>

                      <!-- Dark Ground -->
                      <rect width="800" height="900" fill="#0C0D11" />

                      <!-- Regional Park -->
                      <path d="M 520,380 Q 640,340 760,420 L 800,560 L 580,580 Z" fill="#101815" stroke="#14261F" stroke-width="1.5" />
                      <text x="630" y="460" fill="#2E4C3E" font-size="11" font-weight="800" letter-spacing="1">REGIONAL PARK</text>

                      <!-- Neighborhood Labels -->
                      <text x="60" y="740" fill="#2E2E3A" font-size="15" font-weight="900" letter-spacing="2">KORAMANGALA</text>
                      <text x="440" y="160" fill="#2E2E3A" font-size="15" font-weight="900" letter-spacing="2">INDIRANAGAR</text>
                      <text x="120" y="240" fill="#2E2E3A" font-size="15" font-weight="900" letter-spacing="2">{loc_label.upper()}</text>

                      <!-- Secondary Roads Grid -->
                      <g stroke="url(#roadGlow)" stroke-width="2" stroke-linecap="round" opacity="0.6">
                        <line x1="40" y1="120" x2="760" y2="120" />
                        <line x1="40" y1="280" x2="760" y2="280" />
                        <line x1="40" y1="440" x2="760" y2="440" />
                        <line x1="40" y1="620" x2="760" y2="620" />
                        <line x1="40" y1="780" x2="760" y2="780" />
                        <line x1="160" y1="40" x2="160" y2="860" />
                        <line x1="320" y1="40" x2="320" y2="860" />
                        <line x1="480" y1="40" x2="480" y2="860" />
                        <line x1="660" y1="40" x2="660" y2="860" />
                      </g>

                      <!-- Major Arteries -->
                      <g stroke="#3D2028" stroke-width="7" stroke-linecap="round" opacity="0.75">
                        <path d="M 60,820 C 220,680 380,500 520,240 S 720,100 780,80" fill="none" />
                        <path d="M 80,180 C 240,260 480,480 720,740" fill="none" />
                      </g>
                      <g stroke="#E23744" stroke-width="2" stroke-linecap="round" opacity="0.45" filter="url(#glowFilter)">
                        <path d="M 60,820 C 220,680 380,500 520,240 S 720,100 780,80" fill="none" />
                      </g>
                    </svg>

                    <!-- Dynamic Interactive HTML Pins -->
                    <div id="mapPinsLayer"></div>

                    <!-- Floating Focused Card on Map Bottom -->
                    <div class="map-focus-card" id="mapFocusCard">
                      <div class="map-focus-top">
                        <div>
                          <div class="focus-title">
                            <span id="focusRank" style="color:#E23744; font-weight:900">#1</span>
                            <span id="focusName">Restaurant</span>
                            <span class="focus-dist" id="focusDist">0.8 km</span>
                          </div>
                          <div class="focus-sub" id="focusSub">Cuisine • Location</div>
                        </div>
                        <div style="text-align:right">
                          <span class="rating-badge-green" id="focusRating">4.4 ★</span>
                          <div style="font-size:11px; color:#94A3B8; margin-top:2px" id="focusCost">₹480 for two</div>
                        </div>
                      </div>
                      <div class="focus-snippet" id="focusSnippet">"AI Recommendation quote"</div>
                      <div class="map-action-row">
                        <a id="btnDirections" class="btn-action-red" href="#" target="_blank">↗ Directions</a>
                        <button type="button" class="btn-action-dark" onclick="window.scrollTo({{top:0, behavior:'smooth'}})">↑ Top</button>
                      </div>
                    </div>

                  </div>
                </div>
              </div>

              <script>
                const recs = {recs_json_str};
                let selectedIdx = 0;
                let currentZoom = 1;

                const cardsStream = document.getElementById('cardsStream');
                const mapPinsLayer = document.getElementById('mapPinsLayer');
                const mapSvg = document.getElementById('mapSvg');

                function escapeHtml(str) {{
                  if (!str) return '';
                  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                }}

                function render() {{
                  cardsStream.innerHTML = '';
                  mapPinsLayer.innerHTML = '';

                  recs.forEach((item, idx) => {{
                    // 1. Build List Card
                    const card = document.createElement('div');
                    card.className = `rec-card ${{idx === selectedIdx ? 'selected' : ''}}`;
                    card.setAttribute('data-index', idx);
                    
                    let chipsHtml = '';
                    if (item.online_order && item.online_order.toLowerCase() === 'yes') chipsHtml += '<span class="tag-chip">🛵 Online Delivery</span>';
                    if (item.table_booking && item.table_booking.toLowerCase() === 'yes') chipsHtml += '<span class="tag-chip">📅 Table Booking</span>';
                    if (item.votes) chipsHtml += `<span class="tag-chip">🗳️ ${{item.votes.toLocaleString()}} votes</span>`;

                    card.innerHTML = `
                      <div class="card-top">
                        <div class="card-left-meta">
                          <div class="card-rank">#${{item.rank}}</div>
                          <div>
                            <span class="card-name">${{escapeHtml(item.name)}}</span>
                            ${{idx === selectedIdx ? '<span class="badge-map-link">↑ LINKED TO MAP</span>' : ''}}
                            <div class="card-subline">🍲 ${{escapeHtml(item.cuisine)}}</div>
                          </div>
                        </div>
                        <span class="rating-badge-green">★ ${{Number(item.rating).toFixed(1)}}</span>
                      </div>
                      <div class="card-meta-row">
                        <span>Approx. Cost for Two: <span class="cost-highlight">₹${{item.estimated_cost.toLocaleString()}}</span></span>
                        ${{chipsHtml}}
                      </div>
                      <div class="card-reason-box">
                        <div class="reason-label">✦ WHY THIS MATCHES YOUR CRAVING</div>
                        <div class="reason-text">${{escapeHtml(item.explanation)}}</div>
                      </div>
                    `;

                    card.addEventListener('click', () => selectIndex(idx));
                    cardsStream.appendChild(card);

                    // 2. Build Map Pin
                    const xPos = item.coords.x;
                    const yPos = item.coords.y;

                    const pin = document.createElement('div');
                    pin.className = `map-pin ${{idx === selectedIdx ? 'active' : ''}}`;
                    pin.style.left = `${{xPos}}%`;
                    pin.style.top = `${{yPos}}%`;
                    pin.setAttribute('data-index', idx);
                    pin.innerHTML = `
                      <div class="pin-bubble">
                        <span class="pin-rank">#${{item.rank}}</span>
                        <span>${{escapeHtml(item.name)}}</span>
                        <span class="pin-rating">★ ${{Number(item.rating).toFixed(1)}}</span>
                      </div>
                      <div class="pin-pointer"></div>
                    `;

                    pin.addEventListener('click', (e) => {{
                      e.stopPropagation();
                      selectIndex(idx);
                    }});
                    mapPinsLayer.appendChild(pin);
                  }});

                  updateFocus(recs[selectedIdx]);
                }}

                function selectIndex(idx) {{
                  selectedIdx = idx;
                  const target = recs[idx];
                  if (!target) return;

                  // Update Cards
                  document.querySelectorAll('.rec-card').forEach((c, i) => {{
                    if (i === idx) {{
                      c.classList.add('selected');
                      if (!c.querySelector('.badge-map-link')) {{
                        const nameBox = c.querySelector('.card-name');
                        const b = document.createElement('span');
                        b.className = 'badge-map-link';
                        b.innerText = '↑ LINKED TO MAP';
                        nameBox.after(b);
                      }}
                      c.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                    }} else {{
                      c.classList.remove('selected');
                      const b = c.querySelector('.badge-map-link');
                      if (b) b.remove();
                    }}
                  }});

                  // Update Pins
                  document.querySelectorAll('.map-pin').forEach((p, i) => {{
                    if (i === idx) p.classList.add('active');
                    else p.classList.remove('active');
                  }});

                  updateFocus(target);
                }}

                function updateFocus(item) {{
                  if (!item) return;
                  document.getElementById('focusRank').innerText = `#${{item.rank}}`;
                  document.getElementById('focusName').innerText = item.name;
                  document.getElementById('focusDist').innerText = item.dist;
                  document.getElementById('focusSub').innerText = item.cuisine;
                  document.getElementById('focusRating').innerText = `${{Number(item.rating).toFixed(1)}} ★`;
                  document.getElementById('focusCost').innerText = `₹${{item.estimated_cost.toLocaleString()}} for two`;
                  document.getElementById('focusSnippet').innerText = `"${{item.explanation}}"`;
                  
                  const dirBtn = document.getElementById('btnDirections');
                  dirBtn.href = `https://www.google.com/maps/search/?api=1&query=${{encodeURIComponent(item.name + ' ' + item.cuisine)}}`;
                }}

                // Zoom Tools
                document.getElementById('mapZoomIn').addEventListener('click', () => {{
                  currentZoom = Math.min(1.8, currentZoom + 0.2);
                  mapSvg.style.transform = `scale(${{currentZoom}})`;
                  mapPinsLayer.style.transform = `scale(${{currentZoom}})`;
                }});
                document.getElementById('mapZoomOut').addEventListener('click', () => {{
                  currentZoom = Math.max(0.8, currentZoom - 0.2);
                  mapSvg.style.transform = `scale(${{currentZoom}})`;
                  mapPinsLayer.style.transform = `scale(${{currentZoom}})`;
                }});
                document.getElementById('mapRecenter').addEventListener('click', () => {{
                  currentZoom = 1;
                  mapSvg.style.transform = 'scale(1)';
                  mapPinsLayer.style.transform = 'scale(1)';
                }});

                render();
              </script>
            </body>
            </html>
            """

            st.markdown(
                f"#### 🍽️ Top Recommendations ({len(recommendations)} curated from {len(candidates)} candidates)"
            )
            components.html(split_view_html, height=660, scrolling=False)

else:
    st.info("👈 **Select your dining preferences in the sidebar and tap 'Get Recommendations' to start!**")
