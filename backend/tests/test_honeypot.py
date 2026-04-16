"""Tests for honeypot detector."""

from unittest.mock import AsyncMock, patch

import pytest
from token_sentry.honeypot_detector import HoneypotDetector
from token_sentry.models import HoneypotResult

SAFE_TOKEN = "0x1234567890123456789012345678901234567890"
ROUTER = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"


class TestHoneypotDetector:
    def setup_method(self):
        self.detector = HoneypotDetector(rpc_url="http://fake-rpc")

    @pytest.mark.asyncio
    async def test_clean_token_not_honeypot(self):
        # Simulate buy gets 1000 tokens, sell gives back ~990 (1% tax - acceptable)
        with patch.object(self.detector, "_simulate_buy", AsyncMock(return_value=1000)):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(return_value=990)):
                result = await self.detector.detect(SAFE_TOKEN)
        assert isinstance(result, HoneypotResult)
        assert result.is_honeypot is False
        assert result.sell_tax < 0.10

    @pytest.mark.asyncio
    async def test_high_sell_tax_is_honeypot(self):
        # Buy gets 1000 tokens, but sell returns only 50 (95% sell tax)
        with patch.object(self.detector, "_simulate_buy", AsyncMock(return_value=1000)):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(return_value=50)):
                result = await self.detector.detect(SAFE_TOKEN)
        assert result.is_honeypot is True
        assert result.sell_tax > 0.10

    @pytest.mark.asyncio
    async def test_sell_blocked_is_honeypot(self):
        # Sell simulation raises an exception (reverts)
        with patch.object(self.detector, "_simulate_buy", AsyncMock(return_value=1000)):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(side_effect=Exception("execution reverted"))):
                result = await self.detector.detect(SAFE_TOKEN)
        assert result.is_honeypot is True
        assert result.sell_blocked is True

    @pytest.mark.asyncio
    async def test_buy_blocked_is_honeypot(self):
        # Buy simulation raises exception
        with patch.object(self.detector, "_simulate_buy", AsyncMock(side_effect=Exception("execution reverted"))):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(return_value=0)):
                result = await self.detector.detect(SAFE_TOKEN)
        assert result.is_honeypot is True
        assert result.buy_blocked is True

    @pytest.mark.asyncio
    async def test_buy_tax_calculated_correctly(self):
        # Expect 1000, get 900 -> 10% buy tax
        with patch.object(self.detector, "_simulate_buy", AsyncMock(return_value=900)):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(return_value=890)):
                with patch.object(self.detector, "_get_expected_buy", AsyncMock(return_value=1000)):
                    result = await self.detector.detect(SAFE_TOKEN)
        # buy_tax = (1000 - 900) / 1000 = 0.10
        assert abs(result.buy_tax - 0.10) < 0.02

    @pytest.mark.asyncio
    async def test_result_has_address(self):
        with patch.object(self.detector, "_simulate_buy", AsyncMock(return_value=1000)):
            with patch.object(self.detector, "_simulate_sell", AsyncMock(return_value=1000)):
                result = await self.detector.detect(SAFE_TOKEN)
        assert result.address == SAFE_TOKEN
