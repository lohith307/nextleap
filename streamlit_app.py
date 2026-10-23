"""
Zomato AI Restaurant Recommendation System - Streamlit Web Application
Combines structured catalog retrieval with grounded LLM reasoning for personalized recommendations.
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
    page_title="Zomato AI - Restaurant Recommender",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Custom Styling (Zomato Red Theme & Clean Card Layout)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Global accents */
    :root {
        --zomato-red: #E23744;
        --zomato-dark: #1C1C1C;
        --zomato-light-gray: #F8F9FA;
        --zomato-green: #24963F;
    }
    
    /* Header typography */
    .hero-title {
        color: #E23744;
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #555555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    /* Engine status pill */
    .engine-pill {
        display: inline-block;
        padding: 4px 12px;
        background-color: #FEECEE;
        color: #E23744;
        border: 1px solid #FCD4D7;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    /* Summary Card */
    .summary-card {
        background: linear-gradient(135deg, #FFF5F5 0%, #FFFFFF 100%);
        border: 1px solid #FCD4D7;
        border-left: 5px solid #E23744;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 24px;
        box-shadow: 0 2px 6px rgba(226, 55, 68, 0.06);
    }
    .summary-title {
        color: #E23744;
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 6px;
    }
    .summary-body {
        color: #2D2D2D;
        font-size: 0.96rem;
        line-height: 1.5;
    }

    /* Restaurant Card */
    .restaurant-card {
        background-color: #FFFFFF;
        border: 1px solid #EBEBEB;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .restaurant-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
        border-color: #E23744;
    }

    /* Card Elements */
    .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
    }
    .restaurant-name {
        color: #1C1C1C;
        font-size: 1.35rem;
        font-weight: 700;
        margin: 0;
    }
    .rank-badge {
        background-color: #E23744;
        color: #FFFFFF;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 12px;
        font-size: 0.82rem;
    }
    .rating-badge {
        display: inline-flex;
        align-items: center;
        background-color: #24963F;
        color: #FFFFFF;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.9rem;
    }
    .rating-badge-high { background-color: #24963F; }
    .rating-badge-mid  { background-color: #E58E26; }
    .rating-badge-low  { background-color: #757575; }

    .cuisine-text {
        color: #555555;
        font-size: 0.95rem;
        margin-bottom: 6px;
    }
    .cost-text {
        color: #1C1C1C;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 12px;
    }
    .explanation-box {
        background-color: #F8F9FA;
        border-left: 3px solid #4A90E2;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 10px;
        font-size: 0.92rem;
        color: #333333;
        line-height: 1.45;
    }
    .tag-chip {
        display: inline-block;
        padding: 2px 8px;
        background-color: #F1F2F6;
        color: #475569;
        border-radius: 4px;
        font-size: 0.78rem;
        margin-right: 6px;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Cached Service Initialization (Single memory instance)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Loading Zomato catalog and initializing AI engine...")
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
# Sidebar: User Preference Inputs
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔍 **Search & Filters**")

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
        "🍳 **Cuisine**",
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
        "💰 **Budget Tier**",
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
        help="Filter and emphasize vegetarian or non-vegetarian options.",
    )

    # 6. Ambiance & Occasion
    ambiance_tags = st.multiselect(
        "✨ **Ambiance / Occasion**",
        options=[
            "Family Friendly",
            "Romantic / Date Night",
            "Quick Bite & Fast Service",
            "Rooftop & Outdoor Seating",
            "Cozy Cafe Vibes",
            "Late Night Food",
            "Live Music & Drinks",
        ],
        default=[],
        help="Select desired vibes or occasions for LLM personalization.",
    )

    # 7. Additional Free-text Notes
    additional_notes = st.text_input(
        "📝 **Custom Notes** (Optional)",
        value="",
        placeholder="e.g. authentic biryani, good desserts, quiet corner",
        help="Additional custom requirements passed to the AI reasoning engine.",
    )

    st.markdown("---")
    search_submitted = st.button("🚀 **Get AI Recommendations**", use_container_width=True, type="primary")

    # Sidebar Catalog Stats & Engine Info
    st.markdown("### 📊 **Catalog Metadata**")
    st.caption(f"**Verified Restaurants:** {len(repo.restaurants):,}")
    st.caption(f"**Distinct Locations:** {len(locations)}")
    st.caption(f"**Distinct Cuisines:** {len(cuisines)}")
    st.caption(f"**Active Reasoning:** {active_engine}")


# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------
st.markdown('<div class="hero-title">🍽️ Zomato AI Restaurant Recommender</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Combines structured catalog retrieval with LLM reasoning for verified, fact-grounded dining suggestions.</div>',
    unsafe_allow_html=True,
)
st.markdown(f'<span class="engine-pill">⚡ Powered by {active_engine}</span>', unsafe_allow_html=True)


# ---------------------------------------------------------
# Quick Preset Inspiration (1-Click)
# ---------------------------------------------------------
if not search_submitted and "preset_pref" not in st.session_state:
    st.markdown("##### 💡 Or try a popular discovery prompt:")
    col_p1, col_p2, col_p3 = st.columns(3)

    if col_p1.button("🍛 North Indian in Banashankari (Mid-Range)"):
        st.session_state["preset_pref"] = UserPreference(
            location="Banashankari",
            cuisine="North Indian",
            budget=BudgetBand.MEDIUM,
            min_rating=3.8,
            additional_preferences="family friendly, flavorful curry",
        )
        st.rerun()

    if col_p2.button("☕ Cafe Vibes in Bangalore (Budget)"):
        st.session_state["preset_pref"] = UserPreference(
            location="Bangalore",
            cuisine="Cafe",
            budget=BudgetBand.LOW,
            min_rating=3.5,
            additional_preferences="cozy ambiance, quick coffee and snacks",
        )
        st.rerun()

    if col_p3.button("🍕 Italian in Koramangala (Fine Dining)"):
        st.session_state["preset_pref"] = UserPreference(
            location="Bangalore",
            cuisine="Italian",
            budget=BudgetBand.HIGH,
            min_rating=4.0,
            additional_preferences="authentic pasta, premium date night",
        )
        st.rerun()


# ---------------------------------------------------------
# Execute Recommendation Logic
# ---------------------------------------------------------
pref_to_run = None
if search_submitted:
    # Combine dietary preference, ambiance tags, and custom notes
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
    with st.spinner("Finding best matching restaurants and generating AI recommendations..."):
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

            # Step 5: AI Contextual Summary Banner
            if summary:
                st.markdown(
                    f"""
                    <div class="summary-card">
                        <div class="summary-title">🤖 AI Recommendation Summary</div>
                        <div class="summary-body">{summary}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Step 6: Render Recommendations
            st.markdown(
                f"### 🍽️ Top Recommendations ({len(recommendations)} found out of {len(candidates)} verified candidates)"
            )

            for rec in recommendations:
                # Find candidate metadata for additional tags
                cand = next((c for c in candidates if c.id == rec.id), None)

                # Determine rating badge color
                if rec.rating >= 4.0:
                    badge_class = "rating-badge rating-badge-high"
                elif rec.rating >= 3.5:
                    badge_class = "rating-badge rating-badge-mid"
                else:
                    badge_class = "rating-badge rating-badge-low"

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

                st.markdown(
                    f"""
                    <div class="restaurant-card">
                        <div class="card-header-row">
                            <div>
                                <span class="rank-badge">#{rec.rank}</span>
                                <h3 class="restaurant-name" style="display:inline-block; margin-left: 8px;">{rec.name}</h3>
                            </div>
                            <div class="{badge_class}">
                                ★ {rec.rating:.1f}
                            </div>
                        </div>
                        <div class="cuisine-text">🍲 <strong>Cuisine:</strong> {rec.cuisine} &nbsp;•&nbsp; 📍 <strong>Location:</strong> {cand.location if cand else pref_to_run.location}</div>
                        <div class="cost-text">💰 <strong>Approx. Cost for two:</strong> ₹{int(rec.estimated_cost):,} &nbsp;<span class="tag-chip">{cost_tier_badge}</span> {chips_html}</div>
                        <div class="explanation-box">
                            💡 <strong>Why this was recommended:</strong> {rec.explanation}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
else:
    # Initial landing screen guidance
    st.info("👈 **Select your dining preferences from the sidebar and click 'Get AI Recommendations' to begin!**")
