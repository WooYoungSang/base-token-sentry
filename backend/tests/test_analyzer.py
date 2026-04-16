"""Tests for contract analyzer."""

from unittest.mock import AsyncMock, patch

import pytest
from token_sentry.analyzer import ContractAnalyzer
from token_sentry.models import ContractAnalysis

SAFE_TOKEN = "0x1234567890123456789012345678901234567890"

RISKY_SOURCE = """
pragma solidity ^0.8.0;
contract RiskyToken {
    address public owner;
    mapping(address => bool) public blacklisted;
    mapping(address => uint256) public balanceOf;
    modifier onlyOwner() { require(msg.sender == owner); _; }
    function mint(address to, uint256 amount) external onlyOwner {
        balanceOf[to] += amount;
    }
    function blacklist(address account, bool status) external onlyOwner {
        blacklisted[account] = status;
    }
    function pause() external onlyOwner {}
    function transfer(address to, uint256 amount) external returns (bool) {
        require(!blacklisted[msg.sender]);
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
"""

SAFE_SOURCE = """
pragma solidity ^0.8.0;
contract SafeToken {
    mapping(address => uint256) public balanceOf;
    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
"""


class TestContractAnalyzer:
    def setup_method(self):
        self.analyzer = ContractAnalyzer(rpc_url="http://fake-rpc", basescan_api_key="fake_key")

    @pytest.mark.asyncio
    async def test_detects_mint_in_source(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value=RISKY_SOURCE)):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert isinstance(result, ContractAnalysis)
        assert result.has_owner_mint is True

    @pytest.mark.asyncio
    async def test_detects_blacklist_in_source(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value=RISKY_SOURCE)):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert result.has_blacklist is True
        assert result.has_owner_blacklist is True

    @pytest.mark.asyncio
    async def test_detects_pause_in_source(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value=RISKY_SOURCE)):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert result.has_owner_pause is True

    @pytest.mark.asyncio
    async def test_safe_token_no_flags(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value=SAFE_SOURCE)):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert result.has_owner_mint is False
        assert result.has_blacklist is False
        assert result.has_owner_pause is False
        assert result.critical_flag_count == 0

    @pytest.mark.asyncio
    async def test_detects_proxy_pattern_in_bytecode(self):
        # delegatecall opcode 0xf4 is proxy indicator
        proxy_bytecode = bytes.fromhex("608060405234801561001057600080fd5bf4")
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value="")):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=proxy_bytecode)):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert result.is_proxy is True

    @pytest.mark.asyncio
    async def test_no_source_returns_analysis_with_address(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value="")):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert result.address == SAFE_TOKEN
        assert result.verified_source is False

    @pytest.mark.asyncio
    async def test_risk_flags_list_populated(self):
        with patch.object(self.analyzer, "_fetch_source", AsyncMock(return_value=RISKY_SOURCE)):
            with patch.object(self.analyzer, "_fetch_bytecode", AsyncMock(return_value=b"\x60\x80")):
                result = await self.analyzer.analyze(SAFE_TOKEN)
        assert len(result.risk_flags) > 0
