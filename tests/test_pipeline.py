"""Unit tests verifying domain models, filters, grounding, and recommendation API."""
import pytest
from pydantic import ValidationError

from domain.models import BudgetBand, UserPreference, Restaurant, Candidate, Recommendation
from ingestion.cleaner import clean_rating, clean_cost, clean_votes
from ingestion.repo import RestaurantRepo
from filters.budget_mapper import BudgetMapper
from filters.candidate_filter import CandidateFilterEngine
from llm.client import LLMClient


def test_cleaner_functions():
    assert clean_rating("4.1/5") == 4.1
    assert clean_rating("3.8") == 3.8
    assert clean_rating("NEW") is None
    assert clean_rating("-") is None

    assert clean_cost("800") == 800.0
    assert clean_cost("1,200") == 1200.0
    assert clean_cost(None) is None

    assert clean_votes("775") == 775
    assert clean_votes("1,240") == 1240


def test_user_preference_validation():
    # Valid preference
    pref = UserPreference(
        location="Banashankari",
        budget=BudgetBand.MEDIUM,
        cuisine="Italian",
        min_rating=3.8,
        additional_preferences="quiet atmosphere",
    )
    assert pref.location == "Banashankari"
    assert pref.budget == BudgetBand.MEDIUM

    # Blank location should fail
    with pytest.raises(ValidationError):
        UserPreference(location="  ", budget=BudgetBand.LOW, cuisine="Italian")

    # Invalid rating (> 5.0) should fail
    with pytest.raises(ValidationError):
        UserPreference(location="Delhi", budget=BudgetBand.LOW, cuisine="Italian", min_rating=5.5)


def test_budget_mapper():
    mapper = BudgetMapper(p33=400.0, p66=800.0)
    low_min, low_max = mapper.get_cost_range(BudgetBand.LOW)
    assert low_min == 0.0
    assert low_max > 400.0

    med_min, med_max = mapper.get_cost_range(BudgetBand.MEDIUM)
    assert med_min <= 400.0
    assert med_max >= 800.0

    high_min, high_max = mapper.get_cost_range(BudgetBand.HIGH)
    assert high_min >= 700.0


def test_candidate_filter_and_zero_matches():
    repo = RestaurantRepo()
    filter_engine = CandidateFilterEngine(repo)

    # 1. Normal query that matches seed data
    pref = UserPreference(
        location="Banashankari",
        budget=BudgetBand.MEDIUM,
        cuisine="North Indian",
        min_rating=3.5,
    )
    candidates, _ = filter_engine.extract_candidates(pref)
    assert len(candidates) > 0
    assert all("Banashankari" in c.location for c in candidates)
    assert all(c.rating >= 3.5 for c in candidates)

    # 2. City-wide aliases (Bengaluru, blr) should match across all areas
    blr_pref = UserPreference(
        location="Bengaluru",
        budget=BudgetBand.HIGH,
        cuisine="Italian",
        min_rating=4.0,
    )
    blr_candidates, _ = filter_engine.extract_candidates(blr_pref)
    assert len(blr_candidates) > 0

    # 3. Cuisine with extra whitespace
    spaced_pref = UserPreference(
        location="Indiranagar",
        budget=BudgetBand.HIGH,
        cuisine=" Italian ,  Continental ",
        min_rating=3.8,
    )
    spaced_candidates, _ = filter_engine.extract_candidates(spaced_pref)
    assert len(spaced_candidates) > 0

    # 4. Impossible query (should return 0 candidates)
    impossible_pref = UserPreference(
        location="NonExistentCity12345",
        budget=BudgetBand.LOW,
        cuisine="MartianFood",
        min_rating=4.9,
    )
    impossible_candidates, _ = filter_engine.extract_candidates(impossible_pref)
    assert len(impossible_candidates) == 0


def test_grounding_and_hallucination_prevention():
    client = LLMClient()
    repo = RestaurantRepo()
    filter_engine = CandidateFilterEngine(repo)

    pref = UserPreference(
        location="Koramangala",
        budget=BudgetBand.MEDIUM,
        cuisine="Cafe",
        min_rating=4.0,
    )
    candidates, _ = filter_engine.extract_candidates(pref)
    assert len(candidates) > 0

    candidate_map = {c.id: c for c in candidates}

    # Simulate an LLM payload with one real candidate and one hallucinated candidate
    fake_llm_json = {
        "summary": "Sample summary",
        "ranked_results": [
            {"id": candidates[0].id, "explanation": "Legitimate reason for top pick"},
            {"id": "hallucinated_ghost_id_999", "explanation": "Fake restaurant explanation"},
        ],
    }

    recs, summary = client._ground_and_format(fake_llm_json, candidate_map)

    # Verify hallucinated item was stripped
    assert len(recs) == 1
    assert recs[0].id == candidates[0].id
    assert recs[0].name == candidates[0].name
    assert recs[0].rating == candidates[0].rating
    assert recs[0].estimated_cost == candidates[0].cost
    assert recs[0].explanation == "Legitimate reason for top pick"
