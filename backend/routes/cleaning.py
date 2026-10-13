from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from backend.database import get_db, Dataset, Review
from backend.models import (
    CleaningReportResponse,
    CleaningStatusResponse,
    ReviewResponse,
    ReviewListResponse,
    ReviewUpdateRequest,
)
from backend.services.cleaning import cleaning_service

router = APIRouter(prefix="/api/v1", tags=["cleaning"])


@router.post("/datasets/{dataset_id}/clean", response_model=CleaningReportResponse)
def clean_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """
    Run data cleaning pipeline:
    - Mojibake / encoding fix
    - HTML tag removal
    - Unicode and whitespace normalization
    - Exact & near-duplicate detection
    - Language identification
    - Low-information flagging
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    reviews = db.query(Review).filter(Review.dataset_id == dataset_id).order_by(Review.row_index).all()
    if not reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found for this dataset. Please map columns first.",
        )

    dataset.status = "cleaning"
    db.commit()

    # Prepare inputs for cleaning service
    reviews_input = [
        {
            "id": r.id,
            "dataset_id": r.dataset_id,
            "row_index": r.row_index,
            "original_text": r.original_text,
            "rating": r.rating,
            "review_date": r.review_date,
            "source": r.source,
            "reviewer": r.reviewer,
        }
        for r in reviews
    ]

    processed, stats = cleaning_service.process_reviews(reviews_input)

    # Batch update database reviews
    reviews_by_id = {r.id: r for r in reviews}
    for item in processed:
        r = reviews_by_id.get(item["id"])
        if r:
            r.cleaned_text = item["cleaned_text"]
            r.flags = item["flags"]
            r.is_duplicate = item["is_duplicate"]
            r.duplicate_of = item["duplicate_of"]
            r.language = item["language"]
            r.is_low_info = item["is_low_info"]

    dataset.cleaning_stats = stats
    dataset.status = "cleaned"
    db.commit()
    db.refresh(dataset)

    return CleaningReportResponse(
        dataset_id=dataset.id,
        total_reviews=stats["total_reviews"],
        cleaned_count=stats["cleaned_count"],
        exact_duplicates=stats["exact_duplicates"],
        near_duplicates=stats["near_duplicates"],
        low_info_count=stats["low_info_count"],
        non_english_count=stats["non_english_count"],
        html_removed_count=stats["html_removed_count"],
        encoding_fixed_count=stats["encoding_fixed_count"],
        flags_breakdown=stats["flags_breakdown"],
    )


@router.get("/datasets/{dataset_id}/cleaning-status", response_model=CleaningStatusResponse)
def get_cleaning_status(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Get the current cleaning status and progress."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    progress_map = {
        "uploaded": 0.0,
        "cleaning": 50.0,
        "cleaned": 100.0,
        "classifying": 100.0,
        "classified": 100.0,
        "complete": 100.0,
    }
    progress = progress_map.get(dataset.status, 0.0)

    return CleaningStatusResponse(
        dataset_id=dataset.id,
        status=dataset.status,
        progress=progress,
        message=f"Current dataset status: {dataset.status}",
    )


@router.get("/datasets/{dataset_id}/cleaning-report", response_model=CleaningReportResponse)
def get_cleaning_report(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve full cleaning statistics report."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    stats = dataset.cleaning_stats or {}
    total = stats.get("total_reviews", dataset.row_count)

    flags_breakdown = stats.get("flags_breakdown", {
        "exact_duplicate": stats.get("exact_duplicates", 0),
        "near_duplicate": stats.get("near_duplicates", 0),
        "low_info": stats.get("low_info_count", 0),
        "non_english": stats.get("non_english_count", 0),
        "html_tags_removed": stats.get("html_removed_count", 0),
        "encoding_fixed": stats.get("encoding_fixed_count", 0),
    })

    return CleaningReportResponse(
        dataset_id=dataset.id,
        total_reviews=total,
        cleaned_count=stats.get("cleaned_count", total if dataset.status in ["cleaned", "classified", "complete"] else 0),
        exact_duplicates=stats.get("exact_duplicates", 0),
        near_duplicates=stats.get("near_duplicates", 0),
        low_info_count=stats.get("low_info_count", 0),
        non_english_count=stats.get("non_english_count", 0),
        html_removed_count=stats.get("html_removed_count", 0),
        encoding_fixed_count=stats.get("encoding_fixed_count", 0),
        flags_breakdown=flags_breakdown,
    )


@router.get("/datasets/{dataset_id}/reviews", response_model=ReviewListResponse)
def get_dataset_reviews(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_duplicate: Optional[bool] = None,
    is_low_info: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get paginated reviews for a dataset with optional filters
    (duplicate, low-info, text search).
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    query = db.query(Review).filter(Review.dataset_id == dataset_id)

    if is_duplicate is not None:
        query = query.filter(Review.is_duplicate == is_duplicate)

    if is_low_info is not None:
        query = query.filter(Review.is_low_info == is_low_info)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (Review.cleaned_text.ilike(term)) | (Review.original_text.ilike(term))
        )

    total = query.count()
    offset = (page - 1) * page_size
    reviews = (
        query.options(joinedload(Review.predictions), joinedload(Review.sentiment))
        .order_by(Review.row_index)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ReviewListResponse(
        total=total,
        page=page,
        page_size=page_size,
        reviews=reviews,
    )


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: str,
    update_data: ReviewUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Human editing of review data (cleaned text, rating, flags).
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    if update_data.cleaned_text is not None:
        review.cleaned_text = update_data.cleaned_text
    if update_data.rating is not None:
        review.rating = update_data.rating
    if update_data.is_low_info is not None:
        review.is_low_info = update_data.is_low_info
    if update_data.is_duplicate is not None:
        review.is_duplicate = update_data.is_duplicate
    if update_data.flags is not None:
        review.flags = update_data.flags

    db.commit()
    db.refresh(review)
    return review
