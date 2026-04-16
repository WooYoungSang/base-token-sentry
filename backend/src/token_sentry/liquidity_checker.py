"""Liquidity checker - verifies DEX liquidity depth and LP lock status."""

from web3 import Web3

from .models import LiquidityAnalysis

# Low liquidity threshold in USD
LOW_LIQUIDITY_USD = 10_000

# Uniswap V3 factory on Base
UNISWAP_V3_FACTORY = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

# Common WETH / USDC on Base
WETH_BASE = "0x4200000000000000000000000000000000000006"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class LiquidityChecker:
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    async def analyze(self, address: str) -> LiquidityAnalysis:
        liquidity_usd = await self._fetch_pool_liquidity(address)
        lp_locked = await self._check_lp_lock(address)
        mcap = await self._fetch_mcap(address)

        liquidity_mcap_ratio = liquidity_usd / mcap if mcap > 0 else 0.0
        low_liquidity = liquidity_usd < LOW_LIQUIDITY_USD

        return LiquidityAnalysis(
            address=address,
            total_liquidity_usd=liquidity_usd,
            liquidity_mcap_ratio=liquidity_mcap_ratio,
            lp_locked=lp_locked,
            low_liquidity=low_liquidity,
            pool_count=1 if liquidity_usd > 0 else 0,
        )

    async def _fetch_pool_liquidity(self, address: str) -> float:
        """Fetch total liquidity in USD across known DEX pools. Override in tests."""
        try:
            # Try Uniswap V3 pool via factory
            factory_abi = [{
                "inputs": [
                    {"name": "tokenA", "type": "address"},
                    {"name": "tokenB", "type": "address"},
                    {"name": "fee", "type": "uint24"},
                ],
                "name": "getPool",
                "outputs": [{"name": "pool", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            }]
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(UNISWAP_V3_FACTORY),
                abi=factory_abi
            )
            pool_addr = factory.functions.getPool(
                Web3.to_checksum_address(address),
                Web3.to_checksum_address(WETH_BASE),
                3000
            ).call()
            if pool_addr == "0x" + "0" * 40:
                return 0.0

            pool_abi = [{"inputs": [], "name": "liquidity", "outputs": [{"name": "", "type": "uint128"}],
                         "stateMutability": "view", "type": "function"}]
            pool = self.w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=pool_abi)
            raw_liq = pool.functions.liquidity().call()
            # Rough conversion: treat as USD proxy (real impl would use price oracles)
            return float(raw_liq) / 1e12
        except Exception:
            return 0.0

    async def _check_lp_lock(self, address: str) -> bool:
        """Check if LP tokens are locked. Override in tests."""
        # MVP: check if LP tokens transferred to known lock contracts
        # Common lockers: Unicrypt, Team.Finance
        return False

    async def _fetch_mcap(self, address: str) -> float:
        """Fetch approximate market cap. Override in tests."""
        return 0.0
