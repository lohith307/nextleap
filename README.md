# AI-Powered Restaurant Recommendation System

A Zomato-inspired restaurant discovery and recommendation engine that combines structured catalog filtering with LLM reasoning.

## Architecture

- **Data Ingestion:** Loads and cleans the official [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) dataset.
- **Integration Layer:** Filters catalog based on location, cuisine, budget tier, and minimum rating.
- **LLM Recommendation Engine:** Ranks candidate restaurants, generates personalized explanations, and provides a contextual summary.
- **Grounded Verification:** Strict enforcement ensuring only real catalog restaurants are recommended, keeping facts (name, cuisine, rating, cost) 100% accurate.
- **Streamlit Web UI (`streamlit_app.py`):** Interactive, modern Zomato-themed application presenting the 5 required fields (Name, Cuisine, Rating, Estimated Cost, and AI-generated Explanation).
- **FastAPI Backend (`api/app.py`):** Headless REST API and static UI server.

## Getting Started

### 1. Setup Virtual Environment
```bash
py -3.9 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` (or configure `.streamlit/secrets.toml`) and add your `GROQ_API_KEY` (or OpenAI/Gemini key). If omitted, the system seamlessly uses its built-in Grounded AI Reasoning Engine:
```bash
cp .env.example .env
```

### 3. Run the Streamlit Application (Recommended for Deployment)
```bash
.\venv\Scripts\streamlit run streamlit_app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

### 4. Run the FastAPI Backend & Static UI (Alternative)
```bash
.\venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 5. Deployment on Streamlit Community Cloud
1. Push this repository to GitHub (refer to [`docs/streamlit_deployment_plan.md`](docs/streamlit_deployment_plan.md) for isolation steps).
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
3. Point to your repository with Main file path: `streamlit_app.py`.
4. (Optional) In **Advanced settings > Secrets**, add `GROQ_API_KEY` (and optionally `LLM_MODEL = "llama-3.3-70b-versatile"`).
5. Click **Deploy!**

### 6. Run Tests
```bash
.\venv\Scripts\pytest
```
