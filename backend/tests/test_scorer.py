"""Tests for safety scorer."""

from token_sentry.models import (
    ContractAnalysis,
    HolderAnalysis,
    HoneypotResult,
    LiquidityAnalysis,
    SafetyScore,
)
from token_sentry.scorer import SafetyScorer

ADDR = "0x1234567890123456789012345678901234567890"


class TestSafetyScorer:
    def setup_method(self):
        self.scorer = SafetyScorer()

    def _safe_inputs(self):
        contract = ContractAnalysis(address=ADDR, verified_source=True)
        holder = HolderAnalysis(address=ADDR, top10_concentration=0.3, whale_percentage=0.15)
        liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=100_000, lp_locked=True)
        honeypot = HoneypotResult(address=ADDR, is_honeypot=False, sell_tax=0.01)
        return contract, holder, liquidity, honeypot

    def test_clean_token_scores_high(self):
        contract, holder, liquidity, honeypot = self._safe_inputs()
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert isinstance(result, SafetyScore)
        assert result.score >= 80
        assert result.grade == "A"

    def test_honeypot_heavy_penalty(self):
        contract, holder, liquidity, _ = self._safe_inputs()
        honeypot = HoneypotResult(address=ADDR, is_honeypot=True, sell_tax=0.95)
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert result.score <= 50

    def test_mint_flag_penalty(self):
        contract, holder, liquidity, honeypot = self._safe_inputs()
        contract.has_owner_mint = True
        contract.risk_flags = ["owner_mint"]
        result_clean = self.scorer.score(ADDR, ContractAnalysis(address=ADDR), holder, liquidity, honeypot)
        result_mint = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert result_mint.score < result_clean.score

    def test_high_holder_concentration_penalty(self):
        contract, _, liquidity, honeypot = self._safe_inputs()
        holder_risky = HolderAnalysis(
            address=ADDR, top10_concentration=0.95, whale_percentage=0.6,
            single_holder_dominant=True
        )
        result = self.scorer.score(ADDR, contract, holder_risky, liquidity, honeypot)
        assert result.score < 85

    def test_low_liquidity_penalty(self):
        contract, holder, _, honeypot = self._safe_inputs()
        liquidity_low = LiquidityAnalysis(
            address=ADDR, total_liquidity_usd=500, lp_locked=False, low_liquidity=True
        )
        result = self.scorer.score(ADDR, contract, holder, liquidity_low, honeypot)
        assert result.score < 80

    def test_grade_mapping(self):
        contract, holder, liquidity, honeypot = self._safe_inputs()
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_grade_f_for_very_low_score(self):
        contract = ContractAnalysis(
            address=ADDR,
            has_hidden_mint=True, has_blacklist=True, is_proxy=True,
            has_owner_pause=True, has_owner_blacklist=True, has_owner_mint=True,
            risk_flags=["hidden_mint", "blacklist", "proxy", "owner_pause", "owner_blacklist", "owner_mint"]
        )
        holder = HolderAnalysis(address=ADDR, whale_percentage=0.9, single_holder_dominant=True, creator_dominant=True)
        liquidity = LiquidityAnalysis(address=ADDR, total_liquidity_usd=0, lp_locked=False, low_liquidity=True)
        honeypot = HoneypotResult(address=ADDR, is_honeypot=True, sell_tax=1.0)
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert result.score <= 19
        assert result.grade == "F"

    def test_score_clamped_0_to_100(self):
        contract, holder, liquidity, honeypot = self._safe_inputs()
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert 0 <= result.score <= 100

    def test_penalties_list_populated_for_risky(self):
        contract, holder, liquidity, _ = self._safe_inputs()
        honeypot = HoneypotResult(address=ADDR, is_honeypot=True, sell_tax=0.95)
        result = self.scorer.score(ADDR, contract, holder, liquidity, honeypot)
        assert len(result.penalties) > 0
