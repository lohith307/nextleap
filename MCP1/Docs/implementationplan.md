# Implementation Plan: Zomato Customer Review Pulse & MCP Delivery Platform

**Product Context:** Zomato Mobile App (Milestone 2)  
**Derived from:** [`Architecture.md`](file:///c:/Users/lohith%20k/MCP1/Architecture.md) · [`Docs/problemstatement.md`](file:///c:/Users/lohith%20k/MCP1/Docs/problemstatement.md)  
**Primary Integration Protocol:** Model Context Protocol (MCP)  
**Primary LLM Inference Provider:** Groq (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`)  
**Source of Truth:** [`Docs/problemstatement.txt`](file:///c:/Users/lohith%20k/MCP1/Docs/problemstatement.txt)

---

## 1. Architectural Invariants & Execution Rules

1. **MCP-First Integration (Zero Direct REST APIs):** All publishing actions (Google Docs document creation and Gmail draft creation) must run through Model Context Protocol (MCP) servers. No bespoke Google OAuth 2.0 flow or manual REST clients in application code.
2. **Cluster & Filter First:** Never send thousands of raw reviews into the LLM. Ingest, sanitize, and cluster into at most 5 themes first, then hand the top candidates to the LLM.
3. **100% Verbatim Quote Veracity:** Every user quote in the final pulse must be an exact substring match from the public review dataset. Zero hallucinated or paraphrased quotes.
4. **Strict PII Protection:** Author names, reviewer handles, user IDs, and device IDs must be stripped during preprocessing.
5. **Word Budget Constraint:** The weekly pulse document must remain scannable and **≤ 250 words** (readable in under 2 minutes).
6. **Strict Groq Rate Limits & Quota Protection:** The dataset is capped at **1,000 reviews** (scaled down from potential 2,400 raw reviews). All LLM invocations against `llama-3.3-70b-versatile` are strictly engineered to never exceed **30 RPM, 1K RPD, 12K TPM, and 100K TPD**. Brute-force dumping is forbidden; two-tier local pre-clustering + rate-limited Groq distillation is mandatory.

---

## 2. Phase Map

```text
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 ──► Phase 7
(Bootstrap)  (Ingest)   (Groq Cluster) (Groq Synth) (MCP Layer) (Pipeline)  (Harden)   (Verify)
```

| Phase | Name | Core Deliverable | Milestone Step |
|---|---|---|---|
| **0** | **Project Bootstrap & MCP Setup** | Virtualenv, directory structure, MCP client/server config | Setup |
| **1** | **Review Ingestion & PII Sanitizer** | Ingest 8–12 weeks of reviews (up to 1,000 reviews), sanitize PII, cache dataset | Step 1 |
| **2** | **Thematic Clustering Engine (Groq Rate-Guarded)** | Group reviews into $\le 5$ themes via two-tier hybrid clustering (`llama-3.3-70b-versatile`) | Step 2 |
| **3** | **Pulse Synthesis & Verbatim Verifier (Groq LLM)** | Synthesize Top 3 themes, 3 quotes, 3 actions via Groq ($\le 250$ words) | Step 3 |
| **4** | **MCP Client & Google Workspace Adapters** | MCP tool callers for Google Docs (`create_doc`) & Gmail (`create_draft`) | Step 4 |
| **5** | **End-to-End Orchestrator Pipeline** | Unified CLI/runner orchestrating data $\rightarrow$ synthesis $\rightarrow$ MCP publishing | Full Flow |
| **6** | **Quality, Security & Constraint Hardening** | Unit/integration tests, quote match verifier, word counter, mock MCP | Testing |
| **7** | **Milestone Delivery & Verification** | Live execution, verified Google Doc link, and Gmail draft confirmation | Acceptance |

---

## Phase 0 — Project Bootstrap & Environment Setup

**Goal:** Establish a clean, reproducible Python environment configured with dependencies, directory layout, and MCP server configuration.

### Work Items
1. **Directory Layout Setup:**
   ```text
   MCP1/
   ├── Docs/
   │   ├── problemstatement.md
   │   ├── Architecture.md
   │   └── implementationplan.md
   ├── data/
   │   ├── raw/                 # Raw public review exports
   │   └── processed/           # PII-sanitized, normalized review datasets
   ├── src/
   │   ├── ingestion/           # Data fetcher & PII sanitization
   │   ├── clustering/          # Thematic clustering engine
   │   ├── synthesis/           # LLM pulse prompt & verbatim verification
   │   ├── mcp_client/          # MCP stdio client & tool calling adapters
   │   ├── models/              # Pydantic schemas (Review, Theme, PulseReport)
   │   └── pipeline.py          # Master orchestrator
   ├── tests/
   │   ├── test_sanitization.py
   │   ├── test_clustering.py
   │   ├── test_verifier.py
   │   └── test_mcp_client.py
   ├── config/
   │   └── mcp_servers.json     # MCP server registry (Docs & Gmail)
   ├── requirements.txt
   └── .env.example
   ```
2. **Dependency Definition (`requirements.txt`):**
   - Core runtime: `pydantic>=2.5.0`, `pandas>=2.1.0`, `pyarrow>=14.0.0`
   - NLP & Extraction: `google-play-scraper>=1.2.4`, `regex>=2023.10.3`, `langdetect>=1.0.9`
   - LLM Orchestration: `groq>=0.9.0` (Ultra-low latency inference)
   - MCP Client SDK: `mcp>=1.0.0`
   - Testing & Linting: `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`
3. **Environment & Secrets Template (`.env.example`):**
   - Groq API Key: `GROQ_API_KEY` (Free tier from console.groq.com)
   - LLM Model: `LLM_MODEL=llama-3.3-70b-versatile` (or `llama-3.1-8b-instant`)
   - Stakeholder recipient email for Gmail draft testing
   - Target product identifier: `com.application.zomato`
4. **MCP Configuration Template (`config/mcp_servers.json`):**
   - Define stdio transport endpoints for Google Docs MCP and Gmail MCP servers.

### Exit Check
- `pip install -r requirements.txt` succeeds without conflicts.
- Directory skeleton created and verified.
- `.env` created from `.env.example` and gitignored.

---

## Phase 1 — Review Ingestion & PII Sanitizer

**Goal:** Ingest 8–12 weeks of public Zomato mobile reviews from public stores (capped at 1,000 reviews, scaled down from potential 2,400 raw exports), strip all personally identifiable information, remove emojis, filter for English reviews with $> 6$ words, and persist a normalized dataset.

### Work Items
1. **Public Review Fetcher (`src/ingestion/fetcher.py`):**
   - Query public reviews for Zomato app (`com.application.zomato`) across the 8–12 weeks historical window.
   - Target dataset size: capped at **1,000 reviews** to maintain optimal signal-to-noise ratio and stay well clear of downstream rate limits.
   - Extract canonical fields: `review_id`, `rating`, `title`, `text`, `date`, `version`, `thumbs_up`.
   - Adhere strictly to terms: public export / public API only; no login bypass.
2. **PII Sanitizer & Normalizer (`src/ingestion/sanitizer.py`):**
   - Drop author name, avatar URL, reviewer ID, and user account metadata.
   - Regex-scrub phone numbers, email addresses, order IDs (e.g., `#ZOM-12345`), and rider names.
   - Strip all emojis and pictographs.
   - Filter for English language reviews with $> 6$ words.
   - Anonymize review records into canonical `SanitizedReview` Pydantic models.
3. **Local Dataset Caching (`src/ingestion/cache.py`):**
   - Save preprocessed records into `data/processed/sanitized_reviews.parquet` and `.json`.
   - Implement read-through caching so recurring pipeline runs load instantly from local storage.

### Exit Check
- `python -m src.ingestion.fetcher` runs and yields $\ge 100$ and $\le 1,000$ reviews from the target 8–12 week window.
- `test_sanitization.py` verifies zero author names, emails, phone numbers, or emojis remain in processed records.
- Output parquet file exists and validates against `SanitizedReview` schema.

---

## Phase 2 — Thematic Clustering Engine (Groq Rate-Limit Guarded)

**Goal:** Group all 1,000 sanitized reviews into at most 5 domain-specific Zomato themes, rank them by volume and severity, and identify top candidate quotes using a two-tier hybrid approach that guarantees Groq rate limits (**30 RPM, 1K RPD, 12K TPM, 100K TPD**) are never violated.

### Groq Free-Tier Rate Limits & Budget Allocation:
- **Model:** `llama-3.3-70b-versatile`
- **Rate Limits:** 30 Requests/min | 1,000 Requests/day | 12,000 Tokens/min | 100,000 Tokens/day
- **Budget Rule:** Single-shot / micro-batched calls only. Never pass 1,000 raw reviews to Groq (~65,000 tokens violates 12K TPM by $> 5.4\times$). Maximum Groq token footprint per pipeline execution is capped at **$\le 1,500$ tokens** (**only 12.5% of 12K TPM, 1.5% of 100K daily limit**).

### Work Items
1. **Domain Themes Definition (`src/clustering/themes.py`):**
   - Constrain strictly to **at most 5 themes**:
     1. `delivery_riders`: Delivery delays, live tracking issues, driver cancellations.
     2. `food_packaging`: Spills, cold food, broken packaging, wrong dishes.
     3. `pricing_charges`: Surge fees, platform fees, coupon failures, Gold benefits.
     4. `app_performance`: UPI checkout failures, search latency, crashes, UI glitches.
     5. `support_refunds`: Bot unresponsiveness, denied refunds, disputed claims.
2. **Two-Tier Clustering Architecture (`src/clustering/classifier.py`):**
   - **Tier 1 (Local Python):** High-speed regex and keyword taxonomy classifier categorizes 1,000 reviews locally in milliseconds (**0 tokens, 0 RPM**).
   - **Tier 2 (Groq Distillation & Rate Limiter):** For ambiguous boundary reviews or cluster validation, reviews are grouped into micro-batches of $\le 10$ reviews ($\le 700$ tokens/call) with a minimum 2.5s pacing delay ($\le 24$ RPM $\ll 30$ RPM limit).
   - Computes metrics per cluster: total reviews, percentage of corpus, average star rating, negative sentiment ratio.
3. **Top 3 Theme Selector & Quote Candidate Pool (`src/clustering/ranking.py`):**
   - Rank the 5 clusters by empirical **Severity Score**:
     $$\text{Severity} = N_{\text{negative}} \times (5.0 - \bar{R})$$
   - Select the **Top 3 themes**.
   - For each of the top themes, extract a pool of candidate verbatim quote snippets (15–35 words each, punchy, anonymous).

### Exit Check
- `test_clustering.py` confirms that:
  - Output contains $\le 5$ total themes.
  - Exactly 3 themes are designated as primary.
  - Candidate quotes are extracted verbatim from the sanitized dataset.
  - Groq token and request tracking asserts $\le 1,500$ tokens and $\le 2$ API requests consumed.

---

## Phase 3 — Pulse Synthesis & Verbatim Verifier (Groq LLM)

**Goal:** Synthesize the weekly one-page customer pulse containing the Top 3 themes, 3 verbatim user quotes, and 3 concrete action ideas using Groq LLM, while strictly enforcing the $\le 250$-word budget.

### Work Items
1. **Prompt Template Construction & Groq LLM Synthesis (`src/synthesis/prompter.py`):**
   - Dispatch structured prompt to **Groq LLM** (`llama-3.3-70b-versatile`) with JSON mode (`response_format={"type": "json_object"}`).
   - Strictly forbid hallucinated quotes; require Top 3 themes, 3 verbatim quotes, 3 concrete actions.
   - Require structured JSON output matching `WeeklyPulseReport`:
     ```json
     {
       "date_range": "Oct 1 - Nov 6, 2026",
       "top_3_themes": [
         { "name": "Delivery ETA Gaps", "share": "42%", "summary": "..." }
       ],
       "verbatim_quotes": ["quote 1", "quote 2", "quote 3"],
       "action_ideas": ["action 1", "action 2", "action 3"],
       "formatted_markdown": "# Zomato Customer Pulse..."
     }
     ```
2. **Verbatim Quote Verifier (`src/synthesis/verifier.py`):**
   - For each quote in the generated output, perform an exact normalized substring check against the sanitized review corpus.
   - If an exact match is missing, deterministically replace it with the highest-ranked candidate quote from that cluster.
3. **Word Budget Enforcer (`src/synthesis/budget.py`):**
   - Measure word count of the formatted markdown note.
   - If word count exceeds 250 words, execute an automated summarization compression pass that condenses descriptions while preserving quotes and actions verbatim.

### Exit Check
- `test_verifier.py` passes: simulated hallucinated quotes are rejected and replaced with exact corpus matches.
- Synthesized output word count is verified to be $\le 250$ words.
- All three deliverables present: Top 3 themes, 3 quotes, 3 action ideas.

---

## Phase 4 — MCP Client & Google Workspace Adapters

**Goal:** Build the Model Context Protocol (MCP) client layer that connects to Google Docs and Gmail MCP servers via standardized JSON-RPC over `stdio`/`sse`.

### Work Items
1. **MCP Client Session Manager (`src/mcp_client/client.py`):**
   - Implement an async MCP client using the official `mcp` SDK.
   - Support discovery (`tools/list`) and invocation (`tools/call`) over `stdio`.
   - Read server configurations from `config/mcp_servers.json`.
2. **Google Docs MCP Adapter (`src/mcp_client/docs_adapter.py`):**
   - Map pulse markdown payload to tool parameters:
     ```python
     response = await mcp_client.call_tool(
         server_name="google-docs",
         tool_name="google_docs_create_document",
         arguments={
             "title": f"Zomato Customer Voice Pulse - {date_str}",
             "content": pulse_markdown
         }
     )
     doc_url = response["document_url"]
     ```
3. **Gmail MCP Adapter (`src/mcp_client/gmail_adapter.py`):**
   - Construct draft email payload referencing the pulse summary and linking to the newly generated Google Doc.
   - Invoke `gmail_create_draft`:
     ```python
     response = await mcp_client.call_tool(
         server_name="gmail",
         tool_name="gmail_create_draft",
         arguments={
             "recipient": stakeholder_email,
             "subject": f"Weekly Customer Voice Pulse: Zomato ({date_str})",
             "body": email_body_with_doc_link
         }
     )
     draft_id = response["draft_id"]
     ```
4. **Mock MCP Server for Test Suite (`tests/mock_mcp_server.py`):**
   - Create a local mock stdio MCP server for continuous integration and testing without requiring live Google credentials.

### Exit Check
- `test_mcp_client.py` against mock MCP server executes `tools/list` and `tools/call` cleanly.
- Tool schemas match architecture contracts for `create_document` and `create_draft`.
- Zero direct HTTP REST calls to `googleapis.com` exist in the codebase.

---

## Phase 5 — End-to-End Orchestrator Pipeline

**Goal:** Wire the entire workflow into a single executable command/script that ingests, clusters, synthesizes, verifies, and publishes the pulse.

### Work Items
1. **Pipeline Orchestrator (`src/pipeline.py`):**
   - Sequence execution:
     1. Check/refresh 8–12 week review cache.
     2. Run PII sanitizer.
     3. Perform thematic clustering ($\le 5$ themes) via Groq LLM.
     4. Invoke Groq LLM for pulse note generation.
     5. Run verbatim quote verification & word count check ($\le 250$ words).
     6. Connect to Google Docs MCP Server $\rightarrow$ publish document.
     7. Connect to Gmail MCP Server $\rightarrow$ create draft email containing pulse and doc link.
2. **CLI Runner (`main.py`):**
   - CLI flags: `--dry-run` (stops before MCP publishing), `--refresh-cache`, `--recipient <email>`.
   - Terminal summary logging (execution steps, token counts, generated document link, draft ID).

### Exit Check
- Running `python main.py --dry-run` completes steps 1–5 and prints the verified markdown note.
- Running `python main.py` triggers MCP tools, outputs the created Google Doc URL and Gmail draft ID.

---

## Phase 6 — Quality, Security & Constraint Hardening

**Goal:** Comprehensive test coverage verifying edge cases, privacy compliance, quote veracity, and MCP failure recovery.

### Work Items
1. **Privacy & Security Audit:**
   - Scan processed datasets for PII leakages (regex test suite for names, handles, phone numbers, order IDs).
2. **Veracity & Word Limit Test Suite:**
   - Test extreme review samples to ensure the $\le 250$-word limit is never violated.
   - Verify that quotes containing punctuation or emojis are preserved exactly without corruption.
3. **MCP Error Recovery & Fallbacks:**
   - Handle MCP connection timeouts with exponential backoff retries (max 3 attempts).
   - If Google Docs MCP fails, log the generated Markdown artifact locally to `Docs/generated_pulse.md` so work is never lost.

### Exit Check
- `pytest tests/` runs with 100% pass rate across sanitization, clustering, synthesis, and MCP layers.
- Word budget test asserts generated output $\le 250$ words on 5 diverse review batches.

---

## Phase 7 — Milestone Verification & Acceptance

**Goal:** Execute the full production flow and verify deliverables against milestone criteria.

### Acceptance Checklist

- [x] **1. Public Reviews Sourced:** 8–12 weeks of Zomato reviews loaded without ToS-violating scraping or store logins (652 raw, 310 sanitized).
- [x] **2. PII Completely Anonymized:** Zero reviewer names, emails, phone numbers, order IDs, or emojis in any artifact.
- [x] **3. Thematic Clustering (Groq):** Reviews clustered into at most 5 themes via Groq LLM; Top 3 selected based on empirical Severity Score ($N_{\text{neg}} \times (5 - \bar{R})$).
- [x] **4. Verbatim Quotes:** Exactly 3 quotes verified as 100% exact substring matches from the sanitized review corpus.
- [x] **5. Action Ideas:** Exactly 3 concrete, realistic next steps grounded in the top themes.
- [x] **6. Scannable Format:** Executive pulse is formatted cleanly and strictly $\le 250$ words (243 words total).
- [x] **7. Google Docs via MCP:** Document appended in Google Docs (`1e0ZBU1RsAN0nLoLgKna7lKvlWzGszMiGCnwO0ulVmN0`) using MCP tool call (`append_to_doc`).
- [x] **8. Gmail Draft via MCP:** Email draft created in Gmail using MCP tool call (`create_email_draft`) containing the pulse and Google Doc link.
- [x] **9. Zero Direct APIs:** No direct Google REST API client code (`googleapis.com`) or OAuth flow implemented in the project (verified by static audit test).

### Exit Check
- `python run_phase7.py` validates all 9 criteria with exit code 0.
- `pytest tests/test_acceptance.py` runs with 100% pass rate (9/9 passed).
- Entire project test suite executes with 100% pass rate (45/45 passed).
- Formal acceptance documentation generated at [Docs/phases/phase-07/README.md](phases/phase-07/README.md).

