import re
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.database import Dataset, Review, Prediction, Sentiment
from backend.ml.seed_data import ASPECT_DISPLAY_NAMES
from backend.services.classifier import ASPECT_KEYWORDS


class ChatbotService:
    """
    Intelligent SQL-grounded chatbot for EV review intelligence.
    Extracts intent, queries real database metrics, searches reviews,
    and constructs template responses backed by explicit review evidence.
    Never fabricates data.
    """

    def __init__(self):
        # Reverse map display names and aliases to internal aspect codes
        self.aspect_aliases = {
            "battery": "range_battery",
            "range": "range_battery",
            "miles": "range_battery",
            "degradation": "range_battery",
            "charging": "charging",
            "charger": "charging",
            "supercharger": "charging",
            "fast charging": "charging",
            "ccs": "charging",
            "performance": "performance",
            "acceleration": "performance",
            "torque": "performance",
            "handling": "performance",
            "braking": "performance",
            "regen": "performance",
            "software": "software_infotainment",
            "infotainment": "software_infotainment",
            "screen": "software_infotainment",
            "carplay": "software_infotainment",
            "app": "software_infotainment",
            "ota": "software_infotainment",
            "interior": "interior_comfort",
            "comfort": "interior_comfort",
            "seats": "interior_comfort",
            "cabin": "interior_comfort",
            "noise": "interior_comfort",
            "suspension": "interior_comfort",
            "build": "build_quality",
            "build quality": "build_quality",
            "panel gaps": "build_quality",
            "paint": "build_quality",
            "rattles": "build_quality",
            "safety": "safety_driver_assist",
            "autopilot": "safety_driver_assist",
            "fsd": "safety_driver_assist",
            "driver assist": "safety_driver_assist",
            "adas": "safety_driver_assist",
            "phantom braking": "safety_driver_assist",
            "price": "price_value",
            "value": "price_value",
            "expensive": "price_value",
            "cost": "price_value",
            "tax credit": "price_value",
            "service": "customer_service",
            "customer service": "customer_service",
            "dealership": "customer_service",
            "warranty": "customer_service",
            "reliability": "reliability",
            "breakdown": "reliability",
            "issues": "reliability",
            "problems": "reliability",
            "faults": "reliability",
            "space": "space_practicality",
            "practicality": "space_practicality",
            "trunk": "space_practicality",
            "frunk": "space_practicality",
            "cargo": "space_practicality",
            "legroom": "space_practicality",
        }

    def _extract_aspect(self, query: str) -> Optional[str]:
        """Detect EV aspect mentioned in the query."""
        q = query.lower()
        for phrase, aspect in sorted(self.aspect_aliases.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(phrase) + r"\b", q):
                return aspect
        return None

    def _extract_polarity(self, query: str) -> Optional[str]:
        """Detect polarity requested (positive vs negative)."""
        q = query.lower()
        if any(w in q for w in ["bad", "complaint", "complaints", "hate", "issue", "problem", "negative", "worst", "broken", "flaw"]):
            return "neg"
        if any(w in q for w in ["good", "love", "like", "positive", "praise", "strength", "best", "great", "awesome", "pros"]):
            return "pos"
        return None

    def _extract_emotion(self, query: str) -> Optional[str]:
        """Detect emotion mentioned in the query."""
        q = query.lower()
        for emo in ["frustrated", "sad", "happy", "satisfaction", "neutral"]:
            if emo in q:
                return emo
        if "angry" in q or "furious" in q:
            return "frustrated"
        if "disappointed" in q:
            return "sad"
        return None

    def answer_query(
        self,
        db: Session,
        dataset_id: str,
        user_query: str,
    ) -> Dict[str, Any]:
        """
        Parses user query, queries real database for counts & reviews,
        and generates an evidence-backed template response.
        """
        clean_q = user_query.strip()
        q_lower = clean_q.lower()

        # Check dataset existence
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {
                "query": user_query,
                "answer": f"Dataset with ID '{dataset_id}' was not found.",
                "intent": "unknown",
                "sql_or_search": "SELECT * FROM datasets WHERE id = :id",
                "total_matched": 0,
                "evidence": [],
            }

        total_reviews = db.query(Review).filter(Review.dataset_id == dataset_id).count()
        if total_reviews == 0:
            return {
                "query": user_query,
                "answer": "This dataset currently has 0 reviews uploaded. Please upload reviews first.",
                "intent": "empty_dataset",
                "sql_or_search": f"SELECT count(*) FROM reviews WHERE dataset_id = '{dataset_id}'",
                "total_matched": 0,
                "evidence": [],
            }

        # 1. Total count / summary overview query
        if any(kw in q_lower for kw in ["how many reviews", "total reviews", "dataset size", "dataset overview", "summary of dataset"]):
            avg_rating = db.query(func.avg(Review.rating)).filter(
                Review.dataset_id == dataset_id,
                Review.rating.isnot(None),
            ).scalar()
            avg_str = f"{avg_rating:.2f} / 5.0" if avg_rating else "N/A"

            pos_count = db.query(Sentiment).join(Review).filter(
                Review.dataset_id == dataset_id,
                Sentiment.overall_sentiment == "positive",
            ).count()
            neg_count = db.query(Sentiment).join(Review).filter(
                Review.dataset_id == dataset_id,
                Sentiment.overall_sentiment == "negative",
            ).count()

            answer = (
                f"The dataset '{dataset.name}' contains a total of {total_reviews} reviews. "
                f"The average user rating is {avg_str}. "
                f"Among analyzed reviews, {pos_count} are positive and {neg_count} are negative."
            )
            return {
                "query": user_query,
                "answer": answer,
                "intent": "dataset_summary",
                "sql_or_search": f"SELECT count(*), avg(rating) FROM reviews WHERE dataset_id = '{dataset_id}'",
                "total_matched": total_reviews,
                "evidence": [],
            }

        # 2. Rating queries
        if "average rating" in q_lower or "avg rating" in q_lower or "overall rating" in q_lower:
            avg_rating = db.query(func.avg(Review.rating)).filter(
                Review.dataset_id == dataset_id,
                Review.rating.isnot(None),
            ).scalar()
            rated_count = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                Review.rating.isnot(None),
            ).count()

            if avg_rating is not None:
                answer = f"The average rating across {rated_count} rated reviews is {avg_rating:.2f} out of 5 stars."
            else:
                answer = "No numeric star ratings were found in this dataset."

            return {
                "query": user_query,
                "answer": answer,
                "intent": "average_rating",
                "sql_or_search": f"SELECT avg(rating), count(rating) FROM reviews WHERE dataset_id = '{dataset_id}'",
                "total_matched": rated_count,
                "evidence": [],
            }

        # 3. Data quality / duplicates / low info queries
        if any(kw in q_lower for kw in ["duplicate", "low info", "quality", "clean", "cleaned", "foreign language"]):
            exact_dups = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                Review.is_duplicate.is_(True),
            ).count()
            low_infos = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                Review.is_low_info.is_(True),
            ).count()
            foreign = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                Review.language != "en",
                Review.language.isnot(None),
            ).count()

            answer = (
                f"Data Quality Analysis for '{dataset.name}':\n"
                f"- Total Reviews: {total_reviews}\n"
                f"- Duplicates flagged: {exact_dups} ({exact_dups / total_reviews * 100:.1f}%)\n"
                f"- Low-information reviews (<3 meaningful words): {low_infos}\n"
                f"- Foreign language reviews: {foreign}"
            )
            return {
                "query": user_query,
                "answer": answer,
                "intent": "data_quality",
                "sql_or_search": f"SELECT count(is_duplicate), count(is_low_info) FROM reviews WHERE dataset_id = '{dataset_id}'",
                "total_matched": exact_dups + low_infos,
                "evidence": [],
            }

        # 4. Overall Sentiment distribution
        if any(kw in q_lower for kw in ["sentiment", "positive vs negative", "how many positive", "how many negative"]):
            pos = db.query(Sentiment).join(Review).filter(Review.dataset_id == dataset_id, Sentiment.overall_sentiment == "positive").count()
            neg = db.query(Sentiment).join(Review).filter(Review.dataset_id == dataset_id, Sentiment.overall_sentiment == "negative").count()
            neu = db.query(Sentiment).join(Review).filter(Review.dataset_id == dataset_id, Sentiment.overall_sentiment == "neutral").count()

            answer = (
                f"Sentiment Breakdown ({total_reviews} total reviews):\n"
                f"• Positive: {pos} ({pos / total_reviews * 100:.1f}%)\n"
                f"• Negative: {neg} ({neg / total_reviews * 100:.1f}%)\n"
                f"• Neutral: {neu} ({neu / total_reviews * 100:.1f}%)"
            )
            return {
                "query": user_query,
                "answer": answer,
                "intent": "sentiment_distribution",
                "sql_or_search": f"SELECT overall_sentiment, count(*) FROM sentiments JOIN reviews ON reviews.id=sentiments.review_id WHERE reviews.dataset_id='{dataset_id}' GROUP BY overall_sentiment",
                "total_matched": pos + neg + neu,
                "evidence": [],
            }

        # 5. Aspect-Specific Queries
        detected_aspect = self._extract_aspect(q_lower)
        detected_polarity = self._extract_polarity(q_lower)

        if detected_aspect:
            aspect_name = ASPECT_DISPLAY_NAMES.get(detected_aspect, detected_aspect)

            query_preds = db.query(Prediction).join(Review).filter(
                Review.dataset_id == dataset_id,
                Prediction.aspect == detected_aspect,
            )

            if detected_polarity:
                query_preds = query_preds.filter(Prediction.polarity == detected_polarity)

            preds = query_preds.all()
            matched_count = len(preds)

            pos_preds = [p for p in preds if p.polarity == "pos"]
            neg_preds = [p for p in preds if p.polarity == "neg"]

            # Fetch evidence reviews
            review_ids = [p.review_id for p in preds[:5]]
            evidence_reviews = db.query(Review).filter(Review.id.in_(review_ids)).all() if review_ids else []

            evidence_items = []
            for rev in evidence_reviews:
                evidence_items.append({
                    "review_id": rev.id,
                    "text": rev.cleaned_text or rev.original_text,
                    "rating": rev.rating,
                    "aspects": [f"{p.aspect}:{p.polarity}" for p in rev.predictions],
                    "sentiment": rev.sentiment.overall_sentiment if rev.sentiment else None,
                })

            if matched_count == 0:
                answer = f"No reviews specifically mentioned '{aspect_name}' in this dataset."
            elif detected_polarity:
                pol_word = "positive mentions" if detected_polarity == "pos" else "complaints"
                answer = f"Found {matched_count} {pol_word} regarding '{aspect_name}'."
            else:
                answer = (
                    f"For '{aspect_name}', there are {matched_count} total mentions: "
                    f"{len(pos_preds)} positive and {len(neg_preds)} negative complaints."
                )

            return {
                "query": user_query,
                "answer": answer,
                "intent": "aspect_query",
                "sql_or_search": f"SELECT * FROM predictions JOIN reviews ON reviews.id=predictions.review_id WHERE predictions.aspect='{detected_aspect}'",
                "total_matched": matched_count,
                "evidence": evidence_items,
            }

        # 6. Emotion queries
        detected_emotion = self._extract_emotion(q_lower)
        if detected_emotion:
            emo_query = db.query(Sentiment).join(Review).filter(
                Review.dataset_id == dataset_id,
                Sentiment.emotion == detected_emotion,
            )
            emo_count = emo_query.count()
            review_ids = [s.review_id for s in emo_query.limit(5).all()]
            evidence_reviews = db.query(Review).filter(Review.id.in_(review_ids)).all() if review_ids else []

            evidence_items = [
                {
                    "review_id": rev.id,
                    "text": rev.cleaned_text or rev.original_text,
                    "rating": rev.rating,
                    "aspects": [f"{p.aspect}:{p.polarity}" for p in rev.predictions],
                    "sentiment": rev.sentiment.overall_sentiment if rev.sentiment else None,
                }
                for rev in evidence_reviews
            ]

            answer = f"There are {emo_count} reviews reflecting a '{detected_emotion}' emotion in this dataset."
            return {
                "query": user_query,
                "answer": answer,
                "intent": "emotion_query",
                "sql_or_search": f"SELECT * FROM sentiments WHERE emotion='{detected_emotion}'",
                "total_matched": emo_count,
                "evidence": evidence_items,
            }

        # 7. Keyword search fallback in review texts
        search_terms = [w for w in re.findall(r"\b[a-zA-Z0-9_\'-]+\b", q_lower) if len(w) > 3]
        if search_terms:
            like_conditions = [Review.original_text.ilike(f"%{term}%") for term in search_terms]
            matched_reviews = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                or_(*like_conditions),
            ).limit(5).all()

            matched_count = db.query(Review).filter(
                Review.dataset_id == dataset_id,
                or_(*like_conditions),
            ).count()

            evidence_items = [
                {
                    "review_id": rev.id,
                    "text": rev.cleaned_text or rev.original_text,
                    "rating": rev.rating,
                    "aspects": [f"{p.aspect}:{p.polarity}" for p in rev.predictions],
                    "sentiment": rev.sentiment.overall_sentiment if rev.sentiment else None,
                }
                for rev in matched_reviews
            ]

            terms_str = ", ".join([f"'{t}'" for t in search_terms[:3]])
            if matched_count > 0:
                answer = f"Found {matched_count} reviews matching keyword(s) {terms_str}."
            else:
                answer = f"No reviews found containing the terms {terms_str}."

            return {
                "query": user_query,
                "answer": answer,
                "intent": "keyword_search",
                "sql_or_search": f"SELECT * FROM reviews WHERE dataset_id='{dataset_id}' AND original_text LIKE '%{search_terms[0]}%'",
                "total_matched": matched_count,
                "evidence": evidence_items,
            }

        # Default fallback
        return {
            "query": user_query,
            "answer": "I can help you analyze aspects (e.g. charging, battery, build quality), ratings, duplicates, and sentiment. What would you like to know?",
            "intent": "general_help",
            "sql_or_search": "N/A",
            "total_matched": 0,
            "evidence": [],
        }


chatbot_service = ChatbotService()
