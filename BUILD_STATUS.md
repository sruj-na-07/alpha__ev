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
| Cleaning Routes | ✅ Complete | `backend/routes/cleaning.py` |
| Classification Routes | ✅ Complete | `backend/routes/classification.py` |
| Sentiment Routes | ✅ Complete | `backend/routes/sentiment.py` |
| Dashboard Routes | ✅ Complete | `backend/routes/dashboard.py` |
| Chatbot Routes | ✅ Complete | `backend/routes/chatbot.py` |
| Data Cleaning Service | ✅ Complete | `backend/services/cleaning.py` |
| Classifier Service (TF-IDF + Rules) | ✅ Complete | `backend/services/classifier.py` |
| Chatbot Service (SQL-grounded) | ✅ Complete | `backend/services/chatbot.py` |
| Seed Training Data (88 samples) | ✅ Complete | `backend/ml/seed_data.py` |
| Test Pipeline | ✅ Complete | `backend/test_pipeline.py` |
| Sample CSV Data | ✅ Complete | `backend/sample_data/sample_ev_reviews.csv` |

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
