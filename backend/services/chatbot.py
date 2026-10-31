"""
AlphaEV chatbot using Cohere LLM + dataset-grounded review retrieval.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import cohere
from dotenv import load_dotenv
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database import Dataset, Review, Prediction, Sentiment


# Load backend/.env automatically whenever this module is imported.
# This works regardless of which directory you launch the backend from.
BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)


class ChatbotService:
    """Answers EV questions using Cohere and the selected review dataset."""

    COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")

    def __init__(self) -> None:
        # These are the canonical aspects used by the current Statiq dataset.
        self.aspect_aliases = {
            "pricing": "pricing",
            "price": "pricing",
            "cost": "pricing",
            "expensive": "pricing",
            "charging cost": "pricing",
            "tariff": "pricing",

            "payment": "payment_issues",
            "payment issue": "payment_issues",
            "payment issues": "payment_issues",
            "payment failure": "payment_issues",
            "payment failed": "payment_issues",
            "transaction": "payment_issues",
            "refund": "payment_issues",

            "charging speed": "charging_speed",
            "charging time": "charging_speed",
            "charge speed": "charging_speed",
            "slow charging": "charging_speed",
            "fast charging": "charging_speed",

            "reliability": "reliability",
            "reliable": "reliability",
            "unreliable": "reliability",
            "malfunction": "reliability",
            "fault": "reliability",
            "broken": "reliability",

            "waiting time": "waiting_time",
            "wait time": "waiting_time",
            "queue": "waiting_time",
            "waiting": "waiting_time",
            "long wait": "waiting_time",

            "app usability": "app_usability",
            "app": "app_usability",
            "application": "app_usability",
            "mobile app": "app_usability",
            "app interface": "app_usability",
            "user interface": "app_usability",

            "availability": "availability",
            "available": "availability",
            "charger availability": "availability",
            "charging availability": "availability",
            "working charger": "availability",

            "location convenience": "location_convenience",
            "location": "location_convenience",
            "station location": "location_convenience",
            "nearby station": "location_convenience",
            "accessibility": "location_convenience",

            "improvement suggestion": "improvement_suggestion",
            "improvement": "improvement_suggestion",
            "suggestion": "improvement_suggestion",
            "suggestions": "improvement_suggestion",

            "overall experience": "overall_experience",
            "experience": "overall_experience",
            "user experience": "overall_experience",

            "customer support": "customer_support",
            "support": "customer_support",
            "customer service": "customer_support",
            "helpdesk": "customer_support",
            "complaint resolution": "customer_support",
        }

        self.stop_words = {
            "what", "when", "where", "which", "would", "could", "should",
            "does", "did", "have", "has", "had", "about", "from", "with",
            "that", "this", "they", "them", "their", "there", "then",
            "than", "into", "your", "you", "are", "the", "and", "for",
            "how", "why", "can", "tell", "explain", "give", "show",
            "please", "based", "according", "reviews", "review", "users",
            "user", "customers", "customer", "dataset", "data", "alphaev",
        }

    def parse_intent(self, query: str) -> Dict[str, Any]:
        q = (query or "").lower().strip()

        if any(term in q for term in (
            "priority issue", "priority issues", "biggest problem",
            "biggest problems", "top issue", "top issues", "critical issue",
        )):
            return {"intent": "priority_issues", "aspect": None}

        if any(term in q for term in (
            "recommendation", "recommendations", "suggest",
            "actionable", "engineering team",
        )):
            return {"intent": "recommendations", "aspect": None}

        if any(term in q for term in (
            "data quality", "low information", "duplicate review",
            "duplicate reviews", "cleaning breakdown",
        )):
            return {"intent": "data_quality", "aspect": None}

        aspect = self._extract_aspect(q)

        if aspect:
            if any(word in q for word in (
                "complaint", "issue", "bad", "poor", "slow",
                "broken", "failed", "problem", "negative",
            )):
                intent = "aspect_complaint"
            elif any(word in q for word in (
                "praise", "great", "good", "fast", "love",
                "reliable", "best", "positive",
            )):
                intent = "aspect_praise"
            else:
                intent = "aspect_query"

            return {"intent": intent, "aspect": aspect}

        return {"intent": "general_query", "aspect": None}

    def _extract_aspect(self, query: str) -> Optional[str]:
        q = query.lower()

        for phrase, aspect in sorted(
            self.aspect_aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if re.search(r"\b" + re.escape(phrase) + r"\b", q):
                return aspect

        return None

    def _is_ev_related(self, query: str) -> bool:
        q = query.lower()

        terms = (
            "ev", "electric vehicle", "electric car", "charging",
            "charger", "charging station", "battery", "vehicle",
            "car", "automotive", "statiq", "review", "dataset",
            "customer", "sentiment", "complaint", "rating",
            "aspect", "infrastructure", "payment", "refund",
            "charging speed", "waiting time", "customer support",
        )

        return (
            any(term in q for term in terms)
            or self._extract_aspect(q) is not None
        )

    def _needs_dataset(self, query: str) -> bool:
        q = query.lower()

        explicit_data_phrases = (
            "in this dataset", "in the dataset",
            "according to reviews", "according to the reviews",
            "what do users say", "what do customers say",
            "based on reviews", "from reviews", "our data",
            "how many", "what percentage", "percentage of",
            "most common", "top complaint", "top issue",
            "biggest complaint", "sentiment", "average rating",
            "average score", "count of", "number of reviews",
            "do users complain", "are users satisfied",
            "customer feedback", "review evidence",
        )

        aspect = self._extract_aspect(q)

        return (
            any(phrase in q for phrase in explicit_data_phrases)
            or (
                aspect is not None
                and any(word in q for word in (
                    "review", "complaint", "users", "customers",
                    "dataset", "feedback", "issue", "problem",
                    "mention", "say", "sentiment",
                ))
            )
        )

    def _retrieve_reviews(
        self,
        db: Session,
        dataset_id: str,
        query: str,
        limit: int = 6,
    ) -> List[Review]:
        """Retrieve relevant usable reviews from the selected dataset."""

        q = query.lower()
        aspect = self._extract_aspect(q)

        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", q)
            if len(token) >= 3 and token not in self.stop_words
        ]

        # Apply the same usable-review conditions used by the project:
        # not duplicate, not low-information, and non-empty text.
        base = db.query(Review).filter(
            Review.dataset_id == dataset_id,
            Review.is_duplicate.is_(False),
            Review.is_low_info.is_(False),
            func.trim(
                func.coalesce(
                    Review.cleaned_text,
                    Review.original_text,
                    "",
                )
            ) != "",
        )

        conditions = []

        for token in tokens[:8]:
            pattern = f"%{token}%"
            conditions.extend([
                Review.cleaned_text.ilike(pattern),
                Review.original_text.ilike(pattern),
            ])

        text_matches: List[Review] = []

        if conditions:
            text_matches = (
                base.filter(or_(*conditions))
                .order_by(Review.row_index)
                .limit(limit * 3)
                .all()
            )

        aspect_matches: List[Review] = []

        if aspect:
            aspect_matches = (
                base.join(
                    Prediction,
                    Prediction.review_id == Review.id,
                )
                .filter(Prediction.aspect == aspect)
                .order_by(Review.row_index)
                .limit(limit * 3)
                .all()
            )

        combined: List[Review] = []
        seen = set()

        for review in text_matches + aspect_matches:
            if review.id not in seen:
                seen.add(review.id)
                combined.append(review)

            if len(combined) >= limit:
                break

        return combined

    def _call_cohere(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate a response using Cohere's Chat API."""

        api_key = os.getenv("COHERE_API_KEY")

        if not api_key:
            raise RuntimeError(
                "Cohere API key is missing. Add COHERE_API_KEY to backend/.env "
                "and restart the backend."
            )

        try:
            client = cohere.ClientV2(api_key=api_key)

            response = client.chat(
                model=self.COHERE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.25,
            )

            answer_parts = [
                block.text
                for block in response.message.content
                if getattr(block, "type", None) == "text"
                and getattr(block, "text", None)
            ]

            answer = "\n".join(answer_parts).strip()

            if not answer:
                raise RuntimeError(
                    "Cohere returned an empty response. Please try again."
                )

            return answer

        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                f"Cohere API request failed: {exc}"
            ) from exc

    def answer_query(
        self,
        db: Session,
        dataset_id: str,
        user_query: str,
    ) -> Dict[str, Any]:

        clean_q = user_query.strip()

        dataset = (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id)
            .first()
        )

        if not dataset:
            return self._result(
                clean_q,
                "Dataset not found.",
                "unknown",
            )

        if not clean_q:
            return self._result(
                clean_q,
                "Please enter a question.",
                "general_help",
            )

        total_reviews = (
            db.query(Review)
            .filter(
                Review.dataset_id == dataset_id,
                Review.is_duplicate.is_(False),
                Review.is_low_info.is_(False),
                func.trim(
                    func.coalesce(
                        Review.cleaned_text,
                        Review.original_text,
                        "",
                    )
                ) != "",
            )
            .count()
        )

        if total_reviews == 0:
            return self._result(
                clean_q,
                "This dataset has no usable reviews yet. Upload and clean a dataset first.",
                "empty_dataset",
            )

        if not self._is_ev_related(clean_q):
            return self._result(
                clean_q,
                "I'm AlphaEV's EV intelligence assistant. I can help with "
                "EV charging stations, charging speed, payment issues, "
                "reliability, customer feedback, and analysis of your dataset. "
                "Please ask me something related to EVs or this dataset.",
                "out_of_scope",
            )

        q = clean_q.lower()
        intent = "ev_knowledge"

        context_parts = [
            f"Dataset name: {dataset.name}",
            f"Total usable reviews: {total_reviews}",
        ]

        evidence: List[Dict[str, Any]] = []
        matched_count = 0
        sql_description = "No dataset retrieval needed for this question."

        # Calculate exact metrics in SQL, not with the LLM.
        if any(term in q for term in (
            "how many reviews",
            "total reviews",
            "dataset size",
            "number of reviews",
        )):
            matched_count = total_reviews
            intent = "dataset_summary"
            context_parts.append(
                f"Exact usable review count: {total_reviews}."
            )
            sql_description = (
                "COUNT of usable reviews scoped to dataset_id"
            )

        if any(term in q for term in (
            "average rating", "avg rating", "overall rating",
        )):
            avg_rating, rated_count = db.query(
                func.avg(Review.rating),
                func.count(Review.rating),
            ).filter(
                Review.dataset_id == dataset_id,
                Review.is_duplicate.is_(False),
                Review.is_low_info.is_(False),
                Review.rating.isnot(None),
                func.trim(
                    func.coalesce(
                        Review.cleaned_text,
                        Review.original_text,
                        "",
                    )
                ) != "",
            ).first()

            if avg_rating is not None:
                context_parts.append(
                    f"Exact average rating: {float(avg_rating):.2f}/5 "
                    f"across {rated_count} usable rated reviews."
                )
            else:
                context_parts.append(
                    "No numeric ratings are available."
                )

            matched_count = int(rated_count or 0)
            intent = "average_rating"
            sql_description = (
                "AVG and COUNT of non-null ratings for usable reviews"
            )

        if any(term in q for term in (
            "sentiment breakdown",
            "sentiment distribution",
            "how many positive",
            "how many negative",
            "positive vs negative",
        )):
            sentiment_rows = (
                db.query(
                    Sentiment.overall_sentiment,
                    func.count(Sentiment.id),
                )
                .join(Review)
                .filter(
                    Review.dataset_id == dataset_id,
                    Review.is_duplicate.is_(False),
                    Review.is_low_info.is_(False),
                    func.trim(
                        func.coalesce(
                            Review.cleaned_text,
                            Review.original_text,
                            "",
                        )
                    ) != "",
                )
                .group_by(Sentiment.overall_sentiment)
                .all()
            )

            counts = {
                str(label).lower(): int(count)
                for label, count in sentiment_rows
                if label is not None
            }

            analyzed = sum(counts.values())

            context_parts.append(
                f"Exact sentiment counts from analyzed usable reviews: "
                f"{counts}; analyzed total: {analyzed}."
            )

            matched_count = analyzed
            intent = "sentiment_distribution"
            sql_description = (
                "GROUP BY sentiment label for usable reviews"
            )

        needs_dataset = self._needs_dataset(clean_q)

        if needs_dataset:
            reviews = self._retrieve_reviews(
                db,
                dataset_id,
                clean_q,
            )

            matched_count = max(matched_count, len(reviews))

            if reviews:
                if intent == "ev_knowledge":
                    intent = "dataset_rag"

                for review in reviews:
                    text = (
                        review.cleaned_text
                        or review.original_text
                        or ""
                    ).strip()

                    if not text:
                        continue

                    aspects = [
                        f"{prediction.aspect}:{prediction.polarity}"
                        for prediction in (review.predictions or [])
                    ]

                    sentiment = (
                        review.sentiment.overall_sentiment
                        if review.sentiment
                        else None
                    )

                    evidence_item = {
                        "review_id": review.id,
                        "text": text[:1200],
                        "rating": review.rating,
                        "aspects": aspects,
                        "sentiment": sentiment,
                    }

                    evidence.append(evidence_item)

                context_parts.append(
                    "Retrieved review evidence. These are user-generated "
                    "opinions, not universal facts:"
                )

                context_parts.extend(
                    f"[{index}] Rating={item['rating']}; "
                    f"sentiment={item['sentiment']}; "
                    f"aspects={', '.join(item['aspects']) or 'not classified'}; "
                    f"review={item['text']}"
                    for index, item in enumerate(evidence, start=1)
                )

                sql_description = (
                    "Dataset-scoped usable review text/aspect retrieval"
                )

            else:
                context_parts.append(
                    "No sufficiently relevant review evidence was retrieved. "
                    "Do not claim that the dataset supports a conclusion."
                )
                intent = "dataset_rag_no_match"
                sql_description = (
                    "Dataset-scoped retrieval returned no relevant matches"
                )

        system_prompt = """
You are AlphaEV, an EV charging review intelligence assistant.

Answer the user's actual question directly in natural, helpful language.

Scope:
- Help with EV charging stations, charging infrastructure, charging apps,
  payments, pricing, reliability, waiting time, availability and customer support.
- Answer questions about the selected review dataset.
- For unrelated topics, politely explain that you specialize in EVs
  and EV review analysis.

Grounding rules:
- Treat the supplied dataset context as the only source for claims about
  what this dataset's users said, counts, percentages, ratings and sentiment.
- Never invent counts, percentages, brands, quotations or dataset findings.
- If evidence is absent, say that the dataset does not provide enough evidence.
- For general EV educational questions, use general knowledge without
  pretending that the dataset proves it.
- Clearly distinguish general knowledge from dataset-specific observations.
- When relevant reviews are supplied, synthesize their patterns and cite
  them briefly as [1], [2], etc.
- Do not repeat all review text verbatim.
- Preserve exact SQL-derived metrics. Do not calculate new statistics
  from a small sample of retrieved reviews.
- Offer practical recommendations when asked.
- Be concise, clear and transparent about uncertainty.

Formatting rules:
- Always respond using standard Markdown.
- Never generate HTML tags such as <br>, <div>, or <p>.
- Use headings and bullet points to organize explanations.
- Use Markdown tables only when comparing multiple categories.
- Keep table cells short and readable.
- Use bold text for important findings.
- Avoid unnecessarily wide tables.
- Prefer numbered lists for explanations and recommendations.
"""

        user_prompt = (
            f"USER QUESTION:\n{clean_q}\n\n"
            "ALPHAEV DATASET CONTEXT:\n"
            + "\n".join(context_parts)
        )

        try:
            answer = self._call_cohere(
                system_prompt,
                user_prompt,
            )

        except RuntimeError as exc:
            return self._result(
                clean_q,
                str(exc),
                "llm_unavailable",
                evidence=evidence,
                total_matched=matched_count,
                sql_or_search=sql_description,
            )

        return self._result(
            clean_q,
            answer,
            intent,
            evidence=evidence,
            total_matched=matched_count,
            sql_or_search=sql_description,
        )

    @staticmethod
    def _result(
        query: str,
        answer: str,
        intent: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        total_matched: int = 0,
        sql_or_search: str = "N/A",
    ) -> Dict[str, Any]:

        return {
            "query": query,
            "answer": answer,
            "intent": intent,
            "sql_or_search": sql_or_search,
            "total_matched": total_matched,
            "evidence": evidence or [],
        }


chatbot_service = ChatbotService()