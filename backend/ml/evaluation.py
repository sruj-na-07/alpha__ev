
"""
Model Evaluation and Metrics Module for AlphaEV.

Evaluates the multi-label classifier on EV charging application reviews
using exact match ratio, Hamming loss, precision, recall, F1, and
per-label metrics across all 22 aspect-polarity labels.

Important:
- Seed-data evaluation is a diagnostic, not a production accuracy claim.
- For trustworthy performance estimates, use an independent,
  manually annotated test dataset.
"""

from typing import Dict, Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    hamming_loss,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import MultiLabelBinarizer

from backend.ml.seed_data import (
    SEED_DATA,
    ALL_LABELS,
    ASPECT_DISPLAY_NAMES,
)
from backend.services.classifier import classifier_service


def evaluate_classifier_performance(
    k_folds: int = 4,
) -> Dict[str, Any]:
    """
    Evaluate AlphaEV on curated EV charging review seed examples.

    This function preserves the existing API expected by the tests.
    It reports diagnostic metrics on seed examples. Since the shared
    classifier may have been trained on these examples, these results
    must not be interpreted as independent test performance.

    Args:
        k_folds: Retained for backward compatibility. This function
                 does not perform cross-validation.

    Returns:
        A dictionary containing overall metrics and all 22 label metrics.
    """
    del k_folds  # Retained for compatibility; no cross-validation here.

    if not SEED_DATA:
        raise ValueError(
            "SEED_DATA is empty. Add annotated EV charging review examples "
            "before running evaluation."
        )

    # Extract review text and ground-truth multi-label annotations.
    texts = [item[0] for item in SEED_DATA]
    true_labels = [item[1] for item in SEED_DATA]

    valid_labels = set(ALL_LABELS)

    for index, labels in enumerate(true_labels):
        invalid = set(labels) - valid_labels
        if invalid:
            raise ValueError(
                f"Invalid labels in SEED_DATA example {index}: {sorted(invalid)}"
            )

    # Explicitly define the full label space so all 22 labels are reported,
    # including labels not present in a small benchmark.
    mlb = MultiLabelBinarizer(classes=ALL_LABELS)
    mlb.fit([[]])

    y_true = mlb.transform(true_labels)

    # Generate predictions using the existing classifier interface.
    predicted_labels = []

    for text in texts:
        predictions = classifier_service.predict(
            text,
            threshold=0.30,
            use_fallback=True,
        )

        predicted_tags = {
            f"{prediction['aspect']}:{prediction['polarity']}"
            for prediction in predictions
            if (
                prediction.get("aspect") in ASPECT_DISPLAY_NAMES
                and prediction.get("polarity") in {"pos", "neg"}
            )
        }

        # Do not allow unexpected labels into the evaluation matrix.
        predicted_labels.append(predicted_tags & valid_labels)

    y_pred = mlb.transform(predicted_labels)

    # Overall multi-label metrics.
    exact_match = float(accuracy_score(y_true, y_pred))
    loss = float(hamming_loss(y_true, y_pred))

    macro_precision, macro_recall, macro_f1, _ = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            average="macro",
            zero_division=0,
        )
    )

    micro_precision, micro_recall, micro_f1, _ = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            average="micro",
            zero_division=0,
        )
    )

    # Per-label metrics across the complete 22-label taxonomy.
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        average=None,
        labels=np.arange(len(ALL_LABELS)),
        zero_division=0,
    )

    aspect_metrics = []

    for index, label in enumerate(ALL_LABELS):
        aspect_code, polarity = label.rsplit(":", 1)

        display_name = ASPECT_DISPLAY_NAMES.get(
            aspect_code,
            aspect_code,
        )
        polarity_name = "Positive" if polarity == "pos" else "Negative"

        aspect_metrics.append(
            {
                "label": label,
                "aspect": aspect_code,
                "aspect_display": f"{display_name} ({polarity_name})",
                "polarity": polarity,
                "precision": round(float(precision[index]), 3),
                "recall": round(float(recall[index]), 3),
                "f1_score": round(float(f1[index]), 3),
                "support": int(support[index]),
            }
        )

    summary = (
        f"AlphaEV evaluated on {len(texts)} curated EV charging review "
        f"examples: Micro F1 = {micro_f1:.2f}, "
        f"Macro F1 = {macro_f1:.2f}, "
        f"Hamming Loss = {loss:.3f}, "
        f"Exact Match = {exact_match:.2%}. "
        "These are seed-set diagnostic results, not independent "
        "production accuracy estimates."
    )

    return {
        "overall_exact_match_ratio": round(exact_match, 4),
        "hamming_loss": round(loss, 4),
        "macro_precision": round(float(macro_precision), 4),
        "macro_recall": round(float(macro_recall), 4),
        "macro_f1": round(float(macro_f1), 4),
        "micro_precision": round(float(micro_precision), 4),
        "micro_recall": round(float(micro_recall), 4),
        "micro_f1": round(float(micro_f1), 4),
        "total_samples": len(texts),
        "aspect_metrics": aspect_metrics,
        "summary": summary,
    }


# Backward-compatible alias used by the test suite.
evaluate_model_on_benchmark = evaluate_classifier_performance
