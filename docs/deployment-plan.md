# Streamlit Deployment Plan: Zomato AI Restaurant Recommender

> [!IMPORTANT]
> **Git Repository Root Warning:**  
> Your current Git repository root is set to `C:\Users\lohith k` (your Windows user home folder). Before pushing to GitHub, you **must isolate `zomato-milestone` as its own independent Git repository** so personal files, OneDrive contents, or local configurations are not committed.

---

## 1. Architecture Overview

Currently, the project runs as a **FastAPI backend** (`api/app.py`) serving a static **HTML/JS frontend** (`ui/index.html`).

For Streamlit deployment, the cleanest and most efficient approach is a **Native Single-Service Streamlit Application (`streamlit_app.py`)**:

```mermaid
flowchart TD
    subgraph Client["Streamlit Community Cloud / Local Web Browser"]
        UI["Streamlit Interactive UI (Zomato Themed)"]
    end

    subgraph App["streamlit_app.py"]
        Cache["@st.cache_resource<br/>RestaurantRepo"]
        Filter["CandidateFilterEngine"]
        LLM["LLMClient (OpenAI / Gemini / Grounded Engine)"]
    end

    subgraph Storage["Data & Config"]
        CSV[("data/restaurants.csv (1.58 MB)")]
        Secrets["st.secrets / .env<br/>(API Keys)"]
    end

    UI -->|Filter Criteria| Filter
    Filter -->|Query Catalog| Cache
    Cache -->|Read Once| CSV
    Filter -->|Candidates (Top 15)| LLM
    Secrets -->|Inject Keys| LLM
    LLM -->|Grounded Recommendations + Explanations| UI
```

### Why Native Streamlit over Dual-Service (FastAPI + Streamlit)?
- **Zero CORS / Networking Overhead:** Streamlit directly calls your modular domain logic (`CandidateFilterEngine`, `RestaurantRepo`, and `LLMClient`).
- **Memory Efficiency & Speed:** Streamlit's `@st.cache_resource` loads the 1.58 MB CSV file once in memory (< 150 MB RAM, well within Streamlit Cloud's 1 GB limit).
- **Single-Click Deploy:** No need to manage and coordinate two hosted services (e.g., Render for FastAPI and Streamlit for UI).
- **Fallback Safe:** Seamlessly works with OpenAI, Gemini, or the built-in Grounded AI Reasoning Engine if no API keys are supplied.

---

## 2. Prerequisites & File Additions

| File | Purpose | Action Required |
|------|---------|-----------------|
| `streamlit_app.py` | Main Streamlit interface & interaction flow | Create file |
| `.streamlit/config.toml` | Zomato branding theme (Red `#E23744`, clean white) | Create file |
| `.streamlit/secrets.toml.example` | Template for local and cloud secrets | Create file |
| `requirements.txt` | Add `streamlit>=1.30.0` | Update file |
| `.gitignore` | Ignore `secrets.toml`, `.env`, `venv/`, `.pytest_cache/` | Verify & update |
| `data/restaurants.csv` | Preprocessed catalog (1.58 MB) | Keep in repo |

---

## 3. Step-by-Step Implementation & Deployment Plan

### Phase 1: Codebase Adaptation for Streamlit

1. **Add Streamlit to `requirements.txt`**:
   ```text
   streamlit>=1.30.0
   fastapi>=0.100.0
   uvicorn[standard]>=0.22.0
   pydantic>=2.0.0
   pandas>=1.5.0
   requests>=2.28.0
   python-dotenv>=1.0.0
   jinja2>=3.1.0
   pytest>=7.0.0
   httpx>=0.24.0
   ```

2. **Configure Streamlit Theme (`.streamlit/config.toml`)**:
   Set up Zomato brand identity:
   ```toml
   [theme]
   primaryColor = "#E23744"
   backgroundColor = "#FFFFFF"
   secondaryBackgroundColor = "#F8F9FA"
   textColor = "#1C1C1C"
   font = "sans serif"

   [server]
   headless = true
   enableCORS = false
   enableXsrfProtection = true
   ```

3. **Enable Secrets Reading in `llm/client.py`**:
   Allow `LLMClient` to pick up API keys from `st.secrets` when running on Streamlit Cloud, alongside `os.getenv`:
   ```python
   try:
       import streamlit as st
       if hasattr(st, "secrets"):
           if "GROQ_API_KEY" in st.secrets:
               self.groq_api_key = st.secrets["GROQ_API_KEY"]
           if "OPENAI_API_KEY" in st.secrets:
               self.openai_api_key = st.secrets["OPENAI_API_KEY"]
           if "GEMINI_API_KEY" in st.secrets:
               self.gemini_api_key = st.secrets["GEMINI_API_KEY"]
   except Exception:
       pass
   ```

4. **Build `streamlit_app.py`**:
   - **Header & Hero Banner:** Zomato logo/branding, project taglines.
   - **Sidebar / Filter Panel:**
     - Location dropdown (pre-populated from `repo.get_locations()`).
     - Cuisine multi-select or dropdown (from `repo.get_cuisines()`).
     - Budget Tier selector (Budget `₹`, Mid-range `₹₹`, Fine Dining `₹₹₹`).
     - Minimum Rating slider (e.g. 3.0 to 5.0).
     - Optional Dietary preference (Veg / Non-Veg) and Ambiance/Occasion keywords.
   - **Cached Ingestion:**
     ```python
     @st.cache_resource(show_spinner="Loading restaurant catalog...")
     def get_services():
         repo = RestaurantRepo()
         filter_engine = CandidateFilterEngine(repo)
         llm_client = LLMClient()
         return repo, filter_engine, llm_client
     ```
   - **Results Display:**
     - AI Summary banner explaining the overall recommendation logic.
     - Recommendation Cards with 5 mandatory fields:
       1. **Restaurant Name** (bold, clickable)
       2. **Cuisine Tags**
       3. **Rating Badge** (color-coded, star icon)
       4. **Estimated Cost** (for two, with budget tier badge)
       5. **AI Personalized Explanation** (grounded reasoning)
     - Graceful empty state when no match is found, with tips to relax search filters.

---

### Phase 2: Local Testing & Verification

1. Install Streamlit in your virtual environment:
   ```powershell
   .\venv\Scripts\pip install streamlit
   ```

2. Run the Streamlit app locally:
   ```powershell
   .\venv\Scripts\streamlit run streamlit_app.py
   ```

3. Verify:
   - Location and cuisine drop-downs load instantly.
   - Recommendations render correctly with all 5 mandatory fields.
   - Filtering with extreme parameters handles zero matches cleanly.
   - Grounded engine works without API keys, and OpenAI/Gemini works when keys are in `.env` or `.streamlit/secrets.toml`.

---

### Phase 3: Git Repository Isolation & GitHub Push

> [!CAUTION]
> Do NOT run `git push` directly in `C:\Users\lohith k`. Follow these steps to create a clean repository for `zomato-milestone`.

1. **Verify `.gitignore` in `zomato-milestone`:**
   ```gitignore
   venv/
   .env
   .streamlit/secrets.toml
   __pycache__/
   *.pyc
   .pytest_cache/
   .cursor/
   ```

2. **Initialize Standalone Git Repository:**
   ```powershell
   cd "c:\Users\lohith k\zomato-milestone"
   git init
   git add .
   git commit -m "Initial commit: Zomato AI Restaurant Recommender with Streamlit UI"
   ```

3. **Create GitHub Repository:**
   - Go to [GitHub -> New Repository](https://github.com/new).
   - Name: `zomato-ai-recommender` (Public or Private).
   - Do NOT check "Initialize with README".

4. **Push Code:**
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<your-username>/zomato-ai-recommender.git
   git push -u origin main
   ```

---

### Phase 4: Streamlit Community Cloud Deployment

1. **Log in to Streamlit Community Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io).
   - Sign in with your GitHub account.

2. **Deploy New App:**
   - Click **New app**.
   - **Repository:** `<your-username>/zomato-ai-recommender`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** (Choose a custom subdomain like `zomato-ai-recommender.streamlit.app`)

3. **Configure Secrets (Optional / If using Groq, OpenAI, or Gemini):**
   - Click **Advanced settings** -> **Secrets**.
   - Enter your secrets in TOML format:
     ```toml
     GROQ_API_KEY = "gsk_..."
     LLM_MODEL = "llama-3.3-70b-versatile"
     # or
     OPENAI_API_KEY = "sk-..."
     GEMINI_API_KEY = "AIzaSy..."
     ```
   - Click **Save**.

4. **Launch & Monitor:**
   - Click **Deploy!**.
   - Watch the build logs in the lower-right console.
   - Test live URL on desktop and mobile.

---

### Phase 5: Alternative Deployment Option: Docker Container

If you prefer to deploy on **AWS ECS, Google Cloud Run, Hugging Face Spaces**, or **Render**:

1. **`Dockerfile`**:
   ```dockerfile
   FROM python:3.10-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8501

   HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

   ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

2. **Build and Run Locally**:
   ```bash
   docker build -t zomato-recommender .
   docker run -p 8501:8501 -e GROQ_API_KEY="gsk_..." zomato-recommender
   ```

---

## 4. Operational Considerations & Best Practices

1. **Catalog Persistence**:
   - `data/restaurants.csv` is committed directly to GitHub (~1.58 MB), ensuring zero startup latency or external dependencies.
   - Fallback seed catalog is already embedded in `ingestion/repo.py` in case of file system errors.

2. **Resource Limits**:
   - Streamlit Cloud free tier offers **1 GB RAM**.
   - The catalog consumes ~45 MB RAM when loaded into Pandas / Pydantic models. Total app footprint is ~140 MB, leaving abundant headroom.

3. **API Key Security**:
   - Never commit `.env` or `.streamlit/secrets.toml` to Git.
   - Streamlit Cloud encrypts secrets at rest and injects them safely.
   - The application functions seamlessly even with no API keys using the built-in Grounded AI Reasoning Engine.
