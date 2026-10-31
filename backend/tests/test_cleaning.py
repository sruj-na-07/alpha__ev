"""
Unit tests for AlphaEV Data Cleaning Pipeline.
Validates:
- Preserving raw review data without deletion
- HTML and entity stripping without destroying mathematical comparators (< 20%, > 100kW)
- Mojibake encoding correction (with emojis and accents safely preserved)
- EV technical acronym/code preservation (CCS, NACS, BMS, kWh, OTA, regen, etc.)
- Negation word preservation in meaningful tokens
- Jaccard similarity near-duplicate detection
- Exact duplicate detection
- Low-information and empty text exclusion
- Traceability between original records, cleaned records, and specific exclusion/flagging reasons
- Dedicated cleaning export endpoint
"""

import pytest
from backend.services.cleaning import (
    DataCleaningService,
    cleaning_service,
    clean_html,
    fix_encoding_and_mojibake,
    extract_meaningful_tokens,
    calculate_jaccard_similarity,
    EV_REGEX,
)


@pytest.fixture
def cleaner():
    return cleaning_service


def test_mojibake_repair():
    raw = "The carâ€™s battery wonâ€™t charge and driverâ€™s display has glitches."
    repaired, fixed = fix_encoding_and_mojibake(raw)
    assert "car's" in repaired
    assert "won't" in repaired
    assert "driver's" in repaired
    assert fixed is True


def test_mojibake_repair_with_emojis():
    # Must not raise UnicodeEncodeError when emojis or accents are present
    raw = "The carâ€™s range is incredible! 🚗⚡ Highly recommend Ã©lectric vehicles."
    repaired, fixed = fix_encoding_and_mojibake(raw)
    assert "car's" in repaired
    assert "électric" in repaired
    assert "🚗⚡" in repaired
    assert fixed is True


def test_html_stripping(cleaner):
    raw = "<p>Great vehicle! <br/>Range was <b>excellent</b> &amp; fast charging. <!-- comment --></p>"
    stripped, removed = clean_html(raw)
    assert "<p>" not in stripped
    assert "<b>" not in stripped
    assert "&amp;" not in stripped
    assert "<!-- comment -->" not in stripped
    assert "Great vehicle!" in stripped
    assert "fast charging." in stripped
    assert removed is True

    # Full clean single text collapses whitespace after HTML removal
    cleaned, flags_info = cleaner.clean_single_text(raw)
    assert cleaned == "Great vehicle! Range was excellent & fast charging."
    assert flags_info["html_removed"] is True


def test_html_stripping_preserves_mathematical_comparators(cleaner):
    # Critical requirement: Math comparators like '< 20%' or '> 100kW' must NOT be stripped as HTML
    raw = "Battery level is < 20% and charging speed is > 100kW at DC fast charger."
    stripped, removed = clean_html(raw)
    assert "< 20%" in stripped
    assert "> 100kW" in stripped
    assert stripped == raw
    assert removed is False

    cleaned, flags_info = cleaner.clean_single_text(raw)
    assert "< 20%" in cleaned
    assert "> 100kW" in cleaned
    assert flags_info["html_removed"] is False


def test_url_removal(cleaner):
    raw = "Great car but check my promo link https://ev-referrals.com/deal123 for $500 off!"
    cleaned, flags_info = cleaner.clean_single_text(raw)
    assert "https://ev-referrals.com" not in cleaned
    assert "Great car but check my promo link" in cleaned
    assert flags_info["url_removed"] is True


def test_ev_technical_terms_preservation(cleaner):
    text = "Charged from 10% to 80% SOC using 350kW DCFC CCS2 stall. BMS managed thermal cooling well with Heat Pump. Got error CP_a054."
    matches = EV_REGEX.findall(text)
    assert len(matches) > 0

    cleaned, flags_info = cleaner.clean_single_text(text)
    assert "SOC" in cleaned or "soc" in cleaned.lower()
    assert "CCS2" in cleaned or "ccs2" in cleaned.lower()
    assert "DCFC" in cleaned or "dcfc" in cleaned.lower()
    assert "BMS" in cleaned or "bms" in cleaned.lower()
    assert "CP_a054" in cleaned


def test_negations_preservation_in_tokens():
    # Negations must be retained as meaningful tokens
    text = "The charger was not working and I could not connect."
    tokens = extract_meaningful_tokens(text)
    assert "not" in tokens
    assert "charger" in tokens
    assert "working" in tokens
    assert "connect" in tokens


def test_process_reviews_and_duplicate_detection(cleaner):
    reviews = [
        {"id": "r1", "original_text": "The Tesla Model 3 charging speed is amazing on the Supercharger network."},
        {"id": "r2", "original_text": "The Tesla Model 3 charging speed is amazing on the Supercharger network."},  # Exact
        {"id": "r3", "original_text": "The Tesla Model 3 charging speed is really amazing on the Supercharger network."},  # Near (8/9 = 88.9% Jaccard)
        {"id": "r4", "original_text": "Completely different text about interior cabin road noise and rattles."},
    ]
    processed, stats = cleaner.process_reviews(reviews)
    assert stats["total_reviews"] == 4
    assert stats["exact_duplicates"] == 1
    assert stats["near_duplicates"] >= 1

    r2 = next(r for r in processed if r["id"] == "r2")
    assert r2["is_duplicate"] is True
    assert r2["duplicate_of"] == "r1"
    # Verify exclusion flag and reason
    dup_flag = next(f for f in r2["flags"] if f["type"] == "exact_duplicate")
    assert dup_flag["action"] == "excluded"
    assert "r1" in dup_flag["reason"]

    r3 = next(r for r in processed if r["id"] == "r3")
    assert r3["is_duplicate"] is True
    assert r3["duplicate_of"] == "r1"
    near_flag = next(f for f in r3["flags"] if f["type"] == "near_duplicate")
    assert near_flag["action"] == "excluded"


def test_empty_text_and_low_info_traceability(cleaner):
    reviews = [
        {"id": "r1", "original_text": ""},  # Empty
        {"id": "r2", "original_text": "   "},  # Blank
        {"id": "r3", "original_text": "Good car."},  # Low info (< 3 meaningful tokens)
        {"id": "r4", "original_text": "I drove 250 miles in cold winter weather with cabin heating on, and the battery dropped faster than estimated."},
    ]
    processed, stats = cleaner.process_reviews(reviews)
    assert stats["total_reviews"] == 4

    r1 = next(r for r in processed if r["id"] == "r1")
    assert r1["is_low_info"] is True
    assert any(f["type"] == "empty_text" and f["action"] == "excluded" for f in r1["flags"])

    r2 = next(r for r in processed if r["id"] == "r2")
    assert r2["is_low_info"] is True
    assert any(f["type"] == "empty_text" and f["action"] == "excluded" for f in r2["flags"])

    r3 = next(r for r in processed if r["id"] == "r3")
    assert r3["is_low_info"] is True
    assert any(f["type"] == "low_info" and f["action"] == "excluded" for f in r3["flags"])

import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db, SessionLocal, Dataset, Review


@pytest.fixture(scope="module")
def api_client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_cleaning_api_routes_and_export(api_client):
    db = SessionLocal()
    dataset_id = f"test-clean-{uuid.uuid4().hex[:8]}"
    ds = Dataset(
        id=dataset_id,
        name="Test Cleaning Dataset",
        filename="test.csv",
        original_filename="test.csv",
        status="uploaded",
        row_count=3,
        column_mapping={"text_column": "text"},
        cleaning_stats={},
    )
    r1 = Review(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        row_index=0,
        original_text="The Tesla Supercharger network charging speed was fantastic and reliable.",
        flags=[],
    )
    r2 = Review(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        row_index=1,
        original_text="<p>Battery was &lt; 20% &amp; speed was &gt; 100kW at charger.</p>",
        flags=[],
    )
    r3 = Review(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        row_index=2,
        original_text="Ok.",
        flags=[],
    )
    db.add_all([ds, r1, r2, r3])
    db.commit()
    db.close()

    # 1. Run cleaning via API
    clean_res = api_client.post(f"/api/v1/datasets/{dataset_id}/clean")
    assert clean_res.status_code == 200
    report = clean_res.json()
    assert report["total_reviews"] == 3
    assert report["cleaned_count"] == 3
    assert report["low_info_count"] == 1
    assert report["html_removed_count"] == 1

    # 2. Test flags_only filter
    all_res = api_client.get(f"/api/v1/datasets/{dataset_id}/reviews")
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3

    flagged_res = api_client.get(f"/api/v1/datasets/{dataset_id}/reviews?flags_only=true")
    assert flagged_res.status_code == 200
    flagged_data = flagged_res.json()
    assert flagged_data["total"] >= 2  # r2 (html) and r3 (low_info)

    # 3. Test dedicated clean export endpoint
    export_res = api_client.get(f"/api/v1/datasets/{dataset_id}/clean/export")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers.get("content-type", "")
    assert "attachment" in export_res.headers.get("content-disposition", "")
    csv_text = export_res.text
    assert "is_excluded" in csv_text
    assert "quality_flags" in csv_text
    assert "Battery was < 20% & speed was > 100kW" in csv_text


