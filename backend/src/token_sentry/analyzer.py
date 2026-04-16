"""Contract analyzer - detects red flags in token contracts."""

import re

import httpx
from web3 import Web3

from .models import ContractAnalysis

# Function signatures that indicate risky owner privileges
_MINT_PATTERNS = re.compile(r"\bmint\s*\(", re.IGNORECASE)
_BLACKLIST_PATTERNS = re.compile(r"\b(blacklist|blocklist|addToBlacklist|setBlacklist|banned)\s*\(", re.IGNORECASE)
_PAUSE_PATTERNS = re.compile(r"\b(pause|unpause)\s*\(", re.IGNORECASE)
_OWNER_ONLY = re.compile(r"\bonlyOwner\b", re.IGNORECASE)
_FEE_PATTERNS = re.compile(r"\b(_fee|taxFee|sellFee|buyFee|transferFee)\b", re.IGNORECASE)

# delegatecall opcode (0xf4) in bytecode = proxy pattern
_DELEGATECALL_OPCODE = b"\xf4"


class ContractAnalyzer:
    def __init__(self, rpc_url: str, basescan_api_key: str = ""):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.api_key = basescan_api_key
        self._basescan_url = "https://api.basescan.org/api"

    async def analyze(self, address: str) -> ContractAnalysis:
        result = ContractAnalysis(address=address)
        source, bytecode = await self._fetch_source(address), await self._fetch_bytecode(address)

        if source:
            result.verified_source = True
            self._analyze_source(source, result)
        else:
            result.verified_source = False

        self._analyze_bytecode(bytecode, result)
        return result

    def _analyze_source(self, source: str, result: ContractAnalysis) -> None:
        has_owner = bool(_OWNER_ONLY.search(source))

        if _MINT_PATTERNS.search(source):
            result.has_hidden_mint = True
            if has_owner:
                result.has_owner_mint = True
                result.risk_flags.append("owner_mint")
            else:
                result.risk_flags.append("hidden_mint")

        if _BLACKLIST_PATTERNS.search(source):
            result.has_blacklist = True
            if has_owner:
                result.has_owner_blacklist = True
                result.risk_flags.append("owner_blacklist")
            else:
                result.risk_flags.append("blacklist")

        if _PAUSE_PATTERNS.search(source):
            if has_owner:
                result.has_owner_pause = True
                result.risk_flags.append("owner_pause")

        if _FEE_PATTERNS.search(source):
            result.has_fee_on_transfer = True
            result.risk_flags.append("fee_on_transfer")

    def _analyze_bytecode(self, bytecode: bytes, result: ContractAnalysis) -> None:
        if _DELEGATECALL_OPCODE in bytecode:
            result.is_proxy = True
            if "proxy" not in result.risk_flags:
                result.risk_flags.append("proxy")

    async def _fetch_source(self, address: str) -> str:
        if not self.api_key:
            return ""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._basescan_url, params={
                    "module": "contract",
                    "action": "getsourcecode",
                    "address": address,
                    "apikey": self.api_key,
                })
                data = resp.json()
                if data.get("status") == "1" and data.get("result"):
                    return data["result"][0].get("SourceCode", "")
        except Exception:
            pass
        return ""

    async def _fetch_bytecode(self, address: str) -> bytes:
        try:
            code = self.w3.eth.get_code(address)
            return bytes(code)
        except Exception:
            return b""
