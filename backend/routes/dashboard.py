import io
import re
from typing import Any, Dict, List, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import Dataset, Prediction, Review, Sentiment, get_db
from backend.ml.seed_data import ASPECT_DISPLAY_NAMES
from backend.models import (
    ActionableRecommendation,
    AspectMetric,
    CriticalFlagItem,
    DashboardStatsResponse,
    EmotionDistribution,
    FeaturedProblem,
    PriorityIssue,
    QualityMetrics,
    SentimentDistribution,
)
from backend.services.classifier import ASPECT_KEYWORDS
from backend.services.severity import severity_service

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

RECOMMENDATION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "pricing": {
        "title": "Improve Charging Price Transparency",
        "category": "Pricing & Billing",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate concerns about charging fees, "
            "unclear pricing, or unexpected charges."
        ),
        "suggested_action": (
            "Display charging rates, applicable fees, and the estimated "
            "session cost clearly before charging begins. Explain any "
            "price differences between stations and charging plans."
        ),
        "expected_impact": (
            "Improve pricing transparency and reduce billing-related complaints."
        ),
    },
    "payment_issues": {
        "title": "Strengthen Payment and Refund Handling",
        "category": "Payments & Billing",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate payment failures, incorrect deductions, "
            "refund delays, or difficulties completing transactions."
        ),
        "suggested_action": (
            "Investigate failed transactions, provide clear payment status "
            "messages, improve refund tracking, and communicate expected "
            "refund timelines to customers."
        ),
        "expected_impact": (
            "Reduce payment complaints and improve customer trust."
        ),
    },
    "charging_speed": {
        "title": "Improve Charging-Speed Consistency",
        "category": "Charging Performance",
        "priority": "P1 - High",
        "description": (
            "Negative reviews report slow charging or charging performance "
            "that does not meet customer expectations."
        ),
        "suggested_action": (
            "Investigate reported slow sessions, verify charger performance, "
            "and clearly communicate expected charging speeds and factors "
            "that may affect them."
        ),
        "expected_impact": (
            "Improve charging-session consistency and customer satisfaction."
        ),
    },
    "reliability": {
        "title": "Improve Charger Reliability and Uptime",
        "category": "Infrastructure Reliability",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate charger failures, unsuccessful sessions, "
            "or recurring service interruptions."
        ),
        "suggested_action": (
            "Track repeated charger failures, prioritize maintenance for "
            "frequently reported stations, and show clear fault or maintenance "
            "status in the application."
        ),
        "expected_impact": (
            "Reduce repeated charging failures and improve service reliability."
        ),
    },
    "waiting_time": {
        "title": "Reduce Charging Queues and Waiting Times",
        "category": "Customer Experience",
        "priority": "P2 - Medium",
        "description": (
            "Negative reviews indicate long queues, delays, or excessive "
            "waiting before a charging session."
        ),
        "suggested_action": (
            "Display available chargers accurately, communicate expected "
            "waiting times where data is available, and investigate stations "
            "with recurring queue-related complaints."
        ),
        "expected_impact": (
            "Help customers plan charging stops and reduce waiting-related frustration."
        ),
    },
    "app_usability": {
        "title": "Improve Charging-App Usability",
        "category": "Application Experience",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate difficulties using the app, navigating "
            "features, logging in, or completing charging-related actions."
        ),
        "suggested_action": (
            "Review reported usability problems, fix reproducible crashes "
            "and login issues, simplify common charging workflows, and test "
            "the app across supported devices."
        ),
        "expected_impact": (
            "Make charging tasks easier to complete and reduce app-related complaints."
        ),
    },
    "availability": {
        "title": "Improve Live Charger Availability Information",
        "category": "Station Availability",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate unavailable chargers, inaccurate "
            "availability information, or difficulty finding a usable charger."
        ),
        "suggested_action": (
            "Improve synchronization between charger status and the app, "
            "show when availability information was last updated, and "
            "investigate stations with recurring availability complaints."
        ),
        "expected_impact": (
            "Help customers identify usable chargers and avoid unnecessary trips."
        ),
    },
    "location_convenience": {
        "title": "Improve Charging-Station Location Guidance",
        "category": "Location & Navigation",
        "priority": "P2 - Medium",
        "description": (
            "Negative reviews indicate difficulties finding stations, "
            "reaching charging locations, or understanding station directions."
        ),
        "suggested_action": (
            "Verify station coordinates and address details, improve map "
            "directions and access instructions, and provide useful location "
            "information for stations that are difficult to find."
        ),
        "expected_impact": (
            "Make charging stations easier to locate and access."
        ),
    },
    "improvement_suggestion": {
        "title": "Prioritize Customer-Suggested Improvements",
        "category": "Product Improvement",
        "priority": "P2 - Medium",
        "description": (
            "Customer feedback contains suggestions for improving the "
            "charging service or application."
        ),
        "suggested_action": (
            "Review the underlying customer comments, group recurring "
            "suggestions, and prioritize feasible improvements according "
            "to frequency, customer impact, and implementation effort."
        ),
        "expected_impact": (
            "Help prioritize improvements that address recurring customer needs."
        ),
    },
    "overall_experience": {
        "title": "Investigate Overall Charging Experience Complaints",
        "category": "Customer Experience",
        "priority": "P2 - Medium",
        "description": (
            "Negative overall-experience predictions indicate dissatisfaction "
            "that may require further investigation to identify the underlying cause."
        ),
        "suggested_action": (
            "Review supporting comments and their other detected aspects "
            "to identify recurring causes of dissatisfaction before choosing "
            "a corrective action."
        ),
        "expected_impact": (
            "Identify the main sources of dissatisfaction and guide targeted improvements."
        ),
    },
    "customer_support": {
        "title": "Improve Customer Support and Complaint Resolution",
        "category": "Customer Support",
        "priority": "P1 - High",
        "description": (
            "Negative reviews indicate difficulties contacting support, "
            "slow responses, or unresolved customer complaints."
        ),
        "suggested_action": (
            "Track response and resolution times, make support channels "
            "easy to find, provide complaint-status updates, and investigate "
            "recurring unresolved issues."
        ),
        "expected_impact": (
            "Improve complaint resolution and customer confidence in the service."
        ),
    },
}


def compute_priority_issues_and_recommendations(
    dataset_id: str,
    db: Session,
) -> Tuple[List[PriorityIssue], List[ActionableRecommendation]]:
    """Calculate evidence-backed priority issues and recommendations for one dataset."""

    negative_predictions = (
        db.query(Prediction, Review)
        .join(Review, Prediction.review_id == Review.id)
        .filter(
            Review.dataset_id == dataset_id,
            Prediction.polarity == "neg",
        )
        .order_by(Prediction.aspect, Review.row_index, Prediction.id)
        .all()
    )

    review_ids = list({review.id for _, review in negative_predictions})
    sentiments_by_review: Dict[str, Sentiment] = {}

    if review_ids:
        sentiment_records = (
            db.query(Sentiment)
            .filter(Sentiment.review_id.in_(review_ids))
            .order_by(Sentiment.id)
            .all()
        )
        for sentiment in sentiment_records:
            sentiments_by_review.setdefault(sentiment.review_id, sentiment)

    supported_aspects = set(ASPECT_DISPLAY_NAMES.keys())
    aspect_groups: Dict[str, List[Any]] = {}

    for prediction, review in negative_predictions:
        aspect = prediction.aspect
        if aspect not in supported_aspects:
            continue
        sentiment = sentiments_by_review.get(review.id)
        aspect_groups.setdefault(aspect, []).append((prediction, review, sentiment))

    priority_issues: List[PriorityIssue] = []

    for aspect in sorted(aspect_groups):
        items = aspect_groups[aspect]
        display_name = ASPECT_DISPLAY_NAMES[aspect]
        complaint_count = len(items)

        frustration_count = sum(
            1 for _, _, sentiment in items if sentiment and sentiment.emotion == "frustrated"
        )

        ratings = [review.rating for _, review, _ in items if review.rating is not None]
        average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        rating_penalty = (
            max(0.0, 3.0 - average_rating) * 2.0 if average_rating is not None else 0.0
        )
        impact_score = round(
            complaint_count + frustration_count * 1.5 + rating_penalty,
            2,
        )

        if impact_score >= 7.0:
            severity = "Critical"
        elif impact_score >= 3.5:
            severity = "High"
        elif impact_score >= 1.5:
            severity = "Medium"
        else:
            severity = "Low"

        keywords = [keyword.lower() for keyword in ASPECT_KEYWORDS.get(aspect, [])][:5]
        key_drivers = keywords or [display_name.lower()]

        evidence_review = next(
            (review for _, review, _ in items if review is not None),
            None,
        )
        sample_text = ""
        if evidence_review is not None:
            sample_text = evidence_review.cleaned_text or evidence_review.original_text or ""
            sample_text = sample_text.strip()
        sample_evidence = sample_text[:180] if sample_text else None

        if impact_score >= 1.5:
            priority_issues.append(
                PriorityIssue(
                    aspect=aspect,
                    aspect_display=display_name,
                    severity=severity,
                    complaint_count=complaint_count,
                    frustration_count=frustration_count,
                    average_rating=average_rating,
                    impact_score=impact_score,
                    key_drivers=key_drivers,
                    sample_evidence=sample_evidence,
                )
            )

    priority_issues.sort(
        key=lambda issue: (
            {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}[issue.severity],
            issue.impact_score,
            issue.complaint_count,
        ),
        reverse=True,
    )

    recommendations: List[ActionableRecommendation] = []
    for issue in priority_issues[:5]:
        template = RECOMMENDATION_TEMPLATES.get(issue.aspect, {})
        if not template:
            continue
        recommendations.append(
            ActionableRecommendation(
                id=f"{issue.aspect}-{issue.severity.lower()}",
                title=template.get("title", f"Improve {issue.aspect_display}"),
                category=template.get("category", "Operations"),
                priority=template.get("priority", "P2 - Medium"),
                description=template.get(
                    "description",
                    "Review negative customer feedback and improve this experience.",
                ),
                target_aspect=issue.aspect,
                expected_impact=template.get("expected_impact", "Improve customer satisfaction."),
                suggested_action=template.get(
                    "suggested_action",
                    "Investigate the root cause and address recurring complaints.",
                ),
                supporting_review_count=issue.complaint_count,
            )
        )

    return priority_issues, recommendations


def _build_dataset_dashboard_stats(dataset_id: str, db: Session) -> DashboardStatsResponse:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    total_reviews = db.query(Review).filter(Review.dataset_id == dataset_id).count()
    average_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.dataset_id == dataset_id, Review.rating.isnot(None))
        .scalar()
    )
    if average_rating is not None:
        average_rating = round(float(average_rating), 2)

    reviews = db.query(Review).filter(Review.dataset_id == dataset_id).all()
    quality_metrics = QualityMetrics(
        total_rows=total_reviews,
        usable_rows=sum(
            1 for review in reviews if not review.is_duplicate and not review.is_low_info
        ),
        exact_duplicates=sum(1 for review in reviews if review.is_duplicate),
        near_duplicates=sum(
            1
            for review in reviews
            if any((flag or {}).get("type") == "near_duplicate" for flag in (review.flags or []))
        ),
        low_info_reviews=sum(1 for review in reviews if review.is_low_info),
        non_english=sum(
            1
            for review in reviews
            if review.language and review.language.lower() not in {"en", "english"}
        ),
    )

    aspect_metrics: List[AspectMetric] = []
    for aspect in sorted(ASPECT_DISPLAY_NAMES):
        positive_count = (
            db.query(Prediction)
            .join(Review, Prediction.review_id == Review.id)
            .filter(
                Review.dataset_id == dataset_id,
                Prediction.aspect == aspect,
                Prediction.polarity == "pos",
            )
            .count()
        )
        negative_count = (
            db.query(Prediction)
            .join(Review, Prediction.review_id == Review.id)
            .filter(
                Review.dataset_id == dataset_id,
                Prediction.aspect == aspect,
                Prediction.polarity == "neg",
            )
            .count()
        )
        total_count = positive_count + negative_count
        sentiment_ratio = (positive_count / total_count) if total_count else 0.0
        aspect_metrics.append(
            AspectMetric(
                aspect=aspect,
                aspect_display=ASPECT_DISPLAY_NAMES[aspect],
                positive_count=positive_count,
                negative_count=negative_count,
                total_count=total_count,
                sentiment_ratio=round(sentiment_ratio, 2),
            )
        )

    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    scores = (
        db.query(Sentiment)
        .join(Review, Sentiment.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
        .all()
    )
    for item in scores:
        sentiment_counts[item.overall_sentiment] = (
            sentiment_counts.get(item.overall_sentiment, 0) + 1
        )

    sentiment_distribution = []
    total_sentiments = sum(sentiment_counts.values())
    for sentiment_name in ["positive", "negative", "neutral"]:
        count = sentiment_counts.get(sentiment_name, 0)
        sentiment_distribution.append(
            SentimentDistribution(
                sentiment=sentiment_name,
                count=count,
                percentage=round((count / total_sentiments) * 100, 2) if total_sentiments else 0.0,
            )
        )

    emotion_counts = {}
    for item in scores:
        emotion_counts[item.emotion] = emotion_counts.get(item.emotion, 0) + 1

    emotion_distribution = []
    total_emotions = sum(emotion_counts.values())
    for emotion_name, count in sorted(emotion_counts.items()):
        emotion_distribution.append(
            EmotionDistribution(
                emotion=emotion_name,
                count=count,
                percentage=round((count / total_emotions) * 100, 2) if total_emotions else 0.0,
            )
        )

    top_strengths = [
        metric.aspect_display
        for metric in sorted(
            aspect_metrics,
            key=lambda m: (m.positive_count, m.total_count),
            reverse=True,
        )[:3]
    ]
    top_complaints = [
        metric.aspect_display
        for metric in sorted(
            aspect_metrics,
            key=lambda m: (m.negative_count, m.total_count),
            reverse=True,
        )[:3]
    ]

    priority_issues, recommendations = compute_priority_issues_and_recommendations(dataset_id, db)

    # ---------------------------------------------------------
    # Severity-First Critical Issue Prioritization
    # ---------------------------------------------------------
    reviews_for_severity = (
        db.query(Review)
        .filter(Review.dataset_id == dataset_id, Review.cleaned_text.isnot(None))
        .all()
    )
    assessments = []
    for rev in reviews_for_severity:
        ass = severity_service.assess_review(
            review_id=rev.id,
            text=rev.original_text,
            rating=rev.rating,
            cleaned_text=rev.cleaned_text,
        )
        if ass:
            assessments.append(ass)
            if rev.severity_score is None or rev.severity_score != ass.priority_score:
                rev.severity_score = ass.priority_score
                rev.severity_level = ass.severity
                rev.hazard_category = ass.category
                rev.verification_status = ass.verification_status

    try:
        db.commit()
    except Exception:
        db.rollback()

    ranked_clusters, critical_flags_raw = severity_service.group_and_prioritize_issues(assessments)
    top_featured_raw = severity_service.extract_top_featured_problems(ranked_clusters, limit=2)

    featured_problems = [
        FeaturedProblem(
            hazard_key=c.hazard_key,
            title=c.title,
            category=c.category,
            severity=c.severity,
            priority_score=c.priority_score,
            complaint_count=c.complaint_count,
            evidence_confidence=c.evidence_confidence,
            verification_status=c.verification_status,
            urgency=c.urgency,
            potential_harm=c.potential_harm,
            recommended_action=c.recommended_action,
            supporting_review_ids=c.supporting_review_ids,
            supporting_reviews=c.supporting_reviews,
            top_evidence_quote=c.top_evidence_quote,
        )
        for c in top_featured_raw
    ]

    critical_flags = [
        CriticalFlagItem(
            review_id=f["review_id"],
            hazard_key=f["hazard_key"],
            title=f["title"],
            severity=f["severity"],
            priority_score=f["priority_score"],
            evidence_confidence=f["evidence_confidence"],
            verification_status=f["verification_status"],
            potential_harm=f["potential_harm"],
            urgency=f["urgency"],
            evidence_quote=f["evidence_quote"],
            rating=f.get("rating"),
        )
        for f in critical_flags_raw
    ]

    return DashboardStatsResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        total_reviews=total_reviews,
        average_rating=average_rating,
        version=dataset.version,
        is_stale=dataset.is_stale,
        quality_metrics=quality_metrics,
        aspect_metrics=aspect_metrics,
        sentiment_distribution=sentiment_distribution,
        emotion_distribution=emotion_distribution,
        top_strengths=top_strengths,
        top_complaints=top_complaints,
        priority_issues=priority_issues,
        recommendations=recommendations,
        featured_problems=featured_problems,
        critical_flags=critical_flags,
    )


@router.get("/datasets/{dataset_id}/dashboard", response_model=DashboardStatsResponse)
def get_dataset_dashboard_stats(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Return dataset quality, sentiment, and issue-priority dashboards."""
    return _build_dataset_dashboard_stats(dataset_id, db)


@router.get("/datasets/{dataset_id}/export")
def export_dataset_report(
    dataset_id: str,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """
    Exports full dataset analysis as CSV or multi-sheet Excel report.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    reviews = (
        db.query(Review)
        .filter(Review.dataset_id == dataset_id)
        .order_by(Review.row_index)
        .all()
    )

    review_rows = []
    for r in reviews:
        aspects_str = ", ".join(f"{p.aspect}:{p.polarity}" for p in (r.predictions or []))
        sentiment_str = r.sentiment.overall_sentiment if r.sentiment else ""
        emotion_str = r.sentiment.emotion if r.sentiment else ""
        flags_str = "; ".join(f["type"] for f in (r.flags or []))

        review_rows.append({
            "review_id": r.id,
            "row_index": r.row_index,
            "original_text": r.original_text,
            "cleaned_text": r.cleaned_text or "",
            "rating": r.rating,
            "review_date": r.review_date,
            "source": r.source,
            "reviewer": r.reviewer,
            "overall_sentiment": sentiment_str,
            "emotion": emotion_str,
            "predicted_aspects": aspects_str,
            "severity_level": r.severity_level or "None",
            "severity_score": r.severity_score or 0.0,
            "hazard_category": r.hazard_category or "",
            "verification_status": r.verification_status or "unverified_complaint",
            "quality_flags": flags_str,
        })

    df_reviews = pd.DataFrame(review_rows)

    clean_name = re.sub(r"[^\w\-_\. ]", "_", dataset.name).strip().replace(" ", "_")

    if format.lower() == "csv":
        csv_buffer = io.StringIO()
        df_reviews.to_csv(csv_buffer, index=False)
        content = csv_buffer.getvalue().encode("utf-8")
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="alphaev_{clean_name}.csv"'
            },
        )
    elif format.lower() in ["xlsx", "excel"]:
        xlsx_buffer = io.BytesIO()
        with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
            df_reviews.to_excel(writer, sheet_name="Reviews", index=False)

            stats = _build_dataset_dashboard_stats(dataset_id, db)

            aspect_data = [
                {
                    "Aspect": m.aspect_display,
                    "Total": m.total_count,
                    "Positive": m.positive_count,
                    "Negative": m.negative_count,
                    "Sentiment Ratio": m.sentiment_ratio,
                }
                for m in stats.aspect_metrics
            ]
            pd.DataFrame(aspect_data).to_excel(writer, sheet_name="Aspect Metrics", index=False)

            hazards_data = [
                {
                    "Hazard / Problem": p.title,
                    "Category": p.category,
                    "Severity Tier": p.severity,
                    "Priority Score": p.priority_score,
                    "Complaint Count": p.complaint_count,
                    "Confidence": p.evidence_confidence,
                    "Verification Status": p.verification_status,
                    "Urgency": p.urgency,
                    "Potential Harm": p.potential_harm,
                    "Recommended Action": p.recommended_action,
                }
                for p in stats.featured_problems
            ]
            pd.DataFrame(hazards_data).to_excel(writer, sheet_name="Priority Hazards", index=False)

            qm = stats.quality_metrics
            qm_data = [
                {"Metric": "Total Rows", "Value": qm.total_rows},
                {"Metric": "Usable Rows", "Value": qm.usable_rows},
                {"Metric": "Exact Duplicates", "Value": qm.exact_duplicates},
                {"Metric": "Near Duplicates", "Value": qm.near_duplicates},
                {"Metric": "Low Info Reviews", "Value": qm.low_info_reviews},
                {"Metric": "Non-English Reviews", "Value": qm.non_english},
            ]
            pd.DataFrame(qm_data).to_excel(writer, sheet_name="Quality Summary", index=False)

        xlsx_buffer.seek(0)
        return Response(
            content=xlsx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="alphaev_{clean_name}.xlsx"'
            },
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Supported formats: 'csv', 'xlsx'")