import re
import os
import pickle
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from backend.ml.seed_data import SEED_DATA, ASPECT_DISPLAY_NAMES, ALL_LABELS

# -------------------------------------------------------------
# Curated Aspect Keywords & Sentiment Lexicon
# -------------------------------------------------------------

ASPECT_KEYWORDS = {
    "range_battery": [
        "range", "battery", "miles", "mileage", "km", "kwh", "degradation",
        "degrade", "battery health", "drain", "phantom drain", "winter range",
        "cold weather range", "efficiency", "mpge", "wh/mi", "wh/km", "pack",
        "soc", "state of charge", "capacity", "bms", "battery management",
    ],
    "charging": [
        "charge", "charging", "charger", "supercharger", "supercharging",
        "ccs", "nacs", "chademo", "plug", "station", "level 2", "l2", "dcfc",
        "fast charge", "fast charging", "electrify america", "evgo", "ionity",
        "chargepoint", "stall", "kwh rate", "kw", "charge port", "connector",
    ],
    "performance": [
        "acceleration", "torque", "speed", "fast", "quick", "handling",
        "steering", "responsive", "pedal", "power", "0-60", "horse power",
        "horsepower", "regen", "regenerative", "braking", "cornering",
        "sport mode", "drive unit", "motor", "dual motor", "awd",
    ],
    "software_infotainment": [
        "software", "screen", "touchscreen", "infotainment", "navigation",
        "gps", "display", "ota", "update", "bluetooth", "carplay", "android auto",
        "app", "mobile app", "lag", "ui", "interface", "audio", "sound system",
        "spotify", "connectivity", "glitch", "freeze", "reboot",
    ],
    "interior_comfort": [
        "seat", "seats", "cabin", "quiet", "noise", "road noise", "wind noise",
        "comfortable", "comfort", "suspension", "ride", "ride quality",
        "materials", "leather", "dashboard", "ac", "air condition", "heating",
        "heat pump", "ventilated", "lumbar", "headroom", "legroom",
    ],
    "build_quality": [
        "build quality", "panel gap", "panel gaps", "paint", "finish", "fit and finish",
        "squeak", "squeaks", "rattle", "rattles", "trim", "door", "glass",
        "seal", "seals", "alignment", "weatherstrip", "water leak", "defect",
    ],
    "safety_driver_assist": [
        "autopilot", "fsd", "self-driving", "driver assist", "adas", "cruise control",
        "adaptive cruise", "lane keep", "blind spot", "phantom brake", "phantom braking",
        "sensor", "camera", "airbag", "safety", "collision", "emergency brake",
    ],
    "price_value": [
        "price", "cost", "value", "expensive", "cheap", "affordable", "tax credit",
        "rebate", "incentive", "depreciation", "resale", "overpriced", "worth it",
        "deal", "lease", "insurance", "subscription",
    ],
    "customer_service": [
        "customer service", "dealer", "dealership", "service center", "support",
        "warranty", "appointment", "loaner", "mechanic", "repair", "ticket",
        "delivery", "advisor", "recall", "service team",
    ],
    "reliability": [
        "reliable", "reliability", "breakdown", "broke down", "broken", "issue",
        "problem", "failure", "stranded", "tow", "towed", "error code",
        "warning light", "fault", "durable", "durability", "12v battery", "bricked",
    ],
    "space_practicality": [
        "space", "trunk", "frunk", "cargo", "storage", "boot", "practical",
        "practicality", "family", "stroller", "luggage", "folding seats",
        "roomy", "cramped", "backseat", "back seat",
    ],
}

POSITIVE_WORDS = {
    "great", "excellent", "amazing", "good", "fast", "smooth", "love", "loved",
    "best", "perfect", "flawless", "impressive", "outstanding", "reliable",
    "comfortable", "quiet", "high", "easy", "effortless", "fantastic", "solid",
    "pleased", "happy", "recommend", "superior", "snappy", "wonderful", "super",
    "plenty", "spacious", "responsive", "intuitive", "helpful", "valuable", "exceeded",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "horrible", "poor", "slow", "disappointed", "disappointing",
    "broken", "broke", "issue", "issues", "problem", "problems", "fail", "failed",
    "failure", "awful", "worst", "uncomfortable", "noisy", "loud", "cheap",
    "expensive", "overpriced", "glitch", "buggy", "laggy", "stranded", "freeze",
    "freezes", "died", "dead", "unacceptable", "annoying", "hate", "hated",
    "cramped", "harsh", "stiff", "rattle", "squeak", "defect", "flawed", "useless",
}

NEGATIONS = {
    "not", "no", "never", "hardly", "barely", "scarcely", "without", "none",
    "didn't", "didnt", "don't", "dont", "doesn't", "doesnt", "wasn't", "wasnt",
    "isn't", "isnt", "won't", "wont", "can't", "cant", "couldn't", "couldnt",
}

EMOTION_KEYWORDS = {
    "frustrated": [
        "frustrated", "frustrating", "annoyed", "annoying", "angry", "terrible",
        "nightmare", "scam", "unacceptable", "furious", "garbage", "lemon",
        "stranded", "ridiculous", "worst experience", "fed up", "waste of money",
    ],
    "sad": [
        "disappointed", "disappointing", "sad", "unfortunate", "regret", "regretted",
        "upset", "pity", "depressed", "letdown", "wished", "miss", "shame",
    ],
    "happy": [
        "happy", "love", "thrilled", "excited", "awesome", "delighted", "joy",
        "fun", "best car", "fantastic", "amazing", "smiling", "ecstatic",
    ],
    "satisfaction": [
        "satisfied", "satisfaction", "content", "solid", "dependable", "meets expectations",
        "good enough", "does the job", "reliable", "practical", "reasonable", "pleased",
    ],
    "neutral": [
        "average", "okay", "ok", "fine", "neutral", "standard", "normal", "moderate",
    ],
}


class RuleBasedSentimentAnalyzer:
    """EV-domain rule-based sentiment and emotion analyzer."""

    def analyze_sentiment(
        self,
        text: str,
        rating: Optional[float] = None,
    ) -> Tuple[str, float]:
        """
        Determines overall sentiment ('positive', 'negative', 'neutral')
        and confidence score (0.0 to 1.0).
        """
        text_lower = text.lower()
        words = re.findall(r"\b[a-zA-Z\'-]+\b", text_lower)

        pos_score = 0.0
        neg_score = 0.0

        for i, word in enumerate(words):
            # Check negation in previous 3 words
            negated = False
            start_window = max(0, i - 3)
            for prev in words[start_window:i]:
                if prev in NEGATIONS:
                    negated = True
                    break

            weight = 1.0
            if i > 0 and words[i - 1] in {"very", "extremely", "super", "highly", "really"}:
                weight = 1.5

            if word in POSITIVE_WORDS:
                if negated:
                    neg_score += weight
                else:
                    pos_score += weight
            elif word in NEGATIVE_WORDS:
                if negated:
                    pos_score += weight * 0.8  # "not bad" is mildly positive
                else:
                    neg_score += weight

        # Calibrate with rating if provided (1-5 star scale)
        if rating is not None and not np.isnan(rating):
            if rating >= 4.0:
                pos_score += 1.5 * (rating - 3.0)
            elif rating <= 2.0:
                neg_score += 1.5 * (3.0 - rating)

        diff = pos_score - neg_score
        total = pos_score + neg_score

        if total == 0:
            if rating is not None and not np.isnan(rating):
                if rating >= 4.0:
                    return "positive", min(0.65 + (rating - 4.0) * 0.15, 0.95)
                elif rating <= 2.0:
                    return "negative", min(0.65 + (2.0 - rating) * 0.15, 0.95)
            return "neutral", 0.70

        if diff > 0.5:
            confidence = min(0.60 + (diff / (total + 1.0)) * 0.35, 0.98)
            return "positive", round(confidence, 3)
        elif diff < -0.5:
            confidence = min(0.60 + (abs(diff) / (total + 1.0)) * 0.35, 0.98)
            return "negative", round(confidence, 3)
        else:
            confidence = 0.65
            return "neutral", round(confidence, 3)

    def analyze_emotion(
        self,
        text: str,
        overall_sentiment: str,
    ) -> Tuple[str, float]:
        """
        Determines dominant emotion ('happy', 'sad', 'frustrated', 'satisfaction', 'neutral')
        and confidence.
        """
        text_lower = text.lower()
        counts: Dict[str, float] = {k: 0.0 for k in EMOTION_KEYWORDS}

        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    counts[emotion] += 1.0

        # Strongest detected emotion keyword
        best_emotion = max(counts, key=counts.get)
        max_count = counts[best_emotion]

        if max_count > 0:
            confidence = min(0.65 + max_count * 0.1, 0.95)
            return best_emotion, round(confidence, 3)

        # Fallback based on sentiment
        if overall_sentiment == "positive":
            return "satisfaction", 0.70
        elif overall_sentiment == "negative":
            return "frustrated", 0.70
        else:
            return "neutral", 0.80


class AlphaEVClassifier:
    """
    Hybrid Aspect-Based Sentiment Classification Engine:
    1. Scikit-learn TF-IDF + LogisticRegression (One-Vs-Rest) for all 22 classes.
    2. Curated rule-based keyword & context fallback that operates zero-shot.
    3. Integrated SHAP word attribution explanations for linear classifiers.
    """

    def __init__(self):
        self.rule_sentiment = RuleBasedSentimentAnalyzer()
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
            stop_words="english",
        )
        self.mlb = MultiLabelBinarizer(classes=ALL_LABELS)
        self.model: Optional[OneVsRestClassifier] = None
        self.is_trained = False

        # Initialize and fit on curated seed dataset immediately
        self._initialize_seed_model()

    def _initialize_seed_model(self):
        """Train baseline model with rich curated seed data so it works immediately."""
        texts = [item[0] for item in SEED_DATA]
        labels = [item[1] for item in SEED_DATA]

        try:
            self.train(texts, labels)
        except Exception as e:
            print(f"[Warning] Seed model initialization skipped: {e}")

    def train(self, texts: List[str], labels: List[List[str]]):
        """
        Train the TF-IDF and OneVsRest LogisticRegression model.
        labels is a list of label lists, e.g. [["range_battery:pos", "charging:pos"]]
        """
        X = self.vectorizer.fit_transform(texts)
        y = self.mlb.fit_transform(labels)

        base_estimator = LogisticRegression(
            C=1.5,
            max_iter=300,
            class_weight="balanced",
            solver="liblinear",
        )
        self.model = OneVsRestClassifier(base_estimator)
        self.model.fit(X, y)
        self.is_trained = True

    def _rule_based_aspect_predict(self, text: str) -> List[Dict[str, Any]]:
        """Zero-shot aspect and polarity classifier based on keywords and context."""
        text_lower = text.lower()
        words = re.findall(r"\b[a-zA-Z\'-]+\b", text_lower)
        predictions = []

        for aspect, keywords in ASPECT_KEYWORDS.items():
            found_kw = False
            for kw in keywords:
                if kw in text_lower:
                    found_kw = True
                    break

            if not found_kw:
                continue

            # Determine polarity in context of this aspect
            pos_matches = 0
            neg_matches = 0

            # Scan surrounding words
            for i, word in enumerate(words):
                if any(kw_part in word for kw_part in keywords if len(kw_part) > 3):
                    # Check window of 5 words around keyword
                    start = max(0, i - 4)
                    end = min(len(words), i + 5)
                    window = words[start:end]

                    # Negation check
                    has_negation = any(neg in window[:min(4, len(window))] for neg in NEGATIONS)

                    for w in window:
                        if w in POSITIVE_WORDS:
                            if has_negation:
                                neg_matches += 1
                            else:
                                pos_matches += 1
                        elif w in NEGATIVE_WORDS:
                            if has_negation:
                                pos_matches += 0.8
                            else:
                                neg_matches += 1

            # Default to text-level sentiment if window is neutral
            if pos_matches == 0 and neg_matches == 0:
                overall, _ = self.rule_sentiment.analyze_sentiment(text)
                polarity = "pos" if overall == "positive" else ("neg" if overall == "negative" else "pos")
                confidence = 0.72
            elif pos_matches >= neg_matches:
                polarity = "pos"
                confidence = min(0.75 + (pos_matches * 0.05), 0.95)
            else:
                polarity = "neg"
                confidence = min(0.75 + (neg_matches * 0.05), 0.95)

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
        """
        Predict aspect labels and polarities for a given text.
        Returns a list of dicts:
        [{'aspect': 'range_battery', 'polarity': 'pos', 'confidence': 0.88, ...}]
        """
        results: List[Dict[str, Any]] = []

        if self.is_trained and self.model:
            try:
                X = self.vectorizer.transform([text])
                probabilities = self.model.predict_proba(X)[0]

                for idx, prob in enumerate(probabilities):
                    if prob >= threshold:
                        label = self.mlb.classes_[idx]
                        aspect, polarity = label.split(":")
                        results.append({
                            "aspect": aspect,
                            "polarity": polarity,
                            "confidence": round(float(prob), 3),
                            "model_prediction": label,
                            "model_confidence": round(float(prob), 3),
                        })
            except Exception:
                pass

        # If model gave no results or fallback is requested when empty
        if not results and use_fallback:
            results = self._rule_based_aspect_predict(text)

        # De-duplicate aspect pairs: if both pos and neg exist for same aspect, pick higher confidence
        aspect_dict: Dict[str, Dict[str, Any]] = {}
        for res in results:
            asp = res["aspect"]
            if asp not in aspect_dict or res["confidence"] > aspect_dict[asp]["confidence"]:
                aspect_dict[asp] = res

        return list(aspect_dict.values())

    def explain(self, text: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Explain predictions using feature attribution / SHAP method for linear TF-IDF model.
        Returns top influential words for each active aspect.
        """
        predictions = self.predict(text, threshold=0.25)
        if not self.is_trained or not self.model or not predictions:
            # Fallback explanation using keyword matches
            explanations: Dict[str, List[Dict[str, Any]]] = {}
            for pred in predictions:
                aspect = pred["aspect"]
                polarity = pred["polarity"]
                kws = [w for w in text.lower().split() if w in ASPECT_KEYWORDS.get(aspect, []) or w in POSITIVE_WORDS or w in NEGATIVE_WORDS]
                explanations[f"{aspect}:{polarity}"] = [
                    {"word": kw, "score": 0.8} for kw in kws[:top_k]
                ]
            return {
                "aspect_explanations": explanations,
                "summary": "Explanations generated from EV aspect and sentiment keywords.",
            }

        X = self.vectorizer.transform([text])
        feature_names = self.vectorizer.get_feature_names_out()
        explanations = {}

        # For linear models, shap attribution = feature_value * weight
        feature_indices = X.nonzero()[1]
        feature_values = X.data

        summary_parts = []

        for pred in predictions:
            label = f"{pred['aspect']}:{pred['polarity']}"
            if label not in self.mlb.classes_:
                continue

            class_idx = list(self.mlb.classes_).index(label)
            estimator = self.model.estimators_[class_idx]
            coefs = estimator.coef_[0]

            word_scores = []
            for col_idx, val in zip(feature_indices, feature_values):
                weight = coefs[col_idx]
                attribution = float(val * weight)
                if attribution > 0:
                    word_scores.append((feature_names[col_idx], attribution))

            # Sort by attribution
            word_scores.sort(key=lambda x: x[1], reverse=True)
            top_words = word_scores[:top_k]

            explanations[label] = [
                {"word": w, "score": round(score, 4)} for w, score in top_words
            ]

            display_aspect = ASPECT_DISPLAY_NAMES.get(pred['aspect'], pred['aspect'])
            if top_words:
                words_str = ", ".join([f"'{w}' (+{s:.2f})" for w, s in top_words[:3]])
                summary_parts.append(
                    f"{display_aspect} ({'Positive' if pred['polarity'] == 'pos' else 'Negative'}): strongly driven by {words_str}."
                )

        summary = " | ".join(summary_parts) if summary_parts else "Prediction attribution computed across tokens."

        return {
            "aspect_explanations": explanations,
            "summary": summary,
        }


classifier_service = AlphaEVClassifier()
