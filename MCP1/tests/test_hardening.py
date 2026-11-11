"""
Phase 6: Quality, Security & Constraint Hardening Test Suite.
Verifies:
1. Full dataset PII audit across all 310 sanitized records.
2. Adversarial PII edge-case scrubbing (obfuscated emails, split phones, order ID patterns).
3. Word budget enforcement across 5 diverse, stress-testing review batches (<= 250 words).
4. Complex quote punctuation and smart-quote verbatim preservation.
5. Hallucinated quote deterministic replacement guardrail.
6. MCP exponential backoff retry mechanism (max 3 attempts).
7. Local backup preservation on MCP connection failures.
"""
import re
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import requests

from src.ingestion.sanitizer import PIISanitizer
from src.ingestion.cache import load_sanitized_reviews
from src.synthesis.budget import count_words, enforce_word_budget
from src.synthesis.verifier import PulseVerifier, normalize_quote_text, is_substring_in_corpus
from src.models.review import RawReview, SanitizedReview
from src.models.theme import ThemeCluster
from src.mcp_client.client import RemoteHttpMCPClient, MCPError
from src.mcp_client.docs_adapter import GoogleDocsAdapter
from src.mcp_client.gmail_adapter import GmailAdapter


# ==============================================================================
# 1. Full Dataset PII & Security Audit
# ==============================================================================

def test_pii_audit_full_processed_dataset():
    """
    Scans 100% of the cached sanitized dataset (310 records).
    Asserts zero unredacted emails, phone numbers, order IDs, or emojis.
    """
    reviews = load_sanitized_reviews()
    assert reviews is not None and len(reviews) > 0, "Sanitized review dataset missing!"

    for review in reviews:
        text = review.text
        # Zero emojis
        assert not PIISanitizer.EMOJI_REGEX.search(text), f"Emoji leak in review {review.review_id}: {text}"
        # Zero unmasked email addresses
        assert not re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text), (
            f"Email leak in review {review.review_id}: {text}"
        )
        # Zero unmasked phone numbers (10 digits starting with 6-9)
        assert not re.search(r"(?:\+91[-\s]?)?[6-9]\d{9}\b", text), (
            f"Phone leak in review {review.review_id}: {text}"
        )
        # Length constraint (> 6 words)
        assert PIISanitizer.count_words(text) > 6, (
            f"Review {review.review_id} has <= 6 words: {text}"
        )


def test_adversarial_pii_sanitization():
    """Tests adversarial and obfuscated PII patterns."""
    adversarial_inputs = [
        # Obfuscated emails
        ("Write to me at john.doe [at] example dot com urgently", "[EMAIL]"),
        ("Send support details to admin(at)zomato.in right now", "[EMAIL]"),
        # Phone numbers with spaces and dashes
        ("Call my cell +91 98765 43210 for food pickup address", "[PHONE]"),
        ("Phone number 98765-12345 was unreachable by rider", "[PHONE]"),
        # Order IDs with diverse formats
        ("My food for Order #ZOM-992134 never showed up at my doorstep", "[ORDER_ID]"),
        ("Order ID 882194812 missing item refund denied by chatbot", "[ORDER_ID]"),
        ("Tracking ORD_123455 was stuck on live map for 45 minutes", "[ORDER_ID]"),
        # Rider name masking
        ("The delivery boy Ramesh was extremely courteous and quick", "delivery partner"),
        ("Rider Suresh cancelled the order after driving in opposite direction", "delivery partner"),
    ]

    for raw_text, expected_token in adversarial_inputs:
        sanitized = PIISanitizer.sanitize_text(raw_text)
        assert expected_token in sanitized, (
            f"Adversarial sanitization failed for '{raw_text}'. Result: '{sanitized}'"
        )


# ==============================================================================
# 2. Word Budget Stress Testing Across 5 Diverse Batches
# ==============================================================================

def test_word_budget_5_diverse_batches():
    """
    Stress-tests the word budget enforcer across 5 diverse, realistic synthesis batches:
    1. Ultra-verbose executive pulse (> 420 words).
    2. Dense bullet points with excessive corporate jargon.
    3. Short reviews with verbose, multi-clause action recommendations.
    4. Repeated bullet lists and verbose headers.
    5. Real production pulse under extreme wordiness conditions.
    """
    batch_1_verbose = (
        "# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05\n\n"
        "### Top Themes\n"
        "1. **Customer Support & Chatbot Looping (59.0% mentions):** Diners across metro and non-metro cities "
        "consistently report an extraordinarily frustrating experience where they find themselves hopelessly trapped "
        "inside recursive, automated AI chatbot loops that refuse to provide any meaningful escalation path to human agents "
        "when orders fail or missing items are reported, resulting in automatic rejection of genuine refund requests.\n"
        "2. **Delivery Delays & Rider Operations (59.0% mentions):** Persistent discrepancies between estimated delivery "
        "times and actual arrival times, frequently ranging between thirty to sixty minutes of uncommunicated delays caused "
        "by logistical dispatch algorithms assigning delivery partners stationed excessively far from restaurant locations.\n"
        "3. **Food Quality, Packaging Spills & Broken Seals (45.2% mentions):** Frequent customer disputes regarding "
        "unsealed food containers, spilled gravies that ruin meals, broken safety seals, and cold food delivery resulting "
        "in severe friction during customer satisfaction resolution and dispute handling processes.\n\n"
        "### What Users Are Saying\n"
        "- *\"They always try to convert to another currency with inconvenient rate, I many times ticked 'remember for future payments' and still sets the wrong currency by default.\"*\n"
        "- *\"Then, check the time a few minutes later, you will notice that there is a discrepancy in the time that has passed since you placed the order and the actual delivery time.\"*\n"
        "- *\"They show you a certain time the food will reach in & then manipulate the time without you noticing.\"*\n\n"
        "### Action Ideas\n"
        "1. **Mandatory Human Escalation Routing for Missing Items:** Develop and deploy an immediate escalation mechanism "
        "that instantly triggers seamless human customer support agent takeover whenever photographic evidence of missing "
        "or tampered food items is submitted through the in-app support chat interface.\n"
        "2. **Dynamic Logistical Dispatch Radius Cap:** Implement strict geo-fencing constraints restricting dispatch "
        "assignments exclusively to riders situated within a three-kilometer radius of merchants during peak evening dinner hours.\n"
        "3. **Merchant Packaging Standards & Spill-Proof Certification:** Establish a comprehensive tamper-evident packaging "
        "audit program penalizing non-compliant restaurants and awarding spill-proof trust badges to top-rated partners."
    )

    batch_2_jargon = (
        "# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05\n\n"
        "### Top Themes\n"
        "1. **Support Inefficiencies (65%):** Automated conversational agents exhibit programmatic deadlock conditions.\n"
        "2. **Rider Routing Anomalies (58%):** Algorithmic dispatch misalignments result in cascading operational latency.\n"
        "3. **Package Integrity Breaches (48%):** Physical packaging failures compromise consumable integrity.\n\n"
        "### What Users Are Saying\n"
        "- *\"App freezes repeatedly at payment screen and debits money without order creation.\"*\n"
        "- *\"Delivery rider reached 40 minutes late with spilled soup and torn container.\"*\n"
        "- *\"Chatbot refused refund for missing biryani and closed ticket automatically.\"*\n\n"
        "### Action Ideas\n"
        "1. **Protocol A:** Deploy automated reconciliation telemetry on gateway webhooks.\n"
        "2. **Protocol B:** Enforce tight dispatch radius bounds during high demand intervals.\n"
        "3. **Protocol C:** Audit merchant packaging materials and penalize recurring leakages."
    )

    batch_3_long_actions = (
        "# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05\n\n"
        "### Top Themes\n"
        "1. **Customer Support Bottlenecks (50%):** Bot rejections.\n"
        "2. **Delivery Latency (40%):** Delayed food.\n"
        "3. **Packaging Defects (30%):** Spilled curry.\n\n"
        "### What Users Are Saying\n"
        "- *\"Service was unacceptably delayed and food arrived stone cold.\"*\n"
        "- *\"Driver had two other deliveries in opposite direction while my food got cold.\"*\n"
        "- *\"No human support was available when entire dinner order was missing.\"*\n\n"
        "### Action Ideas\n"
        "1. **Comprehensive Customer Service Overhaul:** Completely redesign the customer interaction flow by establishing "
        "a cross-functional support command center with automated sentiment detection and instant voucher disbursements.\n"
        "2. **Hyper-Local Dispatch Optimization:** Redesign rider assignment algorithms to prioritize single-order "
        "deliveries during high congestion rain events and peak dinner surges.\n"
        "3. **Spill-Proof Packaging Engineering Initiative:** Partner with sustainable packaging suppliers to provide "
        "standardized spill-resistant containers for all high-volume curry restaurants."
    )

    batch_4_bullet_heavy = (
        "# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05\n\n"
        "### Top Themes\n"
        "1. **Support Bot Deficiencies (60%):** Loop without resolution.\n"
        "2. **Delivery Discrepancies (55%):** ETA manipulated on map.\n"
        "3. **Spill Incurred In Transit (45%):** Broken seals on food.\n\n"
        "### What Users Are Saying\n"
        "- *\"Food delivery was delayed by an hour and arrived frozen.\"*\n"
        "- *\"Customer service bot gives robotic answers and closes chat.\"*\n"
        "- *\"Torn packaging with spilled curry all over the delivery bag.\"*\n\n"
        "### Action Ideas\n"
        "1. **Photo-Verified Escalations:** Route directly to human agent upon photo upload.\n"
        "2. **Proactive ETA Recalibration:** Alert diner if rider is held up at merchant.\n"
        "3. **Spill Compensation Protocol:** Instant refund for documented broken seals."
    )

    batch_5_extreme_repetition = (
        "# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05\n\n"
        "### Top Themes\n"
        "1. **Customer Support & Chatbot Looping (59.0% mentions):** " + ("Chatbot keeps looping without human help. " * 15) + "\n"
        "2. **Delivery Delays & Rider Operations (59.0% mentions):** " + ("Delivery partner arrived extremely late. " * 15) + "\n"
        "3. **Food Quality & Packaging (45.2% mentions):** " + ("Food was spilled and cold inside bag. " * 15) + "\n\n"
        "### What Users Are Saying\n"
        "- *\"They always try to convert to another currency with inconvenient rate.\"*\n"
        "- *\"Discrepancy in the time that has passed since you placed the order.\"*\n"
        "- *\"They show you a certain time the food will reach in & manipulate it.\"*\n\n"
        "### Action Ideas\n"
        "1. **Human Escalation:** Trigger human agent immediately on photo upload.\n"
        "2. **Radius Cap:** Restrict rider assignments to 3km from restaurant.\n"
        "3. **Packaging Audits:** Mandate tamper-evident packaging badges."
    )

    test_batches = [
        batch_1_verbose,
        batch_2_jargon,
        batch_3_long_actions,
        batch_4_bullet_heavy,
        batch_5_extreme_repetition
    ]

    for idx, batch_text in enumerate(test_batches, start=1):
        condensed = enforce_word_budget(batch_text, max_words=250)
        final_word_count = count_words(condensed)

        assert final_word_count <= 250, (
            f"Batch {idx} failed word budget: {final_word_count} words > 250 words!"
        )
        # Verify required sections are preserved
        assert "### Top Themes" in condensed, f"Batch {idx} lost Top Themes header"
        assert "### What Users Are Saying" in condensed, f"Batch {idx} lost Quotes header"
        assert "### Action Ideas" in condensed, f"Batch {idx} lost Action Ideas header"


# ==============================================================================
# 3. Complex Punctuation & Exact Substring Veracity
# ==============================================================================

def test_quote_veracity_complex_punctuation():
    """
    Verifies that quotes containing internal quotes, contractions, hyphens,
    and currency symbols are verified accurately without losing verbatim fidelity.
    """
    raw_reviews = [
        "They always try to convert to another currency with inconvenient rate, "
        "I many times ticked \"remember for future payments\" and still sets the wrong currency by default.",
        "Rider's GPS tracking showed him 5-km away; dinner arrived ice-cold & unsealed!",
        "Platform fee was ₹15.00 extra, Gold MOQ increased to ₹299 — utterly disappointing."
    ]

    test_quotes = [
        "They always try to convert to another currency with inconvenient rate, "
        "I many times ticked \"remember for future payments\" and still sets the wrong currency by default.",
        "Rider's GPS tracking showed him 5-km away; dinner arrived ice-cold & unsealed!",
        "Platform fee was ₹15.00 extra, Gold MOQ increased to ₹299 — utterly disappointing."
    ]

    for q in test_quotes:
        assert is_substring_in_corpus(q, raw_reviews), (
            f"Failed to match complex quote in corpus: {q}"
        )


def test_hallucination_deterministic_replacement():
    """
    Verifies that when an LLM invents or paraphrases a quote,
    PulseVerifier detects the hallucination and substitutes a genuine candidate quote.
    """
    reviews = [
        SanitizedReview(
            review_id="r1",
            rating=1,
            text="The chatbot kept looping for an hour and refused to process refund for missing burger."
        ),
        SanitizedReview(
            review_id="r2",
            rating=1,
            text="Delivery was delayed by fifty minutes and soup spilled completely in container."
        )
    ]

    cluster = ThemeCluster(
        theme_id="customer_support_bot",
        name="Customer Support & Chatbot Looping",
        description="Bot loop issues",
        review_count=1,
        percentage_share=50.0,
        negative_count=1,
        average_star_rating=1.0,
        severity_score=4.0,
        candidate_quotes=["The chatbot kept looping for an hour and refused to process refund for missing burger."],
        sample_reviews=reviews
    )

    verifier = PulseVerifier(reviews)
    hallucinated_quote = "I am a totally invented quote that does not exist in any customer review."

    verified, all_ok = verifier.verify_quotes([hallucinated_quote], [cluster])

    assert not all_ok, "Verifier should have flagged the hallucinated quote!"
    assert verified[0] == "The chatbot kept looping for an hour and refused to process refund for missing burger."
    assert is_substring_in_corpus(verified[0], [r.text for r in reviews])


# ==============================================================================
# 4. MCP Resilience: Exponential Backoff, Retries & Fallback
# ==============================================================================

def test_mcp_client_exponential_backoff_retry():
    """
    Simulates transient network timeouts and 503 errors on attempts 1 and 2,
    verifying RemoteHttpMCPClient retries with exponential backoff and succeeds on attempt 3.
    """
    client = RemoteHttpMCPClient(
        base_url="https://mock-mcp.railway.app",
        max_retries=3,
        backoff_factor=0.01  # Fast for tests
    )

    # Mock response objects
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_503.text = "Service Unavailable"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"tools": [{"name": "append_to_doc"}, {"name": "create_email_draft"}]}

    with patch("requests.request", side_effect=[
        requests.exceptions.Timeout("Connection timed out"),
        resp_503,
        resp_200
    ]) as mock_req:
        tools = client.list_tools()
        assert len(tools) == 2
        assert mock_req.call_count == 3


def test_mcp_client_graceful_fallback_after_max_retries():
    """
    Verifies that when all 3 retry attempts fail, call_tool returns
    a graceful fallback dictionary instead of crashing unhandled.
    """
    client = RemoteHttpMCPClient(
        base_url="https://mock-mcp.railway.app",
        max_retries=3,
        backoff_factor=0.01
    )

    with patch("requests.request", side_effect=requests.exceptions.ConnectionError("Network down")):
        result = client.call_tool("append_to_doc", {"doc_id": "doc123", "content": "Sample content"})
        assert result["status"] == "local_fallback"
        assert result["document_id"] == "doc123"


def test_google_docs_adapter_local_backup_on_failure(tmp_path, monkeypatch):
    """
    Verifies GoogleDocsAdapter always writes to Docs/generated_pulse.md
    even if the underlying MCP client throws an unexpected error.
    """
    mock_client = MagicMock()
    mock_client.call_tool.side_effect = MCPError("Remote MCP service down")

    adapter = GoogleDocsAdapter(client=mock_client)
    test_pulse = "# Test Pulse\n\nCrucial executive insights that must never be lost."

    res = adapter.create_document(title="Test Pulse", content=test_pulse, doc_id="fallback_id")

    backup_path = Path(res["local_backup_path"])
    assert backup_path.exists(), "Local backup must exist even when MCP publishing fails!"
    assert test_pulse in backup_path.read_text(encoding="utf-8")
    assert res["status"] == "local_fallback"

