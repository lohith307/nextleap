# Architecture: AI-Powered Restaurant Recommendation System

**Use case:** Zomato-inspired restaurant discovery  
**Derived from:** [`problemStatement.md`](../problemStatement.md) · [`problemStatement.txt`](problemStatement.txt)

This document describes the target architecture for a **retrieval-plus-reasoning** service: structured catalog filters find matching restaurants; an LLM ranks that shortlist and explains why each pick fits the user.

---

## 1. Architectural goal

The system is not a general chatbot and must not generate restaurants from model memory. It has two responsibilities:

| Layer | Question it answers |
|-------|---------------------|
| Structured data (ingest + filter) | What restaurants exist, and which ones match location, budget, cuisine, and rating? |
| LLM recommendation engine | Of those candidates, which should be recommended first, and why, in human language? |

Invariant: **filter first, then reason**. The LLM only sees a compact candidate set produced from the Hugging Face catalog.

---

## 2. High-level architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Presentation                             │
│  Preference form  →  Recommendation cards  →  Optional summary  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ UserPreference
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application / API                           │
│  Validate input → Orchestrate recommend() → Shape UI payload    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  Catalog store    │  │ Integration layer │  │ Recommendation    │
│  (preprocessed    │  │ Filter + budget   │  │ engine (LLM)      │
│   Zomato rows)    │  │ map + candidate   │  │ Rank, explain,    │
│                   │  │ payload           │  │ optional summary  │
└─────────▲─────────┘  └─────────▲─────────┘  └───────────────────┘
          │                      │
          │                      │ grounded rows only
┌─────────┴─────────┐            │
│ Data ingestion    │            │
│ Hugging Face load │────────────┘
│ clean, extract    │
└───────────────────┘
```

---

## 3. Logical layers

### 3.1 Data ingestion

**Purpose:** Load the official dataset once (or on a refresh schedule), clean it, and publish a queryable catalog.

| Concern | Design |
|---------|--------|
| Source | [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) |
| Load | Hugging Face `datasets` (or equivalent) into a tabular structure |
| Clean | Drop or impute missing name/location/rating/cost; normalize location and cuisine strings; parse cost into a numeric value |
| Extract | Keep at least name, location, cuisine, cost, rating |
| Optional keep | Address, votes, online order, table booking, and similar fields used for extra-preference ranking |
| Publish | In-memory DataFrame, local parquet/CSV cache, or a small DB — implementation choice; interface is a read-only restaurant catalog |

Ingestion is **offline relative to a single user request**. Request latency should not include a full dataset download on every search.

### 3.2 Catalog store

**Purpose:** Authoritative structured restaurant table used by the filter layer.

- Read-only at request time.
- Indexed or at least filterable by location, cuisine, rating, and cost.
- Never sent wholesale to the LLM.

### 3.3 Presentation (user input + output display)

**Input UI** collects:

- Location (e.g. Delhi, Bangalore)
- Budget: `low` | `medium` | `high`
- Cuisine (e.g. Italian, Chinese)
- Minimum rating (numeric)
- Additional preferences (free text: family-friendly, quick service, …)

**Output UI** shows top recommendations as cards/rows:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

Optional: a short summary of the overall set above or below the list.

### 3.4 Application / orchestration

**Purpose:** Single use-case entry point, e.g. `recommend(preferences) -> RecommendationResponse`.

Responsibilities:

1. Validate and normalize user input.
2. Call the integration layer to obtain candidates.
3. If zero candidates, return an empty/helpful UI state (do not ask the LLM to invent venues).
4. If candidates exist, call the recommendation engine with preferences + candidates.
5. Merge LLM ranking/explanations with catalog fields (name, cuisine, rating, cost stay catalog-sourced).
6. Return a display DTO matching the output contract.

### 3.5 Integration layer

**Purpose:** Translate user intent into a **grounded candidate payload** and an LLM prompt.

Steps:

1. Map budget band → cost range using catalog statistics or fixed thresholds.
2. Filter: location match, cuisine match, rating ≥ minimum, cost within budget band.
3. Cap candidate count (e.g. top N by rating/votes) so the prompt stays small.
4. Serialize candidates as structured JSON (only needed columns).
5. Build a ranking prompt: user preferences verbatim + candidates + instructions (rank, justify, stay on-list, fill display fields).

Extra preferences: if catalog columns support them (e.g. table booking), use them as extra filters or sort keys; otherwise pass them only as LLM ranking guidance.

### 3.6 Recommendation engine (LLM)

**Purpose:** Rank the candidate list and write human-like explanations.

The model must:

- Rank only restaurants present in the payload
- Explain why each pick fits location, budget, cuisine, rating, and extra preferences
- Optionally produce a one-paragraph summary of the set
- Return structured output the UI can parse (JSON preferred)

The engine does **not** own truth for name, cuisine, rating, or cost. Those fields are copied from the catalog row after the LLM returns IDs or names that match candidates.

---

## 4. End-to-end request flow

```text
User submits preferences
        │
        ▼
Validate UserPreference
        │
        ▼
Map budget  (low/medium/high → cost bounds)
        │
        ▼
Query catalog: location ∧ cuisine ∧ rating ∧ cost
        │
        ├── 0 rows → EmptyResult ("no matches; relax filters")
        │
        ▼
Select top N candidates (structured table/JSON)
        │
        ▼
Build prompt (preferences + candidates + ranking rules)
        │
        ▼
LLM: rank, explain, optional summary
        │
        ▼
Validate model output against candidate IDs/names
        │
        ├── unknown restaurant → drop or retry
        │
        ▼
Join explanations onto catalog fields
        │
        ▼
UI: top recommendations + optional summary
```

---

## 5. Component diagram (runtime)

```text
┌────────────┐     POST /recommend      ┌────────────────────┐
│  Web UI /  │ ───────────────────────► │  API / Orchestrator│
│  Form app  │ ◄─────────────────────── │                    │
└────────────┘   RecommendationResponse └─────────┬──────────┘
                                                  │
                           ┌──────────────────────┼──────────────────────┐
                           ▼                      ▼                      ▼
                  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
                  │ BudgetMapper   │    │ RestaurantRepo │    │ PromptBuilder  │
                  └────────────────┘    └───────┬────────┘    └────────┬───────┘
                                                │                      │
                                                ▼                      ▼
                                       ┌────────────────┐    ┌────────────────┐
                                       │ Catalog (HF    │    │ LLM client     │
                                       │ preprocessed)  │    │ (rank+explain) │
                                       └────────────────┘    └────────────────┘
```

Suggested module boundaries (language-agnostic):

| Module | Responsibility |
|--------|----------------|
| `ingestion` | Download, clean, extract, persist catalog |
| `domain` | `UserPreference`, `Restaurant`, `Candidate`, `Recommendation` types |
| `filters` | Budget mapping + catalog query |
| `prompts` | System/user prompt templates |
| `llm` | Provider client, JSON parse, retry |
| `api` / `ui` | HTTP or web form + result rendering |

---

## 6. Data contracts

### 6.1 Restaurant (catalog row)

| Field | Required | Notes |
|-------|----------|--------|
| `id` | recommended | Stable key for join after LLM ranking |
| `name` | yes | Display + identity |
| `location` | yes | Filter |
| `cuisine` | yes | Filter; may be multi-value |
| `cost` | yes | Numeric after parse; drives budget filter and display |
| `rating` | yes | Numeric; `rating >= min_rating` |
| extras | no | votes, address, online_order, table_booking, … |

### 6.2 UserPreference

| Field | Type | Notes |
|-------|------|--------|
| `location` | string | Normalized to catalog location tokens |
| `budget` | enum: low, medium, high | Never sent raw to cost column without mapping |
| `cuisine` | string | Substring or token match against cuisine list |
| `min_rating` | number | Inclusive lower bound |
| `additional_preferences` | string | Ranking/explanation signal |

### 6.3 Candidate payload (to LLM)

Subset of catalog rows: `id`, `name`, `location`, `cuisine`, `cost`, `rating`, plus any extra signals. Omit unused columns. Cap size (recommended **8–20** rows).

### 6.4 Recommendation (to UI)

| Field | Source of truth |
|-------|-----------------|
| Restaurant name | Catalog |
| Cuisine | Catalog |
| Rating | Catalog |
| Estimated cost | Catalog (optionally formatted as ₹ / band) |
| AI-generated explanation | LLM |
| Rank order | LLM (validated) |
| Optional summary | LLM |

---

## 7. Filtering and budget mapping

Budget is a **band**, cost is a **number**. Mapping must be explicit and consistent.

Example policy (tune from dataset percentiles after ingestion):

| User budget | Cost rule (illustrative) |
|-------------|---------------------------|
| low | cost ≤ P33 of catalog (or a fixed cap) |
| medium | P33 < cost ≤ P66 |
| high | cost > P66 |

Other filters:

- **Location:** case-insensitive equality or contains (city / locality as present in the dataset).
- **Cuisine:** case-insensitive token/substring match; a restaurant with multiple cuisines matches if any token matches.
- **Rating:** `rating >= min_rating`; drop rows with unknown rating unless a documented fallback exists.

If filters are too strict, the API should return **no matches** with a message to relax constraints — not hallucinated venues.

---

## 8. LLM integration design

### 8.1 Prompt roles

| Block | Content |
|-------|---------|
| System | You are a restaurant recommender. Rank only the provided restaurants. Do not invent names. Prefer JSON output. |
| User | Preferences (verbatim) + candidate JSON + “rank, explain each, optional summary” |
| Output schema | Ordered list: `id` or `name`, `explanation`; optional `summary` string |

### 8.2 Grounding rules

- Input list is the closed world for this request.
- After parse, drop any item whose `id`/`name` is not in the candidate set.
- Reattach `cuisine`, `rating`, and `cost` from the catalog, even if the model also echoed them (prevents drift).
- If parse fails, retry once with a stricter schema reminder; then fail the request with an error the UI can show.

### 8.3 Ranking guidance

Ask the model to weigh:

1. Cuisine fit  
2. Location fit  
3. Budget fit  
4. Rating vs. minimum  
5. Additional preferences (family-friendly, quick service, …)

Explanations should mention the user’s actual constraints, not generic marketing copy.

---

## 9. Output display architecture

Presentation maps 1:1 to the assignment output contract:

```text
[ Optional AI summary ]

┌─────────────────────────────────────────────┐
│ Name                                        │
│ Cuisine          Rating          Cost       │
│ Explanation: …                              │
└─────────────────────────────────────────────┘
        repeated for top K recommendations
```

The UI does not need to expose internal IDs, prompt text, or raw candidate dumps.

---

## 10. Error handling and edge cases

| Case | Behavior |
|------|----------|
| Invalid input (missing location, bad budget enum) | 400 / form validation; no LLM call |
| Dataset not ingested | Startup or first-request error; do not proceed |
| Zero candidates after filter | Empty state; skip LLM |
| LLM timeout / provider error | User-visible failure; catalog results without explanations are optional fallback only if product wants it — default is fail closed on explanations |
| Hallucinated restaurant | Strip from list; if none remain, treat as engine error |
| Too many candidates | Truncate to N before prompt (by rating, then votes if present) |

---

## 11. Non-functional design

| Concern | Approach |
|---------|----------|
| Latency | Cache ingested catalog locally; LLM is the slow path — small N, structured JSON |
| Cost | Never prompt on the full dataset; cap candidates |
| Grounding / trust | Catalog fields win over model-echoed facts |
| Repeatability | Deterministic filters; LLM ranking may vary unless temperature is low |
| Privacy | Preferences are request-scoped; do not log extra preferences more than needed |

---

## 12. Suggested technology shape

The problem statement does not lock a stack. A natural fit:

| Piece | Typical choice |
|-------|----------------|
| Language | Python |
| Dataset | `datasets` (Hugging Face) + pandas |
| API | FastAPI (or Flask) |
| UI | Simple web form (Jinja/HTML, Streamlit, or a small frontend) |
| LLM | Any chat/completions API that can return JSON |

Swap UI/API freely as long as layer boundaries stay the same: **ingest → store → filter → prompt → LLM → display**.

---

## 13. Mapping to assignment workflow

| Assignment step | Architecture component |
|-----------------|------------------------|
| 1. Data ingestion | Ingestion pipeline + catalog store |
| 2. User input | Presentation form → `UserPreference` |
| 3. Integration layer | Budget mapper, filters, candidate JSON, prompt builder |
| 4. Recommendation engine | LLM client: rank, explain, optional summary |
| 5. Output display | Recommendation cards (name, cuisine, rating, cost, explanation) |

---

## 14. What “done” looks like architecturally

1. Catalog is loaded from Hugging Face and queryable on the required fields.  
2. A request with location, budget, cuisine, min rating, and extras runs the filter-then-LLM path.  
3. The LLM never receives the unfiltered dataset.  
4. The UI shows top grounded recommendations with explanations (and optional summary).  
5. Empty filters and invalid model output are handled without fabricated restaurants.
