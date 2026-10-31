"""
Full End-to-End API Integration Tests for AlphaEV.
Validates:
- Health and status endpoints
- Dataset upload and column mapping
- Data cleaning and safety (no dropped rows)
- 22-label multi-label classification
- Sentiment and emotion scoring
- Human corrections (audit separation between model prediction and human correction)
- Explainability (SHAP top-K attribution)
- Priority issues and actionable recommendations
- Dashboard statistics calculation
- Multi-sheet Excel and CSV exports
- Chatbot API
- SPA static serving
"""

import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal, Dataset, Review, Prediction


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_health_endpoints(client):
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    r2 = client.get("/api/v1/health")
    assert r2.status_code == 200
    assert r2.json()["status"] == "healthy"


def test_spa_root_and_fallback(client):
    r = client.get("/")
    assert r.status_code == 200
    # Should serve either HTML or online status JSON
    assert "AlphaEV" in r.text or "alphaev" in r.text

    # Route fallback for client-side routing
    r_route = client.get("/upload")
    assert r_route.status_code == 200


def test_model_evaluation_endpoint(client):
    r = client.get("/api/v1/model/evaluation")
    assert r.status_code == 200
    data = r.json()
    assert "overall_exact_match_ratio" in data
    assert "macro_f1" in data
    assert "aspect_metrics" in data
    assert len(data["aspect_metrics"]) == 22


def test_full_pipeline_flow(client):
    # 1. Upload CSV
    csv_content = (
        "review_id,review_text,star_rating,date\n"
        "1,Supercharger fast charging is blazing fast and reliable!,5,2026-01-01\n"
        "2,Horrible panel gaps and paint peeling on delivery.,1,2026-01-02\n"
        "3,Great vehicle with smooth acceleration and quiet cabin.,5,2026-01-03\n"
        "4,Range drops 40% in winter weather with heater on.,2,2026-01-04\n"
        "5,Good.,4,2026-01-05\n"
    )
    files = {"file": ("test_reviews.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/upload", files=files, params={"dataset_name": "Integration Test Dataset"})
    assert upload_res.status_code == 200
    dataset_info = upload_res.json()
    dataset_id = dataset_info["dataset_id"]
    assert dataset_id is not None
    assert dataset_info["row_count"] == 5

    # 2. Get Columns
    cols_res = client.get(f"/api/v1/datasets/{dataset_id}/columns")
    assert cols_res.status_code == 200
    assert "review_text" in cols_res.json()["columns"]

    # 3. Map Columns
    map_res = client.post(
        f"/api/v1/datasets/{dataset_id}/map-columns",
        json={
            "text_column": "review_text",
            "rating_column": "star_rating",
            "date_column": "date",
        }
    )
    assert map_res.status_code == 200
    assert map_res.json()["status"] == "uploaded"

    # 4. Clean Dataset
    clean_res = client.post(f"/api/v1/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200
    cleaning_report = clean_res.json()
    assert cleaning_report["total_reviews"] == 5
    assert cleaning_report["cleaned_count"] == 5
    assert cleaning_report["low_info_count"] >= 1  # "Good." is low info

    # 5. Check Cleaning Report
    rep_res = client.get(f"/api/v1/datasets/{dataset_id}/cleaning-report")
    assert rep_res.status_code == 200

    # 6. Reviews listing (verify all 5 rows preserved!)
    revs_res = client.get(f"/api/v1/datasets/{dataset_id}/reviews?page_size=10")
    assert revs_res.status_code == 200
    reviews = revs_res.json()["reviews"]
    assert len(reviews) == 5

    # 7. Classify Aspects
    clf_res = client.post(f"/api/v1/datasets/{dataset_id}/classify", params={"threshold": 0.25})
    assert clf_res.status_code == 200
    clf_data = clf_res.json()
    assert clf_data["reviews_classified"] >= 4

    # 8. Sentiment & Emotion Analysis
    sent_res = client.post(f"/api/v1/datasets/{dataset_id}/analyze-sentiment")
    assert sent_res.status_code == 200
    sent_data = sent_res.json()
    assert sent_data["total_analyzed"] >= 4

    # 9. Get Predictions & Verify Human Correction Separation
    preds_res = client.get(f"/api/v1/datasets/{dataset_id}/predictions")
    assert preds_res.status_code == 200
    predictions = preds_res.json()
    assert len(predictions) > 0

    first_pred = predictions[0]
    pred_id = first_pred["id"]
    original_aspect = first_pred["aspect"]
    original_conf = first_pred["confidence"]

    # Perform Human Correction
    correction_res = client.put(
        f"/api/v1/predictions/{pred_id}",
        json={
            "aspect": "reliability",
            "polarity": "pos",
            "confidence": 0.99
        }
    )
    assert correction_res.status_code == 200
    corrected = correction_res.json()
    assert corrected["is_human_corrected"] is True
    assert corrected["aspect"] == "reliability"
    assert corrected["model_prediction"] is not None
    assert corrected["model_confidence"] is not None

    # 10. Explainability (SHAP feature attribution)
    sample_rev_id = reviews[0]["id"]
    explain_res = client.get(f"/api/v1/reviews/{sample_rev_id}/explain")
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert "aspect_explanations" in explain_data

    # 11. Dashboard Analytics, Priority Issues & Recommendations
    dash_res = client.get(f"/api/v1/datasets/{dataset_id}/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "aspect_metrics" in dash_data
    assert "sentiment_distribution" in dash_data
    assert "emotion_distribution" in dash_data
    assert "priority_issues" in dash_data
    assert "recommendations" in dash_data
    assert dash_data["total_reviews"] == 5

    # 12. Chatbot Query
    chat_res = client.post(
        f"/api/v1/datasets/{dataset_id}/chat",
        json={"message": "What is the charging experience like?"}
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "answer" in chat_data
    assert "evidence" in chat_data

    # 13. CSV and Multi-Sheet Excel Exports
    csv_exp = client.get(f"/api/v1/datasets/{dataset_id}/export?format=csv")
    assert csv_exp.status_code == 200
    assert len(csv_exp.content) > 0

    xlsx_exp = client.get(f"/api/v1/datasets/{dataset_id}/export?format=xlsx")
    assert xlsx_exp.status_code == 200
    assert len(xlsx_exp.content) > 0
