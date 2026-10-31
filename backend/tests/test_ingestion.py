"""
Tests for AlphaEV Dynamic Review Ingestion Service and API endpoints.

Verifies:
1. API authentication: Valid API key accepted, invalid or missing key returns 401.
2. Idempotency & deduplication: Re-ingesting reviews skips duplicates without error or double-insertion.
3. Pipeline reuse: Ingested reviews are cleaned, classified for aspects, sentiment scored, and severity assessed.
4. Telemetry status: GET /api/v1/ingestion/status returns live connection health and history.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.ingestion import DEFAULT_INGESTION_KEY

client = TestClient(app)


def test_ingestion_authentication():
    """Verify webhook endpoint rejects unauthorized requests and accepts valid API keys."""
    uid = uuid.uuid4().hex[:8]
    sample_payload = {
        "source": f"ev_pulse_{uid}",
        "reviews": [
            {
                "external_review_id": f"ext_{uid}_001",
                "text": "Great charger speed, reached 80% quickly.",
                "rating": 5.0,
            }
        ],
    }

    # 1. Missing authentication
    res_no_auth = client.post("/api/v1/ingestion/reviews", json=sample_payload)
    assert res_no_auth.status_code == 401

    # 2. Invalid API key header
    res_bad_auth = client.post(
        "/api/v1/ingestion/reviews",
        json=sample_payload,
        headers={"X-API-Key": "wrong-secret-key"},
    )
    assert res_bad_auth.status_code == 401

    # 3. Valid API key header
    res_ok = client.post(
        "/api/v1/ingestion/reviews",
        json=sample_payload,
        headers={"X-API-Key": DEFAULT_INGESTION_KEY},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["total_received"] == 1
    assert data["total_inserted"] == 1
    assert data["status"] == "success"


def test_ingestion_idempotency_and_deduplication():
    """Verify that re-submitting identical external_review_ids skips duplicates safely."""
    uid = uuid.uuid4().hex[:8]
    payload = {
        "source": f"chargepoint_{uid}",
        "api_key": DEFAULT_INGESTION_KEY,
        "reviews": [
            {
                "external_review_id": f"cp_{uid}_101",
                "text": "Fast 50kW charging session without issues.",
                "rating": 5.0,
            },
            {
                "external_review_id": f"cp_{uid}_102",
                "text": "App crashed during payment processing.",
                "rating": 2.0,
            },
        ],
    }

    # First delivery: Should insert 2 reviews
    res_first = client.post("/api/v1/ingestion/reviews", json=payload)
    assert res_first.status_code == 200
    data_first = res_first.json()
    assert data_first["total_inserted"] == 2
    assert data_first["total_duplicates"] == 0

    # Second delivery with exact same external IDs: Should be 2 duplicates skipped
    res_second = client.post("/api/v1/ingestion/reviews", json=payload)
    assert res_second.status_code == 200
    data_second = res_second.json()
    assert data_second["total_inserted"] == 0
    assert data_second["total_duplicates"] == 2
    assert all(r["status"] == "duplicate" for r in data_second["results"])


def test_ingestion_severe_hazard_flagging():
    """Verify ingested reviews describing severe safety hazards are evaluated by severity service."""
    uid = uuid.uuid4().hex[:8]
    severe_payload = {
        "source": f"emergency_{uid}",
        "reviews": [
            {
                "external_review_id": f"hazard_{uid}_999",
                "text": "Warning! Sparks and smoke came out of the CCS2 gun and the connector pins melted!",
                "rating": 1.0,
            }
        ],
    }

    res = client.post(
        "/api/v1/ingestion/reviews",
        json=severe_payload,
        headers={"X-API-Key": DEFAULT_INGESTION_KEY},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_inserted"] == 1
    hazard_item = data["results"][0]
    assert hazard_item["severity_level"] == "Critical"
    assert hazard_item["priority_score"] >= 80.0


def test_ingestion_status_telemetry():
    """Verify telemetry endpoint reports live connection status and audit logs."""
    res = client.get("/api/v1/ingestion/status")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is True
    assert "total_received" in data
    assert "total_processed" in data
    assert isinstance(data["recent_syncs"], list)
    assert len(data["recent_syncs"]) >= 1
