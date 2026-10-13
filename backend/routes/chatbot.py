from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db, Dataset
from backend.models import ChatRequest, ChatResponse
from backend.services.chatbot import chatbot_service

router = APIRouter(prefix="/api/v1", tags=["chatbot"])


@router.post("/datasets/{dataset_id}/chat", response_model=ChatResponse)
def chat_with_dataset(
    dataset_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Intelligent chatbot answering questions using SQL queries and review evidence.
    Covers aspects, sentiment breakdowns, average ratings, quality flags, and keyword queries.
    Never fabricates responses.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    result = chatbot_service.answer_query(
        db=db,
        dataset_id=dataset_id,
        user_query=request.message.strip(),
    )

    return ChatResponse(**result)
