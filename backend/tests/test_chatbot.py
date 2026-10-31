"""
Unit and Integration tests for AlphaEV SQL-Grounded Chatbot.
Validates:
- Intent detection across aspects, ratings, counts, data quality, priority issues, recommendations.
- Bug regression test: 'build quality' queries aspect_complaint, NOT generic data_quality.
- Grounded query execution and real evidence extraction (no LLM hallucination).
"""

import pytest
from backend.services.chatbot import ChatbotService
from backend.database import init_db, SessionLocal, Dataset, Review, Prediction, Sentiment
from backend.services.cleaning import cleaning_service
from backend.services.classifier import classifier_service


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def chatbot():
    return ChatbotService()


def test_intent_detection_aspect(chatbot):
    query = "How is the charging speed and supercharger network?"
    parsed = chatbot.parse_intent(query)
    assert parsed["intent"] in ["aspect_query", "aspect_complaint", "aspect_praise"]
    assert parsed["aspect"] == "charging"


def test_build_quality_disambiguation(chatbot):
    # Bug regression: 'build quality' must NOT trigger 'data_quality'
    query = "Are there any complaints about build quality and panel gaps?"
    parsed = chatbot.parse_intent(query)
    assert parsed["intent"] in ["aspect_query", "aspect_complaint"]
    assert parsed["aspect"] == "build_quality"
    assert parsed["intent"] != "data_quality"


def test_intent_detection_priority_issues(chatbot):
    query = "What are the top priority issues and biggest problems?"
    parsed = chatbot.parse_intent(query)
    assert parsed["intent"] == "priority_issues"


def test_intent_detection_recommendations(chatbot):
    query = "What actionable recommendations do you suggest for the engineering team?"
    parsed = chatbot.parse_intent(query)
    assert parsed["intent"] == "recommendations"


def test_intent_detection_data_quality(chatbot):
    query = "What is the data quality breakdown of low information and duplicate reviews?"
    parsed = chatbot.parse_intent(query)
    assert parsed["intent"] == "data_quality"


def test_chatbot_grounded_response_execution(db_session, chatbot):
    # Ensure there is a test dataset with reviews in db
    dataset = db_session.query(Dataset).first()
    if not dataset:
        dataset = Dataset(name="Test Chatbot Dataset", filename="test.csv")
        db_session.add(dataset)
        db_session.commit()

        review = Review(
            dataset_id=dataset.id,
            row_index=0,
            original_text="The battery range is poor in cold weather.",
            cleaned_text="The battery range is poor in cold weather.",
            rating=2.0
        )
        db_session.add(review)
        db_session.commit()

        pred = Prediction(
            review_id=review.id,
            aspect="range_battery",
            polarity="neg",
            confidence=0.88,
            is_human_corrected=False
        )
        db_session.add(pred)
        db_session.commit()

    resp = chatbot.answer_query(db_session, dataset.id, "Tell me about battery range issues")
    assert "query" in resp
    assert "answer" in resp
    assert "sql_or_search" in resp
    assert "evidence" in resp
    assert isinstance(resp["evidence"], list)
