"""
Zomato AI Restaurant Recommendation System - Streamlit Web Application
Combines structured catalog retrieval with grounded LLM reasoning for personalized recommendations.
Replicates the ultra-premium dark-mode design system from ui/index.html.
"""
import os
import streamlit as st
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

    /* Global Streamlit Reset to Dark Palette */
    .stApp {
        background-color: var(--bg) !important;
        font-family: var(--font) !important;
        color: var(--text-1) !important;
    }

    [data-testid="stSidebar"] {
        background-color: var(--bg-panel) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }

    [data-testid="stSidebar"] * {
        font-family: var(--font) !important;
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
        padding: 40px 20px 30px;
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
        font-size: 14.5px;
        color: var(--text-2);
        max-width: 600px;
        margin: 0 auto 18px;
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

    /* Recommendation Cards */
    .rec-card {
        background: var(--bg-panel);
        border: 1.5px solid var(--border-subtle);
        border-radius: var(--radius-lg);
        padding: 20px 22px;
        margin-bottom: 16px;
        transition: all 0.22s ease;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
    }
    .rec-card:hover {
        border-color: rgba(226, 55, 68, 0.45);
        background: var(--bg-card);
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5), 0 0 16px rgba(226, 55, 68, 0.15);
    }
    .card-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 14px;
        margin-bottom: 8px;
    }
    .card-left-meta {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .card-rank {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: rgba(226, 55, 68, 0.15);
        border: 1px solid rgba(226, 55, 68, 0.35);
        color: var(--brand);
        font-size: 13px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .card-name {
        font-size: 1.25rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.3px;
        margin: 0;
    }
    .rating-badge-green {
        background: var(--rating-green);
        color: #FFFFFF;
        font-size: 12.5px;
        font-weight: 800;
        padding: 3px 9px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
    }
    .card-subline {
        font-size: 13px;
        color: var(--text-2);
        margin-bottom: 10px;
    }
    .card-meta-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        font-size: 12.5px;
        color: var(--text-2);
        margin-bottom: 12px;
    }
    .cost-highlight {
        color: #FFFFFF;
        font-weight: 700;
    }
    .tag-chip {
        display: inline-block;
        padding: 3px 9px;
        background: #181820;
        border: 1px solid var(--border-subtle);
        border-radius: 99px;
        color: var(--text-2);
        font-size: 11px;
        font-weight: 600;
    }
    .card-reason-box {
        background: rgba(226, 55, 68, 0.06);
        border: 1px solid rgba(226, 55, 68, 0.16);
        border-left: 3px solid var(--brand);
        border-radius: var(--radius-md);
        padding: 12px 16px;
        margin-top: 10px;
    }
    .reason-label {
        font-size: 10.5px;
        font-weight: 800;
        color: var(--brand);
        text-transform: uppercase;
        letter-spacing: 0.7px;
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 5px;
    }
    .reason-text {
        font-size: 12.8px;
        color: #F1F5F9;
        line-height: 1.5;
    }

    /* Streamlit Widget Styles */
    .stButton > button {
        background: linear-gradient(135deg, #E23744 0%, #C02734 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 20px !important;
        font-size: 14px !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 4px 20px var(--brand-glow) !important;
        transition: all 0.22s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 26px rgba(226, 55, 68, 0.55) !important;
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
# Sidebar: User Preference Inputs
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔍 **Filter & Preferences**")

    # 1. Location
    locations = repo.get_locations()
    default_loc_idx = 0
    for target in ["Banashankari", "Bangalore", "Koramangala", "Indiranagar"]:
        if target in locations:
            default_loc_idx = locations.index(target)
            break

    selected_location = st.selectbox(
        "📍 **Location**",
        options=locations,
        index=default_loc_idx,
        help="Select a city or locality from the verified Zomato catalog.",
    )

    # 2. Cuisine
    cuisines = repo.get_cuisines()
    default_cui_idx = 0
    for target in ["North Indian", "South Indian", "Chinese", "Italian", "Cafe"]:
        if target in cuisines:
            default_cui_idx = cuisines.index(target)
            break

    selected_cuisine = st.selectbox(
        "🍳 **Target Cuisine**",
        options=cuisines,
        index=default_cui_idx,
        help="Target cuisine style to discover.",
    )

    # 3. Budget Tier
    budget_options = {
        f"Budget (Under ₹{int(repo.p33_cost)})": BudgetBand.LOW,
        f"Mid-range (₹{int(repo.p33_cost)} - ₹{int(repo.p66_cost)})": BudgetBand.MEDIUM,
        f"Fine Dining (Above ₹{int(repo.p66_cost)})": BudgetBand.HIGH,
    }
    budget_choice = st.radio(
        "💰 **Budget Band**",
        options=list(budget_options.keys()),
        index=1,
        help="Categorized based on catalog percentiles (p33 & p66).",
    )
    selected_budget = budget_options[budget_choice]

    # 4. Minimum Rating
    selected_min_rating = st.slider(
        "⭐ **Minimum Rating**",
        min_value=3.0,
        max_value=5.0,
        value=3.8,
        step=0.1,
        help="Filter candidates with at least this verified customer rating.",
    )

    # 5. Dietary Preference
    dietary_preference = st.selectbox(
        "🥗 **Dietary Preference**",
        options=["Any", "Vegetarian / Pure Veg", "Non-Veg Friendly"],
        index=0,
    )

    # 6. Ambiance & Occasion
    ambiance_tags = st.multiselect(
        "✨ **Ambiance / Vibe**",
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
        help="Select desired vibes for LLM personalization.",
    )

    # 7. Additional Free-text Notes
    additional_notes = st.text_input(
        "📝 **Custom Cravings / Notes**",
        value="",
        placeholder="e.g. authentic biryani, quiet corner, great desserts",
    )

    st.markdown("---")
    search_submitted = st.button("🚀 Find Recommendations", use_container_width=True)


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

            # Step 6: Render Recommendations Header
            st.markdown(
                f"#### 🍽️ Top Recommendations ({len(recommendations)} curated from {len(candidates)} candidates)"
            )

            # Step 7: Render Cards matching .rec-card from ui/index.html
            for rec in recommendations:
                cand = next((c for c in candidates if c.id == rec.id), None)

                # Cost tier formatting
                if rec.estimated_cost <= repo.p33_cost:
                    cost_tier_badge = "Budget (₹)"
                elif rec.estimated_cost <= repo.p66_cost:
                    cost_tier_badge = "Mid-range (₹₹)"
                else:
                    cost_tier_badge = "Fine Dining (₹₹₹)"

                # Additional catalog chips
                chips_html = ""
                if cand:
                    if cand.online_order and cand.online_order.lower() == "yes":
                        chips_html += '<span class="tag-chip">🛵 Online Delivery</span>'
                    if cand.table_booking and cand.table_booking.lower() == "yes":
                        chips_html += '<span class="tag-chip">📅 Table Booking</span>'
                    if cand.votes:
                        chips_html += f'<span class="tag-chip">🗳️ {cand.votes:,} votes</span>'

                cand_location = cand.location if cand else pref_to_run.location

                st.markdown(
                    f"""
                    <div class="rec-card">
                        <div class="card-top">
                            <div class="card-left-meta">
                                <div class="card-rank">#{rec.rank}</div>
                                <div>
                                    <h3 class="card-name">{rec.name}</h3>
                                    <div class="card-subline">🍲 {rec.cuisine} &nbsp;•&nbsp; 📍 {cand_location}</div>
                                </div>
                            </div>
                            <div>
                                <span class="rating-badge-green">★ {rec.rating:.1f}</span>
                            </div>
                        </div>
                        <div class="card-meta-row">
                            <span>Approx. Cost for Two: <span class="cost-highlight">₹{int(rec.estimated_cost):,}</span></span>
                            <span class="tag-chip">{cost_tier_badge}</span>
                            {chips_html}
                        </div>
                        <div class="card-reason-box">
                            <div class="reason-label">✦ WHY THIS MATCHES YOUR CRAVING</div>
                            <div class="reason-text">{rec.explanation}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
else:
    st.info("👈 **Select your dining preferences in the sidebar and tap 'Find Recommendations' to start!**")
