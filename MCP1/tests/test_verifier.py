"""
Unit tests for Phase 3: Pulse Synthesis, Verbatim Verifier, and Word Budget Enforcer.
Verifies:
1. 100% exact substring match enforcement (zero hallucination).
2. Deterministic replacement when quotes are altered.
3. Word count strictly <= 250 words.
4. 0% PII leakage guarantee.
"""
import pytest
from src.ingestion.cache import load_sanitized_reviews
from src.clustering.ranking import run_thematic_clustering
from src.synthesis.verifier import PulseVerifier, is_substring_in_corpus, normalize_quote_text
from src.synthesis.budget import count_words, enforce_word_budget
from src.synthesis.prompter import synthesize_pulse_deterministic, build_compact_payload
from src.models.review import SanitizedReview


def test_quote_veracity_exact_match():
    """Assert verbatim substring returns True and altered returns False."""
    reviews = [
        SanitizedReview(
            review_id="r1",
            rating=1,
            text="The delivery rider was 45 minutes late and the food was completely cold."
        )
    ]
    corpus_texts = [r.text for r in reviews]

    # Exact substring
    assert is_substring_in_corpus(
        "delivery rider was 45 minutes late",
        corpus_texts
    ) is True

    # Altered/hallucinated wording
    assert is_substring_in_corpus(
        "delivery driver was nearly an hour tardy",
        corpus_texts
    ) is False


def test_verifier_replaces_hallucinated_quote():
    """Assert verifier catches hallucinated quotes and substitutes verified candidate quotes."""
    reviews = load_sanitized_reviews()
    assert reviews is not None and len(reviews) > 0

    clustering_result = run_thematic_clustering(reviews)
    top_3 = clustering_result.top_3_clusters

    verifier = PulseVerifier(reviews)

    # Supply an invented/hallucinated quote
    fake_quotes = [
        "This is an invented quote that does not exist in any app review.",
        top_3[1].candidate_quotes[0],
        top_3[2].candidate_quotes[0]
    ]

    verified_quotes, all_passed = verifier.verify_quotes(fake_quotes, top_3)

    assert all_passed is False, "Verifier must detect that the first quote was fabricated"
    # The first quote should now be replaced by the cluster's genuine candidate quote
    assert verified_quotes[0] == top_3[0].candidate_quotes[0]
    # And it must now be an exact substring of the corpus
    assert is_substring_in_corpus(verified_quotes[0], [r.text for r in reviews]) is True


def test_word_budget_counter_and_enforcer():
    """Assert word counter strips markdown formatting and enforcer caps output at <= 250 words."""
    short_text = "# Zomato Pulse\n\n1. **Support (60%):** Great improvements needed.\n- *\"Disappointing.\"*"
    assert count_words(short_text) < 20

    # Create a long text exceeding 250 words
    long_theme_desc = " ".join(["excessive operational delay detail explaining edge cases"] * 45)
    over_budget_md = f"# Title\n\n### Top Themes\n1. **Delivery Delays:** {long_theme_desc}\n\n### Quotes\n- *\"Late food.\"*\n\n### Actions\n1. **Fix:** Do it."
    assert count_words(over_budget_md) > 250

    enforced_md = enforce_word_budget(over_budget_md, max_words=250)
    assert count_words(enforced_md) <= 250


def test_pii_scanner():
    """Assert PII scanner catches emails, phone numbers, and handles."""
    verifier = PulseVerifier([])

    clean_text = "# Zomato Pulse\nCustomer support chatbot is failing customers."
    is_clean, violations = verifier.verify_pii_clean(clean_text)
    assert is_clean is True
    assert len(violations) == 0

    dirty_text = "Contact support at customer@zomato.com or call +91 9876543210 regarding order ZOM-99281."
    is_clean, violations = verifier.verify_pii_clean(dirty_text)
    assert is_clean is False
    assert len(violations) >= 3


def test_end_to_end_synthesis_deliverables():
    """
    Assert full synthesis produces:
    1. Top 3 themes
    2. 3 verbatim user quotes (100% exact match in dataset)
    3. 3 concrete action ideas
    4. Word count strictly <= 250 words
    5. Zero PII
    """
    reviews = load_sanitized_reviews()
    assert reviews is not None and len(reviews) > 0

    clustering_result = run_thematic_clustering(reviews)
    report = synthesize_pulse_deterministic(clustering_result, reviews)

    # 1. Top 3 themes
    assert len(report.top_themes) == 3

    # 2. 3 verbatim user quotes
    assert len(report.verbatim_quotes) == 3
    corpus_texts = [r.text for r in reviews]
    for quote in report.verbatim_quotes:
        assert is_substring_in_corpus(quote, corpus_texts) is True, f"Quote '{quote}' must be in corpus"

    # 3. 3 concrete action ideas
    assert len(report.action_ideas) == 3

    # 4. Strictly <= 250 words
    assert report.word_count <= 250
    assert count_words(report.weekly_pulse_markdown) <= 250

    # 5. Zero PII
    assert report.pii_free_verified is True
    assert "@" not in report.weekly_pulse_markdown or "mentions" in report.weekly_pulse_markdown
