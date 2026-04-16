"""Token watcher - monitors new token deployments on Base via PairCreated events."""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from web3 import Web3

from .analyzer import ContractAnalyzer
from .holder_analyzer import HolderAnalyzer
from .honeypot_detector import HoneypotDetector
from .liquidity_checker import LiquidityChecker
from .models import SafetyScore
from .scorer import SafetyScorer

logger = logging.getLogger(__name__)

# Uniswap V2 factory on Base (emits PairCreated for new token pairs)
UNISWAP_V2_FACTORY = "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6"
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

_FACTORY_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "name": "token0", "type": "address"},
        {"indexed": True, "name": "token1", "type": "address"},
        {"indexed": False, "name": "pair", "type": "address"},
        {"indexed": False, "name": "", "type": "uint256"},
    ],
    "name": "PairCreated",
    "type": "event",
}]

DB_PATH = Path("/tmp/token_sentry.db")


class TokenWatcher:
    def __init__(
        self,
        rpc_url: str,
        basescan_api_key: str = "",
        db_path: Path = DB_PATH,
        poll_interval: int = 12,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.rpc_url = rpc_url
        self.basescan_api_key = basescan_api_key
        self.db_path = db_path
        self.poll_interval = poll_interval

        self.analyzer = ContractAnalyzer(rpc_url, basescan_api_key)
        self.holder_analyzer = HolderAnalyzer(rpc_url)
        self.honeypot_detector = HoneypotDetector(rpc_url)
        self.liquidity_checker = LiquidityChecker(rpc_url)
        self.scorer = SafetyScorer()

        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_scores (
                    address TEXT PRIMARY KEY,
                    score INTEGER,
                    grade TEXT,
                    is_honeypot BOOLEAN,
                    penalties TEXT,
                    analyzed_at TEXT
                )
            """)
            conn.commit()

    async def run(self) -> None:
        """Main event loop: watch for new pairs and analyze them."""
        logger.info("Token Watcher started")
        last_block = self.w3.eth.block_number

        async def producer():
            nonlocal last_block
            while True:
                try:
                    current_block = self.w3.eth.block_number
                    if current_block > last_block:
                        tokens = await self._scan_new_pairs(last_block + 1, current_block)
                        for token in tokens:
                            await self._queue.put(token)
                        last_block = current_block
                except Exception as e:
                    logger.error(f"Watcher error: {e}")
                await asyncio.sleep(self.poll_interval)

        async def consumer():
            while True:
                token = await self._queue.get()
                try:
                    score = await self._analyze_token(token)
                    self._store_result(score)
                    logger.info(f"Analyzed {token}: score={score.score} grade={score.grade}")
                except Exception as e:
                    logger.error(f"Analysis failed for {token}: {e}")
                finally:
                    self._queue.task_done()

        await asyncio.gather(producer(), consumer())

    async def _scan_new_pairs(self, from_block: int, to_block: int) -> list[str]:
        """Scan for PairCreated events and return new token addresses."""
        tokens: list[str] = []
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(UNISWAP_V2_FACTORY),
                abi=_FACTORY_ABI,
            )
            events = factory.events.PairCreated.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
            )
            WETH = "0x4200000000000000000000000000000000000006".lower()
            for event in events:
                t0 = event.args["token0"].lower()
                t1 = event.args["token1"].lower()
                token = t1 if t0 == WETH else t0
                tokens.append(Web3.to_checksum_address(token))
        except Exception as e:
            logger.warning(f"Pair scan error: {e}")
        return tokens

    async def _analyze_token(self, address: str) -> SafetyScore:
        contract = await self.analyzer.analyze(address)
        holder = await self.holder_analyzer.analyze(address)
        liquidity = await self.liquidity_checker.analyze(address)
        honeypot = await self.honeypot_detector.detect(address)
        return self.scorer.score(address, contract, holder, liquidity, honeypot)

    def _store_result(self, score: SafetyScore) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO token_scores
                (address, score, grade, is_honeypot, penalties, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    score.address,
                    score.score,
                    score.grade,
                    score.honeypot.is_honeypot if score.honeypot else False,
                    json.dumps(score.penalties),
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def get_stored_scores(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM token_scores ORDER BY analyzed_at DESC").fetchall()
            return [dict(row) for row in rows]
