"""Shared fixtures for Token Sentry tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from web3 import Web3

# Sample token addresses
SAFE_TOKEN = "0x1234567890123456789012345678901234567890"
HONEYPOT_TOKEN = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
RUG_TOKEN = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

# Minimal ERC20 bytecode marker (simplified for tests)
SAFE_BYTECODE = (
    "0x608060405234801561001057600080fd5b50"
    "6004361061002b5760003560e01c806306fdde0314610030575b600080fd5b"
    # transfer(address,uint256) selector: 0xa9059cbb
    "a9059cbb"
)

HONEYPOT_BYTECODE = (
    "0x608060405234801561001057600080fd5b50"
    # includes blacklist-like pattern
    "6004361061002b5760003560e01c806306fdde0314610030575b600080fd5b"
    "e47d9999"  # fake blacklist-like selector
)

# Mock verified source - safe token
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

# Mock verified source with mint + blacklist
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


@pytest.fixture
def mock_w3():
    """Mock Web3 instance."""
    w3 = MagicMock(spec=Web3)
    w3.eth = MagicMock()
    w3.eth.get_code = MagicMock(return_value=bytes.fromhex(SAFE_BYTECODE[2:]))
    w3.is_connected = MagicMock(return_value=True)
    return w3


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for Basescan API calls."""
    client = AsyncMock()
    return client
