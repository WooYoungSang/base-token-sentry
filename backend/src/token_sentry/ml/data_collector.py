"""Real data collection from GoPlusLabs and Basescan APIs for Base chain tokens."""

import json
import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

BASE_CHAIN_ID = "8453"
GOPLUS_BASE_URL = "https://api.gopluslabs.io/api/v1"
BASESCAN_BASE_URL = "https://api.basescan.org/api"

# Rate limit settings
GOPLUS_DELAY = 2.1  # ~30 req/min without API key
BASESCAN_DELAY = 0.25  # 5 req/sec with free key

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
RAW_GOPLUS_DIR = DATA_DIR / "raw" / "goplus"
RAW_BASESCAN_DIR = DATA_DIR / "raw" / "basescan"


def _ensure_dirs() -> None:
    """Create data directories if they don't exist."""
    RAW_GOPLUS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_BASESCAN_DIR.mkdir(parents=True, exist_ok=True)


def _get_basescan_api_key() -> str | None:
    """Read Basescan API key from environment."""
    return os.environ.get("BASESCAN_API_KEY")


class GoPlusCollector:
    """Collect token security data from GoPlusLabs API."""

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < GOPLUS_DELAY:
            time.sleep(GOPLUS_DELAY - elapsed)
        self._last_call = time.monotonic()

    def fetch_token_security(self, address: str) -> dict | None:
        """Fetch token security info from GoPlusLabs.

        Returns the raw API response dict for the token, or None on failure.
        """
        cache_path = RAW_GOPLUS_DIR / f"{address.lower()}.json"
        if cache_path.exists():
            logger.debug("Cache hit for GoPlusLabs: %s", address)
            with open(cache_path) as f:
                return json.load(f)

        self._rate_limit()
        url = f"{GOPLUS_BASE_URL}/token_security/{BASE_CHAIN_ID}"
        params = {"contract_addresses": address.lower()}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.warning("GoPlusLabs API error for %s: %s", address, e)
            return None

        if data.get("code") != 1:
            logger.warning("GoPlusLabs returned error code for %s: %s", address, data.get("message"))
            return None

        result = data.get("result", {})
        token_data = result.get(address.lower())
        if token_data is None:
            logger.warning("No GoPlusLabs data for %s", address)
            return None

        _ensure_dirs()
        with open(cache_path, "w") as f:
            json.dump(token_data, f, indent=2)

        logger.info("Collected GoPlusLabs data for %s", address)
        return token_data

    def fetch_batch(self, addresses: list[str]) -> dict[str, dict]:
        """Fetch security data for multiple tokens. Returns {address: data}."""
        results = {}
        for addr in addresses:
            data = self.fetch_token_security(addr)
            if data is not None:
                results[addr.lower()] = data
        return results


class BasescanCollector:
    """Collect contract and token data from Basescan API."""

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self._api_key = api_key or _get_basescan_api_key()
        self._timeout = timeout
        self._last_call = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < BASESCAN_DELAY:
            time.sleep(BASESCAN_DELAY - elapsed)
        self._last_call = time.monotonic()

    def _request(self, params: dict) -> dict | None:
        """Make a rate-limited request to Basescan API."""
        self._rate_limit()
        if self._api_key:
            params["apikey"] = self._api_key

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(BASESCAN_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.warning("Basescan API error: %s", e)
            return None

        if data.get("status") == "0" and data.get("message") != "No transactions found":
            logger.warning("Basescan error: %s", data.get("result", data.get("message")))
            return None

        return data

    def get_source_code(self, address: str) -> dict | None:
        """Get verified contract source code."""
        cache_path = RAW_BASESCAN_DIR / f"{address.lower()}_source.json"
        if cache_path.exists():
            logger.debug("Cache hit for Basescan source: %s", address)
            with open(cache_path) as f:
                return json.load(f)

        data = self._request({
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
        })
        if data is None:
            return None

        result = data.get("result", [])
        if not result or not isinstance(result, list):
            return None

        source_data = result[0]
        _ensure_dirs()
        with open(cache_path, "w") as f:
            json.dump(source_data, f, indent=2)

        logger.info("Collected Basescan source for %s", address)
        return source_data

    def get_token_transactions(self, address: str, page: int = 1, offset: int = 100) -> list[dict]:
        """Get recent token transfers for an address (used for token discovery)."""
        data = self._request({
            "module": "account",
            "action": "tokentx",
            "address": address,
            "page": str(page),
            "offset": str(offset),
            "sort": "desc",
        })
        if data is None:
            return []
        return data.get("result", []) if isinstance(data.get("result"), list) else []

    def discover_tokens_from_transfers(self, factory_or_router: str, max_tokens: int = 50) -> list[str]:
        """Discover token addresses from transfer events of a DEX router/factory."""
        txs = self.get_token_transactions(factory_or_router, offset=200)
        seen: set[str] = set()
        tokens: list[str] = []
        for tx in txs:
            contract = tx.get("contractAddress", "").lower()
            if contract and contract not in seen:
                seen.add(contract)
                tokens.append(contract)
                if len(tokens) >= max_tokens:
                    break
        return tokens


# Aerodrome Router on Base — used for token discovery
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"


def collect_all(
    seed_addresses: list[str] | None = None,
    discover_from_dex: bool = True,
    max_discovered: int = 100,
) -> list[dict]:
    """Collect data for seed addresses plus discovered tokens.

    Returns list of raw records: {address, goplus_data, basescan_source}.
    """
    from .token_lists import ALL_SEED_ADDRESSES

    if seed_addresses is None:
        seed_addresses = list(ALL_SEED_ADDRESSES)

    # Deduplicate
    all_addresses: list[str] = list(dict.fromkeys(addr.lower() for addr in seed_addresses))

    # Discover additional tokens from DEX activity
    if discover_from_dex:
        basescan_api_key = _get_basescan_api_key()
        if basescan_api_key:
            logger.info("Discovering tokens from Aerodrome Router...")
            bsc = BasescanCollector(api_key=basescan_api_key)
            discovered = bsc.discover_tokens_from_transfers(AERODROME_ROUTER, max_tokens=max_discovered)
            for addr in discovered:
                if addr not in all_addresses:
                    all_addresses.append(addr)
            logger.info("Discovered %d additional tokens from DEX", len(discovered))
        else:
            logger.warning("No BASESCAN_API_KEY set; skipping DEX token discovery")

    logger.info("Total addresses to collect: %d", len(all_addresses))

    goplus = GoPlusCollector()
    basescan = BasescanCollector()
    records: list[dict] = []

    for i, addr in enumerate(all_addresses):
        logger.info("[%d/%d] Collecting %s", i + 1, len(all_addresses), addr)

        goplus_data = goplus.fetch_token_security(addr)
        basescan_source = basescan.get_source_code(addr) if basescan._api_key else None

        if goplus_data is not None:
            records.append({
                "address": addr,
                "goplus_data": goplus_data,
                "basescan_source": basescan_source,
            })

    logger.info("Collected %d records out of %d addresses", len(records), len(all_addresses))
    return records
