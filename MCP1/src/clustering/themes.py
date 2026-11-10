"""
Canonical domain themes and taxonomy definitions for Zomato app reviews.
Strictly constrained to at most 5 operational themes.
"""
from typing import Dict, List
from src.models.theme import ThemeDefinition

CANONICAL_THEMES: Dict[str, ThemeDefinition] = {
    "customer_support_bot": ThemeDefinition(
        theme_id="customer_support_bot",
        name="Customer Support & Chatbot Looping",
        description="Frustration with automated AI chat assistants, inability to reach human agents, and denied refunds for incorrect or missing orders.",
        keywords=[
            "support", "customer care", "customer service", "chat bot", "chatbot", "bot",
            "assistant", "agent", "human", "representative", "helpdesk", "refund", "refunds",
            "money back", "loop", "looping", "useless bot", "automated", "helpline", "complaint"
        ],
        regex_patterns=[
            r"\b(?:chat\s*bot|bot|ai\s*assistant)\b",
            r"\b(?:customer\s*(?:care|service|support))\b",
            r"\b(?:refund|refunds|money\s*back|no\s*refund)\b",
            r"\b(?:no\s*human|talk\s*to\s*(?:human|agent)|cannot\s*reach)\b",
            r"\b(?:looping|circles|automated\s*reply|canned\s*response)\b",
        ]
    ),
    "delivery_delays_riders": ThemeDefinition(
        theme_id="delivery_delays_riders",
        name="Delivery Delays & Rider Operations",
        description="Delivery ETA overruns, rider tracking inaccuracy, far-distance rider dispatch, driver cancellations, and rude partner interactions.",
        keywords=[
            "delivery", "delayed", "delay", "late", "eta", "time", "hour", "hours", "minute",
            "minutes", "rider", "driver", "valet", "delivery boy", "delivery partner", "tracking",
            "location", "distance", "far", "waiting", "wait", "standing", "cancelled order"
        ],
        regex_patterns=[
            r"\b(?:delivery\s*(?:delay|delayed|partner|boy|valet|time|status))\b",
            r"\b(?:\d+\s*(?:mins?|minutes?|hours?|hrs?))\b",
            r"\b(?:late\s*delivery|took\s*\d+\s*(?:mins?|hours?))\b",
            r"\b(?:rider\s*(?:cancelled|refused|delayed|far|standing))\b",
            r"\b(?:tracking|live\s*location|wrong\s*location)\b",
        ]
    ),
    "payment_upi_glitches": ThemeDefinition(
        theme_id="payment_upi_glitches",
        name="App Stability & Payment/UPI Failures",
        description="Payment deduction without order placement, UPI gateway timeouts, double debit, app crashes, freezing, and infinite loading screens.",
        keywords=[
            "payment", "upi", "gpay", "phonepe", "paytm", "debit", "deducted", "transaction",
            "failed", "failure", "crash", "crashed", "crashes", "crashing", "freeze", "froze",
            "glitch", "bug", "stuck", "blank screen", "loading", "slow", "error", "server error"
        ],
        regex_patterns=[
            r"\b(?:payment\s*(?:failed|failure|issue|deducted|pending))\b",
            r"\b(?:upi|gpay|phonepe|paytm|netbanking)\b",
            r"\b(?:money\s*deducted|amount\s*debited|double\s*charge)\b",
            r"\b(?:app\s*(?:crash|crashed|crashes|freeze|freezing|not\s*working))\b",
            r"\b(?:white\s*screen|blank\s*screen|infinite\s*loading|stuck)\b",
        ]
    ),
    "pricing_gold_fees": ThemeDefinition(
        theme_id="pricing_gold_fees",
        name="Platform Pricing, Hidden Fees & Gold MOQ",
        description="Escalating platform fees, rain fees, surge pricing, coupon discrepancies, minimum order quantity rules, and diminished Zomato Gold perks.",
        keywords=[
            "price", "pricing", "costly", "expensive", "charge", "charges", "platform fee",
            "rain fee", "handling fee", "surge", "coupon", "discount", "offer", "promocode",
            "gold", "membership", "moq", "minimum order", "bill", "tax", "scam"
        ],
        regex_patterns=[
            r"\b(?:platform\s*fee|rain\s*fee|delivery\s*fee|extra\s*charges?)\b",
            r"\b(?:surge\s*pricing|handling\s*charge|hidden\s*charges?)\b",
            r"\b(?:zomato\s*gold|gold\s*(?:membership|benefits?|discount))\b",
            r"\b(?:minimum\s*order|moq|high\s*price|overpriced)\b",
            r"\b(?:coupon\s*(?:not\s*working|removed|invalid|scam))\b",
        ]
    ),
    "food_quality_packaging": ThemeDefinition(
        theme_id="food_quality_packaging",
        name="Food Quality, Packaging Spills & Broken Seals",
        description="Gravy spills, damaged container boxes, broken safety seals, cold/stale food, missing cutlery or dishes, and restaurant hygiene complaints.",
        keywords=[
            "food", "packaging", "packing", "package", "spill", "spilled", "spilt", "leak",
            "leaking", "broken", "seal", "cold", "stale", "quality", "taste", "smell", "rotten",
            "wrong item", "missing item", "portion", "hygiene", "spoiled", "damage"
        ],
        regex_patterns=[
            r"\b(?:spill|spilled|spilling|leak|leaked|leaking)\b",
            r"\b(?:packaging|container|box|seal\s*broken|poor\s*packing)\b",
            r"\b(?:cold\s*food|stale|rotten|tasteless|bad\s*quality|spoiled)\b",
            r"\b(?:wrong\s*item|missing\s*dish|missing\s*item|half\s*portion)\b",
        ]
    ),
}


def get_canonical_theme_list() -> List[ThemeDefinition]:
    """Returns the ordered list of canonical theme definitions (exactly 5 themes)."""
    return list(CANONICAL_THEMES.values())

