"""
PII Sanitizer & Review Normalizer for mobile store reviews.
1. Scrubs reviewer names, handles, phone numbers, email addresses, order IDs, URLs.
2. Strips all emojis and pictographic symbols.
3. Enforces language filter: retains ONLY English reviews.
4. Enforces length filter: retains ONLY reviews with MORE THAN 6 words.
"""
import re
from typing import Optional, List
import regex
from langdetect import detect, DetectorFactory
from src.models.review import RawReview, SanitizedReview

# Seed detector for deterministic language classification
DetectorFactory.seed = 0


class PIISanitizer:
    """
    Sanitizes raw reviews by stripping PII, removing emojis,
    filtering for English language, and enforcing word count > 6.
    """

    # Comprehensive Emoji & Pictographic regex (excluding bare digits/hashes)
    EMOJI_REGEX = regex.compile(
        r"[\p{Extended_Pictographic}\p{Emoji_Presentation}]"
    )

    # Email pattern (standard and obfuscated: user [at] domain dot com, user(at)domain.com, user at domain dot com)
    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9_.+-]+(?:\s*@\s*|\s*\[at\]\s*|\s*\(at\)\s*|\s+at\s+)[a-zA-Z0-9-]+(?:\s*\.\s*|\s*\(dot\)\s*|\s*\[dot\]\s*|\s+dot\s+)[a-zA-Z0-9-.]+"
        r"|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        re.IGNORECASE,
    )

    # Phone numbers (Indian mobile formats: +91, 0, 10 digits, spaced or hyphenated, 5-5 split)
    PHONE_REGEX = re.compile(
        r"(?:\+?91[\-\s]?)?[6-9]\d{9}|(?:\+?\d{1,3}[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}|\b[6-9]\d{4}[\-\s]\d{5}\b",
        re.IGNORECASE,
    )

    # Order IDs / Tracking / Transaction IDs (e.g., Order #12345, Order ID: 99812, #ZOM-12345, OD12345678)
    ORDER_ID_REGEX = re.compile(
        r"(?:order\s*(?:id|no|number|#)\s*[:#-]?\s*[A-Za-z0-9\-_]{3,20})"
        r"|(?:\b(?:ZOM|ORD|TXN|TRX|OD)[-_]?[A-Za-z0-9]{3,15}\b)"
        r"|(?:#\d{4,12}\b)",
        re.IGNORECASE,
    )

    # User mentions / handles (e.g., @john_doe, @zomato)
    MENTION_REGEX = re.compile(r"@[\w_.-]+", re.IGNORECASE)

    # URLs
    URL_REGEX = re.compile(
        r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)",
        re.IGNORECASE,
    )

    # Explicit reviewer / delivery boy mentions (e.g., "delivery boy Ramesh", "rider Suresh")
    RIDER_REGEX = re.compile(
        r"\b(?:delivery\s*(?:boy|partner|guy|person|rider)|rider|driver)\s+([A-Z][a-z]+)\b",
        re.IGNORECASE,
    )

    @classmethod
    def strip_emojis(cls, text: str) -> str:
        """Removes all emojis, symbols, and pictographs from text."""
        return cls.EMOJI_REGEX.sub("", text)

    @classmethod
    def count_words(cls, text: str) -> int:
        """Counts words using word boundary tokens."""
        words = re.findall(r"\b[a-zA-Z0-9_\'-]+\b", text)
        return len(words)

    @classmethod
    def is_english(cls, text: str) -> bool:
        """
        Determines whether the text is written in English.
        Requires high Latin character ratio and positive langdetect classification.
        """
        if not text or len(text.strip()) == 0:
            return False

        # Check Latin script ratio (Devanagari, Cyrillic, Arabic, Chinese, etc.)
        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return False

        latin_chars = [c for c in alpha_chars if c.isascii()]
        if (len(latin_chars) / len(alpha_chars)) < 0.7:
            return False

        try:
            detected_lang = detect(text)
            return detected_lang == "en"
        except Exception:
            return False

    @classmethod
    def sanitize_text(cls, text: Optional[str]) -> str:
        """
        Sanitizes text by stripping PII and removing all emojis.
        """
        if not text:
            return ""

        clean = text

        # 1. Remove all emojis
        clean = cls.strip_emojis(clean)

        # 2. Strip URLs
        clean = cls.URL_REGEX.sub("[URL]", clean)

        # 3. Strip Emails
        clean = cls.EMAIL_REGEX.sub("[EMAIL]", clean)

        # 4. Strip Phone numbers
        clean = cls.PHONE_REGEX.sub("[PHONE]", clean)

        # 5. Strip Order IDs
        clean = cls.ORDER_ID_REGEX.sub("[ORDER_ID]", clean)

        # 6. Strip User Handles / Mentions
        clean = cls.MENTION_REGEX.sub("[USER]", clean)

        # 7. Mask rider names: replace named rider with "delivery partner"
        clean = cls.RIDER_REGEX.sub("delivery partner", clean)

        # 8. Normalize redundant whitespace
        clean = re.sub(r"\s+", " ", clean).strip()

        return clean

    @classmethod
    def sanitize(cls, raw: RawReview, min_words: int = 6) -> Optional[SanitizedReview]:
        """
        Normalizes and sanitizes a RawReview.
        Returns None if:
        - Word count <= min_words (must be > 6 words)
        - Language is not English
        """
        sanitized_title = cls.sanitize_text(raw.title) if raw.title else None
        sanitized_text = cls.sanitize_text(raw.text)

        # 1. Check word count (> 6 words)
        word_count = cls.count_words(sanitized_text)
        if word_count <= min_words:
            return None

        # 2. Check English language
        if not cls.is_english(sanitized_text):
            return None

        return SanitizedReview(
            review_id=raw.review_id,
            rating=raw.rating,
            title=sanitized_title,
            text=sanitized_text,
            date=raw.date,
            platform=raw.platform,
            version=raw.version,
            thumbs_up=raw.thumbs_up or 0,
            cluster_id=None,
        )

    @classmethod
    def sanitize_batch(
        cls, raw_reviews: List[RawReview], min_words: int = 6
    ) -> List[SanitizedReview]:
        """
        Normalizes a batch of RawReview instances.
        Retains only sanitized, emoji-free, English reviews with > 6 words.
        """
        results: List[SanitizedReview] = []
        for raw in raw_reviews:
            sanitized = cls.sanitize(raw, min_words=min_words)
            if sanitized is not None:
                results.append(sanitized)
        return results
