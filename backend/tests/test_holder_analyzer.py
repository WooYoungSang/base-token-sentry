"""Tests for holder analyzer."""

from unittest.mock import AsyncMock, patch

import pytest
from token_sentry.holder_analyzer import HolderAnalyzer
from token_sentry.models import HolderAnalysis

ADDR = "0x1234567890123456789012345678901234567890"
CREATOR = "0xaaaa000000000000000000000000000000000001"


def _make_transfer_events(holders: dict[str, int], total: int) -> list[dict]:
    """Build mock Transfer event data: from, to, value."""
    events = []
    for addr, amount in holders.items():
        events.append({"args": {"from": "0x0000000000000000000000000000000000000000", "to": addr, "value": amount}})
    return events


class TestHolderAnalyzer:
    def setup_method(self):
        self.analyzer = HolderAnalyzer(rpc_url="http://fake-rpc")

    @pytest.mark.asyncio
    async def test_equal_distribution_low_concentration(self):
        # 10 equal holders
        holders = {f"0x{'aa' * 19}{i:02x}": 100 for i in range(10)}
        events = _make_transfer_events(holders, 1000)
        with patch.object(self.analyzer, "_fetch_transfer_events", AsyncMock(return_value=events)):
            result = await self.analyzer.analyze(ADDR)
        assert isinstance(result, HolderAnalysis)
        assert result.top10_concentration <= 1.0
        assert result.single_holder_dominant is False

    @pytest.mark.asyncio
    async def test_whale_dominant_detected(self):
        # One holder with 60%, 9 others share 40%
        holders = {f"0xwhale{'0' * 34}": 600}
        for i in range(9):
            holders[f"0x{'bb' * 19}{i:02x}"] = 40 // 9 + 1
        events = _make_transfer_events(holders, 1000)
        with patch.object(self.analyzer, "_fetch_transfer_events", AsyncMock(return_value=events)):
            result = await self.analyzer.analyze(ADDR)
        assert result.single_holder_dominant is True
        assert result.whale_percentage > 0.5

    @pytest.mark.asyncio
    async def test_creator_dominant_detected(self):
        # Creator holds 85%
        holders = {CREATOR: 850}
        for i in range(5):
            holders[f"0x{'cc' * 19}{i:02x}"] = 30
        events = _make_transfer_events(holders, 1000)
        with patch.object(self.analyzer, "_fetch_transfer_events", AsyncMock(return_value=events)):
            result = await self.analyzer.analyze(ADDR, creator_address=CREATOR)
        assert result.creator_dominant is True
        assert result.creator_holding > 0.8

    @pytest.mark.asyncio
    async def test_empty_events_returns_default(self):
        with patch.object(self.analyzer, "_fetch_transfer_events", AsyncMock(return_value=[])):
            result = await self.analyzer.analyze(ADDR)
        assert result.address == ADDR
        assert result.total_holders == 0

    @pytest.mark.asyncio
    async def test_result_has_correct_address(self):
        events = _make_transfer_events({"0x" + "aa" * 20: 100}, 100)
        with patch.object(self.analyzer, "_fetch_transfer_events", AsyncMock(return_value=events)):
            result = await self.analyzer.analyze(ADDR)
        assert result.address == ADDR
