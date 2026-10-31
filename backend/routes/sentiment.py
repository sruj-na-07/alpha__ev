from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db, Dataset, Review, Sentiment
from backend.models import (
    SentimentResponse,
    SentimentUpdateRequest,
)
from backend.services.classifier import classifier_service

router = APIRouter(prefix="/api/v1", tags=["sentiment"])


@router.post("/datasets/{dataset_id}/analyze-sentiment", response_model=Dict[str, Any])
def analyze_dataset_sentiment(
    dataset_id: str,
    skip_duplicates: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Run overall sentiment (positive/negative/neutral) and emotion analysis
    (happy/sad/frustrated/satisfaction/neutral) on dataset reviews.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if dataset.status not in {"classified", "complete"}:
        raise HTTPException(
            status_code=400,
            detail="Please complete aspect classification before sentiment and emotion analysis.",
        )

    # Use exactly the same eligible-review criteria as aspect classification.
    reviews_query = db.query(Review).filter(
        Review.dataset_id == dataset_id,
        Review.is_low_info.is_(False),
        func.trim(func.coalesce(Review.cleaned_text, Review.original_text, "")) != "",
    )
    if skip_duplicates:
        reviews_query = reviews_query.filter(Review.is_duplicate.is_(False))

    reviews = reviews_query.all()
    if not reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found to analyze sentiment. Please upload or map columns first.",
        )

    # Existing sentiments
    existing_sentiments = {
        s.review_id: s
        for s in db.query(Sentiment)
        .join(Review, Sentiment.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
        .all()
    }

    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    emotion_counts = {
        "happy": 0,
        "sad": 0,
        "frustrated": 0,
        "satisfaction": 0,
        "neutral": 0,
    }

    new_objects: List[Sentiment] = []

    for r in reviews:
        # If user already corrected sentiment manually, preserve it
        existing = existing_sentiments.get(r.id)
        if existing and existing.is_human_corrected:
            sentiment_counts[existing.overall_sentiment] = sentiment_counts.get(existing.overall_sentiment, 0) + 1
            emotion_counts[existing.emotion] = emotion_counts.get(existing.emotion, 0) + 1
            continue

        text = r.cleaned_text or r.original_text or ""
        sentiment_label, sent_conf = classifier_service.rule_sentiment.analyze_sentiment(
            text, rating=r.rating
        )
        emotion_label, emo_conf = classifier_service.rule_sentiment.analyze_emotion(
            text, overall_sentiment=sentiment_label
        )

        sentiment_counts[sentiment_label] = sentiment_counts.get(sentiment_label, 0) + 1
        emotion_counts[emotion_label] = emotion_counts.get(emotion_label, 0) + 1

        if existing:
            existing.overall_sentiment = sentiment_label
            existing.sentiment_confidence = sent_conf
            existing.emotion = emotion_label
            existing.emotion_confidence = emo_conf
            existing.is_human_corrected = False
        else:
            s_obj = Sentiment(
                review_id=r.id,
                overall_sentiment=sentiment_label,
                sentiment_confidence=sent_conf,
                emotion=emotion_label,
                emotion_confidence=emo_conf,
                is_human_corrected=False,
            )
            new_objects.append(s_obj)

    if new_objects:
        db.bulk_save_objects(new_objects)

    if dataset.status == "classified":
        dataset.status = "complete"
    dataset.is_stale = False

    db.commit()
    db.refresh(dataset)

    return {
        "dataset_id": dataset.id,
        "total_analyzed": len(reviews),
        "sentiment_counts": sentiment_counts,
        "emotion_counts": emotion_counts,
    }


@router.get("/datasets/{dataset_id}/sentiments", response_model=List[SentimentResponse])
def get_dataset_sentiments(
    dataset_id: str,
    sentiment: Optional[str] = None,
    emotion: Optional[str] = None,
    is_human_corrected: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    """Retrieve analyzed sentiments and emotions for reviews in a dataset."""
    query = (
        db.query(Sentiment)
        .join(Review, Sentiment.review_id == Review.id)
        .filter(
            Review.dataset_id == dataset_id,
            Review.is_duplicate.is_(False),
            Review.is_low_info.is_(False),
            func.trim(func.coalesce(Review.cleaned_text, Review.original_text, "")) != "",
        )
    )

    if sentiment:
        query = query.filter(Sentiment.overall_sentiment == sentiment)
    if emotion:
        query = query.filter(Sentiment.emotion == emotion)
    if is_human_corrected is not None:
        query = query.filter(Sentiment.is_human_corrected == is_human_corrected)

    return query.offset(skip).limit(limit).all()


@router.put("/sentiments/{sentiment_id}", response_model=SentimentResponse)
def update_sentiment(
    sentiment_id: int,
    update_data: SentimentUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Human correction of a sentiment and emotion record.
    Marks is_human_corrected=True.
    """
    s_record = db.query(Sentiment).filter(Sentiment.id == sentiment_id).first()
    if not s_record:
        raise HTTPException(status_code=404, detail="Sentiment record not found.")

    s_record.overall_sentiment = update_data.overall_sentiment
    s_record.emotion = update_data.emotion
    if update_data.sentiment_confidence is not None:
        s_record.sentiment_confidence = update_data.sentiment_confidence
    if update_data.emotion_confidence is not None:
        s_record.emotion_confidence = update_data.emotion_confidence
    s_record.is_human_corrected = True

    db.commit()
    db.refresh(s_record)
    return s_record