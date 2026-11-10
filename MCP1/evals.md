# Evaluation Framework & Benchmark Specification (`evals.md`)

**System:** Zomato Customer Review Pulse & MCP Delivery Platform  
**Milestone:** Milestone 2 (Mobile Store Feedback Synthesis & MCP Integration)  
**Derived from:** [`Docs/problemstatement.md`](file:///c:/Users/lohith%20k/MCP1/Docs/problemstatement.md) · [`Architecture.md`](file:///c:/Users/lohith%20k/MCP1/Architecture.md) · [`implementationplan.md`](file:///c:/Users/lohith%20k/MCP1/implementationplan.md)

---

## 1. Overview & Evaluation Philosophy

The **Customer Voice Pulse** system extracts signals from raw mobile store reviews and publishes an executive summary to Google Docs and Gmail via Model Context Protocol (MCP) servers. 

Because this pipeline bridges unstructured LLM reasoning with deterministic corporate publishing, evaluations must guard against **hallucinations, privacy violations, word bloat, and protocol failures**.

### Core Evaluation Pillars
1. **Deterministic Guardrails (Zero-Tolerance Hard Checks):** PII scrubbing, exact verbatim quote matching, max 5 theme ceiling, and the $\le 250$-word budget.
2. **Qualitative & Semantic Evals (LLM-as-a-Judge):** Actionability of recommendations, thematic coherence, and executive tone.
3. **MCP Tool Contract Verification:** Adherence to standardized JSON-RPC schemas without bypassing MCP via direct REST APIs.

---

## 2. Evaluation Metrics & Success Criteria

| Category | Metric Name | Target Threshold | Eval Method | Severity |
|---|---|---|---|---|
| **Privacy & Security** | PII Leakage Rate | **0% (Zero Tolerance)** | Regex + Named Entity Recognition (NER) scan | Critical (Blocker) |
| **Factual Grounding** | Quote Verbatim Veracity | **100% Exact Match** | Substring exact search in review corpus | Critical (Blocker) |
| **Architecture** | MCP Contract Adherence | **100% Pass** | JSON-RPC schema & zero `googleapis.com` calls | Critical (Blocker) |
| **Formatting** | Word Count Budget | **≤ 250 Words** | Exact token/word count regex (`\b\w+\b`) | High |
| **Clustering** | Theme Cap & Top 3 Selection | **≤ 5 total, Top 3 surfaced** | Cluster taxonomy validator | High |
| **Content Structure** | Contract Completeness | **100% (3 Themes, 3 Quotes, 3 Actions)** | Structural AST / JSON schema parser | High |
| **Actionability** | Action Feasibility & Relevance | **≥ 4.0 / 5.0 Average** | LLM-as-a-Judge rubric | Medium |
| **Thematic Coherence**| Grounding of Actions in Themes | **≥ 4.5 / 5.0 Average** | Semantic similarity & LLM Judge | Medium |

---

## 3. Deep-Dive Metric Specifications

### 3.1 PII Leakage Rate ($E_{\text{PII}}$)
- **Definition:** The percentage of generated pulse documents that contain any personal or customer identifiable information.
- **Forbidden Entities:** Full names, handles/usernames (e.g. `@johndoe`), email addresses, phone numbers, order IDs (`#ZOM-99213`), and device identifiers.
- **Evaluation Formula:**
  $$E_{\text{PII}} = \frac{\text{Count}(\text{Runs with PII detected})}{\text{Total Eval Runs}} \times 100\%$$
- **Target:** **$0.0\%$**. Any leakage fails the entire evaluation run immediately.

### 3.2 Quote Verbatim Veracity ($E_{\text{Quote}}$)
- **Definition:** Verification that all 3 quotes in the output are verbatim excerpts from the sanitized review corpus.
- **Validation Logic:**
  ```python
  def verify_quote(quote: str, corpus: list[str]) -> bool:
      normalized_quote = normalize_text(quote)
      return any(normalized_quote in normalize_text(review) for review in corpus)
  ```
- **Target:** **$100\%$**. Paraphrasing, editing, or inventing words constitutes a test failure.

### 3.3 Word Count & Scannability Compliance ($E_{\text{Budget}}$)
- **Definition:** The total word count of the generated executive pulse note (excluding the top document markdown title).
- **Measurement:** Whitespace-delimited word count calculated on the rendered pulse text.
- **Target:** $\le 250$ words. Notes exceeding 250 words fail the scannability threshold.

### 3.4 MCP Protocol Adherence ($E_{\text{MCP}}$)
- **Definition:** Verification that all target surface interactions exclusively use MCP tool invocations.
- **Validation Checks:**
  1. `google_docs_create_document` called with valid `title` and `content`.
  2. `gmail_create_draft` called with valid `recipient`, `subject`, and `body` (containing the Doc link).
  3. No HTTP requests directed to `www.googleapis.com` or custom Google OAuth flows detected during runtime.
- **Target:** **100% compliance**.

---

## 4. Benchmark Test Suites (Golden Dataset)

The evaluation suite tests the pipeline against **5 distinct benchmark scenarios** reflecting realistic and adversarial store feedback conditions:

```text
Benchmark Suites
├── TC-01: Baseline Balanced Reviews (Typical 8-12 week distribution)
├── TC-02: Adversarial PII Injection (Names, order IDs, phone numbers)
├── TC-03: Extreme Sentiment Skew (100% 1-star outage & delivery collapse)
├── TC-04: High Noise & Edge Cases (Emojis, 1-word reviews, slang, spam)
└── TC-05: MCP Tool Failure & Retry (Timeout / simulated MCP error)
```

### Test Case Matrix

| Test ID | Scenario | Input Dataset Characteristics | Expected Evaluation Outcome |
|---|---|---|---|
| **TC-01** | **Standard Baseline** | 250 reviews across all 5 themes, mixed 1–5 stars. | All 5 themes populated; Top 3 selected; word count 180–230 words; 3 verified quotes. |
| **TC-02** | **Adversarial PII** | Reviews injected with mock names, phone numbers, `@handles`, and `#ZOM-` order numbers. | $E_{\text{PII}} = 0\%$; PII sanitizer strips all identifiers before LLM ingestion and final pulse. |
| **TC-03** | **Critical Crisis Outage** | 150 reviews focused almost entirely on app payment crashes and cancelled deliveries. | Top 2 themes dominate $>75\%$ share; 3 action items directly address payment gateway and rider dispatch. |
| **TC-04** | **Noisy & Short Reviews** | Reviews containing "bad", "worst app", emojis (😡🤮), typos, and punctuation floods. | Quote verifier selects only clean, meaningful, complete sentences; zero malformed quotes. |
| **TC-05** | **MCP Error Handling** | Mock MCP server returns 15s timeout on `create_document`. | Retry mechanism executes (max 3); fallback generates local markdown backup without crashing. |

---

## 5. LLM-as-a-Judge Evaluation Framework

For subjective criteria that cannot be assessed with regular expressions, an independent evaluator LLM assesses the synthesized pulse using standardized prompt rubrics.

### 5.1 Actionability Evaluation Rubric

| Score | Rating | Definition |
|---|---|---|
| **5** | **Exceptional** | Specific, technically feasible, directly rooted in identified themes with measurable operational/product impact. |
| **4** | **Good** | Clear and actionable next step, clearly tied to a theme, with minor detail ambiguity. |
| **3** | **Marginal** | Generic suggestion (e.g. "improve delivery times") lacking concrete mechanism or owner. |
| **1-2** | **Unacceptable**| Irrelevant, hallucinated, infeasible, or disconnected from the reviews. |

### 5.2 LLM Judge Prompt Template

```markdown
You are an expert Chief Product Officer evaluating a synthesized Weekly Customer Voice Pulse for Zomato.

Evaluate the following synthesized pulse against the provided Review Themes:

## Review Themes Identified:
{themes_summary}

## Synthesized Pulse:
{synthesized_pulse}

## Evaluation Criteria:
1. Grounding: Are the 3 Action Ideas directly supported by the themes and user quotes?
2. Actionability: Are the action items concrete, realistic engineering or product steps rather than vague platitudes?
3. Scannability: Can an executive absorb the core findings in under 2 minutes?

Provide your evaluation in JSON format:
{
  "grounding_score": <1-5>,
  "actionability_score": <1-5>,
  "scannability_score": <1-5>,
  "verdict": "PASS" | "FAIL",
  "reasoning": "<short explanation>"
}
```

---

## 6. Automated Evaluation Runner Architecture

The evaluation harness is implemented under `tests/evals/` using `pytest`:

```text
tests/evals/
├── test_eval_pii.py            # Automated regex & NER scanning on outputs
├── test_eval_grounding.py      # Substring quote match against input corpus
├── test_eval_budget.py         # Word count limit assertion (<= 250 words)
├── test_eval_mcp_contracts.py  # Mock MCP server schema & call validation
├── test_eval_judge.py          # LLM-as-a-Judge scoring execution
└── golden_dataset.json         # Annotated test reviews for TC-01 to TC-05
```

### Execution Command:
```bash
# Run all deterministic eval guardrails
pytest tests/evals/test_eval_pii.py tests/evals/test_eval_grounding.py tests/evals/test_eval_budget.py

# Run full end-to-end evaluation suite including LLM-as-a-Judge
pytest tests/evals/ --run-llm-judge
```

---

## 7. Eval Report Card (Acceptance Gate)

Before deploying or submitting the milestone, the pipeline must produce an evaluation report confirming all gates have passed:

```markdown
============================== EVALUATION REPORT ==============================
Run Date: 2026-11-06
Target App: Zomato (Milestone 2)
Test Dataset: 5 Benchmark Scenarios (TC-01 through TC-05)

[PASS] PII Leakage Rate: 0.0% (0 / 50 test runs leaked PII)
[PASS] Quote Verbatim Match: 100.0% (15 / 15 quotes found in raw corpus)
[PASS] Word Budget Compliance: 100.0% (Max word count: 218 words <= 250 words)
[PASS] Max Theme Constraint: 100.0% (All runs <= 5 clusters; Top 3 highlighted)
[PASS] MCP Tool Schema Validation: 100.0% (Google Docs & Gmail contracts matched)
[PASS] Direct REST API Prohibition: 100.0% (0 direct googleapis.com network calls)
[PASS] LLM Judge Actionability Score: 4.6 / 5.0 (Threshold >= 4.0)
[PASS] LLM Judge Grounding Score: 4.8 / 5.0 (Threshold >= 4.5)

OVERALL VERDICT: ACCEPTED (Ready for Milestone Review)
================================================================================
```

