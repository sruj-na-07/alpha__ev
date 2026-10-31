# AlphaEV Build Status

**Last Updated**: 2026-10-13T22:15 IST  
**Project**: Explainable AI-Powered EV Review Intelligence Platform

---

## Architecture Overview

- **Backend**: FastAPI + SQLite + SQLAlchemy + scikit-learn (TF-IDF + LogisticRegression)
- **Frontend**: React 19 + TypeScript + Vite + TailwindCSS + Recharts
- **ML Pipeline**: 11 aspects × 2 polarities = 22-class multi-label classifier with keyword fallback
- **Sentiment**: Rule-based sentiment + emotion analysis with negation handling
- **Chatbot**: SQL-grounded intent parser (no LLM, no hallucination)

---

## Component Status

### Backend (FastAPI) — ✅ COMPLETE

| Component | Status | File |
|---|---|---|
| Database Models (SQLAlchemy) | ✅ Complete | `backend/database.py` |
| Pydantic Schemas | ✅ Complete | `backend/models.py` |
| Upload Routes | ✅ Complete | `backend/routes/upload.py` |
| Cleaning Routes & Dedicated Export | ✅ Verified | `backend/routes/cleaning.py` |
| Classification Routes | ✅ Complete | `backend/routes/classification.py` |
| Sentiment Routes | ✅ Complete | `backend/routes/sentiment.py` |
| Dashboard Routes | ✅ Complete | `backend/routes/dashboard.py` |
| Chatbot Routes | ✅ Complete | `backend/routes/chatbot.py` |
| Data Cleaning Service (Mojibake, HTML Math Protection, Exclusion/Flag Traceability) | ✅ Verified | `backend/services/cleaning.py` |
| Classifier Service (TF-IDF + Rules) | ✅ Complete | `backend/services/classifier.py` |
| Chatbot Service (SQL-grounded) | ✅ Complete | `backend/services/chatbot.py` |
| Seed Training Data (88 samples) | ✅ Complete | `backend/ml/seed_data.py` |
| Test Pipeline | ✅ Complete | `backend/test_pipeline.py` |
| Sample CSV Data | ✅ Complete | `backend/sample_data/sample_ev_reviews.csv` |

---

## Cleaning Module Implementation & Verification Status

### Deficiencies Identified & Addressed
1. **Mojibake Decoder UnicodeEncodeError Bug**:
   - *Previous*: `text.encode("latin-1").decode("utf-8")` raised unhandled `UnicodeEncodeError` when text contained emojis alongside mojibake sequences, silently abandoning decoding for the entire string.
   - *Fix*: Comprehensive 40-item `MOJIBAKE_MAP` covering quotes, hyphens, accents, and symbols. Added regex-targeted byte chunk decoding `_safe_repair_mojibake_bytes` on `[\xc0-\xff][\x80-\xbf]+` with fallback to Windows-1252/Latin-1, preserving emojis and non-Latin-1 characters.
2. **HTML Stripping False Positives on Mathematical Comparators**:
   - *Previous*: Generic regex `<[^>]+>` stripped mathematical comparators common in EV reviews (e.g., `battery < 20% and charging speed > 100kW`).
   - *Fix*: Implemented `HTML_TAG_PATTERN` targeting `<(?:!--[\s\S]*?--|/?(?:[a-zA-Z][a-zA-Z0-9]*)\b[^>]*>)` and `SCRIPT_STYLE_PATTERN` for script/style blocks. Mathematical comparators (`< 20%`, `> 100kW`) are strictly preserved. Entities (`&amp;`, `&lt;`, `&gt;`) are unescaped.
3. **URL & Spam Cleanup**:
   - Added `URL_PATTERN` detection to strip promotional web links and flag records with `url_removed`.
4. **Distinction Between Excluded vs. Flagged Records**:
   - *Excluded Records* (`action: "excluded"`): Exact duplicates (SHA-256), near duplicates (Jaccard >= 0.85), empty/blank text (`empty_text`), and low-information reviews (< 3 meaningful tokens).
   - *Flagged Records* (`action: "flagged"`): HTML cleaned, encoding fixed, non-English detected, URL removed. These records are transformed/flagged and retained for downstream analysis.
   - Full traceability metadata (`action` and `reason`) attached to every flag dictionary.
5. **Server-Side Flag Filtering in API**:
   - Updated `GET /api/v1/datasets/{dataset_id}/reviews` with `flags_only: Optional[bool] = Query(None)`.
   - Uses SQLite `func.json_array_length(Review.flags) > 0` and column checks for accurate pagination across flagged reviews.
6. **Dedicated Cleaning Export Route**:
   - Added `GET /api/v1/datasets/{dataset_id}/clean/export` returning a CSV of all reviews with `original_text`, `cleaned_text`, `is_excluded`, `is_duplicate`, `duplicate_of`, `is_low_info`, `language`, and `quality_flags`.

### Test Verification
- **Unit & Integration Tests**: `backend/tests/test_cleaning.py` (10 of 10 passed, 100%)
  - `test_mojibake_repair`: Verified standard mojibake repair.
  - `test_mojibake_repair_with_emojis`: Verified mojibake repair with emojis without `UnicodeEncodeError`.
  - `test_html_stripping`: Verified HTML tag removal and unescaping.
  - `test_html_stripping_preserves_mathematical_comparators`: Verified `< 20%` and `> 100kW` are strictly preserved.
  - `test_url_removal`: Verified removal of promotional links.
  - `test_ev_technical_terms_preservation`: Verified preservation of `SOC`, `CCS2`, `DCFC`, `BMS`, `Heat Pump`, `CP_a054`.
  - `test_negations_preservation_in_tokens`: Verified preservation of `not`, `never`, `cannot` in meaningful tokens.
  - `test_process_reviews_and_duplicate_detection`: Verified exact and near duplicate detection and exclusion flags.
  - `test_empty_text_and_low_info_traceability`: Verified empty text and low info exclusion traceability.
  - `test_cleaning_api_routes_and_export`: Verified cleaning endpoint, `flags_only` filtering, and `/clean/export` CSV download.
- **Full Backend Suite**: `backend/tests/` (39 of 39 passed, 100%)
- **Frontend Production Build**: `npm run build` (`tsc -b && vite build`) passed with exit code 0.

### Frontend (React + Vite) — 🔧 IN PROGRESS

| Component | Status | File |
|---|---|---|
| App Router | ✅ Complete | `frontend/src/App.tsx` |
| Layout Component | ✅ Complete | `frontend/src/components/Layout.tsx` |
| Alphi Mascot | ✅ Complete | `frontend/src/components/Alphi.tsx` |
| Welcome Page | ✅ Complete | `frontend/src/pages/WelcomePage.tsx` |
| Upload Page | ✅ Complete | `frontend/src/pages/UploadPage.tsx` |
| Cleaning Page | ✅ Complete | `frontend/src/pages/CleaningPage.tsx` |
| Classification Page | ✅ Complete | `frontend/src/pages/ClassificationPage.tsx` |
| Sentiment Page | ✅ Complete | `frontend/src/pages/SentimentPage.tsx` |
| Dashboard Page | ✅ Complete | `frontend/src/pages/DashboardPage.tsx` |
| Chatbot Page | ✅ Complete | `frontend/src/pages/ChatbotPage.tsx` |
| API Client | 🔧 Fixing | `frontend/src/api.ts` — response shapes mismatch backend |

### Infrastructure — 🔧 IN PROGRESS

| Component | Status |
|---|---|
| requirements.txt | 🔧 Creating |
| .gitignore | 🔧 Creating |
| Git repo init | 🔧 Creating |
| Vite proxy config | ✅ Complete (proxies /api to :8000) |
| TailwindCSS config | ✅ Complete |
| TypeScript config | ✅ Complete |

---

## API Endpoints (All Implemented)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/upload` | Upload CSV/XLSX dataset |
| GET | `/api/v1/datasets` | List all datasets |
| GET | `/api/v1/datasets/{id}` | Get dataset by ID |
| GET | `/api/v1/datasets/{id}/columns` | Detect columns + suggest mapping |
| POST | `/api/v1/datasets/{id}/map-columns` | Save column mapping, load reviews |
| GET | `/api/v1/datasets/{id}/preview` | Preview raw rows |
| POST | `/api/v1/datasets/{id}/clean` | Run cleaning pipeline |
| GET | `/api/v1/datasets/{id}/cleaning-status` | Check cleaning progress |
| GET | `/api/v1/datasets/{id}/cleaning-report` | Get cleaning stats report |
| GET | `/api/v1/datasets/{id}/reviews` | Paginated reviews with filters |
| PUT | `/api/v1/reviews/{id}` | Human edit of review |
| POST | `/api/v1/datasets/{id}/classify` | Run 22-label classification |
| GET | `/api/v1/datasets/{id}/predictions` | Get predictions |
| PUT | `/api/v1/predictions/{id}` | Human correction of prediction |
| POST | `/api/v1/reviews/{id}/predictions` | Add manual prediction |
| GET | `/api/v1/reviews/{id}/explain` | SHAP feature attribution |
| POST | `/api/v1/datasets/{id}/analyze-sentiment` | Sentiment + emotion analysis |
| GET | `/api/v1/datasets/{id}/sentiments` | Get sentiments |
| PUT | `/api/v1/sentiments/{id}` | Human correction of sentiment |
| GET | `/api/v1/datasets/{id}/dashboard` | Full dashboard stats |
| GET | `/api/v1/datasets/{id}/export` | Export CSV/XLSX |
| POST | `/api/v1/datasets/{id}/chat` | Chatbot query |

---

## Known Issues Being Fixed

1. **Frontend `api.ts` response types** don't match actual backend responses
2. **`getDatasets()`** returns `{total, datasets}` but frontend expects `Dataset[]`
3. **`getDashboard()`** interface completely mismatches backend `DashboardStatsResponse`
4. **`sendChatMessage()`** response shape mismatch
5. **Missing `requirements.txt`** — no Python dependency file
6. **No git repository** initialized

---

## End-to-End Workflow

1. User visits `/` → Welcome page with project overview
2. Navigates to `/upload` → Uploads CSV/XLSX file
3. Maps columns (text, rating, date, source, reviewer)
4. Navigates to `/dataset/:id/clean` → Runs cleaning pipeline
5. Navigates to `/dataset/:id/classify` → Runs 22-label classification
6. Navigates to `/dataset/:id/sentiment` → Runs sentiment + emotion analysis
7. Navigates to `/dataset/:id/dashboard` → Views analytics dashboard
8. Navigates to `/dataset/:id/chat` → Asks questions about the data
9. Can export results as CSV or XLSX
