"""
Unit tests for Phase 1 Sanitization & Normalization.
Verifies:
1. PII scrubbing (emails, phones, order IDs, handles, rider names).
2. Emoji removal (zero emojis remain in text).
3. Word count filtering (> 6 words required).
4. Language filtering (English only).
"""
import pytest
from src.models.review import RawReview
from src.ingestion.sanitizer import PIISanitizer


def test_sanitize_emails():
    raw = RawReview(
        review_id="test_01",
        rating=1,
        title="Bad experience",
        text="Contact me at customer.service@example.com or support@zomato.in immediately for refund issue!",
        author_name="John Doe"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "[EMAIL]" in sanitized.text
    assert "customer.service@example.com" not in sanitized.text
    assert "support@zomato.in" not in sanitized.text


def test_sanitize_phone_numbers():
    raw = RawReview(
        review_id="test_02",
        rating=1,
        title="Delivery call",
        text="Driver called from +91 9876543210 and also 9876543210 but never arrived at my address.",
        author_name="Jane Smith"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "[PHONE]" in sanitized.text
    assert "9876543210" not in sanitized.text


def test_sanitize_order_ids():
    raw = RawReview(
        review_id="test_03",
        rating=1,
        title="Wrong Order",
        text="Order #987214 was missing items and the ZOM-12345 tracking status was completely incorrect.",
        author_name="Anonymous"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "[ORDER_ID]" in sanitized.text
    assert "#987214" not in sanitized.text
    assert "ZOM-12345" not in sanitized.text


def test_sanitize_user_mentions():
    raw = RawReview(
        review_id="test_04",
        rating=2,
        title="Query",
        text="Hey @zomato_care please check why @support_team is not replying to queries on the app.",
        author_name="User123"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "[USER]" in sanitized.text
    assert "@zomato_care" not in sanitized.text


def test_sanitize_rider_names():
    raw = RawReview(
        review_id="test_05",
        rating=1,
        title="Rider issue",
        text="Delivery boy Ramesh was extremely rude and the rider Suresh drove away without handing over food.",
        author_name="Rahul K"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "Ramesh" not in sanitized.text
    assert "Suresh" not in sanitized.text
    assert "delivery partner" in sanitized.text


def test_emoji_removal():
    raw = RawReview(
        review_id="test_06",
        rating=1,
        title="Spill issue",
        text="The soup spilled everywhere 😡🤮 and ruined all other items in the delivery box! 📦",
        author_name="Kiran M"
    )
    sanitized = PIISanitizer.sanitize(raw)
    assert sanitized is not None
    assert "😡" not in sanitized.text
    assert "🤮" not in sanitized.text
    assert "📦" not in sanitized.text
    assert "The soup spilled everywhere" in sanitized.text


def test_short_reviews_dropped():
    # 6 words or less should be dropped
    short_reviews = [
        "good app",
        "nice food",
        "very bad experience",
        "worst service ever delivered late",  # exactly 6 words
        "ok",
        "super"
    ]
    for text in short_reviews:
        raw = RawReview(
            review_id="short_test",
            rating=1,
            text=text
        )
        assert PIISanitizer.sanitize(raw, min_words=6) is None

    # 7 words or more should be retained
    long_raw = RawReview(
        review_id="long_test",
        rating=1,
        text="Food was delivered one hour very late today"  # 8 words
    )
    assert PIISanitizer.sanitize(long_raw, min_words=6) is not None


def test_language_filtering():
    # Non-English reviews should be dropped
    hindi_devanagari = RawReview(
        review_id="lang_01",
        rating=1,
        text="खाना बहुत ही ज्यादा खराब था और डिलीवरी भी लेट थी बिल्कुल बेकार"
    )
    assert PIISanitizer.sanitize(hindi_devanagari) is None

    hinglish = RawReview(
        review_id="lang_02",
        rating=1,
        text="bhai ye app bilkul bakwas hai koi bhi install mat karna khana bekar hai"
    )
    assert PIISanitizer.sanitize(hinglish) is None

    # English should be kept
    english = RawReview(
        review_id="lang_03",
        rating=1,
        text="The order arrived forty minutes late and the food was completely cold and ruined."
    )
    assert PIISanitizer.sanitize(english) is not None
