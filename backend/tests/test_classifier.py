"""
Unit and integration tests for AlphaEV's multi-label classifier.

Validates:
- 11 EV charging review aspects and 22 aspect-polarity labels
- Prediction structure and confidence ranges
- Detection of multiple aspects in a single review
- Customer support aspect detection
- Explanation output format
- Benchmark evaluation metrics
- Valid predictions for realistic EV charging app reviews

Note:
These tests validate functionality and output structure.
They do not claim production-level model accuracy.
"""

import pytest

from backend.services.classifier import (
    AlphaEVClassifier,
    classifier_service,
)
from backend.ml.seed_data import (
    ALL_LABELS,
    ASPECT_DISPLAY_NAMES,
)
from backend.ml.evaluation import evaluate_model_on_benchmark


EXPECTED_ASPECTS = {
    "pricing",
    "payment_issues",
    "charging_speed",
    "reliability",
    "waiting_time",
    "app_usability",
    "availability",
    "location_convenience",
    "improvement_suggestion",
    "overall_experience",
    "customer_support",
}


@pytest.fixture
def classifier():
    """Use the shared classifier service."""
    return classifier_service


def test_aspect_definitions_count():
    """Verify all 11 charging-related aspects and 22 labels exist."""
    assert len(ASPECT_DISPLAY_NAMES) == 11
    assert len(ALL_LABELS) == 22

    assert set(ASPECT_DISPLAY_NAMES.keys()) == EXPECTED_ASPECTS

    for aspect in EXPECTED_ASPECTS:
        assert f"{aspect}:pos" in ALL_LABELS
        assert f"{aspect}:neg" in ALL_LABELS


def test_classifier_predict_multi_aspect(classifier):
    """A review mentioning different charging issues should detect multiple aspects."""
    text = (
        "The charging price is too expensive and the payment failed twice. "
        "The app is easy to use, but the charging station was unavailable."
    )

    predictions = classifier.predict(text, threshold=0.25)

    assert isinstance(predictions, list)
    assert len(predictions) >= 2

    aspects_found = {prediction["aspect"] for prediction in predictions}

    # The review explicitly mentions pricing and payment problems.
    assert "pricing" in aspects_found
    assert "payment_issues" in aspects_found

    for prediction in predictions:
        assert prediction["aspect"] in EXPECTED_ASPECTS
        assert prediction["polarity"] in {"pos", "neg"}
        assert 0.0 <= prediction["confidence"] <= 1.0


def test_classifier_detects_customer_support(classifier):
    """Customer support must be part of the charging-app taxonomy."""
    text = (
        "Customer support never answered my complaint, "
        "and the service team did not resolve my charging issue."
    )

    predictions = classifier.predict(text, threshold=0.25)

    assert isinstance(predictions, list)

    aspects_found = {prediction["aspect"] for prediction in predictions}

    assert "customer_support" in aspects_found


def test_classifier_detects_charging_speed_and_reliability(classifier):
    """Check common charging speed and reliability complaints."""
    text = (
        "The charger is extremely slow, and the station frequently "
        "stops working in the middle of a session."
    )

    predictions = classifier.predict(text, threshold=0.25)

    assert isinstance(predictions, list)

    aspects_found = {prediction["aspect"] for prediction in predictions}

    assert "charging_speed" in aspects_found
    assert "reliability" in aspects_found


def test_prediction_output_structure(classifier):
    """Every prediction must contain the required fields."""
    predictions = classifier.predict(
        "The app is easy to use and the charging station worked perfectly.",
        threshold=0.25,
    )

    assert isinstance(predictions, list)

    required_fields = {"aspect", "polarity", "confidence"}

    for prediction in predictions:
        assert required_fields.issubset(prediction.keys())
        assert prediction["aspect"] in EXPECTED_ASPECTS
        assert prediction["polarity"] in {"pos", "neg"}
        assert isinstance(prediction["confidence"], (int, float))
        assert 0.0 <= prediction["confidence"] <= 1.0


def test_explanation_output_structure(classifier):
    """Explanation output must contain feature attribution information."""
    text = (
        "The charging station is reliable, but customer support "
        "is unresponsive and payment keeps failing."
    )

    explanation = classifier.explain(text, top_k=5)

    assert isinstance(explanation, dict)
    assert "aspect_explanations" in explanation

    aspect_explanations = explanation["aspect_explanations"]

    assert isinstance(aspect_explanations, dict)

    for aspect_label, words in aspect_explanations.items():
        assert isinstance(aspect_label, str)
        assert isinstance(words, list)

        for word_info in words:
            assert "word" in word_info
            assert "score" in word_info
            assert isinstance(word_info["word"], str)
            assert isinstance(word_info["score"], (int, float))


def test_benchmark_evaluation():
    """Validate the benchmark evaluation metrics and their ranges."""
    metrics = evaluate_model_on_benchmark()

    required_metrics = {
        "overall_exact_match_ratio",
        "hamming_loss",
        "macro_f1",
        "micro_f1",
        "aspect_metrics",
    }

    assert required_metrics.issubset(metrics.keys())

    assert len(metrics["aspect_metrics"]) == 22

    for metric_name in (
        "overall_exact_match_ratio",
        "hamming_loss",
        "macro_f1",
        "micro_f1",
    ):
        score = metrics[metric_name]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 1.0

    evaluated_labels = {m["label"] for m in metrics["aspect_metrics"]}
    for label in ALL_LABELS:
        assert label in evaluated_labels


def test_empty_review_does_not_crash(classifier):
    """Empty input should be handled safely."""
    predictions = classifier.predict("", threshold=0.25)

    assert isinstance(predictions, list)


def test_unrelated_review_does_not_crash(classifier):
    """Unrelated text should not crash the classifier."""
    predictions = classifier.predict(
        "I watched a movie yesterday and enjoyed the music.",
        threshold=0.25,
    )

    assert isinstance(predictions, list)


def test_all_predictions_use_valid_labels(classifier):
    """Predictions must only use aspects defined by the current taxonomy."""
    predictions = classifier.predict(
        "The station is expensive, charging is slow, and support is poor.",
        threshold=0.25,
    )

    valid_labels = set(ALL_LABELS)

    for prediction in predictions:
        combined_label = (
            f"{prediction['aspect']}:{prediction['polarity']}"
        )

        assert combined_label in valid_labels
