import os
import json
from datetime import datetime
from typing import Generator
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'alphaev.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="uploaded", nullable=False)
    # Status flow: uploaded -> cleaning -> cleaned -> classifying -> classified -> complete
    row_count = Column(Integer, default=0, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_stale = Column(Boolean, default=False, nullable=False)
    column_mapping = Column(JSON, default=dict, nullable=False)
    cleaning_stats = Column(JSON, default=dict, nullable=False)

    reviews = relationship(
        "Review",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, index=True)
    dataset_id = Column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    row_index = Column(Integer, nullable=False)
    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    review_date = Column(String(100), nullable=True)
    source = Column(String(100), nullable=True)
    reviewer = Column(String(150), nullable=True)
    source_review_id = Column(String(150), nullable=True, index=True)
    severity_score = Column(Float, nullable=True)
    severity_level = Column(String(20), nullable=True)  # "Critical", "High", "Medium", "Low"
    hazard_category = Column(String(100), nullable=True)
    verification_status = Column(String(50), default="unverified_complaint", nullable=True)
    flags = Column(JSON, default=list, nullable=False)  # List of {"type": str, "message": str}
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of = Column(String(36), nullable=True)
    language = Column(String(20), nullable=True)
    is_low_info = Column(Boolean, default=False, nullable=False)

    dataset = relationship("Dataset", back_populates="reviews")
    predictions = relationship(
        "Prediction",
        back_populates="review",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sentiment = relationship(
        "Sentiment",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    review_id = Column(
        String(36),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    aspect = Column(String(100), nullable=False)  # e.g., "range_battery", "charging"
    polarity = Column(String(10), nullable=False)  # "pos" or "neg"
    confidence = Column(Float, default=0.0, nullable=False)
    is_human_corrected = Column(Boolean, default=False, nullable=False)
    model_prediction = Column(String(100), nullable=True)
    model_confidence = Column(Float, default=0.0, nullable=False)

    review = relationship("Review", back_populates="predictions")


class Sentiment(Base):
    __tablename__ = "sentiments"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    review_id = Column(
        String(36),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        unique=True,
    )
    overall_sentiment = Column(String(20), nullable=False)  # "positive", "negative", "neutral"
    sentiment_confidence = Column(Float, default=0.0, nullable=False)
    emotion = Column(String(30), nullable=False)  # "happy", "sad", "frustrated", "satisfaction", "neutral"
    emotion_confidence = Column(Float, default=0.0, nullable=False)
    is_human_corrected = Column(Boolean, default=False, nullable=False)

    review = relationship("Review", back_populates="sentiment")


class IngestionSyncLog(Base):
    __tablename__ = "ingestion_sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    source = Column(String(100), nullable=False, default="website_reviews")
    status = Column(String(50), nullable=False, default="success")  # "success", "partial", "failed"
    reviews_received = Column(Integer, default=0, nullable=False)
    reviews_inserted = Column(Integer, default=0, nullable=False)
    reviews_duplicate = Column(Integer, default=0, nullable=False)
    reviews_failed = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def get_db() -> Generator:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in SQLite and apply non-destructive column migrations."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE datasets ADD COLUMN version INTEGER DEFAULT 1",
            "ALTER TABLE datasets ADD COLUMN is_stale BOOLEAN DEFAULT 0",
            "ALTER TABLE reviews ADD COLUMN source_review_id VARCHAR(150)",
            "ALTER TABLE reviews ADD COLUMN severity_score FLOAT",
            "ALTER TABLE reviews ADD COLUMN severity_level VARCHAR(20)",
            "ALTER TABLE reviews ADD COLUMN hazard_category VARCHAR(100)",
            "ALTER TABLE reviews ADD COLUMN verification_status VARCHAR(50) DEFAULT 'unverified_complaint'",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass


# Initialize tables and schema migrations on import
init_db()

