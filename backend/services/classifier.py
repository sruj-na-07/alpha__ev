
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from backend.ml.seed_data import (
    SEED_DATA,
    ASPECT_DISPLAY_NAMES,
    ALL_LABELS,
)


# ============================================================
# 1. EV CHARGING-STATION ASPECT KEYWORDS
# ============================================================

ASPECT_KEYWORDS = {
    "pricing": [
        "price", "pricing", "tariff", "charging cost", "cost per kwh",
        "expensive", "cheap", "affordable", "overpriced", "rate",
        "charging fee", "service charge", "electricity rate",
    ],
    "payment_issues": [
        "payment", "paid", "payment failed", "transaction", "refund",
        "wallet", "billing", "charged twice", "double charge",
        "money deducted", "upi", "invoice", "receipt", "recharge balance",
    ],
    "charging_speed": [
        "charging speed", "charge speed", "slow charging", "fast charging",
        "charging time", "takes hours", "kw", "kilowatt", "power output",
        "charging rate", "charging took", "charged quickly",
    ],
    "reliability": [
        "charger not working", "charger broken", "charger offline",
        "station down", "not operational", "out of order", "fault",
        "failed to charge", "charging failed", "stopped charging",
        "unreliable", "working properly", "technical issue",
    ],
    "waiting_time": [
        "waiting", "wait time", "queue", "queued", "long wait",
        "waiting time", "delay", "delayed", "busy", "waiting for charger",
    ],
    "app_usability": [
        "app", "application", "login", "log in", "sign in", "signup",
        "sign up", "crash", "crashes", "freezes", "interface", "ui",
        "user friendly", "easy to use", "difficult to use", "map",
        "booking", "session history", "location not updating",
    ],
    "availability": [
        "available", "availability", "occupied", "unavailable",
        "charger available", "no charger", "fully occupied",
        "slots available", "all chargers busy", "not available",
        "charger status", "reservation",
    ],
    "location_convenience": [
        "location", "located", "directions", "navigation", "nearby",
        "easy to find", "hard to find", "accessible", "accessibility",
        "parking", "station location", "easy to reach", "remote location",
    ],
    "improvement_suggestion": [
        "should improve", "please add", "please improve", "suggest",
        "suggestion", "need to add", "would be better", "request",
        "recommend adding", "hope they", "needs improvement",
        "more chargers", "add more stations",
    ],
    "overall_experience": [
        "overall experience", "overall", "experience", "service",
        "convenient", "satisfied", "dissatisfied", "disappointed",
        "excellent service", "great experience", "poor experience",
        "good service", "bad service", "recommend this app",
    ],
    "customer_support": [
        "customer support", "customer service", "support team",
        "help desk", "helpline", "complaint", "complaints",
        "no response", "responded", "response from support",
        "support ticket", "issue resolution", "resolved my issue",
        "not resolved", "customer care", "contacted support",
        "assistance", "representative", "service team",
    ],
}


POSITIVE_WORDS = {
    "good", "great", "excellent", "amazing", "awesome", "fast",
    "smooth", "easy", "quick", "helpful", "reliable", "available",
    "convenient", "affordable", "cheap", "responsive", "resolved",
    "satisfied", "best", "perfect", "friendly", "efficient",
    "working", "seamless", "improved", "recommend", "successful",
    "accurate", "accessible", "prompt", "polite",
}

NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "worst", "slow", "failed", "failure",
    "broken", "unavailable", "expensive", "overpriced", "crashed",
    "crash", "bug", "bugs", "error", "errors", "problem", "problems",
    "issue", "issues", "delay", "delayed", "frustrating", "useless",
    "disappointed", "unreliable", "stuck", "deducted", "refused",
    "unresponsive", "inconvenient", "difficult", "waste", "incorrect",
    "unresolved", "rude", "inaccessible", "cancelled", "failed",
}

NEGATIONS = {
    "not", "no", "never", "hardly", "barely", "without", "neither",
    "didn't", "didnt", "don't", "dont", "doesn't", "doesnt",
    "wasn't", "wasnt", "isn't", "isnt", "won't", "wont",
    "can't", "cant", "couldn't", "couldnt",
}

INTENSIFIERS = {
    "very", "extremely", "really", "highly", "super", "too",
    "incredibly", "absolutely",
}

EMOTION_KEYWORDS = {
    "frustrated": [
        "frustrated", "frustrating", "angry", "annoyed", "annoying",
        "nightmare", "ridiculous", "fed up", "useless", "scam",
    ],
    "sad": [
        "disappointed", "disappointing", "regret", "upset",
        "unfortunate", "letdown", "sad",
    ],
    "happy": [
        "happy", "love", "loved", "thrilled", "excited", "awesome",
        "delighted", "fantastic", "amazing",
    ],
    "satisfaction": [
        "satisfied", "satisfaction", "helpful", "dependable",
        "convenient", "reliable", "pleased", "worth it",
    ],
    "neutral": [
        "average", "okay", "ok", "fine", "normal", "moderate",
    ],
}


# ============================================================
# 2. TEXT UTILITIES
# ============================================================

def _normalize_text(text: Any) -> str:
    """Normalize missing values and whitespace without losing meaning."""
    if text is None:
        return ""

    if isinstance(text, float) and np.isnan(text):
        return ""

    return re.sub(r"\s+", " ", str(text)).strip().lower()


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match whole words/phrases to reduce accidental substring matches."""
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _is_negated(words: List[str], index: int) -> bool:
    """Check nearby words for negation, including common contractions."""
    start = max(0, index - 3)
    window = words[start:index]

    if any(word in NEGATIONS for word in window):
        return True

    # Handle constructions such as 'unable to charge' and 'failed to pay'.
    preceding = " ".join(window)
    return any(
        phrase in preceding
        for phrase in (
            "unable to", "failed to", "fails to",
            "not able to", "never able to",
        )
    )


# ============================================================
# 3. RULE-BASED SENTIMENT AND EMOTION
# ============================================================

class RuleBasedSentimentAnalyzer:
    """Lightweight sentiment and emotion analyzer for EV service reviews."""

    def analyze_sentiment(
        self,
        text: str,
        rating: Optional[float] = None,
    ) -> Tuple[str, float]:

        text = _normalize_text(text)
        words = re.findall(r"\b[a-zA-Z]+(?:'[a-z]+)?\b", text)

        pos_score = 0.0
        neg_score = 0.0

        for i, word in enumerate(words):
            negated = _is_negated(words, i)

            weight = 1.5 if i > 0 and words[i - 1] in INTENSIFIERS else 1.0

            if word in POSITIVE_WORDS:
                if negated:
                    neg_score += weight
                else:
                    pos_score += weight

            elif word in NEGATIVE_WORDS:
                if negated:
                    pos_score += weight * 0.8
                else:
                    neg_score += weight

        # A star rating is supplementary evidence, not a replacement
        # for the actual text. Ratings should be on a 1-5 scale.
        if rating is not None:
            try:
                rating = float(rating)
                if np.isfinite(rating) and 1 <= rating <= 5:
                    if rating >= 4:
                        pos_score += 1.0 * (rating - 3)
                    elif rating <= 2:
                        neg_score += 1.0 * (3 - rating)
            except (TypeError, ValueError):
                pass

        total = pos_score + neg_score
        difference = pos_score - neg_score

        if total == 0:
            if rating is not None:
                try:
                    r = float(rating)
                    if np.isfinite(r) and 1 <= r <= 5:
                        if r >= 4:
                            return "positive", 0.70
                        if r <= 2:
                            return "negative", 0.70
                except (TypeError, ValueError):
                    pass
            return "neutral", 0.65

        if difference > 0:
            sentiment = "positive"
        elif difference < 0:
            sentiment = "negative"
        else:
            return "neutral", 0.65

        confidence = min(
            0.60 + abs(difference) / (total + 1.0) * 0.35,
            0.95,
        )
        return sentiment, round(confidence, 3)

    def analyze_emotion(
        self,
        text: str,
        overall_sentiment: str,
    ) -> Tuple[str, float]:

        text = _normalize_text(text)

        counts = {
            emotion: sum(
                1 for phrase in phrases
                if _contains_phrase(text, phrase)
            )
            for emotion, phrases in EMOTION_KEYWORDS.items()
        }

        # Avoid assigning neutral just because it appears first.
        non_neutral = {
            k: v for k, v in counts.items() if k != "neutral"
        }

        best_emotion = max(non_neutral, key=non_neutral.get)

        if non_neutral[best_emotion] > 0:
            confidence = min(
                0.65 + non_neutral[best_emotion] * 0.08, 0.93
            )
            return best_emotion, round(confidence, 3)

        if overall_sentiment == "positive":
            return "satisfaction", 0.70
        if overall_sentiment == "negative":
            return "frustrated", 0.70

        return "neutral", 0.75


# ============================================================
# 4. ALPHAEV ASPECT CLASSIFIER
# ============================================================

class AlphaEVClassifier:
    """
    Multi-label classifier for EV charging-station reviews.

    Uses:
    - TF-IDF and One-vs-Rest Logistic Regression
    - Curated charging-domain keyword fallback
    - Aspect-specific polarity heuristics
    - Linear-model word attribution explanations
    """

    def __init__(self):
        self.rule_sentiment = RuleBasedSentimentAnalyzer()

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
            stop_words="english",
        )

        self.mlb = MultiLabelBinarizer(classes=ALL_LABELS)
        self.model: Optional[OneVsRestClassifier] = None
        self.is_trained = False

        self._initialize_seed_model()

    def _initialize_seed_model(self):
        """Fit the baseline classifier using curated EV review examples."""
        if not SEED_DATA:
            return

        texts = [item[0] for item in SEED_DATA]
        labels = [item[1] for item in SEED_DATA]

        try:
            self.train(texts, labels)
        except (ValueError, TypeError) as exc:
            print(f"[Warning] Could not initialize seed model: {exc}")

    def train(
        self,
        texts: List[str],
        labels: List[List[str]],
    ):
        """Train using labels such as ['pricing:neg', 'app_usability:pos']."""
        if len(texts) != len(labels) or not texts:
            raise ValueError("Texts and labels must be non-empty and equal in length.")

        cleaned_texts = [_normalize_text(t) for t in texts]

        if any(not text for text in cleaned_texts):
            raise ValueError("Training data contains empty review text.")

        valid_labels = set(ALL_LABELS)
        for row_labels in labels:
            unknown = set(row_labels) - valid_labels
            if unknown:
                raise ValueError(f"Unknown labels in training data: {unknown}")

        X = self.vectorizer.fit_transform(cleaned_texts)
        y = self.mlb.fit_transform(labels)

        base_estimator = LogisticRegression(
            C=1.5,
            max_iter=500,
            class_weight="balanced",
            solver="liblinear",
        )

        self.model = OneVsRestClassifier(base_estimator)
        self.model.fit(X, y)
        self.is_trained = True

    def _rule_based_aspect_predict(
        self,
        text: str,
    ) -> List[Dict[str, Any]]:
        """Detect charging-station aspects and estimate their polarity."""
        normalized = _normalize_text(text)
        words = re.findall(r"\b[a-zA-Z]+(?:'[a-z]+)?\b", normalized)
        predictions = []

        for aspect, keywords in ASPECT_KEYWORDS.items():
            matched = [
                phrase for phrase in keywords
                if _contains_phrase(normalized, phrase)
            ]

            if not matched:
                continue

            # Locate keyword occurrences and inspect local sentiment.
            pos_score = 0.0
            neg_score = 0.0

            for phrase in matched:
                phrase_words = phrase.split()

                positions = [
                    i for i in range(len(words))
                    if words[i:i + len(phrase_words)] == phrase_words
                ]

                for position in positions:
                    start = max(0, position - 4)
                    end = min(len(words), position + len(phrase_words) + 5)
                    window = words[start:end]

                    for j, word in enumerate(window):
                        negated = _is_negated(window, j)
                        weight = (
                            1.5 if j > 0 and window[j - 1] in INTENSIFIERS
                            else 1.0
                        )

                        if word in POSITIVE_WORDS:
                            if negated:
                                neg_score += weight
                            else:
                                pos_score += weight
                        elif word in NEGATIVE_WORDS:
                            if negated:
                                pos_score += weight * 0.8
                            else:
                                neg_score += weight

            # Explicit improvement suggestions are not automatically negative.
            if aspect == "improvement_suggestion" and matched:
                polarity = "neg" if neg_score > pos_score else "pos"
                confidence = 0.70

            elif pos_score == 0 and neg_score == 0:
                overall, _ = self.rule_sentiment.analyze_sentiment(normalized)
                polarity = (
                    "pos" if overall == "positive"
                    else "neg" if overall == "negative"
                    else "pos"
                )
                confidence = 0.60

            elif pos_score > neg_score:
                polarity = "pos"
                confidence = min(0.65 + 0.05 * pos_score, 0.90)

            elif neg_score > pos_score:
                polarity = "neg"
                confidence = min(0.65 + 0.05 * neg_score, 0.90)

            else:
                polarity = "pos"
                confidence = 0.60

            predictions.append({
                "aspect": aspect,
                "polarity": polarity,
                "confidence": round(confidence, 3),
                "model_prediction": f"{aspect}:{polarity}",
                "model_confidence": round(confidence, 3),
            })

        return predictions

    def predict(
        self,
        text: str,
        threshold: float = 0.35,
        use_fallback: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return the detected aspects and their predicted polarities."""
        normalized = _normalize_text(text)

        if not normalized:
            return []

        results: List[Dict[str, Any]] = []

        if self.is_trained and self.model is not None:
            try:
                X = self.vectorizer.transform([normalized])
                probabilities = self.model.predict_proba(X)[0]

                for idx, probability in enumerate(probabilities):
                    if probability >= threshold:
                        label = self.mlb.classes_[idx]
                        aspect, polarity = label.rsplit(":", 1)

                        results.append({
                            "aspect": aspect,
                            "polarity": polarity,
                            "confidence": round(float(probability), 3),
                            "model_prediction": label,
                            "model_confidence": round(float(probability), 3),
                        })
            except (ValueError, AttributeError, IndexError) as exc:
                print(f"[Warning] Model prediction failed: {exc}")

        # Use domain rules when the model has no confident predictions.
        if not results and use_fallback:
            results = self._rule_based_aspect_predict(normalized)

        # Keep only one polarity per aspect, choosing the higher confidence.
        unique: Dict[str, Dict[str, Any]] = {}
        for result in results:
            aspect = result["aspect"]
            if (
                aspect not in unique
                or result["confidence"] > unique[aspect]["confidence"]
            ):
                unique[aspect] = result

        return list(unique.values())

    def explain(
        self,
        text: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Return influential TF-IDF terms for the predicted labels.
        This is linear-model feature attribution, not SHAP itself.
        """
        predictions = self.predict(text, threshold=0.25)

        if not self.is_trained or self.model is None or not predictions:
            explanations = {}

            for prediction in predictions:
                aspect = prediction["aspect"]
                polarity = prediction["polarity"]
                text_lower = _normalize_text(text)

                matched_words = [
                    keyword for keyword in ASPECT_KEYWORDS.get(aspect, [])
                    if _contains_phrase(text_lower, keyword)
                ]

                explanations[f"{aspect}:{polarity}"] = [
                    {"word": word, "score": 0.5}
                    for word in matched_words[:top_k]
                ]

            return {
                "aspect_explanations": explanations,
                "summary": "Explanations are based on charging-domain keywords.",
            }

        X = self.vectorizer.transform([_normalize_text(text)])
        feature_names = self.vectorizer.get_feature_names_out()
        explanations: Dict[str, List[Dict[str, Any]]] = {}
        summary_parts = []

        for prediction in predictions:
            label = (
                f"{prediction['aspect']}:{prediction['polarity']}"
            )

            if label not in self.mlb.classes_:
                continue

            class_idx = list(self.mlb.classes_).index(label)
            estimator = self.model.estimators_[class_idx]
            coefficients = estimator.coef_[0]

            contributions = []
            for col_idx in X.nonzero()[1]:
                value = float(X[0, col_idx])
                contribution = value * float(coefficients[col_idx])

                if contribution > 0:
                    contributions.append(
                        (feature_names[col_idx], contribution)
                    )

            contributions.sort(key=lambda item: item[1], reverse=True)
            top_words = contributions[:top_k]

            explanations[label] = [
                {"word": word, "score": round(score, 4)}
                for word, score in top_words
            ]

            display_name = ASPECT_DISPLAY_NAMES.get(
                prediction["aspect"], prediction["aspect"]
            )

            if top_words:
                summary_parts.append(
                    f"{display_name} ({prediction['polarity']}): "
                    + ", ".join(word for word, _ in top_words[:3])
                )

        return {
            "aspect_explanations": explanations,
            "summary": " | ".join(summary_parts)
            if summary_parts else "No influential terms were identified.",
        }


# Shared service instance used by the backend.
classifier_service = AlphaEVClassifier()
