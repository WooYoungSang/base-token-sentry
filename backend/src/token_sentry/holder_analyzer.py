"""Holder analyzer - checks token holder distribution via transfer events."""

from collections import defaultdict

from web3 import Web3

from .models import HolderAnalysis

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Thresholds
WHALE_THRESHOLD = 0.50   # single holder >50% = dominant
CREATOR_THRESHOLD = 0.80  # creator holding >80% = dominant
LOW_LIQUIDITY_USD = 10_000


class HolderAnalyzer:
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    async def analyze(self, address: str, creator_address: str | None = None) -> HolderAnalysis:
        events = await self._fetch_transfer_events(address)

        balances: dict[str, int] = defaultdict(int)
        for ev in events:
            args = ev.get("args", {})
            from_addr = args.get("from", ZERO_ADDRESS).lower()
            to_addr = args.get("to", ZERO_ADDRESS).lower()
            value = int(args.get("value", 0))

            if from_addr != ZERO_ADDRESS:
                balances[from_addr] -= value
            if to_addr != ZERO_ADDRESS:
                balances[to_addr] += value

        # Remove zero/negative balances
        holders = {addr: bal for addr, bal in balances.items() if bal > 0}
        total_supply = sum(holders.values())

        if total_supply == 0 or not holders:
            return HolderAnalysis(address=address, total_holders=0)

        sorted_holders = sorted(holders.values(), reverse=True)
        top10_sum = sum(sorted_holders[:10])
        top10_concentration = top10_sum / total_supply
        whale_percentage = sorted_holders[0] / total_supply

        creator_holding = 0.0
        if creator_address:
            creator_bal = holders.get(creator_address.lower(), 0)
            creator_holding = creator_bal / total_supply

        return HolderAnalysis(
            address=address,
            top10_concentration=top10_concentration,
            whale_percentage=whale_percentage,
            creator_holding=creator_holding,
            single_holder_dominant=whale_percentage > WHALE_THRESHOLD,
            creator_dominant=creator_holding > CREATOR_THRESHOLD,
            total_holders=len(holders),
        )

    async def _fetch_transfer_events(self, address: str) -> list[dict]:
        """Fetch ERC-20 Transfer events for address. Override in tests."""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=[{
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "from", "type": "address"},
                        {"indexed": True, "name": "to", "type": "address"},
                        {"indexed": False, "name": "value", "type": "uint256"},
                    ],
                    "name": "Transfer",
                    "type": "event",
                }]
            )
            latest = self.w3.eth.block_number
            from_block = max(0, latest - 10_000)
            events = contract.events.Transfer.get_logs(fromBlock=from_block, toBlock=latest)
            return [{"args": {"from": e.args["from"], "to": e.args["to"], "value": e.args["value"]}}
                    for e in events]
        except Exception:
            return []
