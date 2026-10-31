import os
import uuid
import chardet
import pandas as pd
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db, Dataset, Review
from backend.models import (
    DatasetResponse,
    DatasetListResponse,
    ColumnDetectionResponse,
    ColumnMappingRequest,
    DatasetPreviewResponse,
)

router = APIRouter(prefix="/api/v1", tags=["upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def detect_file_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read(50000)
        res = chardet.detect(raw)
        return res.get("encoding") or "utf-8"


def read_uploaded_dataframe(file_path: str, filename: str) -> pd.DataFrame:
    """Read CSV or Excel into pandas DataFrame safely."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    elif ext == ".csv":
        enc = detect_file_encoding(file_path)
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception:
            return pd.read_csv(file_path, encoding="latin-1")
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .csv or .xlsx file.",
        )


def suggest_column_mappings(columns: List[str]) -> Dict[str, Optional[str]]:
    """Automatically suggest standard column mappings based on column names."""
    cols_lower = {col.lower().strip(): col for col in columns}
    suggestions: Dict[str, Optional[str]] = {
        "text_column": None,
        "rating_column": None,
        "date_column": None,
        "source_column": None,
        "reviewer_column": None,
    }

    text_candidates = ["review_text", "review", "text", "comment", "feedback", "content", "body", "comments"]
    for cand in text_candidates:
        if cand in cols_lower:
            suggestions["text_column"] = cols_lower[cand]
            break

    # If not found yet, check partial matches
    if not suggestions["text_column"]:
        for col_l, original in cols_lower.items():
            if "review" in col_l or "text" in col_l or "comment" in col_l:
                suggestions["text_column"] = original
                break

    rating_candidates = ["rating", "score", "stars", "star", "overall_rating", "rate"]
    for cand in rating_candidates:
        if cand in cols_lower:
            suggestions["rating_column"] = cols_lower[cand]
            break

    date_candidates = ["date", "review_date", "timestamp", "created_at", "time", "posted_date"]
    for cand in date_candidates:
        if cand in cols_lower:
            suggestions["date_column"] = cols_lower[cand]
            break

    source_candidates = ["source", "platform", "channel", "site", "origin"]
    for cand in source_candidates:
        if cand in cols_lower:
            suggestions["source_column"] = cols_lower[cand]
            break

    reviewer_candidates = ["reviewer", "author", "user", "username", "customer", "name"]
    for cand in reviewer_candidates:
        if cand in cols_lower:
            suggestions["reviewer_column"] = cols_lower[cand]
            break

    return suggestions


@router.post("/upload", response_model=Dict[str, Any])
async def upload_dataset_file(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Upload CSV or XLSX file, validate format, detect columns,
    and save dataset record.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV and Excel (.xlsx, .xls) files are supported.",
        )

    dataset_id = str(uuid.uuid4())
    saved_filename = f"{dataset_id}_{file.filename}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    # Save to disk
    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        with open(saved_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Read and inspect columns
    try:
        df = read_uploaded_dataframe(saved_path, file.filename)
    except Exception as e:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    columns = list(df.columns)
    suggested = suggest_column_mappings(columns)

    display_name = dataset_name.strip() if dataset_name and dataset_name.strip() else file.filename

    dataset = Dataset(
        id=dataset_id,
        name=display_name,
        filename=saved_filename,
        original_filename=file.filename,
        status="uploaded",
        row_count=len(df),
        column_mapping=suggested,
        cleaning_stats={},
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Preview sample rows
    preview_df = df.head(5).fillna("")
    sample_preview = preview_df.to_dict(orient="records")

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "filename": dataset.original_filename,
        "status": dataset.status,
        "row_count": len(df),
        "columns": columns,
        "suggested_mapping": suggested,
        "sample_preview": sample_preview,
    }


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all uploaded datasets with status and metadata."""
    total = db.query(Dataset).count()
    datasets = (
        db.query(Dataset)
        .order_by(Dataset.upload_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return DatasetListResponse(total=total, datasets=datasets)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Get dataset details by ID."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/datasets/{dataset_id}/columns", response_model=ColumnDetectionResponse)
def get_dataset_columns(
    dataset_id: str,
    db: Session = Depends(get_db),
):
    """Get detected columns and suggested mapping for a dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = os.path.join(UPLOAD_DIR, dataset.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original uploaded file not found on disk.")

    df = read_uploaded_dataframe(file_path, dataset.original_filename)
    columns = list(df.columns)
    suggested = suggest_column_mappings(columns)
    preview = df.head(5).fillna("").to_dict(orient="records")

    return ColumnDetectionResponse(
        dataset_id=dataset.id,
        columns=columns,
        suggested_mapping=suggested,
        sample_preview=preview,
    )


@router.post("/datasets/{dataset_id}/map-columns", response_model=DatasetResponse)
def map_dataset_columns(
    dataset_id: str,
    mapping: ColumnMappingRequest,
    db: Session = Depends(get_db),
):
    """
    Save column mapping and load raw review rows into the reviews table.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = os.path.join(UPLOAD_DIR, dataset.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original uploaded file not found on disk.")

    df = read_uploaded_dataframe(file_path, dataset.original_filename)
    if mapping.text_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Specified text column '{mapping.text_column}' not found in uploaded file.",
        )

    # Clear existing reviews for this dataset if remapping
    db.query(Review).filter(Review.dataset_id == dataset.id).delete()

    new_reviews: List[Review] = []
    for idx, row in df.iterrows():
        raw_text = str(row[mapping.text_column]) if pd.notna(row[mapping.text_column]) else ""
        is_empty = not raw_text.strip()
        initial_flags = []
        if is_empty:
            initial_flags.append({"type": "empty_text", "message": "Row contains no review text in source file"})

        rating_val = None
        if mapping.rating_column and mapping.rating_column in df.columns:
            try:
                val = row[mapping.rating_column]
                if pd.notna(val):
                    rating_val = float(val)
            except (ValueError, TypeError):
                rating_val = None

        date_val = None
        if mapping.date_column and mapping.date_column in df.columns:
            date_raw = row[mapping.date_column]
            date_val = str(date_raw) if pd.notna(date_raw) else None

        source_val = None
        if mapping.source_column and mapping.source_column in df.columns:
            s_raw = row[mapping.source_column]
            source_val = str(s_raw) if pd.notna(s_raw) else None

        reviewer_val = None
        if mapping.reviewer_column and mapping.reviewer_column in df.columns:
            r_raw = row[mapping.reviewer_column]
            reviewer_val = str(r_raw) if pd.notna(r_raw) else None

        review = Review(
            id=str(uuid.uuid4()),
            dataset_id=dataset.id,
            row_index=int(idx),
            original_text=raw_text,
            cleaned_text=None,
            rating=rating_val,
            review_date=date_val,
            source=source_val,
            reviewer=reviewer_val,
            flags=initial_flags,
            is_duplicate=False,
            duplicate_of=None,
            language=None,
            is_low_info=is_empty,
        )
        new_reviews.append(review)

    # Bulk insert
    db.bulk_save_objects(new_reviews)
    dataset.column_mapping = mapping.model_dump() if hasattr(mapping, "model_dump") else mapping.dict()
    dataset.row_count = len(new_reviews)
    dataset.status = "uploaded"
    dataset.is_stale = False
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset_rows(
    dataset_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Preview first N rows of the dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    file_path = os.path.join(UPLOAD_DIR, dataset.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found.")

    df = read_uploaded_dataframe(file_path, dataset.original_filename)
    preview_df = df.head(limit).fillna("")

    return DatasetPreviewResponse(
        dataset_id=dataset.id,
        columns=list(df.columns),
        total_rows=len(df),
        rows=preview_df.to_dict(orient="records"),
    )
