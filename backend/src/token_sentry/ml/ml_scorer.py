"""ML-based scorer using trained XGBoost model."""

import logging
import threading
from pathlib import Path

import numpy as np
import xgboost as xgb

from ..models import ContractAnalysis, HolderAnalysis, HoneypotResult, LiquidityAnalysis
from .data_generator import FEATURE_COLUMNS

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


def extract_features(
    contract: ContractAnalysis,
    holder: HolderAnalysis,
    liquidity: LiquidityAnalysis,
    honeypot: HoneypotResult,
) -> dict[str, float]:
    """Extract numeric feature dict from analysis objects."""
    return {
        "has_hidden_mint": float(contract.has_hidden_mint),
        "has_blacklist": float(contract.has_blacklist),
        "has_fee_on_transfer": float(contract.has_fee_on_transfer),
        "is_proxy": float(contract.is_proxy),
        "has_owner_pause": float(contract.has_owner_pause),
        "has_owner_mint": float(contract.has_owner_mint),
        "critical_flag_count": float(contract.critical_flag_count),
        "top10_concentration": holder.top10_concentration,
        "whale_percentage": holder.whale_percentage,
        "creator_holding": holder.creator_holding,
        "liquidity_depth": liquidity.total_liquidity_usd,
        "liquidity_mcap_ratio": liquidity.liquidity_mcap_ratio,
        "lp_locked": float(liquidity.lp_locked),
        "is_honeypot": float(honeypot.is_honeypot),
        "buy_tax": honeypot.buy_tax,
        "sell_tax": honeypot.sell_tax,
    }


class MLScorer:
    """Thread-safe XGBoost scorer for token safety."""

    def __init__(self, model_path: Path | None = None):
        self._model_path = model_path or DEFAULT_MODEL_PATH
        self._model: xgb.XGBRegressor | None = None
        self._lock = threading.Lock()
        self._load_model()

    def _load_model(self) -> None:
        if not self._model_path.exists():
            logger.warning("Model file not found: %s", self._model_path)
            return
        try:
            model = xgb.XGBRegressor()
            model.load_model(str(self._model_path))
            self._model = model
            logger.info("Loaded ML model from %s", self._model_path)
        except Exception:
            logger.exception("Failed to load ML model")
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def predict(self, features: dict[str, float]) -> tuple[float, str, float]:
        """Predict safety score from feature dict.

        Returns (score, grade, confidence) where confidence is 0-1.
        Raises RuntimeError if model not loaded.
        """
        if self._model is None:
            raise RuntimeError("ML model not loaded")

        feature_array = np.array([[features[col] for col in FEATURE_COLUMNS]])

        with self._lock:
            raw_pred = float(self._model.predict(feature_array)[0])

        score = float(np.clip(raw_pred, 0, 100))
        grade = _score_to_grade(score)

        # Confidence based on how far from grade boundary the prediction is
        boundaries = [0, 20, 40, 60, 80, 100]
        min_dist = min(abs(score - b) for b in boundaries)
        confidence = min(min_dist / 10.0, 1.0)

        return score, grade, confidence

    def predict_from_analyses(
        self,
        contract: ContractAnalysis,
        holder: HolderAnalysis,
        liquidity: LiquidityAnalysis,
        honeypot: HoneypotResult,
    ) -> tuple[float, str, float]:
        """Convenience method: extract features and predict."""
        features = extract_features(contract, holder, liquidity, honeypot)
        return self.predict(features)
