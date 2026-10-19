"""LLM recommendation and ranking client with strict grounding and graceful fallback."""
import os
import json
import logging
import re
from typing import List, Optional, Tuple, Dict, Any
import requests
from dotenv import load_dotenv

from domain.models import Candidate, UserPreference, Recommendation, RecommendationResponse
from prompts.prompt_builder import PromptBuilder

load_dotenv()
logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    def rank_and_explain(
        self, pref: UserPreference, candidates: List[Candidate]
    ) -> Tuple[List[Recommendation], Optional[str]]:
        """
        Rank candidates and generate explanations.
        Attempts remote LLM if key is present; otherwise uses the grounded reasoning engine.
        Enforces strict grounding against candidate IDs.
        """
        if not candidates:
            return [], None

        candidate_map = {c.id: c for c in candidates}

        # Try OpenAI if configured
        if self.openai_api_key:
            try:
                res = self._call_openai(pref, candidates)
                if res:
                    return self._ground_and_format(res, candidate_map, pref)
            except Exception as e:
                logger.warning("OpenAI call failed (%s), falling back to grounded engine", e)

        # Try Gemini if configured
        if self.gemini_api_key:
            try:
                res = self._call_gemini(pref, candidates)
                if res:
                    return self._ground_and_format(res, candidate_map, pref)
            except Exception as e:
                logger.warning("Gemini call failed (%s), falling back to grounded engine", e)

        # Built-in Grounded AI Reasoning Engine
        return self._grounded_reasoning_engine(pref, candidates)

    def _call_openai(self, pref: UserPreference, candidates: List[Candidate]) -> Optional[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": PromptBuilder.SYSTEM_PROMPT},
                {"role": "user", "content": PromptBuilder.build_user_prompt(pref, candidates)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def _call_gemini(self, pref: UserPreference, candidates: List[Candidate]) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        prompt_text = f"{PromptBuilder.SYSTEM_PROMPT}\n\n{PromptBuilder.build_user_prompt(pref, candidates)}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.3},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    def _ground_and_format(
        self, llm_json: Dict[str, Any], candidate_map: Dict[str, Candidate], pref: Optional[UserPreference] = None
    ) -> Tuple[List[Recommendation], Optional[str]]:
        summary = llm_json.get("summary")
        raw_items = llm_json.get("ranked_results", [])

        recommendations: List[Recommendation] = []
        seen_ids = set()

        for idx, item in enumerate(raw_items, 1):
            rest_id = item.get("id")
            if not rest_id or rest_id not in candidate_map:
                # Discard hallucinations or unknown ids
                continue
            if rest_id in seen_ids:
                continue

            seen_ids.add(rest_id)
            cand = candidate_map[rest_id]
            explanation = item.get("explanation", "").strip()
            if not explanation:
                explanation = f"Matches your craving for {cand.cuisine} in {cand.location} with a solid rating of {cand.rating}."

            recommendations.append(
                Recommendation(
                    id=cand.id,
                    name=cand.name,
                    cuisine=cand.cuisine,
                    rating=cand.rating,
                    estimated_cost=cand.cost,
                    explanation=explanation,
                    rank=idx,
                )
            )

        if not recommendations:
            # Fallback if model returned no valid items
            return self._grounded_reasoning_engine(pref, list(candidate_map.values()))

        return recommendations, summary

    def _grounded_reasoning_engine(
        self, pref: Optional[UserPreference], candidates: List[Candidate]
    ) -> Tuple[List[Recommendation], Optional[str]]:
        """
        Deterministic, grounded AI reasoning engine.
        Ranks by alignment score and generates rich, contextual justifications.
        """
        scored = []
        for c in candidates:
            score = c.rating * 2.0
            score += min(c.votes / 2000.0, 3.0)

            if pref:
                if pref.location.lower() in c.location.lower():
                    score += 2.0
                cui_tokens = [t.strip().lower() for t in pref.cuisine.split(",") if t.strip()]
                if any(t in c.cuisine.lower() for t in cui_tokens):
                    score += 2.0
                if pref.additional_preferences:
                    add_lower = pref.additional_preferences.lower()
                    if ("family" in add_lower or "group" in add_lower) and c.rest_type and "Casual" in c.rest_type:
                        score += 1.5
                    if ("quick" in add_lower or "fast" in add_lower) and c.rest_type and "Quick" in c.rest_type:
                        score += 1.5
                    if ("booking" in add_lower or "reserve" in add_lower) and c.table_booking == "Yes":
                        score += 1.5

            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        recommendations = []
        cui_name = pref.cuisine if pref else "your requested cuisine"
        loc_name = pref.location if pref else "your preferred area"
        budget_name = pref.budget.value if pref else "budget"
        extras_name = pref.additional_preferences if (pref and pref.additional_preferences) else ""

        for rank, (_, c) in enumerate(scored, 1):
            reasons = []
            reasons.append(f"Premier destination for {c.cuisine} in {c.location}")
            reasons.append(f"outstanding {c.rating}★ rating from {c.votes:,} diners")
            reasons.append(f"fits your {budget_name} budget at approx ₹{int(c.cost)} for two")

            if extras_name:
                if c.table_booking == "Yes":
                    reasons.append("offers convenient table reservations")
                if c.online_order == "Yes":
                    reasons.append("supports online ordering")
                if c.rest_type:
                    reasons.append(f"ideal {c.rest_type.lower()} setting matching '{extras_name}'")

            explanation = (
                f"Ranked #{rank} because it is a {reasons[0]} with an {reasons[1]}. "
                f"It comfortably {reasons[2]}"
                + (f" and {reasons[3]}." if len(reasons) > 3 else ".")
            )

            recommendations.append(
                Recommendation(
                    id=c.id,
                    name=c.name,
                    cuisine=c.cuisine,
                    rating=c.rating,
                    estimated_cost=c.cost,
                    explanation=explanation,
                    rank=rank,
                )
            )

        top_names = [r.name for r in recommendations[:2]]
        summary = (
            f"Found {len(recommendations)} excellent restaurants for {cui_name} in {loc_name}. "
            f"Top picks include {', '.join(top_names)}, perfectly tailored to your {budget_name} budget and preferences."
        )

        return recommendations, summary
