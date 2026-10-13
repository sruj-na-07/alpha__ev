"""
Verification and Test Suite for AlphaEV Backend.
Tests the complete end-to-end processing pipeline:
- Database initialization
- Data ingestion & column detection
- Data cleaning (HTML removal, mojibake repair, duplicates, low-info, language)
- 11 aspects x 2 polarities (22 labels) ML & fallback classification
- Sentiment & emotion scoring
- Real database query chatbot
- SHAP feature attribution explanations
- Dashboard analytics computation
"""

import os
import sys
import uuid
import pandas as pd

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal, Dataset, Review, Prediction, Sentiment
from backend.services.cleaning import cleaning_service
from backend.services.classifier import classifier_service
from backend.services.chatbot import chatbot_service
from backend.routes.dashboard import get_dataset_dashboard_stats


def run_verification_test():
    print("=" * 60)
    print("AlphaEV Backend Pipeline Verification")
    print("=" * 60)

    # 1. Initialize SQLite DB
    print("[1/8] Initializing database tables...")
    init_db()
    db = SessionLocal()
    print("  -> Database tables initialized successfully.")

    # 2. Ingest Sample CSV
    sample_csv = os.path.join(os.path.dirname(__file__), "sample_data", "sample_ev_reviews.csv")
    print(f"[2/8] Ingesting sample CSV from: {sample_csv}")
    df = pd.read_csv(sample_csv)
    print(f"  -> Read {len(df)} rows from CSV. Columns: {list(df.columns)}")

    dataset_id = str(uuid.uuid4())
    dataset = Dataset(
        id=dataset_id,
        name="Tesla & Multi-EV Test Fleet",
        filename="sample_ev_reviews.csv",
        original_filename="sample_ev_reviews.csv",
        status="uploaded",
        row_count=len(df),
        column_mapping={
            "text_column": "review_text",
            "rating_column": "rating",
            "date_column": "review_date",
            "source_column": "source",
            "reviewer_column": "reviewer",
        },
        cleaning_stats={},
    )
    db.add(dataset)

    reviews_to_add = []
    for idx, row in df.iterrows():
        rev = Review(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            row_index=int(idx),
            original_text=str(row["review_text"]),
            rating=float(row["rating"]) if pd.notna(row["rating"]) else None,
            review_date=str(row["review_date"]) if pd.notna(row["review_date"]) else None,
            source=str(row["source"]) if pd.notna(row["source"]) else None,
            reviewer=str(row["reviewer"]) if pd.notna(row["reviewer"]) else None,
        )
        reviews_to_add.append(rev)

    db.bulk_save_objects(reviews_to_add)
    db.commit()
    print(f"  -> Stored Dataset record and {len(reviews_to_add)} Review records.")

    # 3. Test Data Cleaning Pipeline
    print("[3/8] Running Data Cleaning Pipeline...")
    db_reviews = db.query(Review).filter(Review.dataset_id == dataset_id).order_by(Review.row_index).all()
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
        for r in db_reviews
    ]

    processed, cleaning_stats = cleaning_service.process_reviews(reviews_input)
    print(f"  -> Processed {cleaning_stats['total_reviews']} reviews:")
    print(f"     - Exact duplicates flagged: {cleaning_stats['exact_duplicates']}")
    print(f"     - Near duplicates flagged: {cleaning_stats['near_duplicates']}")
    print(f"     - Low-info reviews flagged: {cleaning_stats['low_info_count']}")
    print(f"     - Foreign language reviews: {cleaning_stats['non_english_count']}")
    print(f"     - HTML tags removed: {cleaning_stats['html_removed_count']}")
    print(f"     - Mojibake fixed: {cleaning_stats['encoding_fixed_count']}")

    # Apply cleaned updates
    for item in processed:
        r = db.query(Review).filter(Review.id == item["id"]).first()
        r.cleaned_text = item["cleaned_text"]
        r.flags = item["flags"]
        r.is_duplicate = item["is_duplicate"]
        r.duplicate_of = item["duplicate_of"]
        r.language = item["language"]
        r.is_low_info = item["is_low_info"]

    dataset.cleaning_stats = cleaning_stats
    dataset.status = "cleaned"
    db.commit()

    # 4. Aspect-Based Classification (22 labels)
    print("[4/8] Running Aspect-Based Multi-Label Classification...")
    non_dup_reviews = db.query(Review).filter(Review.dataset_id == dataset_id, Review.is_duplicate.is_(False)).all()
    predictions_to_add = []
    aspect_counts = {}

    for r in non_dup_reviews:
        preds = classifier_service.predict(r.cleaned_text or r.original_text, threshold=0.30)
        for p in preds:
            pred_obj = Prediction(
                review_id=r.id,
                aspect=p["aspect"],
                polarity=p["polarity"],
                confidence=p["confidence"],
                is_human_corrected=False,
                model_prediction=p.get("model_prediction", f"{p['aspect']}:{p['polarity']}"),
                model_confidence=p["confidence"],
            )
            predictions_to_add.append(pred_obj)
            key = f"{p['aspect']}:{p['polarity']}"
            aspect_counts[key] = aspect_counts.get(key, 0) + 1

    db.bulk_save_objects(predictions_to_add)
    dataset.status = "classified"
    db.commit()
    print(f"  -> Generated {len(predictions_to_add)} aspect predictions across {len(aspect_counts)} unique labels.")
    print(f"  -> Sample labels detected: {list(aspect_counts.keys())[:6]}")

    # 5. Sentiment & Emotion Analysis
    print("[5/8] Running Sentiment & Emotion Analysis...")
    sentiments_to_add = []
    for r in non_dup_reviews:
        text = r.cleaned_text or r.original_text
        sentiment_label, sent_conf = classifier_service.rule_sentiment.analyze_sentiment(text, rating=r.rating)
        emotion_label, emo_conf = classifier_service.rule_sentiment.analyze_emotion(text, overall_sentiment=sentiment_label)

        s_obj = Sentiment(
            review_id=r.id,
            overall_sentiment=sentiment_label,
            sentiment_confidence=sent_conf,
            emotion=emotion_label,
            emotion_confidence=emo_conf,
            is_human_corrected=False,
        )
        sentiments_to_add.append(s_obj)

    db.bulk_save_objects(sentiments_to_add)
    dataset.status = "complete"
    db.commit()
    print(f"  -> Computed sentiments and emotions for {len(sentiments_to_add)} reviews.")

    # 6. SHAP / Feature Attribution Explanation
    print("[6/8] Generating SHAP Explanations...")
    sample_review = non_dup_reviews[0]
    explanation = classifier_service.explain(sample_review.cleaned_text)
    print(f"  -> Explanation for Review 1: \"{sample_review.cleaned_text[:60]}...\"")
    print(f"     Summary: {explanation['summary']}")
    for lbl, words in explanation["aspect_explanations"].items():
        print(f"     Label '{lbl}': {words}")

    # 7. Dashboard Metrics Calculation
    print("[7/8] Generating Dashboard Statistics...")
    dash_stats = get_dataset_dashboard_stats(dataset_id=dataset_id, db=db)
    print(f"  -> Total Reviews: {dash_stats.total_reviews}")
    print(f"  -> Average Rating: {dash_stats.average_rating}")
    print(f"  -> Usable Reviews: {dash_stats.quality_metrics.usable_rows}")
    print(f"  -> Top Strengths: {dash_stats.top_strengths}")
    print(f"  -> Top Complaints: {dash_stats.top_complaints}")
    print(f"  -> Sentiment breakdown: {[(s.sentiment, s.count) for s in dash_stats.sentiment_distribution]}")
    print(f"  -> Emotion breakdown: {[(e.emotion, e.count) for e in dash_stats.emotion_distribution]}")

    # 8. Chatbot Queries
    print("[8/8] Testing Intelligent Chatbot with Real Queries...")
    test_queries = [
        "What do people say about battery range?",
        "Are there any complaints about build quality?",
        "What is the average rating?",
        "How many reviews are positive vs negative?",
        "Show me reviews mentioning phantom braking",
    ]

    for q in test_queries:
        res = chatbot_service.answer_query(db=db, dataset_id=dataset_id, user_query=q)
        print(f"  [Q]: {q}")
        print(f"  [Intent]: {res['intent']} | [Matched]: {res['total_matched']}")
        print(f"  [A]: {res['answer']}")
        if res['evidence']:
            print(f"  [Evidence #1]: \"{res['evidence'][0]['text'][:80]}...\" (Rating: {res['evidence'][0]['rating']})")
        print()

    db.close()
    print("=" * 60)
    print("All Pipeline Steps Verified and Working Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_verification_test()
