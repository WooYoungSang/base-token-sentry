"""Tests for ML scoring pipeline: data generation, training, and prediction."""

import tempfile
from pathlib import Path

from token_sentry.ml.data_generator import FEATURE_COLUMNS, generate_training_data
from token_sentry.ml.ml_scorer import MLScorer, extract_features
from token_sentry.ml.trainer import train_model
from token_sentry.models import (
    ContractAnalysis,
    HolderAnalysis,
    HoneypotResult,
    LiquidityAnalysis,
)
from token_sentry.scorer import SafetyScorer

ADDR = "0x1234567890123456789012345678901234567890"


class TestDataGenerator:
    def test_generates_correct_sample_count(self):
        df = generate_training_data(n_samples=500, seed=99)
        assert len(df) == 500

    def test_default_generates_2000_plus(self):
        df = generate_training_data()
        assert len(df) >= 2000

    def test_all_feature_columns_present(self):
        df = generate_training_data(n_samples=100, seed=1)
        for col in FEATURE_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_safety_score_in_valid_range(self):
        df = generate_training_data(n_samples=500, seed=42)
        assert df["safety_score"].min() >= 0
        assert df["safety_score"].max() <= 100

    def test_binary_features_are_0_or_1(self):
        df = generate_training_data(n_samples=500, seed=42)
        binary_cols = [
            "has_hidden_mint", "has_blacklist", "has_fee_on_transfer",
            "is_proxy", "has_owner_pause", "has_owner_mint",
            "lp_locked", "is_honeypot",
        ]
        for col in binary_cols:
            assert set(df[col].unique()).issubset({0, 1}), f"{col} has non-binary values"

    def test_concentration_in_valid_range(self):
        df = generate_training_data(n_samples=500, seed=42)
        assert df["top10_concentration"].min() >= 0
        assert df["top10_concentration"].max() <= 1.0
        assert df["whale_percentage"].min() >= 0
        assert df["whale_percentage"].max() <= 1.0


class TestTrainer:
    def test_model_trains_and_saves(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            metrics = train_model(n_samples=500, seed=42, model_path=model_path)
            assert model_path.exists()
            assert "mae" in metrics
            assert "r2" in metrics
            assert "per_grade_accuracy" in metrics

    def test_mae_under_threshold(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            metrics = train_model(n_samples=2000, seed=42, model_path=model_path)
            assert metrics["mae"] < 10, f"MAE too high: {metrics['mae']}"

    def test_r2_positive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            metrics = train_model(n_samples=2000, seed=42, model_path=model_path)
            assert metrics["r2"] > 0.5, f"R2 too low: {metrics['r2']}"


class TestMLScorer:
    def test_predict_returns_valid_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            train_model(n_samples=500, seed=42, model_path=model_path)

            scorer = MLScorer(model_path=model_path)
            assert scorer.available

            features = {col: 0.0 for col in FEATURE_COLUMNS}
            score, grade, confidence = scorer.predict(features)

            assert 0 <= score <= 100
            assert grade in ("A", "B", "C", "D", "F")
            assert 0 <= confidence <= 1

    def test_predict_from_analyses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            train_model(n_samples=500, seed=42, model_path=model_path)

            scorer = MLScorer(model_path=model_path)
            contract = ContractAnalysis(address=ADDR, verified_source=True)
            holder = HolderAnalysis(address=ADDR, top10_concentration=0.3)
            liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=100_000, lp_locked=True)
            honeypot = HoneypotResult(address=ADDR, is_honeypot=False)

            score, grade, confidence = scorer.predict_from_analyses(
                contract, holder, liquidity, honeypot,
            )
            assert 0 <= score <= 100
            assert grade in ("A", "B", "C", "D", "F")

    def test_dangerous_token_scores_low(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.json"
            train_model(n_samples=2000, seed=42, model_path=model_path)

            scorer = MLScorer(model_path=model_path)
            contract = ContractAnalysis(
                address=ADDR,
                has_hidden_mint=True, has_blacklist=True, is_proxy=True,
                has_owner_pause=True, has_owner_mint=True,
            )
            holder = HolderAnalysis(
                address=ADDR, top10_concentration=0.9, whale_percentage=0.7,
                creator_holding=0.5,
            )
            liquidity = LiquidityAnalysis(
                address=ADDR, total_liquidity_usd=100, lp_locked=False,
            )
            honeypot = HoneypotResult(
                address=ADDR, is_honeypot=True, sell_tax=0.9, buy_tax=0.3,
            )
            score, grade, _ = scorer.predict_from_analyses(
                contract, holder, liquidity, honeypot,
            )
            assert score < 40, f"Dangerous token scored too high: {score}"

    def test_fallback_when_model_missing(self):
        scorer = MLScorer(model_path=Path("/nonexistent/model.json"))
        assert not scorer.available

    def test_extract_features_from_analyses(self):
        contract = ContractAnalysis(
            address=ADDR, has_hidden_mint=True, has_blacklist=True,
        )
        holder = HolderAnalysis(address=ADDR, top10_concentration=0.5)
        liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=50_000, lp_locked=True)
        honeypot = HoneypotResult(address=ADDR, is_honeypot=False, buy_tax=0.02, sell_tax=0.05)

        features = extract_features(contract, holder, liquidity, honeypot)
        assert features["has_hidden_mint"] == 1.0
        assert features["has_blacklist"] == 1.0
        assert features["top10_concentration"] == 0.5
        assert features["liquidity_depth"] == 50_000
        assert features["lp_locked"] == 1.0
        assert features["is_honeypot"] == 0.0
        assert features["sell_tax"] == 0.05
        assert len(features) == len(FEATURE_COLUMNS)


class TestScorerMLIntegration:
    def test_scorer_has_scoring_method_field(self):
        scorer = SafetyScorer()
        contract = ContractAnalysis(address=ADDR, verified_source=True)
        holder = HolderAnalysis(address=ADDR)
        liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=100_000, lp_locked=True)
        honeypot = HoneypotResult(address=ADDR)

        result = scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert result.scoring_method in ("ml", "rule_based")
        assert 0 <= result.score <= 100
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_ml_confidence_present_when_ml(self):
        scorer = SafetyScorer()
        contract = ContractAnalysis(address=ADDR)
        holder = HolderAnalysis(address=ADDR)
        liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=100_000, lp_locked=True)
        honeypot = HoneypotResult(address=ADDR)

        result = scorer.score(ADDR, contract, holder, liquidity, honeypot)
        if result.scoring_method == "ml":
            assert result.ml_confidence is not None
            assert 0 <= result.ml_confidence <= 1
        else:
            assert result.ml_confidence is None
