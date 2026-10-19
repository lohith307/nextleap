# AI-Powered Restaurant Recommendation System

A Zomato-inspired restaurant discovery and recommendation engine that combines structured catalog filtering with LLM reasoning.

## Architecture

- **Data Ingestion:** Loads and cleans the official [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) dataset.
- **Integration Layer:** Filters catalog based on location, cuisine, budget tier, and minimum rating.
- **LLM Recommendation Engine:** Ranks candidate restaurants, generates personalized explanations, and provides a contextual summary.
- **Grounded Verification:** Strict enforcement ensuring only real catalog restaurants are recommended, keeping facts (name, cuisine, rating, cost) 100% accurate.
- **Web UI:** Responsive, modern Zomato-themed interface presenting the 5 required fields (Name, Cuisine, Rating, Estimated Cost, and AI-generated Explanation).

## Getting Started

### 1. Setup Virtual Environment
```bash
py -3.9 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` and add your OpenAI or Gemini API key. If omitted, the system seamlessly uses its built-in Grounded AI Reasoning Engine:
```bash
cp .env.example .env
```

### 3. Run Backend & Frontend Server
```bash
.\venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 4. (Optional) Run Dataset Ingestion
To download and ingest fresh rows from Hugging Face:
```bash
.\venv\Scripts\python.exe -m ingestion.ingest
```

### 5. Run Tests
```bash
.\venv\Scripts\pytest
```
