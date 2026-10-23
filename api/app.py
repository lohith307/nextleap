"""FastAPI backend service for Zomato AI Restaurant Recommender."""
import os
import logging
from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from domain.models import UserPreference, RecommendationResponse
from ingestion.repo import RestaurantRepo
from filters.candidate_filter import CandidateFilterEngine
from llm.client import LLMClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered Restaurant Recommendation System",
    description="Intelligently suggests restaurants based on user preferences using structured filters and LLM reasoning.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global repo and engines
repo = RestaurantRepo()
filter_engine = CandidateFilterEngine(repo)
llm_client = LLMClient()

UI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "total_restaurants": len(repo.restaurants),
        "cost_p33": repo.p33_cost,
        "cost_p66": repo.p66_cost,
        "llm_engine": (
            f"Groq ({llm_client.model})"
            if llm_client.groq_api_key
            else (
                "OpenAI"
                if llm_client.openai_api_key
                else ("Gemini" if llm_client.gemini_api_key else "Grounded Reasoning Engine")
            )
        ),
    }


@app.get("/api/locations", response_model=List[str])
def get_locations():
    return repo.get_locations()


@app.get("/api/cuisines", response_model=List[str])
def get_cuisines():
    return repo.get_cuisines()


@app.post("/api/recommend", response_model=RecommendationResponse)
def get_recommendations(pref: UserPreference):
    """
    Retrieval-plus-reasoning pipeline:
    1. Filter catalog using structured preferences into grounded candidate list.
    2. If no candidates, return graceful empty state without calling LLM.
    3. Pass candidates and preferences to LLM for ranking, explanations, and summary.
    4. Return verified, catalog-grounded recommendations.
    """
    logger.info("Received recommendation request: %s", pref.model_dump())

    # Step 1: Filter candidates (with graceful relaxation if needed)
    candidates, is_relaxed = filter_engine.extract_candidates(pref, limit=15)
    logger.info("Found %d candidates (is_relaxed=%s)", len(candidates), is_relaxed)

    # Step 2: Zero match guard
    if not candidates:
        return RecommendationResponse(
            recommendations=[],
            summary=None,
            message=(
                f"No restaurants found matching '{pref.cuisine}' in '{pref.location}'. "
                f"Try choosing a broader location (e.g. Bangalore, Indiranagar, Koramangala) or exploring another cuisine."
            ),
            candidate_count=0,
        )

    # Step 3: LLM ranking and explanation
    recommendations, summary = llm_client.rank_and_explain(pref, candidates)

    info_message = None
    if is_relaxed:
        info_message = (
            f"Expanded search: We broadened the rating or budget threshold slightly to find you the best "
            f"{len(recommendations)} available matches for {pref.cuisine} in {pref.location}."
        )

    return RecommendationResponse(
        recommendations=recommendations,
        summary=summary,
        message=info_message,
        candidate_count=len(candidates),
    )


# Serve frontend UI
if os.path.exists(UI_DIR):
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

    @app.get("/")
    def serve_ui():
        index_file = os.path.join(UI_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "UI under development"}
