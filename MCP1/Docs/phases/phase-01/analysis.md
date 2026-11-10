# Phase 1 Data Analysis & Pre-LLM Synthesis Strategy

**Milestone:** Milestone 2 (Mobile Store Feedback Synthesis & MCP Integration)  
**Product:** Zomato Mobile App  
**Analyzed Dataset:** [`data/processed/sanitized_reviews.parquet`](file:///c:/Users/lohith%20k/MCP1/data/processed/sanitized_reviews.parquet)  
**Associated Scripts:** [`run_phase1.py`](file:///c:/Users/lohith%20k/MCP1/run_phase1.py) · [`src/ingestion/sanitizer.py`](file:///c:/Users/lohith%20k/MCP1/src/ingestion/sanitizer.py)

---

## 1. Executive Summary

During Phase 1, we ingested **652 public reviews** from the Google Play Store for Zomato (`com.application.zomato`) spanning a full 12-week window (August 15 to November 5, 2026). Following strict normalization filters (stripping emojis, removing non-English reviews, enforcing word count $> 6$, and scrubbing PII), we isolated a high-signal dataset of **310 in-depth reviews**.

This document analyzes the statistical distributions, key operational pain points, and outlines the **Pre-LLM Distillation Strategy** to ensure high-fidelity thematic clustering and verbatim quote generation without exceeding token budgets or suffering from LLM context dilution.

---

## 2. Dataset Properties & Distribution

### 2.1 High-Level Metrics

| Metric | Raw Ingested | Normalized Dataset | Delta / Reason |
| :--- | :--- | :--- | :--- |
| **Total Reviews** | 652 | **310** | Dropped 342 short phrases (e.g. "good", "nice", emojis) & non-English text |
| **Date Span** | Aug 15 – Nov 5, 2026 | **Aug 15 – Nov 5, 2026** | Maintained full ~12 weeks coverage |
| **Average Word Count** | 31.4 words | **60.6 words** | High-signal, descriptive feedback only |
| **Minimum Word Count** | 1 word | **7 words** | Strictly enforced $> 6$ words rule |
| **Emoji Presence** | 38.2% of reviews | **0.0%** | All Unicode pictographs permanently stripped |
| **PII Contamination** | Present in raw | **0.0%** | Zero names, handles, emails, phones, or order IDs |

### 2.2 Star Rating Distribution

```text
1★  [262 reviews]  84.5%  █████████████████████████████████
2★  [ 17 reviews]   5.5%  ██
3★  [ 10 reviews]   3.2%  █
4★  [  5 reviews]   1.6%  
5★  [ 16 reviews]   5.2%  ██
```

> **Key Observation:** **90.0% of the normalized dataset (279 / 310 reviews)** represents critical negative feedback (1★ and 2★). This provides a dense corpus of concrete user friction points rather than uninformative generic praise.

---

## 3. Thematic Clustering Signals in the Data

By analyzing keyword and semantic co-occurrences across the 279 negative reviews, we mapped user feedback onto the **5 canonical domain themes** defined in the Architecture:

```mermaid
pie title Negative Review Themes Breakdown (279 Reviews)
    "Customer Support & Bot Issues" : 70.3
    "Delivery Delays & Rider Operations" : 54.8
    "App, UPI & Payment Glitches" : 40.5
    "Platform Pricing & Gold MOQ" : 30.1
    "Food Quality & Spilled Packaging" : 27.6
```

### Detailed Theme Breakdown & Discovered Pain Points

#### Theme 1: Customer Support & Refund Bot Issues (70.3% of negative reviews)
- **Root Causes:**
  - Automated chatbots trapping users in endless predefined menu loops.
  - Complete inability to escalate tickets to a human representative.
  - Automated denial of refund claims for spoiled, contaminated, or missing food items.
- **Top Verbatim Quotes from Dataset:**
  - *"Worst support experience. The chatbot doesn't let you do anything. Please don't waste time on this app."*
  - *"Sent photos of stale smelling food but support closed the ticket saying restaurant denied claim."*
  - *"Their customer relations after service is the worst. Restaurants do fraud but Zomato bot closes chat."*

#### Theme 2: Delivery Delays & Rider Operations (54.8% of negative reviews)
- **Root Causes:**
  - Inaccurate initial ETAs jumping by 30–50 minutes after payment.
  - Dispatching riders located far away from the restaurant (5–8 km away).
  - Live GPS tracking stalling or freezing on the map while food turns cold.
- **Top Verbatim Quotes from Dataset:**
  - *"The worst experience I had to wait for 1 hour and 45 mins for an order for a restaurant that is literally 3 mins away."*
  - *"Order showed 30 mins ETA, arrived after 75 mins with no rider movement on map. Food was stone cold."*
  - *"For the past 1–2 weeks, whenever I place a food order, a delivery partner who is located quite far from the restaurant is assigned."*

#### Theme 3: App Stability, UPI & Payment Failures (40.5% of negative reviews)
- **Root Causes:**
  - UPI payment deductions without order confirmation (double-charge / pending webhook reversals).
  - Checkout screen crashing on Android/iOS updates, emptying cart contents.
  - Currency conversion glitches and forced payment mandates.
- **Top Verbatim Quotes from Dataset:**
  - *"Very disappointing experience. While placing an order, payment failed and I received no confirmation message or notification, so I assumed the order was cancelled..."*
  - *"The payment system is a scam. They always try to convert to another currency with inconvenient rate..."*
  - *"UPI failed three times, deducted amount twice, but cart never confirmed. Took 4 days for reversal."*

#### Theme 4: Platform Pricing, Hidden Fees & Gold MOQ (30.1% of negative reviews)
- **Root Causes:**
  - Introduction of a ₹199 Minimum Order Quantity (MOQ) for Zomato Gold free delivery.
  - Compounding fees: Platform Fee + Handling Fee + Weather Surge Fee + High Merchant Markup.
  - Coupons disappearing right before payment redirection.
- **Top Verbatim Quotes from Dataset:**
  - *"1. High moq (199rs) for free delivery with gold membership 2. Frequently items miss in my orders 3. No customer care number to contact."*
  - *"I have noticed that zomato has consistently increased prices on its item to the point that a 200 rs dish costs 350 on app."*

#### Theme 5: Food Packaging, Cold Food & Spills (27.6% of negative reviews)
- **Root Causes:**
  - Crushed containers and liquid leakage (dal/curry) ruining the bag.
  - Broken tamper-proof seals upon delivery.
  - Food arriving cold due to riders lacking insulated thermal bags.
- **Top Verbatim Quotes from Dataset:**
  - *"Container was crushed and dal leaked entirely inside the bag. No refund offered by support."*
  - *"The tamper seal tape was broken on the paper bag and 2 cold drinks were missing from my combo."*

---

## 4. Pre-LLM Synthesis Strategy: How to Prepare Data for Groq

Sending all 310 raw reviews (~20,000 words / ~26,000 tokens) directly to an LLM on every pipeline run introduces serious risks:
1. **Context Window Bloat & Latency:** High token volume slows response time and incurs high token overhead.
2. **Context Dilution ("Lost-in-the-Middle"):** Models struggle to pull exact verbatim quotes across hundreds of dense paragraphs, often inventing or paraphrasing wording (violating the 100% verbatim constraint).
3. **Loss of Quantitative Accuracy:** LLMs are notorious for approximating percentages ("many users said...") rather than reporting exact data counts.

### Recommended 3-Stage Pipeline: Filter $\rightarrow$ Cluster $\rightarrow$ Reason

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: DETERMINISTIC PRE-PROCESSING & BUCKETING (Python)                             │
│ - Assign each review to 1 of 5 themes via keyword-scoring heuristics                   │
│ - Calculate deterministic metrics: Exact count, share %, and average star rating       │
│ - Rank themes by Severity Score: Severity = Count * (5 - Avg_Rating)                   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Top 3 Themes & Selected Quote Candidates
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: GROQ LLM REASONING & SYNTHESIS (llama-3.3-70b-versatile)                      │
│ - Prompt contains ONLY:                                                                │
│     * Top 3 Themes with exact pre-computed percentages and review volumes              │
│     * 3-4 candidate verbatim quote snippets per theme (pre-extracted from dataset)     │
│     * Executive instruction to synthesize 3 concrete action ideas                      │
│ - Model outputs structured JSON in under 1 second (< 500 output tokens)               │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Synthesized Pulse DTO
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: DETERMINISTIC VERIFICATION & GUARDRAIL ENFORCEMENT (Python)                   │
│ - Substring Match: Asserts all 3 quotes exist verbatim in raw dataset                  │
│ - Word Counter: Asserts total pulse is <= 250 words                                    │
│ - PII Scanner: Final regex scan ensuring 0% PII leakage                                │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Deterministic Thematic Ranking Algorithm
To pick the **Top 3 themes** objectively without hallucination, we apply a deterministic **Severity Score**:

$$\text{Severity Score} = N_{\text{theme}} \times (5.0 - \bar{R}_{\text{theme}})$$

Where:
- $N_{\text{theme}}$ = Total number of negative reviews (1★ & 2★) matching the theme.
- $\bar{R}_{\text{theme}}$ = Average star rating of reviews in that cluster.

Based on our Phase 1 dataset, the ranking is:
1. **Customer Support & Chatbot Looping** (Severity: ~760) $\rightarrow$ **Top Theme #1**
2. **Delivery ETA Gaps & Rider Dispatch** (Severity: ~590) $\rightarrow$ **Top Theme #2**
3. **Payment Failures & UPI Reversal Lags** (Severity: ~440) $\rightarrow$ **Top Theme #3**

### Stage 2: What We Send to Groq LLM (Candidate Payload)
Instead of 25,000 tokens of raw reviews, we send a compact ~600 token prompt containing:
1. The Top 3 themes with their verified statistical weights.
2. A small pool of 3 pre-verified verbatim quote candidates for each theme.
3. Instruction to select the single most impactful verbatim quote per theme and generate a concrete product/engineering action item.

### Stage 3: Output Contract
The Groq LLM returns:
- **Top 3 Themes** (summarized in 1 sentence each with percentage share).
- **3 User Quotes** (selected verbatim from the candidate pool).
- **3 Action Ideas** (concrete, feasible, non-generic operational/engineering steps).
- Conforms strictly to the **$\le 250$ words** scannability limit.

---

## 5. Summary & Next Steps for Phase 2

1. **Phase 1 Data is Clean & Verified:** 310 English-only, emoji-free, $> 6$ word reviews ready in [`data/processed/sanitized_reviews.parquet`](file:///c:/Users/lohith%20k/MCP1/data/processed/sanitized_reviews.parquet).
2. **Clear Thematic Dominance:** Customer Support (70.3%), Delivery ETA (54.8%), and UPI Payments (40.5%) form the primary core signals.
3. **Execution Plan for Phase 2:** Implement `src/clustering/classifier.py` and `src/clustering/ranking.py` using this hybrid pre-filtering + Groq LLM strategy.

