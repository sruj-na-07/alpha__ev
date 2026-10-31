import io
import re
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

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
        retained_count=stats.get("retained_count", stats["cleaned_count"]),
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

    retained_count = stats.get("retained_count")
    if retained_count is None:
        retained_count = (
            db.query(Review)
            .filter(
                Review.dataset_id == dataset_id,
                Review.is_duplicate.is_(False),
                Review.is_low_info.is_(False),
                func.trim(func.coalesce(Review.cleaned_text, Review.original_text, "")) != "",
            )
            .count()
        )

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
        retained_count=retained_count,
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
    flags_only: Optional[bool] = Query(None),
    usable_only: bool = Query(False),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get paginated reviews for a dataset with optional filters.
    """

    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id
    ).first()

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found."
        )

    query = db.query(Review).filter(
        Review.dataset_id == dataset_id
    )

    # Return only usable reviews
    if usable_only:
        query = query.filter(
            Review.is_duplicate.is_(False),
            Review.is_low_info.is_(False),
            func.trim(
                func.coalesce(
                    Review.cleaned_text,
                    Review.original_text,
                    ""
                )
            ) != ""
        )

    if is_duplicate is not None:
        query = query.filter(
            Review.is_duplicate == is_duplicate
        )

    if is_low_info is not None:
        query = query.filter(
            Review.is_low_info == is_low_info
        )

    if flags_only is True:
        flags_condition = or_(
            Review.is_duplicate.is_(True),
            Review.is_low_info.is_(True),
            (
                Review.language.isnot(None)
                & (Review.language != "en")
            ),
            func.json_array_length(Review.flags) > 0,
        )
        query = query.filter(flags_condition)

    elif flags_only is False:
        flags_condition = or_(
            Review.is_duplicate.is_(True),
            Review.is_low_info.is_(True),
            (
                Review.language.isnot(None)
                & (Review.language != "en")
            ),
            func.json_array_length(Review.flags) > 0,
        )
        query = query.filter(~flags_condition)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (Review.cleaned_text.ilike(term))
            | (Review.original_text.ilike(term))
        )

    total = query.count()
    offset = (page - 1) * page_size

    reviews = (
        query.options(
            joinedload(Review.predictions),
            joinedload(Review.sentiment)
        )
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



@router.get("/datasets/{dataset_id}/clean/export")
def export_cleaned_reviews(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Export usable reviews and excluded reviews with removal reasons."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if dataset.status not in ["cleaned", "classifying", "classified", "complete"]:
        raise HTTPException(status_code=400, detail="Please run cleaning before exporting reviews.")

    reviews = (
        db.query(Review)
        .filter(Review.dataset_id == dataset_id)
        .order_by(Review.row_index)
        .all()
    )

    base_columns = [
        "Review ID", "Row Index", "Original Review", "Cleaned Review",
        "Rating", "Review Date", "Source", "Reviewer", "Language",
    ]
    removed_columns = base_columns + ["Removal Category", "Removal Reason", "Duplicate Of"]
    cleaned_rows, removed_rows = [], []

    for review in reviews:
        flags = review.flags or []
        if not isinstance(flags, list):
            flags = []
        exclusion_flags = [
            flag for flag in flags
            if isinstance(flag, dict) and str(flag.get("action", "")).lower() == "excluded"
        ]

        is_duplicate = bool(review.is_duplicate)
        is_low_info = bool(review.is_low_info)
        is_excluded = is_duplicate or is_low_info
        reasons = []
        for flag in exclusion_flags:
            reason = flag.get("reason") or flag.get("message") or flag.get("type")
            if reason and str(reason) not in reasons:
                reasons.append(str(reason))
        if is_duplicate and review.duplicate_of:
            reason = f"Duplicate of review ID {review.duplicate_of}"
            if reason not in reasons:
                reasons.append(reason)
        if is_duplicate and not any("duplicate" in reason.lower() for reason in reasons):
            reasons.append("Review identified as a duplicate.")
        if is_low_info and not any(
            any(term in reason.lower() for term in ("empty", "low information", "low-information", "insufficient"))
            for reason in reasons
        ):
            reasons.append("Review is empty or contains insufficient useful information.")

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
        }
        if is_excluded:
            if is_duplicate and is_low_info:
                category = "Duplicate and low information"
            elif is_duplicate:
                category = "Duplicate"
            else:
                category = "Low information / empty review"
            removed_rows.append({
                **row,
                "Removal Category": category,
                "Removal Reason": "; ".join(reasons),
                "Duplicate Of": review.duplicate_of or "",
            })
        else:
            cleaned_rows.append(row)

    cleaned_df = pd.DataFrame(cleaned_rows, columns=base_columns)
    removed_df = pd.DataFrame(removed_rows, columns=removed_columns)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        cleaned_df.to_excel(writer, sheet_name="Cleaned Reviews", index=False)
        removed_df.to_excel(writer, sheet_name="Removed Reviews", index=False)
        for worksheet in writer.sheets.values():
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                max_length = max(
                    (len(str(cell.value)) for cell in column_cells if cell.value is not None),
                    default=10,
                )
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 55)

    excel_buffer.seek(0)
    clean_name = re.sub(r"[^\w\-_\. ]", "_", dataset.name or "dataset").strip().replace(" ", "_")
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="alphaev_cleaning_audit_{clean_name}.xlsx"'},
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

    if review.dataset:
        review.dataset.is_stale = True

    db.commit()
    db.refresh(review)
    return review