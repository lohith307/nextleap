# 🎤 Interview Preparation Script
## Zomato Customer Voice Pulse — MCP Delivery Platform

> **Milestone 2 | Full-Stack AI Pipeline | Python + MCP + LLM + Google Workspace**

---

## 1. Elevator Pitch (30-second version)

> "I built an end-to-end AI platform that automatically reads Zomato app-store reviews, clusters them into actionable themes using a custom Severity Score algorithm, synthesizes a 250-word executive Weekly Pulse report using an LLM with deterministic fallback, and publishes it to Google Docs and Gmail — all using the Model Context Protocol (MCP) for zero direct API calls. The pipeline runs on 652 raw reviews, produces ≤5 ranked clusters, and passes 45 automated acceptance tests."

---

## 2. Architecture Overview

```
Raw Reviews (652)
      ↓
  [Sanitizer] ── strips PII (emails, phones, names) + emoji
      ↓
  310 Sanitized Reviews
      ↓
  [Thematic Clusterer] ── TF-IDF + cosine similarity → 5 theme clusters
      ↓
  [Severity Scorer] ── ranks clusters by: (negative_pct × 0.6) + (1/avg_star × 0.4) × volume_boost
      ↓
  Top 3–5 Clusters
      ↓
  [Groq LLM Synthesizer] → ≤250-word Weekly Pulse + 3 verbatim quotes + 3 actions
     (fallback: deterministic template if LLM unavailable)
      ↓
  [PulseVerifier] ── verifies every quote is exact substring of corpus
      ↓
  [Word Budget Enforcer] ── multi-pass trim to ≤250 words
      ↓
  [MCP Client] ── RemoteHttpMCPClient with exponential backoff
      ├── [Docs Adapter] → append_to_doc → Google Doc
      └── [Gmail Adapter] → create_email_draft → Gmail draft
```

**Key design constraint:** Zero direct `googleapis.com` calls — 100% via MCP tools.

---

## 3. Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11 | Speed of dev, rich NLP ecosystem |
| LLM | Groq (`llama-3.3-70b-versatile`) | Low-latency inference API |
| Clustering | TF-IDF + cosine similarity (scikit-learn) | Lightweight, interpretable |
| MCP | Remote HTTP MCP server (Railway) | Abstraction over Google APIs |
| Delivery | Google Docs + Gmail via MCP | Executive-readable, auditable |
| Testing | pytest (45 tests, 7 test files) | Full coverage from unit to acceptance |
| UI | Vanilla JS SPA + Python stdlib HTTP server | Zero extra dependencies |
| Config | python-dotenv `.env` | 12-factor app pattern |

---

## 4. Phase-by-Phase Breakdown

### Phase 0 — Project Scaffolding
- Set up repo, virtual environment, folder structure (`src/`, `tests/`, `Docs/`, `ui/`)
- Defined `implementationplan.md` with all 7 phases

### Phase 1 — Data Ingestion & Sanitization
- Scraped/loaded 652 raw reviews for `com.application.zomato`
- **Sanitizer:** Regex-based PII stripper (emails, phone numbers, URLs, person names via patterns)
- Emoji stripper using Unicode ranges
- Output: 310 sanitized reviews (spanning 82 days)
- Cached to `data/sanitized_reviews.json` for deterministic replay

### Phase 2 — Thematic Clustering
- **TF-IDF vectorization** of review text
- **Cosine similarity** to group semantically related reviews
- **Severity Score formula:**
  ```
  severity = (negative_pct × 0.6) + (1/avg_star_rating × 0.4) × volume_boost
  ```
  where `volume_boost = log(1 + review_count)`
- Output: `ClusteringResult` with up to 5 `ThemeCluster` objects, ranked by severity

### Phase 3 — LLM Synthesis
- **Groq API** with `llama-3.3-70b-versatile` for natural language synthesis
- Prompt engineering: system role + structured JSON output request
- **Deterministic fallback:** Template-based synthesis if LLM unavailable
- Output: `PulseReport` with pulse text, verbatim quotes, and action items

### Phase 4 — Verification & Budget
- **PulseVerifier:** Checks every quote against corpus for exact substring match
- **WordBudgetEnforcer:** Multi-pass trimming — sentence removal, then word truncation — to reach ≤250 words
- Guarantees: ≥3 quotes, ≥3 actions, word count ≤250

### Phase 5 — MCP Integration
- `RemoteHttpMCPClient`: Wraps HTTP POST calls to Railway MCP endpoint
- **Exponential backoff:** 3 retries with 2^n second delays
- `DocsAdapter.append_to_doc(doc_id, content)` → Google Doc
- `GmailAdapter.create_email_draft(to, subject, body)` → Gmail draft

### Phase 6 — Hardening
- Edge case handling: empty reviews, single-word clusters, Unicode edge cases
- PII double-check pass on synthesized output
- Retry logging and audit trail
- `--dry-run` mode for safe testing without MCP delivery

### Phase 7 — Acceptance Testing
- 9 formal acceptance criteria
- 45 unit + integration tests across 7 test files
- All 9/9 criteria passing, 45/45 tests green

---

## 5. Key Technical Decisions (Q&A Ready)

### "What is MCP and why did you use it?"
> MCP (Model Context Protocol) is an open standard that lets AI agents invoke tools — like Google APIs — through a uniform JSON-RPC-style interface. I used it because it **decouples** the pipeline from raw Google API credentials, makes the system **pluggable** (swap the MCP server without changing pipeline code), and follows the assignment constraint of zero direct googleapis.com calls.

### "What is your Severity Score formula and why?"
> ```
> severity = (negative_pct × 0.6) + (1/avg_star_rating × 0.4) × log(1 + count)
> ```
> - **60% negative-review percentage:** Most direct signal of pain
> - **40% inverse star rating:** Low stars = high severity
> - **Volume boost via log:** A theme with 50 reviews matters more than one with 2, but we dampen it logarithmically to prevent large clusters from always winning

### "How do you ensure quote verbatim accuracy?"
> After synthesis, `PulseVerifier` does a **substring search** of each quoted sentence against the full review corpus. If any quote fails, the report is flagged as unverified and the pipeline either retries or falls back. This guarantees zero hallucinated quotes.

### "How does the word budget enforcer work?"
> It's a **multi-pass trimmer:**
> 1. Count words in the full pulse
> 2. If over 250, remove the last complete sentence
> 3. Repeat until ≤250 words
> 4. Final safety pass: hard truncate at word boundary
> This preserves narrative coherence better than simple word-count truncation.

### "What happens if the LLM API is down?"
> The pipeline has a **deterministic fallback synthesizer** (`src/synthesis/prompter.py`). It uses Python string templates to construct a valid Weekly Pulse from the cluster data without any LLM call. The output is structurally identical — same word budget, same quote format, same action structure — but templated rather than natural language. Users can't tell from the output format, only from slightly less fluent prose.

### "How did you handle PII sanitization edge cases?"
> - **Email:** `\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b` with case-insensitive flag
> - **Phone:** Multiple patterns covering Indian formats (+91, 10-digit, hyphenated)
> - **Names:** Capitalized word pairs after honorifics (Mr., Dr., etc.)
> - **URLs:** `https?://\S+`
> - **Emoji:** Unicode range `[\U0001F600-\U0001FFFF]` and supplemental ranges
> - **Double-pass:** Sanitize raw → synthesize → sanitize output again before MCP delivery

### "Walk me through your test strategy"
> Seven test files, 45 tests total:
> - `test_sanitizer.py` — PII/emoji removal edge cases
> - `test_clusterer.py` — cluster output shape, min/max cluster count
> - `test_severity.py` — severity score math, ranking order
> - `test_synthesis.py` — word count ≤250, quote count ≥3, action count ≥3
> - `test_mcp_client.py` — retry logic with mock server, timeout handling
> - `test_pipeline.py` — end-to-end dry-run with mocked MCP
> - `test_acceptance.py` — all 9 formal acceptance criteria

### "How did you implement MCP retry/backoff?"
> ```python
> for attempt in range(max_retries):
>     try:
>         response = requests.post(url, json=payload, timeout=30)
>         response.raise_for_status()
>         return response.json()
>     except (RequestException, HTTPError) as e:
>         wait = 2 ** attempt  # 1s, 2s, 4s
>         if attempt < max_retries - 1:
>             time.sleep(wait)
> raise MCPClientError("Max retries exceeded")
> ```
> Exponential backoff with `2^attempt` seconds. After 3 failures, raises `MCPClientError` with full context for the caller to handle.

### "What was the hardest bug you fixed?"
> The hardest was the **quote verbatim check failing silently**. The LLM was returning quotes with smart quotes (`"…"`) instead of straight quotes (`"…"`), and our substring search failed. Fix: normalize both the quote and corpus to `NFC` Unicode form and replace curly quotes before comparison. Took a while to spot because the text *looked* identical on screen.

### "How would you scale this to 10,000 reviews?"
> - Replace in-memory TF-IDF with **BM25** or a vector database (Pinecone/Weaviate)
> - Run sanitization and clustering in **parallel batches** using `concurrent.futures`
> - Cache embeddings in **Redis** keyed by review hash
> - Switch from polling to **event-driven** ingestion (Pub/Sub trigger on new review batch)
> - Add a **review deduplication** step using MinHash LSH

---

## 6. Live Demo Talking Points

```bash
# 1. Show project structure
ls src/ tests/ ui/ Docs/

# 2. Run dry-run (no MCP delivery)
python main.py --dry-run

# 3. Launch dashboard
python run_ui.py

# 4. Show live at http://localhost:8000
#    - Dashboard: 5 theme clusters with severity bars
#    - Pulse tab: 250-word executive report
#    - Reviews tab: paginated sanitized reviews
#    - Settings: configure recipient & doc ID

# 5. Run full acceptance suite
python -m pytest tests/test_acceptance.py -v

# 6. Show Google Doc (live link)
# https://docs.google.com/document/d/1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0/edit
```

---

## 7. Numbers to Remember

| Metric | Value |
|---|---|
| Raw reviews ingested | 652 |
| Sanitized reviews | 310 |
| Review time span | 82 days |
| Theme clusters produced | 5 (top 3 featured) |
| Weekly Pulse word count | ≤250 (actual: 243) |
| Verbatim quotes | 3 |
| Concrete actions | 3 |
| Total tests | 45 |
| Test pass rate | 100% (45/45) |
| Acceptance criteria | 9/9 PASSED |
| MCP retry attempts | Up to 3 (exponential backoff) |
| LLM model | llama-3.3-70b-versatile (Groq) |

---

## 8. Likely Follow-Up Questions

| Question | 1-line Answer |
|---|---|
| Why not use OpenAI? | Groq is 10× faster at inference; same quality for structured output |
| Why Railway for MCP? | Zero-config deployment, free tier, HTTPS out of the box |
| Why scikit-learn over transformers? | Interpretable, no GPU needed, 50ms latency vs 2s for BERT |
| How is privacy guaranteed? | PII stripped before any storage or LLM call; output re-sanitized before delivery |
| Why stdlib HTTP server for UI? | Zero extra dependencies = zero security surface for a demo tool |
| What's the Groq fallback trigger? | Any `4xx`/`5xx` from Groq API, or timeout >30s |
| Is the Google Doc append idempotent? | No — by design, each run appends a dated entry. Can be made idempotent by checking last-modified date |

---

## 9. Project Links

- **GitHub:** https://github.com/lohith307/nextleap
- **Google Doc (live output):** https://docs.google.com/document/d/1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0/edit
- **MCP Server:** https://web-production-45fffe.up.railway.app
- **Local dashboard:** http://localhost:8000 (run `python run_ui.py` first)

---

*Prepared for Milestone 2 technical interview — Zomato Customer Voice Pulse Platform*
