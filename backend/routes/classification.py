from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db, Dataset, Review, Prediction
from backend.models import (
    PredictionResponse,
    PredictionUpdateRequest,
    PredictionCreateRequest,
    ExplainResponse,
)
from backend.services.classifier import classifier_service

router = APIRouter(prefix="/api/v1", tags=["classification"])


@router.post("/datasets/{dataset_id}/classify", response_model=Dict[str, Any])
def classify_dataset_reviews(
    dataset_id: str,
    threshold: float = Query(0.35, ge=0.1, le=0.9),
    skip_duplicates: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Run multi-label aspect and polarity classification (11 aspects x 2 polarities = 22 classes)
    on all reviews in the dataset using TF-IDF + LogisticRegression with keyword fallback.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    reviews_query = db.query(Review).filter(Review.dataset_id == dataset_id)
    if skip_duplicates:
        reviews_query = reviews_query.filter(Review.is_duplicate.is_(False))

    reviews = reviews_query.all()
    if not reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews to classify. Ensure dataset has reviews uploaded.",
        )

    dataset.status = "classifying"
    db.commit()

    # Clear prior non-human corrected predictions for this dataset
    db.query(Prediction).filter(
        Prediction.review_id.in_(
            db.query(Review.id).filter(Review.dataset_id == dataset_id)
        ),
        Prediction.is_human_corrected.is_(False),
    ).delete(synchronize_session=False)

    total_predictions = 0
    new_predictions: List[Prediction] = []

    for r in reviews:
        text_to_analyze = (r.cleaned_text or r.original_text or "").strip()
        if not text_to_analyze:
            continue

        preds = classifier_service.predict(text_to_analyze, threshold=threshold)
        for p in preds:
            pred_obj = Prediction(
                review_id=r.id,
                aspect=p["aspect"],
                polarity=p["polarity"],
                confidence=p["confidence"],
                is_human_corrected=False,
                model_prediction=p.get("model_prediction", f"{p['aspect']}:{p['polarity']}"),
                model_confidence=p.get("model_confidence", p["confidence"]),
            )
            new_predictions.append(pred_obj)
            total_predictions += 1

    if new_predictions:
        db.bulk_save_objects(new_predictions)

    dataset.status = "classified"
    db.commit()
    db.refresh(dataset)

    return {
        "dataset_id": dataset.id,
        "status": dataset.status,
        "reviews_classified": len(reviews),
        "total_predictions_generated": total_predictions,
    }


@router.get("/datasets/{dataset_id}/predictions", response_model=List[PredictionResponse])
def get_dataset_predictions(
    dataset_id: str,
    aspect: Optional[str] = None,
    polarity: Optional[str] = None,
    is_human_corrected: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve predictions for a dataset with optional filters."""
    query = (
        db.query(Prediction)
        .join(Review, Prediction.review_id == Review.id)
        .filter(Review.dataset_id == dataset_id)
    )

    if aspect:
        query = query.filter(Prediction.aspect == aspect)
    if polarity:
        query = query.filter(Prediction.polarity == polarity)
    if is_human_corrected is not None:
        query = query.filter(Prediction.is_human_corrected == is_human_corrected)

    preds = query.offset(skip).limit(limit).all()
    return preds


@router.put("/predictions/{prediction_id}", response_model=PredictionResponse)
def update_prediction(
    prediction_id: int,
    update_data: PredictionUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Human correction of a model prediction.
    Maintains audit trail: preserves original model_prediction and model_confidence.
    """
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found.")

    pred.aspect = update_data.aspect
    pred.polarity = update_data.polarity
    if update_data.confidence is not None:
        pred.confidence = update_data.confidence
    pred.is_human_corrected = True

    db.commit()
    db.refresh(pred)
    return pred


@router.post("/reviews/{review_id}/predictions", response_model=PredictionResponse)
def add_human_prediction(
    review_id: str,
    new_pred: PredictionCreateRequest,
    db: Session = Depends(get_db),
):
    """Add a manual human aspect prediction to a review."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    pred = Prediction(
        review_id=review.id,
        aspect=new_pred.aspect,
        polarity=new_pred.polarity,
        confidence=new_pred.confidence or 1.0,
        is_human_corrected=True,
        model_prediction=None,
        model_confidence=0.0,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


@router.get("/reviews/{review_id}/explain", response_model=ExplainResponse)
def explain_review_predictions(
    review_id: str,
    top_k: int = Query(5, ge=1, le=15),
    db: Session = Depends(get_db),
):
    """
    Generate SHAP / feature attribution explanations for model predictions on this review.
    Shows words contributing to each detected aspect.
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    text = review.cleaned_text or review.original_text
    explanation = classifier_service.explain(text, top_k=top_k)

    return ExplainResponse(
        review_id=review.id,
        text=text,
        aspect_explanations=explanation["aspect_explanations"],
        summary=explanation["summary"],
    )
