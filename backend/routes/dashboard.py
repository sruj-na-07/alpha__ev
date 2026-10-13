import io
from typing import Optional, List, Dict, Any
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from backend.database import get_db, Dataset, Review, Prediction, Sentiment
from backend.models import (
    DashboardStatsResponse,
    AspectMetric,
    SentimentDistribution,
    EmotionDistribution,
    QualityMetrics,
)
from backend.ml.seed_data import ASPECT_DISPLAY_NAMES

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/datasets/{dataset_id}/dashboard", response_model=DashboardStatsResponse)
def get_dataset_dashboard_stats(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """
    Computes all dashboard intelligence metrics directly from actual database records:
    - Aspect-level sentiment ratio (positive vs complaints)
    - Overall sentiment & emotion distributions
    - Rating statistics
    - Data cleaning & quality breakdown
    - Top strengths & top complaint areas
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    total_reviews = db.query(Review).filter(Review.dataset_id == dataset_id).count()

    # Rating computation
    avg_rating_val = (
        db.query(func.avg(Review.rating))
        .filter(Review.dataset_id == dataset_id, Review.rating.isnot(None))
        .scalar()
    )
    average_rating = round(float(avg_rating_val), 2) if avg_rating_val is not None else None

    # Quality metrics
    exact_duplicates = db.query(Review).filter(
        Review.dataset_id == dataset_id, Review.is_duplicate.is_(True)
    ).count()

    near_dups_count = 0
    if dataset.cleaning_stats:
        near_dups_count = dataset.cleaning_stats.get("near_duplicates", 0)

    low_info_count = db.query(Review).filter(
        Review.dataset_id == dataset_id, Review.is_low_info.is_(True)
    ).count()

    non_english_count = db.query(Review).filter(
        Review.dataset_id == dataset_id, Review.language != "en", Review.language.isnot(None)
    ).count()

    usable_rows = max(0, total_reviews - exact_duplicates - low_info_count)

    quality_metrics = QualityMetrics(
        total_rows=total_reviews,
        usable_rows=usable_rows,
        exact_duplicates=exact_duplicates,
        near_duplicates=near_dups_count,
        low_info_reviews=low_info_count,
        non_english=non_english_count,
    )

    # Aspect metrics across all 11 aspects
    aspect_counts: Dict[str, Dict[str, int]] = {
        k: {"pos": 0, "neg": 0} for k in ASPECT_DISPLAY_NAMES.keys()
    }

    preds_query = (
        db.query(Prediction.aspect, Prediction.polarity, func.count(Prediction.id))
        .join(Review, Prediction.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
        .group_by(Prediction.aspect, Prediction.polarity)
        .all()
    )

    for asp, pol, cnt in preds_query:
        if asp in aspect_counts:
            if pol == "pos":
                aspect_counts[asp]["pos"] += cnt
            elif pol == "neg":
                aspect_counts[asp]["neg"] += cnt

    aspect_metrics: List[AspectMetric] = []
    strengths_candidates = []
    complaints_candidates = []

    for asp_key, disp_name in ASPECT_DISPLAY_NAMES.items():
        pos = aspect_counts[asp_key]["pos"]
        neg = aspect_counts[asp_key]["neg"]
        total = pos + neg
        ratio = round(pos / total, 3) if total > 0 else 0.0

        metric = AspectMetric(
            aspect=asp_key,
            aspect_display=disp_name,
            positive_count=pos,
            negative_count=neg,
            total_count=total,
            sentiment_ratio=ratio,
        )
        aspect_metrics.append(metric)

        if total > 0:
            strengths_candidates.append((disp_name, pos, ratio))
            complaints_candidates.append((disp_name, neg))

    # Top strengths sorted by positive count and ratio
    strengths_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    top_strengths = [s[0] for s in strengths_candidates[:3] if s[1] > 0]

    # Top complaints sorted by negative count
    complaints_candidates.sort(key=lambda x: x[1], reverse=True)
    top_complaints = [c[0] for c in complaints_candidates[:3] if c[1] > 0]

    # Sentiment distribution
    sent_query = (
        db.query(Sentiment.overall_sentiment, func.count(Sentiment.id))
        .join(Review, Sentiment.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
        .group_by(Sentiment.overall_sentiment)
        .all()
    )

    sent_counts = {s: 0 for s in ["positive", "negative", "neutral"]}
    total_sent = 0
    for s_label, cnt in sent_query:
        sent_counts[s_label] = cnt
        total_sent += cnt

    sentiment_distribution: List[SentimentDistribution] = []
    for s_name in ["positive", "negative", "neutral"]:
        c = sent_counts.get(s_name, 0)
        pct = round((c / total_sent * 100), 1) if total_sent > 0 else 0.0
        sentiment_distribution.append(
            SentimentDistribution(sentiment=s_name, count=c, percentage=pct)
        )

    # Emotion distribution
    emo_query = (
        db.query(Sentiment.emotion, func.count(Sentiment.id))
        .join(Review, Sentiment.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
        .group_by(Sentiment.emotion)
        .all()
    )

    emo_counts = {e: 0 for e in ["happy", "sad", "frustrated", "satisfaction", "neutral"]}
    total_emo = 0
    for e_label, cnt in emo_query:
        emo_counts[e_label] = cnt
        total_emo += cnt

    emotion_distribution: List[EmotionDistribution] = []
    for e_name in ["happy", "sad", "frustrated", "satisfaction", "neutral"]:
        c = emo_counts.get(e_name, 0)
        pct = round((c / total_emo * 100), 1) if total_emo > 0 else 0.0
        emotion_distribution.append(
            EmotionDistribution(emotion=e_name, count=c, percentage=pct)
        )

    return DashboardStatsResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        total_reviews=total_reviews,
        average_rating=average_rating,
        quality_metrics=quality_metrics,
        aspect_metrics=aspect_metrics,
        sentiment_distribution=sentiment_distribution,
        emotion_distribution=emotion_distribution,
        top_strengths=top_strengths,
        top_complaints=top_complaints,
    )


@router.get("/datasets/{dataset_id}/export")
def export_dataset_results(
    dataset_id: str,
    format: str = Query("csv", regex="^(csv|xlsx)$"),
    db: Session = Depends(get_db),
):
    """
    Export processed dataset reviews, data cleaning flags, predictions,
    and sentiments as CSV or Excel (XLSX).
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    reviews = (
        db.query(Review)
        .options(joinedload(Review.predictions), joinedload(Review.sentiment))
        .filter(Review.dataset_id == dataset_id)
        .order_by(Review.row_index)
        .all()
    )

    rows = []
    for r in reviews:
        # Build predictions string
        aspect_strings = [f"{p.aspect}:{p.polarity}" for p in r.predictions]
        has_human_correction = any(
            p.is_human_corrected for p in r.predictions
        ) or (r.sentiment.is_human_corrected if r.sentiment else False)

        flag_messages = "; ".join([f"{f.get('type')}: {f.get('message')}" for f in (r.flags or [])])

        row_data = {
            "Review ID": r.id,
            "Row Index": r.row_index,
            "Original Text": r.original_text,
            "Cleaned Text": r.cleaned_text or "",
            "Rating": r.rating,
            "Review Date": r.review_date or "",
            "Source": r.source or "",
            "Reviewer": r.reviewer or "",
            "Language": r.language or "",
            "Is Duplicate": "Yes" if r.is_duplicate else "No",
            "Duplicate Of": r.duplicate_of or "",
            "Is Low Info": "Yes" if r.is_low_info else "No",
            "Cleaning Flags": flag_messages,
            "Overall Sentiment": r.sentiment.overall_sentiment if r.sentiment else "",
            "Sentiment Confidence": r.sentiment.sentiment_confidence if r.sentiment else "",
            "Emotion": r.sentiment.emotion if r.sentiment else "",
            "Emotion Confidence": r.sentiment.emotion_confidence if r.sentiment else "",
            "Detected Aspects": ", ".join(aspect_strings),
            "Human Corrected": "Yes" if has_human_correction else "No",
        }
        rows.append(row_data)

    df = pd.DataFrame(rows)
    safe_name = "".join(c for c in dataset.name if c.isalnum() or c in (" ", "_", "-")).rstrip()

    if format == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}_export.csv"'
        return response

    elif format == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="AlphaEV Reviews")
        output.seek(0)
        response = StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}_export.xlsx"'
        return response
