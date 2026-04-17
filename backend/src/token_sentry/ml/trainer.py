"""XGBoost model training for token safety scoring."""

import logging
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .data_generator import FEATURE_COLUMNS, generate_training_data

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "token_sentry_model.json"


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


def train_model(
    n_samples: int = 2000,
    seed: int = 42,
    model_path: Path | None = None,
) -> dict:
    """Train XGBoost regressor and return evaluation metrics.

    Returns dict with keys: mae, r2, per_grade_accuracy, model_path.
    """
    if model_path is None:
        model_path = DEFAULT_MODEL_PATH

    df = generate_training_data(n_samples=n_samples, seed=seed)

    X = df[FEATURE_COLUMNS].values
    y = df["safety_score"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed,
    )

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=seed,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_pred_clipped = np.clip(y_pred, 0, 100)

    mae = float(mean_absolute_error(y_test, y_pred_clipped))
    r2 = float(r2_score(y_test, y_pred_clipped))

    # Per-grade accuracy
    true_grades = [_score_to_grade(s) for s in y_test]
    pred_grades = [_score_to_grade(s) for s in y_pred_clipped]
    grade_correct = sum(t == p for t, p in zip(true_grades, pred_grades))
    grade_accuracy = grade_correct / len(true_grades)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))

    metrics = {
        "mae": mae,
        "r2": r2,
        "per_grade_accuracy": grade_accuracy,
        "model_path": str(model_path),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }
    logger.info("Model trained: MAE=%.2f, R2=%.3f, Grade Acc=%.2f%%", mae, r2, grade_accuracy * 100)
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = train_model()
    print(f"MAE: {results['mae']:.2f}")
    print(f"R2: {results['r2']:.3f}")
    print(f"Grade Accuracy: {results['per_grade_accuracy']:.2%}")
    print(f"Model saved to: {results['model_path']}")
