"""
AlphaEV Dynamic Review Ingestion API Routes.

Exposes endpoints for:
1. POST /api/v1/ingestion/reviews: Authenticated webhook endpoint for external EV review feeds.
2. GET /api/v1/ingestion/status: Live telemetry and synchronization status.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import IngestionResponse, IngestionStatusResponse, WebhookIngestRequest
from backend.services.ingestion import ingestion_service

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


@router.post("/reviews", response_model=IngestionResponse)
def ingest_reviews_webhook(
    payload: WebhookIngestRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    dataset_id: Optional[str] = Query(None, description="Optional target dataset ID to attach reviews to"),
    db: Session = Depends(get_db),
):
    """
    Receives and idempotently ingests reviews from an authorized external website/platform.

    - Authenticates via `X-API-Key`, `Authorization: Bearer <key>`, or `payload.api_key`.
    - Deduplicates records using `(source, external_review_id)` to ensure safe retries.
    - Immediately runs reviews through cleaning, aspect classification, sentiment analysis, and severity scoring.
    - Updates dataset row counts, versioning, and dashboard analytics.
    """
    header_key = x_api_key or authorization
    is_authenticated = ingestion_service.authenticate_request(
        provided_key=payload.api_key,
        header_key=header_key,
    )

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key for review ingestion. Provide valid X-API-Key header or api_key payload parameter.",
        )

    response = ingestion_service.process_incoming_reviews(
        payload=payload,
        db=db,
        dataset_id=dataset_id,
    )
    return response


@router.get("/status", response_model=IngestionStatusResponse)
def get_ingestion_telemetry(
    db: Session = Depends(get_db),
):
    """
    Returns the real-time operational status, connection health,
    and recent synchronization audit log for external review ingestion.
    """
    return ingestion_service.get_ingestion_status(db)
