"""Tests for liquidity checker."""

from unittest.mock import AsyncMock, patch

import pytest
from token_sentry.liquidity_checker import LiquidityChecker
from token_sentry.models import LiquidityAnalysis

ADDR = "0x1234567890123456789012345678901234567890"


class TestLiquidityChecker:
    def setup_method(self):
        self.checker = LiquidityChecker(rpc_url="http://fake-rpc")

    @pytest.mark.asyncio
    async def test_sufficient_liquidity_not_flagged(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=500_000)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=True)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=2_000_000)):
                    result = await self.checker.analyze(ADDR)
        assert isinstance(result, LiquidityAnalysis)
        assert result.low_liquidity is False
        assert result.lp_locked is True

    @pytest.mark.asyncio
    async def test_low_liquidity_flagged(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=500)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=False)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=1_000_000)):
                    result = await self.checker.analyze(ADDR)
        assert result.low_liquidity is True
        assert result.lp_locked is False

    @pytest.mark.asyncio
    async def test_unlocked_lp_flagged(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=200_000)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=False)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=1_000_000)):
                    result = await self.checker.analyze(ADDR)
        assert result.lp_locked is False

    @pytest.mark.asyncio
    async def test_liquidity_mcap_ratio_calculated(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=100_000)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=True)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=1_000_000)):
                    result = await self.checker.analyze(ADDR)
        assert abs(result.liquidity_mcap_ratio - 0.1) < 0.01

    @pytest.mark.asyncio
    async def test_zero_mcap_no_crash(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=100_000)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=True)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=0)):
                    result = await self.checker.analyze(ADDR)
        assert result.liquidity_mcap_ratio == 0.0

    @pytest.mark.asyncio
    async def test_result_has_address(self):
        with patch.object(self.checker, "_fetch_pool_liquidity", AsyncMock(return_value=10_000)):
            with patch.object(self.checker, "_check_lp_lock", AsyncMock(return_value=False)):
                with patch.object(self.checker, "_fetch_mcap", AsyncMock(return_value=100_000)):
                    result = await self.checker.analyze(ADDR)
        assert result.address == ADDR
