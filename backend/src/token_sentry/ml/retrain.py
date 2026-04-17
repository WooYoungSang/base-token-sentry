"""Retrain the XGBoost model using real collected data.

If fewer than 300 real samples exist, augments with synthetic data.

Usage: python -m token_sentry.ml.retrain
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .data_generator import FEATURE_COLUMNS, generate_training_data
from .data_processor import load_training_data
from .trainer import DEFAULT_MODEL_PATH

logger = logging.getLogger(__name__)

MIN_REAL_SAMPLES = 300
SYNTHETIC_AUGMENT_TARGET = 2000


def _score_to_grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def retrain(
    model_path: Path | None = None,
    seed: int = 42,
) -> dict:
    """Retrain model from real data, augmenting with synthetic if needed.

    Returns metrics dict.
    """
    if model_path is None:
        model_path = DEFAULT_MODEL_PATH

    real_data = load_training_data()
    n_real = len(real_data) if real_data is not None else 0

    logger.info("Real training samples available: %d", n_real)

    if real_data is not None and not real_data.empty:
        # Drop non-feature columns
        train_df = real_data[FEATURE_COLUMNS + ["safety_score"]].copy()
    else:
        train_df = pd.DataFrame(columns=FEATURE_COLUMNS + ["safety_score"])

    # Augment with synthetic data if not enough real samples
    augmented = False
    n_synthetic = 0
    if n_real < MIN_REAL_SAMPLES:
        n_synthetic = SYNTHETIC_AUGMENT_TARGET - n_real
        logger.info(
            "Only %d real samples (need %d). Augmenting with %d synthetic samples.",
            n_real, MIN_REAL_SAMPLES, n_synthetic,
        )
        synthetic = generate_training_data(n_samples=n_synthetic, seed=seed)
        train_df = pd.concat([train_df, synthetic[FEATURE_COLUMNS + ["safety_score"]]], ignore_index=True)
        augmented = True

    logger.info("Total training samples: %d (real=%d, synthetic=%d)", len(train_df), n_real, n_synthetic)

    X = train_df[FEATURE_COLUMNS].values
    y = train_df["safety_score"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed,
    )

    n_estimators = 200 if len(X_train) >= 800 else 100

    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.1,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=seed,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = np.clip(model.predict(X_test), 0, 100)

    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    true_grades = [_score_to_grade(s) for s in y_test]
    pred_grades = [_score_to_grade(s) for s in y_pred]
    grade_correct = sum(t == p for t, p in zip(true_grades, pred_grades))
    grade_accuracy = grade_correct / len(true_grades) if true_grades else 0.0

    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))

    metrics = {
        "mae": mae,
        "r2": r2,
        "per_grade_accuracy": grade_accuracy,
        "model_path": str(model_path),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_real": n_real,
        "n_synthetic": n_synthetic,
        "augmented": augmented,
    }
    logger.info(
        "Model retrained: MAE=%.2f, R2=%.3f, Grade Acc=%.2f%%",
        mae, r2, grade_accuracy * 100,
    )
    return metrics


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("Retraining Token Sentry model with real data")
    metrics = retrain()

    print()
    print("=" * 50)
    print("Retrain Results")
    print("=" * 50)
    print(f"MAE:            {metrics['mae']:.2f}")
    print(f"R2:             {metrics['r2']:.3f}")
    print(f"Grade Accuracy: {metrics['per_grade_accuracy']:.2%}")
    print(f"Real samples:   {metrics['n_real']}")
    print(f"Synthetic:      {metrics['n_synthetic']}")
    print(f"Augmented:      {metrics['augmented']}")
    print(f"Model saved to: {metrics['model_path']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
