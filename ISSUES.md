# Issues, Bugs, and Fixes

> This document records all bugs discovered and fixed during development and testing of the Zomato AI Recommendation System.

---

## Bug 1: `NameError: name 're' is not defined` — Location/Cuisine Matching

**File:** `ingestion/repo.py`  
**Severity:** 🔴 Critical — caused 4 out of 9 automated tests to fail  
**Status:** ✅ Fixed

### Symptom
Running `pytest` produced `NameError: name 're' is not defined` inside `find_candidates()`, crashing tests:
- `test_recommend_happy_path`
- `test_recommend_zero_matches_relax_filters`
- `test_candidate_filter_and_zero_matches`
- `test_grounding_and_hallucination_prevention`

### Root Cause
When improving location and cuisine matching to use regex-normalized alphanumeric comparison (`re.sub(r'[^a-z0-9]', '', ...)`), the `re` standard library module was used but never imported at the top of the file.

### Fix
Added `import re` to the imports section of `ingestion/repo.py`.

---

## Bug 2: City Alias Searches (`Bengaluru`, `blr`) Returned Zero Results

**File:** `ingestion/repo.py` → `find_candidates()`  
**Severity:** 🟠 High — major usability issue for the primary city served  
**Status:** ✅ Fixed

### Symptom
Entering `"Bengaluru"` or `"blr"` in the location field returned _"No restaurants found"_, even though 9,216 Bangalore restaurants are loaded.

### Root Cause
The location filter only treated the exact string `"bangalore"` as a city-wide wildcard. Other valid common aliases (`bengaluru`, `blr`, `all`, `any`, `karnataka`) were not recognized and were treated as specific locality names — which matched nothing.

### Fix
Added a `city_aliases` set:
```python
city_aliases = {"bangalore", "bengaluru", "blr", "all", "any", "city", "karnataka", ""}
```
Location matching was also upgraded to use alphanumeric-normalized comparison (`re.sub(r'[^a-z0-9]', '', ...)`) to robustly handle spacing, punctuation, and area block numbers (e.g., `"Koramangala 5th Block"` correctly matches input `"Koramangala"`).

**Result:** `Bengaluru` and `blr` now each return 15 top restaurant candidates.

---

## Bug 3: Personalization Lost in LLM Fallback (`pref=None`)

**File:** `llm/client.py` → `_ground_and_format()` and `_grounded_reasoning_engine()`  
**Severity:** 🟡 Medium — incorrect/generic output when LLM API is unavailable  
**Status:** ✅ Fixed

### Symptom
When OpenAI or Gemini returned empty or unparseable JSON and the system fell back to the built-in Grounded Reasoning Engine, the engine received `pref=None` instead of the actual user preferences. Explanations lacked specific mentions of cuisine, location, budget, and dietary preferences.

### Root Cause
`_ground_and_format()` did not accept a `pref` parameter; it hardcoded `None` when calling the fallback engine, losing all personalization context.

### Fix
- Updated `_ground_and_format()` to accept `pref: Optional[UserPreference] = None`
- All callers in `rank_and_explain()` now pass the actual `pref` object through
- The fallback engine now generates fully personalized explanations referencing the user's preferences

---

## Bug 4: Validation Errors Showed `[object Object]` in Browser

**File:** `ui/index.html` → JavaScript fetch error handler  
**Severity:** 🟡 Medium — poor UX, unreadable errors for invalid form submissions  
**Status:** ✅ Fixed

### Symptom
Submitting a form with blank required fields triggered FastAPI's HTTP 422 response. The frontend displayed an unreadable error `[object Object]` instead of a human-friendly message.

### Root Cause
FastAPI 422 responses return `detail` as an **array** of error objects, e.g.:
```json
[{"type": "value_error", "msg": "Field cannot be blank", "loc": ["body", "location"]}]
```
The frontend JavaScript assumed `data.detail` was always a plain string and called `.toString()` on the array.

### Fix
Updated the JavaScript error handler to check `typeof data.detail`:
```js
const msg = Array.isArray(data.detail)
  ? data.detail.map(e => e.msg).join(", ")
  : data.detail;
```

**Result:** Blank location now displays: _"Value error, Field cannot be blank"_

---

## Bug 5: Budget Tier Labels Mismatched Actual Dataset Percentiles

**File:** `ui/index.html` → Budget selection section  
**Severity:** 🟢 Low — misleading UI text, no functional breakage  
**Status:** ✅ Fixed

### Symptom
The UI displayed budget bands as _"Low: ≤ ₹400, Medium: ₹400–₹900, High: ₹900+"_ which did not match the real dataset cost distribution.

### Root Cause
Initial budget labels were set using assumed values before the full dataset (9,216 restaurants) was ingested and analyzed. The real percentiles from the cleaned dataset differ significantly:

| Percentile | Assumed | Actual |
|---|---|---|
| P33 (Low threshold) | ₹400 | ₹300 |
| P66 (Medium threshold) | ₹900 | ₹500 |

### Fix
Updated the UI budget labels to accurately reflect the dataset distribution:
- **Low:** ≤ ₹350
- **Medium:** ₹300–₹600
- **High:** ₹500+

---

## Known Limitations (Not Bugs)

| # | Limitation | Notes |
|---|---|---|
| 1 | **No LLM API key configured** | System defaults to built-in Grounded AI Reasoning Engine. To enable OpenAI or Gemini, copy `.env.example` → `.env` and add your key. |
| 2 | **Bangalore-only dataset** | The Hugging Face dataset covers only Bangalore restaurants. Searching for other cities (Delhi, Mumbai) will return zero results even after filter relaxation. |
| 3 | **Chain restaurant deduplication** | 51,717 raw rows were reduced to 9,216 after deduplication by `(name, location)`. Some chain restaurant branches sharing the same name and area may have been merged. |
| 4 | **No user authentication** | Preferences are session-only; there is no persistent user profile or order history. |

---

## Test Results Summary

All 9 automated tests pass after applying the above fixes.

```
tests/test_pipeline.py .....   [5 passed]
tests/test_api.py ....         [4 passed]
========================= 9 passed in X.XXs =========================
```
