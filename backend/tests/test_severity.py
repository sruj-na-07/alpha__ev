"""
Unit and integration tests for AlphaEV Severity-First Critical Issue Prioritization.

Verifies:
1. Low-frequency severe issues (1 complaint of arcing/fire) outrank high-frequency minor issues (50 complaints of wait time).
2. Evidence confidence scoring reflects technical specificity, review length, and rating consistency.
3. Preservation of scientific uncertainty: unverified complaints are never marked as confirmed incidents.
4. Issue clustering retains distinct review IDs and verbatim evidence quotes.
5. Top 2 featured problems extraction handles 0, 1, or 2+ critical issues without false labeling.
"""

import pytest
from backend.services.severity import (
    assess_review_severity,
    calculate_evidence_confidence,
    group_and_prioritize_issues,
    extract_top_featured_problems,
    HAZARD_TAXONOMY,
    ProblemCluster,
    ReviewSeverityAssessment,
)


def test_evidence_confidence_calculation():
    """Verify evidence confidence increases with technical EV terms, review detail, and rating alignment."""
    # Low detail, no technical terms
    conf_vague = calculate_evidence_confidence("It broke.", rating=3)
    assert 0.50 <= conf_vague <= 0.65

    # Rich technical detail with low rating (consistent with a severe defect)
    detailed_text = (
        "During 150kW DC fast charging on the CCS2 plug, severe sparks and electrical arcing "
        "erupted from the contactor pins. The connector housing began melting and smelling burned. "
        "Emergency stop button failed to disengage."
    )
    conf_technical = calculate_evidence_confidence(detailed_text, rating=1)
    assert conf_technical >= 0.85
    assert conf_technical > conf_vague


def test_single_severe_issue_outranks_many_minor_complaints():
    """Requirement 1 core test: A single credible severe hazard must outrank 50 minor complaints."""
    # 1 critical review: sparking and melting pins
    critical_review = {
        "id": 999,
        "clean_text": (
            "Dangerous situation at charger #3! Sparks and smoke came out of the CCS2 connector "
            "as soon as charging started. The plastic around the pins melted. Extremely unsafe!"
        ),
        "rating": 1,
        "station_name": "Highway Express Hub",
    }

    # 50 minor reviews complaining about queue wait times
    minor_reviews = [
        {
            "id": i,
            "clean_text": f"Too long wait time, had to wait in queue for 40 minutes at charger #{i%4 + 1}.",
            "rating": 3,
            "station_name": "Downtown Mall Station",
        }
        for i in range(1, 51)
    ]

    all_reviews = [critical_review] + minor_reviews
    assessments = [
        assess_review_severity(r["id"], r["clean_text"], rating=r["rating"])
        for r in all_reviews
    ]
    # Filter out any non-matches (though all should match)
    valid_assessments = [a for a in assessments if a is not None]

    ranked_clusters, critical_flags = group_and_prioritize_issues(valid_assessments)

    assert len(ranked_clusters) >= 2
    top_cluster = ranked_clusters[0]

    # The top-ranked issue MUST be the electrical hazard, NOT the 50 queue complaints
    assert top_cluster.hazard_key == "electrical_thermal_hazard"
    assert top_cluster.severity == "Critical"
    assert top_cluster.complaint_count == 1
    assert "999" in top_cluster.supporting_review_ids

    # Find the queue cluster
    queue_cluster = next((c for c in ranked_clusters if c.hazard_key == "queue_waiting_time"), None)
    assert queue_cluster is not None
    assert queue_cluster.complaint_count == 50
    assert top_cluster.priority_score > queue_cluster.priority_score


def test_preservation_of_scientific_uncertainty():
    """Reviews must default to unverified_complaint and not be labeled as confirmed incidents."""
    review_text = "I saw some smoke and smelled burning from the plug."
    assessment = assess_review_severity(101, review_text, rating=1)

    assert assessment is not None
    assert assessment.severity == "Critical"
    assert assessment.verification_status == "unverified_complaint"
    assert "Unverified Customer Complaint" in assessment.status_display
    assert "inspection" in assessment.status_display.lower()


def test_clustering_preserves_review_ids_and_evidence():
    """Clusters must retain all review IDs and verbatim quotes without information loss."""
    reviews = [
        {
            "id": 1,
            "text": "The lock pin failed and the CCS plug got stuck in my car port. Could not unplug!",
            "rating": 1,
        },
        {
            "id": 2,
            "text": "Gun stuck in vehicle port, connector won't release. Had to call towing.",
            "rating": 1,
        },
    ]

    assessments = [
        assess_review_severity(r["id"], r["text"], rating=r["rating"])
        for r in reviews
    ]
    valid_assessments = [a for a in assessments if a is not None]

    clusters, _ = group_and_prioritize_issues(valid_assessments)
    lock_cluster = next((c for c in clusters if c.hazard_key == "vehicle_trapped_lock_failure"), None)

    assert lock_cluster is not None
    assert lock_cluster.complaint_count == 2
    assert set(lock_cluster.supporting_review_ids) == {"1", "2"}
    assert len(lock_cluster.supporting_reviews) == 2
    assert any("stuck in my car port" in ev["quote"] for ev in lock_cluster.supporting_reviews)
    assert any("Had to call towing" in ev["quote"] for ev in lock_cluster.supporting_reviews)


def test_top_featured_problems_selection():
    """Test top 2 featured problem extraction with varying hazard availability."""
    # Scenario A: 1 Critical and 1 High hazard exist
    clusters_a = [
        ProblemCluster(
            hazard_key="electrical_thermal_hazard",
            title="Electrical Arcing",
            category="Physical Safety Hazard",
            severity="Critical",
            potential_harm="Shock risk",
            urgency="Urgent",
            priority_score=92.5,
            complaint_count=1,
            evidence_confidence=0.90,
            verification_status="unverified_complaint",
            recommended_action="Inspect contactor",
            supporting_review_ids=["1"],
            supporting_reviews=[],
            top_evidence_quote="Sparks observed.",
        ),
        ProblemCluster(
            hazard_key="vehicle_trapped_lock_failure",
            title="Vehicle Trapped",
            category="Operational Entrapment",
            severity="High",
            potential_harm="Immobilization",
            urgency="Urgent",
            priority_score=78.0,
            complaint_count=2,
            evidence_confidence=0.85,
            verification_status="unverified_complaint",
            recommended_action="Release solenoid",
            supporting_review_ids=["2", "3"],
            supporting_reviews=[],
            top_evidence_quote="Connector stuck.",
        ),
        ProblemCluster(
            hazard_key="queue_waiting_time",
            title="Long Queues",
            category="Customer Experience",
            severity="Low",
            potential_harm="Convenience",
            urgency="Low",
            priority_score=25.0,
            complaint_count=40,
            evidence_confidence=0.60,
            verification_status="unverified_complaint",
            recommended_action="Add bays",
            supporting_review_ids=[str(i) for i in range(4, 44)],
            supporting_reviews=[],
            top_evidence_quote="Long queue.",
        ),
    ]

    featured = extract_top_featured_problems(clusters_a)
    assert len(featured) == 2
    assert featured[0]["hazard_key"] == "electrical_thermal_hazard"
    assert featured[0]["severity"] == "Critical"
    # Second problem is High, NOT falsely labeled as Critical
    assert featured[1]["hazard_key"] == "vehicle_trapped_lock_failure"
    assert featured[1]["severity"] == "High"

    # Scenario B: Empty clusters
    assert extract_top_featured_problems([]) == []
