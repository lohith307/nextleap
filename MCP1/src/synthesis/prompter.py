"""
Groq LLM Prompting and Pulse Synthesis Engine.
Uses llama-3.3-70b-versatile with strict rate-limit management (30 RPM, 12K TPM, 100K TPD).
Synthesizes Top 3 themes, 3 verbatim quotes, 3 concrete action ideas (<= 250 words).
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()
from src.models.theme import ClusteringResult, ThemeCluster
from src.models.pulse import WeeklyPulseReport, ThemePulseItem
from src.models.review import SanitizedReview
from src.synthesis.verifier import PulseVerifier
from src.synthesis.budget import enforce_word_budget, count_words

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an executive Chief Product Officer for Zomato synthesizing mobile app store feedback into a scannable Weekly Customer Pulse.

STRICT INVARIANTS:
1. Zero Quote Inventions: You MUST pick exactly one quote per theme directly from the provided 'candidate_quotes' array. Copy the quote verbatim without changing a single word or punctuation mark.
2. Concrete Action Ideas: For each of the top 3 themes, formulate exactly one realistic, high-impact product or engineering action idea (3 ideas total).
3. Word Budget: The final markdown text must be concise, crisp, and STRICTLY LESS THAN 220 words (ensuring <= 250 words total).
4. Output Format: Return a valid JSON object matching the requested schema.
"""


def build_compact_payload(clustering_result: ClusteringResult) -> Dict[str, Any]:
    """
    Constructs a lightweight (~600 token) JSON payload for Groq LLM,
    guaranteeing we never exceed the 12,000 Tokens/min limit.
    """
    top_3 = clustering_result.top_3_clusters[:3]
    themes_payload = []

    for rank, cluster in enumerate(top_3, start=1):
        themes_payload.append({
            "rank": rank,
            "theme_id": cluster.theme_id,
            "name": cluster.name,
            "percentage_share": cluster.percentage_share,
            "negative_count": cluster.negative_count,
            "avg_rating": cluster.average_star_rating,
            "candidate_quotes": cluster.candidate_quotes[:3]
        })

    return {
        "reporting_period": clustering_result.reporting_period,
        "total_reviews_analyzed": clustering_result.total_reviews_analyzed,
        "top_ranked_themes": themes_payload
    }


def synthesize_pulse_deterministic(
    clustering_result: ClusteringResult,
    all_reviews: List[SanitizedReview]
) -> WeeklyPulseReport:
    """
    Deterministic synthesis fallback engine used when running offline or without an active Groq API key.
    Produces an executive report satisfying all milestone criteria.
    """
    top_3 = clustering_result.top_3_clusters[:3]
    top_items: List[ThemePulseItem] = []
    selected_quotes: List[str] = []
    action_ideas: List[str] = []

    # Domain-grounded high-impact action templates for Zomato
    action_defaults = {
        "customer_support_bot": (
            "Escalation Trigger for Missing Items",
            "Automatically route chat sessions to human agents when visual photo evidence of wrong or missing food is uploaded."
        ),
        "delivery_delays_riders": (
            "Dynamic Rider Radius Cap",
            "Restrict dispatch assignments to riders within a 3km radius of restaurants during dinner peak hours (7–10 PM)."
        ),
        "payment_upi_glitches": (
            "Instant UPI Webhook Reconciliation",
            "Implement a 30-second server-side retry before declaring a payment failure to prevent double deductions."
        ),
        "pricing_gold_fees": (
            "Transparent Fee Breakdown",
            "Expose itemized platform and surge charges at checkout with clear Gold savings comparison."
        ),
        "food_quality_packaging": (
            "Merchant Spill-Proof Seal Audits",
            "Mandate tamper-evident packaging badges for top spilled categories and penalize recurring leakages."
        ),
    }

    summary_defaults = {
        "customer_support_bot": "Diners are trapped in automated chatbot loops with no escalation path to human support, leading to automated refund rejections on missing items.",
        "delivery_delays_riders": "Frequent 30–50 min uncommunicated delivery delays caused by assigning riders located far away from merchant hubs.",
        "payment_upi_glitches": "Payment deductions occurring without order creation, causing duplicate charges and multi-day refund reversal friction.",
        "pricing_gold_fees": "Customer friction regarding escalating platform fees and restrictive minimum order thresholds on Gold perks.",
        "food_quality_packaging": "Spilled gravies, broken safety seals, and cold food delivery leading to high refund dispute rates.",
    }

    seen_quotes = set()
    for cluster in top_3:
        quote = None
        for candidate in cluster.candidate_quotes:
            if candidate not in seen_quotes:
                quote = candidate
                seen_quotes.add(candidate)
                break
        if not quote:
            quote = cluster.candidate_quotes[0] if cluster.candidate_quotes else "Service experience was unsatisfactory and did not meet expectations."
            seen_quotes.add(quote)
        selected_quotes.append(quote)

        act_title, act_desc = action_defaults.get(
            cluster.theme_id,
            ("Process Optimization", "Review root operational causes with merchant and logistics partners.")
        )
        full_action = f"**{act_title}:** {act_desc}"
        action_ideas.append(full_action)

        summary = summary_defaults.get(cluster.theme_id, cluster.description)
        top_items.append(ThemePulseItem(
            theme_id=cluster.theme_id,
            theme_name=cluster.name,
            percentage_share=cluster.percentage_share,
            executive_summary=summary,
            selected_verbatim_quote=quote,
            action_idea=full_action
        ))

    # Construct clean markdown pulse
    md_lines = [
        f"# Zomato Customer Pulse — Week of {clustering_result.reporting_period}",
        "",
        "### Top Themes",
    ]
    for idx, item in enumerate(top_items, start=1):
        md_lines.append(f"{idx}. **{item.theme_name} ({item.percentage_share}% mentions):** {item.executive_summary}")

    md_lines.extend([
        "",
        "### What Users Are Saying",
    ])
    for q in selected_quotes:
        md_lines.append(f"- *\"{q}\"*")

    md_lines.extend([
        "",
        "### Action Ideas",
    ])
    for idx, act in enumerate(action_ideas, start=1):
        md_lines.append(f"{idx}. {act}")

    markdown_pulse = "\n".join(md_lines)
    # Enforce <= 250 words
    markdown_pulse = enforce_word_budget(markdown_pulse, max_words=250)
    w_count = count_words(markdown_pulse)

    # Verifier pass
    verifier = PulseVerifier(all_reviews)
    verified_quotes, quote_ok = verifier.verify_quotes(selected_quotes, top_3)
    pii_ok, pii_violations = verifier.verify_pii_clean(markdown_pulse)

    return WeeklyPulseReport(
        date_range=clustering_result.reporting_period,
        total_reviews_analyzed=clustering_result.total_reviews_analyzed,
        top_themes=top_items,
        verbatim_quotes=verified_quotes,
        action_ideas=action_ideas,
        weekly_pulse_markdown=markdown_pulse,
        word_count=w_count,
        quote_veracity_verified=quote_ok,
        pii_free_verified=pii_ok,
        tokens_consumed=0,
        model_used="deterministic-fallback"
    )


def synthesize_pulse(
    clustering_result: ClusteringResult,
    all_reviews: List[SanitizedReview],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> WeeklyPulseReport:
    """
    Synthesizes the executive weekly pulse using Groq LLM (llama-3.3-70b-versatile).
    Strictly stays within 12,000 TPM and 30 RPM limits.
    Falls back gracefully to deterministic synthesis if API key is not configured or offline.
    """
    key = api_key or os.getenv("GROQ_API_KEY", "").strip()
    model = model_name or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile").strip()

    if not key:
        logger.info("GROQ_API_KEY not configured. Using deterministic synthesis engine.")
        return synthesize_pulse_deterministic(clustering_result, all_reviews)

    try:
        from groq import Groq
        client = Groq(api_key=key)

        payload = build_compact_payload(clustering_result)
        user_message = (
            "Here is the clustered Zomato customer review distribution and candidate verbatim quotes:\n\n"
            f"{json.dumps(payload, indent=2)}\n\n"
            "Generate the executive Weekly Customer Voice Pulse in valid JSON matching the following structure:\n"
            "{\n"
            '  "top_themes": [\n'
            '    {\n'
            '      "theme_id": "...",\n'
            '      "theme_name": "...",\n'
            '      "percentage_share": 65.2,\n'
            '      "executive_summary": "...",\n'
            '      "selected_verbatim_quote": "...",\n'
            '      "action_idea": "**Title:** Description..."\n'
            '    }\n'
            '  ],\n'
            '  "weekly_pulse_markdown": "# Zomato Customer Pulse..."\n'
            "}"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=600
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        tokens_consumed = response.usage.total_tokens if hasattr(response, "usage") else 0

        # Parse generated themes
        top_items: List[ThemePulseItem] = []
        raw_quotes: List[str] = []
        action_ideas: List[str] = []

        for item in data.get("top_themes", []):
            theme_obj = ThemePulseItem(
                theme_id=item.get("theme_id", ""),
                theme_name=item.get("theme_name", ""),
                percentage_share=float(item.get("percentage_share", 0.0)),
                executive_summary=item.get("executive_summary", ""),
                selected_verbatim_quote=item.get("selected_verbatim_quote", ""),
                action_idea=item.get("action_idea", "")
            )
            top_items.append(theme_obj)
            raw_quotes.append(theme_obj.selected_verbatim_quote)
            action_ideas.append(theme_obj.action_idea)

        # Stage 3: Python Deterministic Guardrails
        verifier = PulseVerifier(all_reviews)
        verified_quotes, quote_ok = verifier.verify_quotes(raw_quotes, clustering_result.top_3_clusters)

        # Build or use returned markdown
        raw_md = data.get("weekly_pulse_markdown", "")
        if not raw_md:
            # Reconstruct from verified parts
            md_lines = [
                f"# Zomato Customer Pulse — Week of {clustering_result.reporting_period}",
                "",
                "### Top Themes",
            ]
            for idx, item in enumerate(top_items, start=1):
                md_lines.append(f"{idx}. **{item.theme_name} ({item.percentage_share}% mentions):** {item.executive_summary}")
            md_lines.extend(["", "### What Users Are Saying"])
            for q in verified_quotes:
                md_lines.append(f"- *\"{q}\"*")
            md_lines.extend(["", "### Action Ideas"])
            for idx, act in enumerate(action_ideas, start=1):
                md_lines.append(f"{idx}. {act}")
            raw_md = "\n".join(md_lines)

        # Enforce <= 250 words strictly
        final_markdown = enforce_word_budget(raw_md, max_words=250)
        w_count = count_words(final_markdown)
        pii_ok, _ = verifier.verify_pii_clean(final_markdown)

        return WeeklyPulseReport(
            date_range=clustering_result.reporting_period,
            total_reviews_analyzed=clustering_result.total_reviews_analyzed,
            top_themes=top_items,
            verbatim_quotes=verified_quotes,
            action_ideas=action_ideas,
            weekly_pulse_markdown=final_markdown,
            word_count=w_count,
            quote_veracity_verified=quote_ok,
            pii_free_verified=pii_ok,
            tokens_consumed=tokens_consumed,
            model_used=model
        )

    except Exception as e:
        logger.warning(f"Groq synthesis encountered error ({e}). Falling back to deterministic synthesis.")
        return synthesize_pulse_deterministic(clustering_result, all_reviews)
