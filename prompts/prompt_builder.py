"""Prompt construction for LLM ranking and explanation."""
import json
from typing import List
from domain.models import UserPreference, Candidate


class PromptBuilder:
    SYSTEM_PROMPT = """You are an expert AI restaurant recommendation assistant inspired by Zomato.
Your task is to rank the provided candidate restaurants and generate a personalized, human-like explanation for why each one fits the user's preferences.

CRITICAL GROUNDING RULES:
1. ONLY recommend restaurants from the provided Candidate list. NEVER invent or hallucinate restaurants.
2. In your response, include each restaurant's exact "id" from the candidate list and write a clear, personalized "explanation" addressing the user's location, cuisine, budget, rating, and additional preferences.
3. Provide an optional brief overall "summary" (1-2 sentences) highlighting the curated selection.
4. Output MUST be valid JSON adhering strictly to this schema:
{
  "summary": "...",
  "ranked_results": [
    {
      "id": "<candidate_id>",
      "explanation": "..."
    }
  ]
}
"""

    @classmethod
    def build_user_prompt(cls, pref: UserPreference, candidates: List[Candidate]) -> str:
        candidates_data = [c.model_dump() for c in candidates]
        prompt = f"""### USER PREFERENCES
- Location: {pref.location}
- Desired Cuisine: {pref.cuisine}
- Budget: {pref.budget.value}
- Minimum Rating: {pref.min_rating}
- Additional Preferences: {pref.additional_preferences or "None"}

### CANDIDATE RESTAURANTS (Grounded Catalog Subset)
{json.dumps(candidates_data, indent=2)}

Please rank these candidate restaurants based on overall fit for the user's preferences, explain why each is recommended, and output the response in JSON format.
"""
        return prompt
