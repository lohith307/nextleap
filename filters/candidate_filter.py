"""Integration filter engine translating UserPreference to grounded Candidate payloads."""
from typing import List, Tuple
from domain.models import UserPreference, Candidate
from ingestion.repo import RestaurantRepo
from filters.budget_mapper import BudgetMapper


class CandidateFilterEngine:
    def __init__(self, repo: RestaurantRepo):
        self.repo = repo
        self.budget_mapper = BudgetMapper(repo.p33_cost, repo.p66_cost)

    def extract_candidates(self, pref: UserPreference, limit: int = 15) -> Tuple[List[Candidate], bool]:
        """
        Filter catalog using structured preferences and return (candidates, is_relaxed).
        If strict constraints yield 0 results, gracefully relaxes rating/budget thresholds
        to provide relevant matching options rather than an empty response.
        """
        self.budget_mapper.update_percentiles(self.repo.p33_cost, self.repo.p66_cost)
        min_cost, max_cost = self.budget_mapper.get_cost_range(pref.budget)

        # 1. Strict filter
        candidates = self.repo.find_candidates(
            location=pref.location,
            cuisine=pref.cuisine,
            min_cost=min_cost,
            max_cost=max_cost,
            min_rating=pref.min_rating,
            limit=limit,
        )

        is_relaxed = False

        # 2. Relax rating threshold slightly if 0 matches
        if not candidates and pref.min_rating > 3.0:
            relaxed_rating = max(pref.min_rating - 0.5, 3.0)
            candidates = self.repo.find_candidates(
                location=pref.location,
                cuisine=pref.cuisine,
                min_cost=min_cost,
                max_cost=max_cost,
                min_rating=relaxed_rating,
                limit=limit,
            )
            if candidates:
                is_relaxed = True

        # 3. Relax budget if still 0 matches (keep location and cuisine)
        if not candidates:
            candidates = self.repo.find_candidates(
                location=pref.location,
                cuisine=pref.cuisine,
                min_cost=0.0,
                max_cost=100000.0,
                min_rating=3.0,
                limit=limit,
            )
            if candidates:
                is_relaxed = True

        # If user has extra preferences matching structured fields, rank those higher
        if pref.additional_preferences and candidates:
            extra_lower = pref.additional_preferences.lower()
            if "booking" in extra_lower or "reserve" in extra_lower:
                candidates.sort(key=lambda c: (1 if c.table_booking == "Yes" else 0, c.rating, c.votes), reverse=True)
            elif "delivery" in extra_lower or "online" in extra_lower:
                candidates.sort(key=lambda c: (1 if c.online_order == "Yes" else 0, c.rating, c.votes), reverse=True)

        return candidates, is_relaxed
