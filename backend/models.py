from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# -----------------------------
# Dataset Schemas
# -----------------------------
class ColumnMappingRequest(BaseModel):
    text_column: str
    rating_column: Optional[str] = None
    date_column: Optional[str] = None
    source_column: Optional[str] = None
    reviewer_column: Optional[str] = None


class ColumnDetectionResponse(BaseModel):
    dataset_id: str
    columns: List[str]
    suggested_mapping: Dict[str, Optional[str]]
    sample_preview: List[Dict[str, Any]]


class DatasetResponse(BaseModel):
    id: str
    name: str
    filename: str
    original_filename: str
    upload_time: datetime
    status: str
    row_count: int
    column_mapping: Dict[str, Any] = {}
    cleaning_stats: Dict[str, Any] = {}

    class Config:
        from_attributes = True
        orm_mode = True


class DatasetListResponse(BaseModel):
    total: int
    datasets: List[DatasetResponse]


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    columns: List[str]
    total_rows: int
    rows: List[Dict[str, Any]]


# -----------------------------
# Cleaning Schemas
# -----------------------------
class CleaningFlag(BaseModel):
    type: str
    message: str


class CleaningReportResponse(BaseModel):
    dataset_id: str
    total_reviews: int
    cleaned_count: int
    exact_duplicates: int
    near_duplicates: int
    low_info_count: int
    non_english_count: int
    html_removed_count: int
    encoding_fixed_count: int
    flags_breakdown: Dict[str, int]


class CleaningStatusResponse(BaseModel):
    dataset_id: str
    status: str
    progress: float
    message: str


class ReviewUpdateRequest(BaseModel):
    cleaned_text: Optional[str] = None
    rating: Optional[float] = None
    is_low_info: Optional[bool] = None
    is_duplicate: Optional[bool] = None
    flags: Optional[List[Dict[str, str]]] = None


# -----------------------------
# Prediction & Sentiment Schemas
# -----------------------------
class PredictionResponse(BaseModel):
    id: int
    review_id: str
    aspect: str
    polarity: str
    confidence: float
    is_human_corrected: bool
    model_prediction: Optional[str] = None
    model_confidence: Optional[float] = None

    class Config:
        from_attributes = True
        orm_mode = True


class PredictionUpdateRequest(BaseModel):
    aspect: str
    polarity: str  # "pos" or "neg"
    confidence: Optional[float] = 1.0


class PredictionCreateRequest(BaseModel):
    aspect: str
    polarity: str  # "pos" or "neg"
    confidence: Optional[float] = 1.0


class SentimentResponse(BaseModel):
    id: int
    review_id: str
    overall_sentiment: str
    sentiment_confidence: float
    emotion: str
    emotion_confidence: float
    is_human_corrected: bool

    class Config:
        from_attributes = True
        orm_mode = True


class SentimentUpdateRequest(BaseModel):
    overall_sentiment: str
    emotion: str
    sentiment_confidence: Optional[float] = 1.0
    emotion_confidence: Optional[float] = 1.0


class ReviewResponse(BaseModel):
    id: str
    dataset_id: str
    row_index: int
    original_text: str
    cleaned_text: Optional[str] = None
    rating: Optional[float] = None
    review_date: Optional[str] = None
    source: Optional[str] = None
    reviewer: Optional[str] = None
    flags: List[Dict[str, Any]] = []
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    language: Optional[str] = None
    is_low_info: bool = False
    predictions: List[PredictionResponse] = []
    sentiment: Optional[SentimentResponse] = None

    class Config:
        from_attributes = True
        orm_mode = True


class ReviewListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    reviews: List[ReviewResponse]


class WordImportance(BaseModel):
    word: str
    score: float


class ExplainResponse(BaseModel):
    review_id: str
    text: str
    aspect_explanations: Dict[str, List[WordImportance]]
    summary: str


# -----------------------------
# Dashboard Schemas
# -----------------------------
class AspectMetric(BaseModel):
    aspect: str
    aspect_display: str
    positive_count: int
    negative_count: int
    total_count: int
    sentiment_ratio: float  # positive / total


class EmotionDistribution(BaseModel):
    emotion: str
    count: int
    percentage: float


class SentimentDistribution(BaseModel):
    sentiment: str
    count: int
    percentage: float


class QualityMetrics(BaseModel):
    total_rows: int
    usable_rows: int
    exact_duplicates: int
    near_duplicates: int
    low_info_reviews: int
    non_english: int


class DashboardStatsResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    total_reviews: int
    average_rating: Optional[float] = None
    quality_metrics: QualityMetrics
    aspect_metrics: List[AspectMetric]
    sentiment_distribution: List[SentimentDistribution]
    emotion_distribution: List[EmotionDistribution]
    top_strengths: List[str]
    top_complaints: List[str]


# -----------------------------
# Chatbot Schemas
# -----------------------------
class ChatRequest(BaseModel):
    message: str


class ChatEvidenceItem(BaseModel):
    review_id: str
    text: str
    rating: Optional[float] = None
    aspects: List[str] = []
    sentiment: Optional[str] = None


class ChatResponse(BaseModel):
    query: str
    answer: str
    intent: str
    sql_or_search: str
    total_matched: int
    evidence: List[ChatEvidenceItem]
