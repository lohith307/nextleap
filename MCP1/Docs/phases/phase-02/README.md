# Phase 2: Thematic Clustering Engine & Groq Rate-Guarded Architecture

## Overview
Phase 2 groups the 310 sanitized, English, emoji-free Zomato reviews (dating from Aug 15 – Nov 05, 2026) into at most 5 canonical domain themes, computes empirical Severity Scores, and extracts verbatim candidate quotes while strictly respecting Groq free-tier rate limits.

---

## 1. Canonical Domain Themes (Strictly $\le 5$)

| Theme ID | Theme Name | Description | Keywords & Regex Patterns |
|---|---|---|---|
| `customer_support_bot` | **Customer Support & Chatbot Looping** | AI bot loops, lack of human escalation, denied refunds | bot, chatbot, support, refund, loop, human |
| `delivery_delays_riders` | **Delivery Delays & Rider Operations** | Delivery ETA gaps, rider cancellations, tracking lag | delivery, delay, late, rider, tracking, eta |
| `payment_upi_glitches` | **App Stability & Payment/UPI Failures** | UPI double debit, failed order creation, app crashes | upi, payment, debited, failed, crash, freeze |
| `pricing_gold_fees` | **Platform Pricing, Hidden Fees & Gold MOQ** | Platform fee escalation, surge fees, Gold perks | platform fee, surge, gold, minimum order, bill |
| `food_quality_packaging` | **Food Quality, Packaging Spills & Broken Seals** | Gravy spills, broken seals, cold/stale food | spill, leak, cold food, bad quality, packaging |

---

## 2. Empirical Severity Ranking Results

The 5 themes are ranked using the formula:
$$\text{Severity Score} = N_{\text{negative}} \times (5.0 - \bar{R})$$
where $N_{\text{negative}}$ is the count of 1★ and 2★ reviews, and $\bar{R}$ is the average star rating.

### Execution Output (`python run_phase2.py`):
| Rank | Theme Name | Reviews | Share | Negative Count | Avg ★ | Severity Score | Status |
|---|---|---|---|---|---|---|---|
| **1** | **Customer Support & Chatbot Looping** | 184 | 59.4% | 174 | 1.19 | **662.9** | ★ **PRIMARY** |
| **2** | **Delivery Delays & Rider Operations** | 183 | 59.0% | 167 | 1.34 | **611.2** | ★ **PRIMARY** |
| **3** | **Food Quality, Packaging Spills & Broken Seals** | 140 | 45.2% | 128 | 1.34 | **468.5** | ★ **PRIMARY** |
| 4 | Platform Pricing, Hidden Fees & Gold MOQ | 81 | 26.1% | 76 | 1.25 | 285.0 | Secondary |
| 5 | App Stability & Payment/UPI Failures | 29 | 9.4% | 26 | 1.28 | 96.7 | Secondary |

---

## 3. Groq Free-Tier Rate-Limit Compliance

| Resource Limit | Free-Tier Allowance | Actual Phase 2 Consumption | Headroom Remaining |
|---|---|---|---|
| **Requests Per Minute (RPM)** | 30 | 0 requests (Tier 1 Local) / max 1 micro-batch | **100% (24+ RPM headroom)** |
| **Requests Per Day (RPD)** | 1,000 | $\le 1$ request | **99.9%** |
| **Tokens Per Minute (TPM)** | 12,000 | 0 tokens (Tier 1 Local) / max 700 tokens | **100% (11,300+ TPM headroom)** |
| **Tokens Per Day (TPD)** | 100,000 | $\le 700$ tokens | **99.3%** |

**Two-Tier Hybrid Design:**
- **Tier 1 (Local Python):** High-speed regex and keyword classification runs locally at **0 tokens / 0 RPM**.
- **Tier 2 (Groq LLM Rate Limiter):** For ambiguous boundary reviews, micro-batches of $\le 10$ reviews ($\le 700$ tokens/call) with a minimum 2.5s pacing delay ($\le 24$ RPM $\ll 30$ RPM limit).

---

## 4. Verification & Testing
Verified via `pytest tests/test_clustering.py`:
- `test_canonical_theme_count`: **PASSED** (strictly 5 themes).
- `test_classifier_pattern_matching`: **PASSED**.
- `test_clustering_on_real_sanitized_dataset`: **PASSED** (Top 3 primary themes identified, candidate quotes verified as exact substrings with 0 PII).
- `test_groq_rate_limiter_pacing`: **PASSED** (pacing delay $\ge 2.5$s and token tracking validated).

Artifacts generated:
- Distribution: [`Docs/phases/phase-02/theme_distribution.json`](file:///c:/Users/lohith%20k/MCP1/Docs/phases/phase-02/theme_distribution.json)
- Candidate Quotes: [`Docs/phases/phase-02/sample_reviews.json`](file:///c:/Users/lohith%20k/MCP1/Docs/phases/phase-02/sample_reviews.json)
