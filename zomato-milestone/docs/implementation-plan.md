# Implementation plan: AI-Powered Restaurant Recommendation System

**Use case:** Zomato-inspired restaurant discovery  
**Derived from:** [`architecture.md`](architecture.md) · [`problemStatement.md`](problemStatement.md)

This plan is **phase-wise**. Each phase has a goal, work items, deliverables, and an exit check. Do not start a later phase until the previous exit check passes, except where a phase is marked as parallelizable.

**Invariant throughout:** filter the Hugging Face catalog first; the LLM only ranks a small grounded candidate set. Never send the full dataset to the model. Never invent restaurants.

**Suggested stack (from architecture, not locked):** Python, Hugging Face `datasets` + pandas, FastAPI, simple web UI (Jinja/HTML or Streamlit), JSON-capable LLM API.

---

## Phase map

| Phase | Name | Maps to assignment step |
|-------|------|-------------------------|
| 0 | Project bootstrap | — |
| 1 | Data ingestion and catalog store | 1. Data ingestion |
| 2 | Domain models and user preference contract | 2. User input (backend shape) |
| 3 | Integration layer (budget, filter, candidates) | 3. Integration layer |
| 4 | Recommendation engine (LLM) | 4. Recommendation engine |
| 5 | Orchestration API | 2–4 wired together |
| 6 | Output display (UI) | 2. User input + 5. Output display |
| 7 | Hardening and grounding | Constraints in problem/architecture |
| 8 | Milestone verification | Full workflow |

```text
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 ──► Phase 7 ──► Phase 8
                         (types)     (filter)     (LLM)       (API)       (UI)
```

Phases 2 and 1 can overlap after catalog columns are known. Phase 6 UI shell can start in parallel with Phase 5 if the display DTO is frozen.

---

## Phase 0 — Project bootstrap

**Goal:** A runnable Python project with layout matching architecture modules, secrets kept out of git.

### Work

- Create the repo layout:

  ```text
  ingestion/    domain/    filters/    prompts/    llm/    api/    ui/
  docs/         data/      tests/
  ```

- Add `requirements.txt` (or `pyproject.toml`): `datasets`, `pandas`, web framework, LLM client, `python-dotenv`.
- Add `.env.example` for the LLM API key; gitignore `.env` and cached dataset files if large.
- Add a README with how to ingest, run API, and open the UI.
- Decide catalog cache format (parquet or CSV under `data/`).

### Exit check

- `pip install -r requirements.txt` succeeds.
- Empty modules import; docs already in `docs/` remain the source of truth.

---

## Phase 1 — Data ingestion and catalog store

**Goal:** Load [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) once, clean it, and publish a read-only catalog. Request path must not re-download Hugging Face on every search.

### Work

- Implement `ingestion` load from Hugging Face.
- Inspect actual column names; map them onto:

  | Canonical field | Required |
  |-----------------|----------|
  | `id` | recommended (generate if missing) |
  | `name` | yes |
  | `location` | yes |
  | `cuisine` | yes |
  | `cost` | yes (parse to numeric) |
  | `rating` | yes (numeric) |
  | extras | optional: address, votes, online_order, table_booking, … |

- Clean: drop or impute missing name/location/rating/cost; normalize location and cuisine strings; parse cost.
- Persist cache (`data/restaurants.parquet` or similar).
- Implement `RestaurantRepo`: load cache into memory; query later in Phase 3.
- Compute cost percentiles (P33, P66) and store them with the catalog for budget mapping.
- Document raw → canonical column mapping in a short comment or `docs` note if names differ.

### Exit check

- A script/command ingest completes and writes the cache.
- Catalog row count > 0; required fields are populated for kept rows.
- Reloading the app uses the cache, not a full remote download.
- Sample query by location returns rows (even if filters are still ad hoc).

---

## Phase 2 — Domain models and preference contract

**Goal:** Freeze types so filters, LLM, API, and UI share one language.

### Work

- Define:

  - `Restaurant` — catalog row  
  - `UserPreference` — `location`, `budget` (`low` \| `medium` \| `high`), `cuisine`, `min_rating`, `additional_preferences`  
  - `Candidate` — subset sent to the LLM (`id`, `name`, `location`, `cuisine`, `cost`, `rating`, extras)  
  - `Recommendation` — name, cuisine, rating, estimated cost, explanation, rank  
  - `RecommendationResponse` — list + optional `summary` + empty-state message  

- Validation rules: required location/budget/cuisine/min_rating; budget enum only; min_rating numeric.
- Normalization: trim/lowercase location and cuisine for matching (keep original for display if needed).

### Exit check

- Invalid preferences fail validation without calling repo or LLM.
- Valid preferences serialize to JSON for API/UI later.

---

## Phase 3 — Integration layer (filter, budget, candidates)

**Goal:** Translate `UserPreference` into a compact, grounded candidate list. No LLM yet.

### Work

- **BudgetMapper:** map `low` / `medium` / `high` onto cost bounds using catalog percentiles (or documented fixed caps).
- **Filters:**

  - Location: case-insensitive equality or contains  
  - Cuisine: case-insensitive token/substring; multi-cuisine rows match on any token  
  - Rating: `rating >= min_rating`; drop unknown ratings unless a fallback is documented  
  - Cost: within mapped band  

- Cap to **8–20** candidates (sort by rating, then votes if present).
- Serialize candidates to JSON with only needed columns.
- Extra preferences: if a catalog column supports them, use as extra filter/sort; otherwise leave for the LLM in Phase 4.
- Zero-match path: return empty list + “relax filters” message; **do not** invent rows.

### Exit check

- Unit tests: known location+cuisine+budget+rating returns a subset; impossible filters return empty.
- Candidate payload size ≤ N; no extra unused columns.
- Budget bands are deterministic given the same catalog.

---

## Phase 4 — Recommendation engine (LLM)

**Goal:** Rank candidates, explain each pick, optionally summarize. Catalog remains source of truth for facts.

### Work

- `PromptBuilder`:

  - System: restaurant recommender; rank only provided rows; do not invent names; JSON output  
  - User: preferences verbatim + candidate JSON + rank/explain/optional summary  
  - Ranking weights: cuisine, location, budget, rating vs minimum, additional preferences  
  - Explanations must mention the user’s constraints  

- `llm` client: chat/completions, low temperature, JSON parse, one retry on parse failure.
- Output schema: ordered `{ id or name, explanation }[]` plus optional `summary`.
- **Grounding:** drop unknown ids/names; reattach name, cuisine, rating, cost from catalog; if none remain, engine error.
- Do not call the LLM when the candidate list is empty (caller’s job; still guard here).

### Exit check

- Given a fixture candidate list, parsed output only contains those restaurants.
- Hallucinated names are stripped.
- Explanations are non-empty strings; summary is optional.
- Facts on the `Recommendation` object come from the catalog join, not model echo.

---

## Phase 5 — Orchestration API

**Goal:** One use case: `recommend(preferences) -> RecommendationResponse`.

### Work

- FastAPI (or Flask) endpoint, e.g. `POST /recommend`.
- Flow (from architecture):

  1. Validate `UserPreference`  
  2. Map budget → cost bounds  
  3. Query catalog  
  4. If 0 rows → empty result, skip LLM  
  5. Take top N candidates  
  6. Build prompt → LLM  
  7. Validate/join  
  8. Return display DTO  

- Startup: load catalog cache; fail fast if missing (dataset not ingested).
- HTTP mapping: 400 validation; 503 missing catalog or LLM provider down; 200 with empty list for no matches.
- Keep request-scoped preferences; avoid logging extra preferences more than needed.

### Exit check

- Curl/Postman: happy path returns ranked items with five display fields.  
- No-match body has empty list and a relax-filters message.  
- Invalid budget enum never hits the LLM.

---

## Phase 6 — Output display (UI)

**Goal:** User-friendly form in, recommendation cards out.

### Work

- **Input form:** location, budget (low/medium/high), cuisine, minimum rating, additional preferences.
- Client-side required-field checks aligned with Phase 2.
- **Results:**

  ```text
  [ Optional AI summary ]

  Card: Name | Cuisine | Rating | Estimated cost
        Explanation
  ```

- Empty state and API/LLM error messages without exposing prompts or internal ids.
- Optional: show cost as ₹ and/or budget band.

### Exit check

- A user can submit preferences and see top recommendations in the five required fields.
- Empty and error states are understandable.
- UI does not display prompt text or raw candidate dumps.

---

## Phase 7 — Hardening and grounding

**Goal:** Production-quality behavior for the edge cases in architecture §10–11.

### Work

- Confirm LLM never receives the unfiltered catalog (log candidate count in debug only).
- Truncation by rating/votes when matches ≫ N.
- Parse retry then user-visible failure (fail closed on explanations by default).
- Strip hallucinations; if the list becomes empty, treat as engine error.
- Latency: catalog in memory; prompt only small JSON.
- Low temperature for more stable ranking if demos need it.
- Tests: validation, filters, budget map, grounding join, empty path, hallucinated-name fixture.

### Exit check

- Architecture error table is covered by tests or manual script.
- A request cannot leak invented restaurant names to the UI.

---

## Phase 8 — Milestone verification

**Goal:** Assignment “done” criteria from problem statement §10 and architecture §14.

### Checklist

1. Dataset loaded and preprocessed with name, location, cuisine, cost, rating.  
2. Users submit location, budget, cuisine, minimum rating, extra preferences.  
3. Matching restaurants are filtered; only that subset is sent to the LLM.  
4. LLM ranks, explains, and optionally summarizes.  
5. UI shows top results: **name, cuisine, rating, estimated cost, explanation**.  
6. Zero matches and invalid model output do not fabricate venues.

### Demo script (manual)

1. Ingest catalog.  
2. Start API + UI.  
3. Happy path: e.g. Bangalore, medium, Italian, min rating 4.0, “family-friendly”.  
4. Tight filters that return no rows.  
5. Invalid form (missing location / bad budget).  
6. Confirm explanations mention the user’s constraints and facts match the catalog.

### Exit check

- All six checklist items pass. Milestone is complete.

---

## Suggested sequencing in the repo

| Order | Implement | Primary modules |
|------:|-----------|-----------------|
| 1 | Ingest + cache | `ingestion`, `data/` |
| 2 | Types + validation | `domain` |
| 3 | Budget + filter + cap | `filters` |
| 4 | Prompts + LLM + grounding | `prompts`, `llm` |
| 5 | `recommend()` + HTTP | `api` |
| 6 | Form + cards | `ui` |
| 7 | Tests + edge cases | `tests` |

---

## Out of scope unless explicitly added later

- User accounts, persistence of past searches  
- Live Zomato APIs (Hugging Face dataset only)  
- Vector search / embeddings (structured filters are the retrieval layer)  
- Sending the full catalog to the LLM  
- Chat-style multi-turn conversation beyond one recommend request  

---

## Document links

- Problem context: [`problemStatement.md`](problemStatement.md) · [`problemStatement.txt`](problemStatement.txt)  
- Target design: [`architecture.md`](architecture.md)
