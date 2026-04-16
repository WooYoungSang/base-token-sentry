"""Honeypot detector - simulates buy/sell via staticCall only (NO real transactions)."""

from web3 import Web3

from .models import HoneypotResult

# Uniswap V2-style router on Base (used for simulation)
# Using Universal Router address on Base
ROUTER_ADDRESS = "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24"
WETH_BASE = "0x4200000000000000000000000000000000000006"

# Simulated trade amount: 0.01 ETH in wei
SIM_ETH_IN = 10**16  # 0.01 ETH

# Tax threshold for honeypot detection
HONEYPOT_SELL_TAX_THRESHOLD = 0.10  # >10% = honeypot

_ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Dummy recipient address for simulations
_SIM_RECIPIENT = "0x000000000000000000000000000000000000dEaD"


class HoneypotDetector:
    def __init__(self, rpc_url: str, router_address: str = ROUTER_ADDRESS):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.router_address = router_address

    async def detect(self, token_address: str) -> HoneypotResult:
        result = HoneypotResult(address=token_address)

        # Simulate buy
        tokens_received = 0
        try:
            tokens_received = await self._simulate_buy(token_address)
        except Exception as e:
            result.buy_blocked = True
            result.is_honeypot = True
            result.details = f"Buy blocked: {e}"
            return result

        if tokens_received <= 0:
            result.buy_blocked = True
            result.is_honeypot = True
            result.details = "Buy simulation returned 0 tokens"
            return result

        # Compute buy tax vs expected (no-tax) amount using getAmountsOut
        expected_buy = await self._get_expected_buy(token_address)
        if expected_buy > 0:
            result.buy_tax = max(0.0, (expected_buy - tokens_received) / expected_buy)

        # Simulate sell
        eth_received = 0
        try:
            eth_received = await self._simulate_sell(token_address)
        except Exception as e:
            result.sell_blocked = True
            result.is_honeypot = True
            result.details = f"Sell blocked: {e}"
            return result

        # Sell tax: compare sell output vs buy output (normalized ratio)
        if tokens_received > 0:
            result.sell_tax = max(0.0, 1.0 - (eth_received / tokens_received))

        if result.sell_tax > HONEYPOT_SELL_TAX_THRESHOLD:
            result.is_honeypot = True
            result.details = f"High sell tax: {result.sell_tax:.1%}"

        return result

    async def _simulate_buy(self, token_address: str) -> int:
        """Simulate buy via getAmountsOut (staticCall only). Returns token amount out."""
        router = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.router_address),
            abi=_ROUTER_ABI,
        )
        path = [
            Web3.to_checksum_address(WETH_BASE),
            Web3.to_checksum_address(token_address),
        ]
        amounts = router.functions.getAmountsOut(SIM_ETH_IN, path).call()
        return int(amounts[-1])

    async def _simulate_sell(self, token_address: str) -> int:
        """Simulate sell via getAmountsOut (staticCall only). Returns ETH amount out."""
        router = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.router_address),
            abi=_ROUTER_ABI,
        )
        # We need tokens_in for sell simulation - use the buy output
        tokens_in = await self._simulate_buy(token_address)
        if tokens_in <= 0:
            return 0
        path = [
            Web3.to_checksum_address(token_address),
            Web3.to_checksum_address(WETH_BASE),
        ]
        amounts = router.functions.getAmountsOut(tokens_in, path).call()
        return int(amounts[-1])

    async def _get_expected_buy(self, token_address: str) -> int:
        """Get expected buy amount without tax (AMM math only)."""
        try:
            return await self._simulate_buy(token_address)
        except Exception:
            return 0
