# AI-Powered Restaurant Recommendation System

**Use case:** Zomato-inspired restaurant discovery  
**Workspace:** `zomato-milestone`  
**Source of truth:** [`docs/problemStatement.txt`](docs/problemStatement.txt)

This file stores the full project context for the milestone: the problem, objectives, data, workflow, input/output contract, and how structured restaurant data is combined with an LLM to produce personalized recommendations.

---

## 1. Problem statement

You are tasked with building an AI-powered restaurant recommendation service inspired by Zomato. The system should intelligently suggest restaurants based on user preferences by combining structured data with a Large Language Model (LLM).

The product is not a generic chatbot. It is a **retrieval-plus-reasoning** pipeline:

1. Narrow a real restaurant catalog with filters (location, budget, cuisine, rating).
2. Hand a small, relevant candidate set to an LLM.
3. Ask the model to rank, explain, and optionally summarize those options in natural language.

---

## 2. Objective

Design and implement an application that:

- Takes user preferences such as **location**, **budget**, **cuisine**, and **ratings**
- Uses a **real-world dataset** of restaurants
- Leverages an **LLM** to generate personalized, human-like recommendations
- Displays **clear and useful** results to the user

Success means a user can state what they want, see a short list of matching restaurants, and understand **why** each one was recommended.

---

## 3. Dataset

| Item | Detail |
|------|--------|
| Source | Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) |
| Role | Authoritative catalog for ingestion, filtering, and grounding LLM output |

### Fields to extract and keep

At minimum, preprocess and retain:

- Restaurant name
- Location
- Cuisine
- Cost (or equivalent budget signal)
- Rating

Additional catalog fields (address, votes, online order, table booking, and similar) may be kept if they improve filtering or explanations. Do not pass the entire unfiltered dataset into the LLM.

---

## 4. User input

Collect these preferences before ranking:

| Preference | Examples / notes |
|------------|------------------|
| Location | Delhi, Bangalore |
| Budget | low, medium, high |
| Cuisine | Italian, Chinese |
| Minimum rating | numeric threshold |
| Additional preferences | family-friendly, quick service, and similar free-text needs |

Budget should be mapped from the user's band (low / medium / high) onto the dataset's cost field so filtering stays consistent.

---

## 5. System workflow

### 5.1 Data ingestion

- Load the Zomato dataset from Hugging Face.
- Clean and preprocess rows (missing values, inconsistent location/cuisine strings, cost parsing).
- Extract the relevant fields listed above into a structured table the rest of the app can query.

### 5.2 User input

- Capture location, budget, cuisine, minimum rating, and extra preferences through a form or equivalent UI/API.

### 5.3 Integration layer

- Filter the catalog to restaurants that match the structured preferences.
- Prepare a compact candidate payload (only matching rows, only needed columns).
- Pass that payload into an LLM prompt designed for **reasoning and ranking**, not unconstrained generation.

### 5.4 Recommendation engine

The LLM must:

- Rank restaurants from the candidate set
- Explain why each recommendation fits the user's preferences
- Optionally summarize the overall set of choices

The model should not invent restaurants that were not in the filtered data. Rankings and explanations must stay grounded in the structured rows.

### 5.5 Output display

Present **top recommendations** in a user-friendly format with:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

---

## 6. Architecture (how the pieces connect)

```text
Hugging Face Zomato dataset
        │
        ▼
 Data ingestion & preprocess
        │
        ▼
 Structured restaurant store
        │
        │  user: location, budget, cuisine, min rating, extras
        ▼
 Filter / integration layer  ──►  candidate restaurants (JSON/table)
        │
        ▼
 LLM prompt (rank + explain + optional summary)
        │
        ▼
 Recommendation engine output
        │
        ▼
 UI: name, cuisine, rating, cost, explanation
```

**Structured data** answers *what exists and matches filters*.  
**The LLM** answers *which of those options to prefer and why*, in a human-like tone.

---

## 7. Prompting contract

The integration-layer prompt should:

- Include the user's preferences verbatim
- Include only filtered candidates with name, location, cuisine, cost, rating, and any extra signals
- Instruct the model to rank, justify each pick, and stay within the provided list
- Request output that maps cleanly onto the display fields (name, cuisine, rating, cost, explanation)

---

## 8. Output contract

Each recommendation shown to the user should include:

| Field | Purpose |
|-------|---------|
| Restaurant name | Identify the place |
| Cuisine | Confirm taste match |
| Rating | Confirm quality bar |
| Estimated cost | Confirm budget match |
| AI-generated explanation | Why this option fits this user |

An optional short summary above or below the list may describe the overall mix of choices.

---

## 9. Constraints and design rules

- Use the specified Hugging Face Zomato dataset as the restaurant source.
- Filter first; then call the LLM on a relevant subset.
- Ground recommendations in real rows (name, cuisine, rating, cost).
- Keep the UI focused on the five output fields above.
- Treat extra preferences (family-friendly, quick service, and similar) as ranking/explanation signals when the dataset supports them, and as LLM guidance when they are only available as user text.

---

## 10. Milestone scope

This project is complete when:

1. The dataset is loaded and preprocessed with the required fields.
2. Users can submit location, budget, cuisine, minimum rating, and extra preferences.
3. Matching restaurants are filtered and sent to an LLM with a ranking prompt.
4. The LLM returns ordered recommendations with explanations (and an optional summary).
5. The UI shows top results as name, cuisine, rating, estimated cost, and explanation.

---

## Reference

Full original wording of the assignment:

- [`docs/problemStatement.txt`](docs/problemStatement.txt)
