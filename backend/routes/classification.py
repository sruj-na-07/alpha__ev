import io
import re
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db, Dataset, Review, Prediction
from backend.ml.seed_data import ASPECT_DISPLAY_NAMES
from backend.models import (
    PredictionResponse,
    PredictionUpdateRequest,
    PredictionCreateRequest,
    ExplainResponse,
    ModelEvaluationResponse,
)
from backend.services.classifier import classifier_service
from backend.ml.evaluation import evaluate_classifier_performance

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

    if dataset.status not in {"cleaned", "classified", "complete"}:
        raise HTTPException(
            status_code=400,
            detail="Please complete the cleaning step before aspect classification.",
        )

    # Match the Cleaning page's Cleaned Reviews export: exclude duplicates,
    # low-information rows, and reviews with no usable cleaned text.
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
    limit: int = Query(50, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    """Retrieve predictions for a dataset with optional filters."""
    query = (
        db.query(Prediction)
        .join(Review, Prediction.review_id == Review.id)
        .filter(
            Review.dataset_id == dataset_id,
            Review.is_duplicate.is_(False),
            Review.is_low_info.is_(False),
            func.trim(func.coalesce(Review.cleaned_text, Review.original_text, "")) != "",
        )
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


@router.get("/datasets/{dataset_id}/analysis/export")
def export_analysis_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Export every eligible cleaned review with binary aspect labels and any
    available overall sentiment/emotion labels to a single Excel workbook.

    Each aspect has two independent binary columns:
      aspect_<code>_pos = 1 when a positive label was detected, otherwise 0
      aspect_<code>_neg = 1 when a negative label was detected, otherwise 0
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if dataset.status not in {"classified", "complete"}:
        raise HTTPException(
            status_code=400,
            detail="Please complete aspect classification before exporting the processed dataset.",
        )

    reviews = (
        db.query(Review)
        .options(
            joinedload(Review.predictions),
            joinedload(Review.sentiment),
        )
        .filter(
            Review.dataset_id == dataset_id,
            Review.is_duplicate.is_(False),
            Review.is_low_info.is_(False),
            func.trim(func.coalesce(Review.cleaned_text, Review.original_text, "")) != "",
        )
        .order_by(Review.row_index)
        .all()
    )

    if not reviews:
        raise HTTPException(status_code=400, detail="No eligible cleaned reviews are available to export.")

    aspect_codes = list(ASPECT_DISPLAY_NAMES.keys())
    export_rows = []

    for review in reviews:
        row = {
            "Review ID": review.id,
            "Row Index": review.row_index,
            "Original Review": review.original_text or "",
            "Cleaned Review": review.cleaned_text or "",
            "Rating": review.rating,
            "Review Date": review.review_date or "",
            "Source": review.source or "",
            "Reviewer": review.reviewer or "",
            "Language": review.language or "",
            "Duplicate": bool(review.is_duplicate),
            "Low Information": bool(review.is_low_info),
        }

        detected_labels = []
        for aspect in aspect_codes:
            row[f"{aspect}_pos"] = 0
            row[f"{aspect}_neg"] = 0

        for prediction in review.predictions or []:
            if prediction.aspect not in aspect_codes:
                continue
            polarity = prediction.polarity
            if polarity in {"pos", "neg"}:
                row[f"{prediction.aspect}_{polarity}"] = 1
                detected_labels.append(
                    f"{prediction.aspect}:{polarity}"
                )

        row["Detected Aspect Labels"] = "; ".join(sorted(set(detected_labels)))

        sentiment = review.sentiment
        row["Overall Sentiment"] = sentiment.overall_sentiment if sentiment else ""
        row["Sentiment Confidence"] = sentiment.sentiment_confidence if sentiment else None
        row["Emotion"] = sentiment.emotion if sentiment else ""
        row["Emotion Confidence"] = sentiment.emotion_confidence if sentiment else None
        row["Sentiment Human Corrected"] = bool(sentiment.is_human_corrected) if sentiment else False

        export_rows.append(row)

    df = pd.DataFrame(export_rows)
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Processed Reviews", index=False)
        worksheet = writer.sheets["Processed Reviews"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

        for column_cells in worksheet.columns:
            max_length = max(
                (len(str(cell.value)) for cell in column_cells if cell.value is not None),
                default=10,
            )
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 55)

        summary = pd.DataFrame([
            {"Metric": "Eligible cleaned reviews exported", "Value": len(reviews)},
            {"Metric": "Aspect classes", "Value": len(aspect_codes) * 2},
            {"Metric": "Aspect prediction records", "Value": sum(len(r.predictions or []) for r in reviews)},
            {"Metric": "Reviews with sentiment and emotion", "Value": sum(1 for r in reviews if r.sentiment is not None)},
        ])
        summary.to_excel(writer, sheet_name="Export Summary", index=False)

    buffer.seek(0)
    clean_name = re.sub(r"[^\w\-_\. ]", "_", dataset.name or "dataset").strip().replace(" ", "_")

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="alphaev_processed_{clean_name}.xlsx"'
        },
    )


@router.get("/model/evaluation", response_model=ModelEvaluationResponse)
def get_model_evaluation():
    """
    Returns empirical multi-label performance evaluation metrics (Precision,
    Recall, F1-score, Exact Match Ratio, and Hamming Loss) across all 22 aspect classes.
    """
    eval_results = evaluate_classifier_performance()
    return ModelEvaluationResponse(**eval_results)