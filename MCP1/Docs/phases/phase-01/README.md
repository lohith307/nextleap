# Phase 1: Review Ingestion, Normalization & EDA

This directory contains the data analysis, thematic discovery, and Groq token budget strategy for the 12-week review dataset ingested during **Phase 1**.

### Key Documents:
- **Comprehensive Data Analysis:** [`analysis.md`](analysis.md)
- **Groq Token Budget & Rate Limit Strategy:** [`token_budget_strategy.md`](token_budget_strategy.md)
- **Prompt Strategy & Output Contracts:** [`prompt_strategy.md`](prompt_strategy.md)
- **Theme Distribution & Metrics:** [`theme_distribution.json`](theme_distribution.json)
- **Curated Candidate Verbatim Quotes:** [`sample_reviews.json`](sample_reviews.json)

### Dataset Source:
- **Raw Downloads:** 652 reviews from Google Play Store (`com.application.zomato`)
- **Normalized Dataset:** 310 English-only reviews ($\ge 7$ words, 0 emojis, 0 PII) in [`../../../data/processed/sanitized_reviews.parquet`](../../../data/processed/sanitized_reviews.parquet)
- **Ingestion Runner:** [`../../../run_phase1.py`](../../../run_phase1.py)

### Groq `llama-3.3-70b-versatile` Rate Limits & Budget:
- **Limits:** 30 RPM | 1K RPD | 12K TPM | 100K TPD
- **Pipeline Strategy:** Single-shot distillation (~750 input tokens, ~300 output tokens = ~1,050 total tokens per run).
- **Consumption:** Uses only **8.7% of TPM limit** and **1.05% of daily token limit**, requiring exactly **1 API request**.
