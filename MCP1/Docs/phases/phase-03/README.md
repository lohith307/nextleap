# Phase 3: Pulse Synthesis & Veracity Guardrails

## Overview
Phase 3 synthesizes the weekly executive pulse document using Groq LLM (`llama-3.3-70b-versatile` / deterministic fallback), enforces 100% exact verbatim quote veracity, and guarantees strict compliance with the $\le 250$-word budget.

---

## 1. Executive Weekly Pulse Document (`Docs/generated_pulse.md`)

```markdown
# Zomato Customer Pulse — Week of 2026-08-15 to 2026-11-05

### Top Themes
1. **Customer Support & Chatbot Looping (59.0% mentions):** Diners are trapped in automated chatbot loops with no escalation path to human support, leading to automated refund rejections on missing items.
2. **Delivery Delays & Rider Operations (59.0% mentions):** Frequent 30–50 min uncommunicated delivery delays caused by assigning riders located far away from merchant hubs.
3. **Food Quality, Packaging Spills & Broken Seals (45.2% mentions):** Spilled gravies, broken safety seals, and cold food delivery leading to high refund dispute rates.

### What Users Are Saying
- *"They always try to convert to another currency with inconvenient rate, I many times ticked "remember for future payments" and still sets the wrong currency by default."*
- *"Then, check the time a few minutes later, you will notice that there is a discrepancy in the time that has passed since you placed the order and the actual delivery time."*
- *"They show you a certain time the food will reach in & then manipulate the time without you noticing."*

### Action Ideas
1. **Escalation Trigger for Missing Items:** Automatically route chat sessions to human agents when visual photo evidence of wrong or missing food is uploaded.
2. **Dynamic Rider Radius Cap:** Restrict dispatch assignments to riders within a 3km radius of restaurants during dinner peak hours (7–10 PM).
3. **Merchant Spill-Proof Seal Audits:** Mandate tamper-evident packaging badges for top spilled categories and penalize recurring leakages.
```

---

## 2. Hard Invariants & Guardrail Verification

1. **Word Budget:** 243 words (Strictly $\le 250$ words; readable in under 2 minutes).
2. **Quote Veracity:** 100% exact verbatim substring match from the review corpus. If any quote differs or paraphrases, the `PulseVerifier` deterministically substitutes the genuine candidate quote.
3. **PII Free:** 0% PII leakage (all names, phones, emails, order IDs scrubbed and verified clean).
4. **Deterministic Fallback:** Robust automatic fallback ensures zero outage even if the LLM provider experiences network or model availability issues.

---

## 3. Test Suite Summary
- Total Tests: **5 passed** (`tests/test_verifier.py`)
  - `test_quote_veracity_exact_match`
  - `test_verifier_replaces_hallucinated_quote`
  - `test_word_budget_counter_and_enforcer`
  - `test_pii_scanner`
  - `test_end_to_end_synthesis_deliverables`
- Dedicated Runner: [`run_phase3.py`](file:///c:/Users/lohith%20k/MCP1/run_phase3.py)

