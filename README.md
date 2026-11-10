# AI-Powered Zomato Intelligence & Automation Platform

This repository contains the full end-to-end Zomato AI product suite:
- **[Milestone 1: AI-Powered Restaurant Recommendation System](#milestone-1-ai-powered-restaurant-recommendation-system)** (FastAPI, Streamlit, Groq LLM, Grounded Verification)
- **[Milestone 2: Customer Voice Pulse & MCP Delivery Platform (`MCP1/`)](#milestone-2-customer-voice-pulse--mcp-delivery-platform-mcp1)** (Review Ingestion, Thematic Clustering, Executive Pulse Synthesis, and Google Workspace delivery via Model Context Protocol MCP)

---

## Milestone 2: Customer Voice Pulse & MCP Delivery Platform (`MCP1/`)

Automated weekly executive customer review intelligence engine for Zomato (`com.application.zomato`), extracting insights from app store reviews and publishing one-page executive summaries to Google Docs and Gmail exclusively via **Model Context Protocol (MCP)**.

### Core Capabilities & Invariants
- **Review Ingestion & Sanitization:** Ingests 8–12 weeks of reviews (up to 1,000 reviews), stripping 100% of PII (names, handles, phones, order IDs) and emojis.
- **Two-Tier Thematic Clustering:** Categorizes feedback into $\le 5$ canonical themes, ranking them by empirical **Severity Score** ($N_{\text{neg}} \times (5 - \bar{R})$) with Groq rate-limiting safety.
- **Executive Pulse Synthesis:** Produces a high-impact, scannable pulse note strictly $\le 250$ words.
- **100% Verbatim Quote Veracity:** Every user quote is an exact substring match from the review dataset; zero hallucinations.
- **Model Context Protocol (MCP) Publishing:** 100% Google Docs and Gmail publishing routed through the Railway MCP server (`web-production-45fffe.up.railway.app`) via `append_to_doc` and `create_email_draft`. Zero direct Google REST APIs.

### Quick Start for Milestone 2 (`MCP1/`):
```powershell
cd MCP1
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run full pipeline with MCP delivery:
python main.py

# Run dry-run (synthesis without MCP publishing):
python main.py --dry-run

# Run full 28-test suite:
python -m pytest tests/ -v
```
Full documentation: [`MCP1/README.md`](MCP1/README.md) · [`MCP1/Docs/Architecture.md`](MCP1/Docs/Architecture.md)

---

## Milestone 1: AI-Powered Restaurant Recommendation System

A Zomato-inspired restaurant discovery and recommendation engine that combines structured catalog filtering with LLM reasoning.

### Architecture
- **Data Ingestion:** Loads and cleans the official [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) dataset.
- **Integration Layer:** Filters catalog based on location, cuisine, budget tier, and minimum rating.
- **LLM Recommendation Engine:** Ranks candidate restaurants, generates personalized explanations, and provides a contextual summary.
- **Grounded Verification:** Strict enforcement ensuring only real catalog restaurants are recommended, keeping facts (name, cuisine, rating, cost) 100% accurate.
- **Streamlit Web UI (`streamlit_app.py`):** Interactive, modern Zomato-themed application presenting the 5 required fields (Name, Cuisine, Rating, Estimated Cost, and AI-generated Explanation).
- **FastAPI Backend (`api/app.py`):** Headless REST API and static UI server.

### Getting Started (Milestone 1)
```bash
py -3.9 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
.\venv\Scripts\streamlit run streamlit_app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.
