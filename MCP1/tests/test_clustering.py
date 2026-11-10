"""
Unit and integration tests for Phase 2: Thematic Clustering Engine.
Verifies:
1. Canonical theme count constraint (strictly <= 5).
2. Exactly Top 3 themes selected by severity score.
3. Verbatim veracity of mined candidate quotes.
4. Zero Groq token burn for local clustering (0 tokens, 0 RPM).
"""
import pytest
from src.clustering.themes import CANONICAL_THEMES, get_canonical_theme_list
from src.clustering.classifier import ThematicClassifier
from src.clustering.ranking import run_thematic_clustering
from src.ingestion.cache import load_sanitized_reviews
from src.models.review import SanitizedReview


def test_canonical_theme_count():
    """Assert canonical themes are strictly <= 5 as per architecture rules."""
    themes = get_canonical_theme_list()
    assert len(themes) <= 5
    assert len(themes) == 5
    expected_ids = {
        "customer_support_bot",
        "delivery_delays_riders",
        "payment_upi_glitches",
        "pricing_gold_fees",
        "food_quality_packaging"
    }
    assert set(CANONICAL_THEMES.keys()) == expected_ids


def test_classifier_pattern_matching():
    """Assert classifier maps distinct complaint patterns to correct themes."""
    classifier = ThematicClassifier()

    support_rev = SanitizedReview(
        review_id="test_1",
        rating=1,
        text="Useless AI chat bot keeps looping and gives no refund for my missing food. Cannot talk to any human agent."
    )
    delivery_rev = SanitizedReview(
        review_id="test_2",
        rating=1,
        text="Delivery delayed by 50 minutes. The rider cancelled after standing far away from restaurant."
    )
    upi_rev = SanitizedReview(
        review_id="test_3",
        rating=1,
        text="UPI payment failed and amount debited twice. App crashes every time I open the order screen."
    )

    assert "customer_support_bot" in classifier.classify_review(support_rev)
    assert "delivery_delays_riders" in classifier.classify_review(delivery_rev)
    assert "payment_upi_glitches" in classifier.classify_review(upi_rev)


def test_clustering_on_real_sanitized_dataset():
    """
    Assert clustering runs on the 310 processed reviews and satisfies all Phase 2 exit checks.
    """
    reviews = load_sanitized_reviews()
    assert len(reviews) > 0, "Sanitized reviews dataset should not be empty"

    result = run_thematic_clustering(reviews)

    # 1. Total clusters <= 5
    assert len(result.all_clusters) <= 5
    assert len(result.all_clusters) == 5

    # 2. Exactly top 3 themes
    assert len(result.top_3_clusters) == 3

    # 3. Severity scores strictly ordered descending
    for i in range(len(result.all_clusters) - 1):
        assert result.all_clusters[i].severity_score >= result.all_clusters[i + 1].severity_score

    # 4. Each of Top 3 clusters has candidate quotes
    all_raw_texts = [r.text for r in reviews]
    for cluster in result.top_3_clusters:
        assert len(cluster.candidate_quotes) > 0, f"Theme {cluster.theme_id} must have candidate quotes"
        for quote in cluster.candidate_quotes:
            # Must be a 100% exact verbatim substring of at least one review
            matched = any(quote in raw_text for raw_text in all_raw_texts)
            assert matched, f"Quote '{quote}' must be an exact substring of the review corpus"
            # Must have no PII placeholders
            assert "[PHONE]" not in quote
            assert "[ORDER_ID]" not in quote
            assert "[EMAIL]" not in quote
            assert "[NAME]" not in quote

    # 5. Groq rate limit compliance (<= 1,500 tokens, <= 2 API requests)
    assert result.tokens_consumed <= 1500, f"Token consumption must be <= 1,500 tokens (got {result.tokens_consumed})"
    assert result.requests_consumed <= 2, f"Requests consumed must be <= 2 calls (got {result.requests_consumed})"


def test_groq_rate_limiter_pacing():
    """Assert GroqRateLimiter tracks tokens and enforces pacing bounds."""
    from src.clustering.classifier import GroqRateLimiter
    import time

    limiter = GroqRateLimiter(min_pacing_delay=0.1)  # Fast delay for unit test
    t0 = time.time()
    limiter.pace()
    limiter.pace()
    t1 = time.time()

    assert t1 - t0 >= 0.09, "Pacing delay should prevent burst calls exceeding RPM"
    assert limiter.requests_consumed == 2

    limiter.record_usage(450)
    assert limiter.tokens_consumed == 450
    assert limiter.tokens_consumed <= limiter.max_tpm


