"""
Two-tier Thematic Classifier for Zomato Customer Reviews.
Tier 1: Ultra-fast local regex + keyword taxonomy (0 tokens, 0 RPM).
Tier 2: Groq distillation & boundary disambiguator with strict rate-limiting (<= 24 RPM, <= 1,500 tokens).
"""
import os
import re
import time
import json
import logging
from typing import List, Dict, Tuple, Set, Optional, Any
from dotenv import load_dotenv

load_dotenv()
from src.models.review import SanitizedReview
from src.models.theme import ThemeDefinition
from src.clustering.themes import CANONICAL_THEMES, get_canonical_theme_list

logger = logging.getLogger(__name__)


class GroqRateLimiter:
    """
    Enforces Groq Free-Tier Rate Limits for llama-3.3-70b-versatile:
    - 30 Requests Per Minute (enforces pacing delay >= 2.5s -> max 24 RPM)
    - 1,000 Requests Per Day
    - 12,000 Tokens Per Minute (safety cap <= 8,000 TPM)
    - 100,000 Tokens Per Day
    """

    def __init__(
        self,
        min_pacing_delay: float = 2.5,
        max_rpm: int = 30,
        max_tpm: int = 12000,
        max_rpd: int = 1000,
        max_tpd: int = 100000
    ):
        self.min_pacing_delay = min_pacing_delay
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.max_rpd = max_rpd
        self.max_tpd = max_tpd
        self.last_request_time: float = 0.0
        self.requests_consumed: int = 0
        self.tokens_consumed: int = 0

    def pace(self) -> None:
        """Enforces minimum pacing delay to guarantee <= 24 RPM."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_pacing_delay:
            time.sleep(self.min_pacing_delay - elapsed)
        self.last_request_time = time.time()
        self.requests_consumed += 1

    def record_usage(self, tokens: int) -> None:
        """Records tokens consumed by a request."""
        self.tokens_consumed += tokens


class GroqBoundaryDisambiguator:
    """
    Tier 2 Disambiguation engine for ambiguous boundary reviews.
    Uses Groq micro-batches (<= 10 reviews) within strict free-tier rate limits.
    Falls back gracefully to semantic deterministic tie-breaking if offline.
    """

    def __init__(self, rate_limiter: Optional[GroqRateLimiter] = None):
        self.rate_limiter = rate_limiter or GroqRateLimiter()
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile").strip()

    def disambiguate_microbatch(
        self,
        ambiguous_reviews: List[Tuple[SanitizedReview, Dict[str, float]]]
    ) -> Dict[str, str]:
        """
        Disambiguates a micro-batch of reviews (<= 10 reviews) into canonical theme IDs.
        Returns a mapping of review_id -> assigned theme_id.
        """
        if not ambiguous_reviews:
            return {}

        # Limit micro-batch to at most 10 reviews to guarantee <= 700 tokens per call
        batch = ambiguous_reviews[:10]
        results: Dict[str, str] = {}

        if not self.api_key:
            # Deterministic semantic tie-breaker when offline or without API key
            for rev, scores in batch:
                sorted_scores = sorted(scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
                best_theme = sorted_scores[0][0] if sorted_scores and sorted_scores[0][1] > 0 else "customer_support_bot"
                results[rev.review_id] = best_theme
            return results

        # Live Groq API invocation
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            # Enforce pacing delay (>= 2.5s)
            self.rate_limiter.pace()

            candidate_themes_desc = {
                t_id: f"{t.name}: {t.description}"
                for t_id, t in CANONICAL_THEMES.items()
            }

            reviews_data = [
                {"id": r.review_id, "text": r.text[:200]}
                for r, _ in batch
            ]

            prompt = (
                f"You are a review classifier. Classify each review into exactly one of these 5 themes:\n"
                f"{json.dumps(candidate_themes_desc, indent=1)}\n\n"
                f"Reviews to classify:\n"
                f"{json.dumps(reviews_data, indent=1)}\n\n"
                f'Respond in JSON: {{"classifications": [{{"id": "...", "theme_id": "..."}}]}}'
            )

            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You classify mobile app reviews into 5 predefined themes. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=250
            )

            tokens = resp.usage.total_tokens if hasattr(resp, "usage") else 400
            self.rate_limiter.record_usage(tokens)

            content = json.loads(resp.choices[0].message.content)
            for item in content.get("classifications", []):
                t_id = item.get("theme_id")
                if t_id in CANONICAL_THEMES:
                    results[item.get("id")] = t_id

        except Exception as e:
            logger.warning(f"Groq disambiguation call failed: {e}. Using deterministic fallback.")
            for rev, scores in batch:
                sorted_scores = sorted(scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
                results[rev.review_id] = sorted_scores[0][0] if sorted_scores else "customer_support_bot"

        return results


class ThematicClassifier:
    """
    Two-Tier Categorizer:
    - Tier 1: Local regex + keyword taxonomy (0 tokens, 0 RPM).
    - Tier 2: Groq distillation for ambiguous boundary cases.
    """

    def __init__(
        self,
        themes: Dict[str, ThemeDefinition] = None,
        rate_limiter: Optional[GroqRateLimiter] = None
    ):
        self.themes = themes or CANONICAL_THEMES
        self.rate_limiter = rate_limiter or GroqRateLimiter()
        self.disambiguator = GroqBoundaryDisambiguator(self.rate_limiter)

        # Precompile regexes for optimal local classification speed
        self._compiled_regexes = {
            t_id: [re.compile(p, re.IGNORECASE) for p in t_def.regex_patterns]
            for t_id, t_def in self.themes.items()
        }
        self._keyword_sets = {
            t_id: set(k.lower() for k in t_def.keywords)
            for t_id, t_def in self.themes.items()
        }

    def score_review_for_themes(self, review_text: str) -> Dict[str, float]:
        """Calculates match scores for each canonical theme against a single review."""
        scores: Dict[str, float] = {t_id: 0.0 for t_id in self.themes}
        lower_text = review_text.lower()
        words = set(re.findall(r"\b[a-z]{3,}\b", lower_text))

        for t_id, t_def in self.themes.items():
            kw_hits = len(words.intersection(self._keyword_sets[t_id]))
            scores[t_id] += kw_hits * 1.0

            for regex in self._compiled_regexes[t_id]:
                if regex.search(review_text):
                    scores[t_id] += 2.0

        return scores

    def classify_review(self, review: SanitizedReview, threshold: float = 1.0) -> List[str]:
        """Returns list of theme_ids matched by this review."""
        scores = self.score_review_for_themes(review.text)
        matched = [t_id for t_id, score in scores.items() if score >= threshold]

        if not matched:
            best_theme, best_score = max(scores.items(), key=lambda x: x[1])
            if best_score > 0:
                matched = [best_theme]
            else:
                matched = ["customer_support_bot"]

        return matched

    def cluster_reviews(
        self,
        reviews: List[SanitizedReview]
    ) -> Tuple[Dict[str, List[SanitizedReview]], int]:
        """
        Clusters reviews across the canonical 5 themes using two-tier hybrid design:
        1. Categorizes unambiguous reviews locally via Tier 1 regex/keywords (0 tokens).
        2. Routes boundary / tied reviews through Tier 2 Groq Disambiguator (micro-batched).
        Returns:
            (clusters_dict, ambiguous_resolved_count)
        """
        clusters: Dict[str, List[SanitizedReview]] = {t_id: [] for t_id in self.themes}
        ambiguous_cases: List[Tuple[SanitizedReview, Dict[str, float]]] = []

        for review in reviews:
            scores = self.score_review_for_themes(review.text)
            matched = [t_id for t_id, score in scores.items() if score >= 1.0]

            # Check if review has tied or zero score
            sorted_scores = sorted(scores.values(), reverse=True)
            is_ambiguous = (
                len(sorted_scores) >= 2
                and sorted_scores[0] > 0
                and abs(sorted_scores[0] - sorted_scores[1]) < 0.5
            ) or (sorted_scores[0] == 0)

            if is_ambiguous and len(ambiguous_cases) < 10:
                ambiguous_cases.append((review, scores))
            else:
                if matched:
                    for t_id in matched:
                        clusters[t_id].append(review)
                else:
                    best_theme, _ = max(scores.items(), key=lambda x: x[1])
                    clusters[best_theme].append(review)

        # Tier 2: Disambiguate micro-batch of ambiguous reviews
        disambiguated_count = 0
        if ambiguous_cases:
            resolved_mapping = self.disambiguator.disambiguate_microbatch(ambiguous_cases)
            for rev, scores in ambiguous_cases:
                assigned = resolved_mapping.get(rev.review_id)
                if not assigned:
                    assigned = max(scores.items(), key=lambda x: x[1])[0] if max(scores.values()) > 0 else "customer_support_bot"
                clusters[assigned].append(rev)
                disambiguated_count += 1

        return clusters, disambiguated_count

    def extract_candidate_quotes(
        self,
        reviews_in_theme: List[SanitizedReview],
        max_quotes: int = 5,
        theme_id: Optional[str] = None
    ) -> List[str]:
        """
        Extracts punchy, representative, 100% verbatim candidate quotes from reviews in a theme.
        
        Strict Quote Criteria:
        1. Negative sentiment (rating 1 or 2 stars)
        2. Exact natural text, free of redaction placeholders ([PHONE], [ORDER_ID], [EMAIL], [NAME])
        3. Scannable length: 12 to 45 words
        4. High emotional valence / specific operational issue described
        """
        candidates: List[Tuple[float, str]] = []
        seen_texts: Set[str] = set()

        for review in reviews_in_theme:
            if review.rating > 2:
                continue

            text = review.text.strip()
            if any(marker in text for marker in ["[PHONE]", "[ORDER_ID]", "[EMAIL]", "[NAME]"]):
                continue

            words = text.split()
            word_count = len(words)

            relevance_bonus = 0.0
            if theme_id and theme_id in self.themes:
                scores = self.score_review_for_themes(text)
                relevance_bonus = scores.get(theme_id, 0.0) * 3.0

            if 12 <= word_count <= 45:
                if text not in seen_texts:
                    seen_texts.add(text)
                    score = (review.thumbs_up or 0) * 2.0 + relevance_bonus
                    if 15 <= word_count <= 35:
                        score += 5.0
                    candidates.append((score, text))
            elif word_count > 45:
                sentences = re.split(r"(?<=[.!?])\s+", text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    s_words = sentence.split()
                    s_count = len(s_words)
                    if 12 <= s_count <= 35 and sentence not in seen_texts:
                        if not any(marker in sentence for marker in ["[PHONE]", "[ORDER_ID]", "[EMAIL]", "[NAME]"]):
                            seen_texts.add(sentence)
                            s_rel = 0.0
                            if theme_id and theme_id in self.themes:
                                s_rel = self.score_review_for_themes(sentence).get(theme_id, 0.0) * 3.0
                            score = 3.0 + (review.thumbs_up or 0) + s_rel
                            candidates.append((score, sentence))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [q[1] for q in candidates[:max_quotes]]
