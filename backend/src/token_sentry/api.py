"""Token Sentry FastAPI application."""

import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import ContractAnalyzer
from .holder_analyzer import HolderAnalyzer
from .honeypot_detector import HoneypotDetector
from .liquidity_checker import LiquidityChecker
from .models import (
    ContractAnalysis,
    HolderAnalysis,
    HoneypotResult,
    LiquidityAnalysis,
    SafetyScore,
)
from .schemas import (
    AnalyzeResponse,
    ContractAnalysisSchema,
    HealthResponse,
    HolderAnalysisSchema,
    HoneypotResultSchema,
    LiquidityAnalysisSchema,
    RecentTokenSchema,
    RecentTokensResponse,
    SafetyScoreSchema,
    TokenDetailSchema,
    TokenListItem,
    TokenListResponse,
)
from .scorer import SafetyScorer

logger = logging.getLogger(__name__)

DB_PATH = Path("/tmp/token_sentry_api.db")
VERSION = "0.1.0"

# Configuration — override via environment variables in production
RPC_URL = "https://mainnet.base.org"
BASESCAN_API_KEY = ""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_scores (
                address TEXT PRIMARY KEY,
                score INTEGER,
                grade TEXT,
                is_honeypot BOOLEAN,
                penalties TEXT,
                contract_json TEXT,
                holder_json TEXT,
                liquidity_json TEXT,
                honeypot_json TEXT,
                analyzed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recent_tokens (
                address TEXT PRIMARY KEY,
                detected_at TEXT
            )
        """)
        conn.commit()


def _store_score(score: SafetyScore) -> None:
    def _contract_dict(c: Optional[ContractAnalysis]) -> Optional[str]:
        if c is None:
            return None
        return json.dumps({
            "has_hidden_mint": c.has_hidden_mint,
            "has_blacklist": c.has_blacklist,
            "has_fee_on_transfer": c.has_fee_on_transfer,
            "is_proxy": c.is_proxy,
            "has_owner_pause": c.has_owner_pause,
            "has_owner_blacklist": c.has_owner_blacklist,
            "has_owner_mint": c.has_owner_mint,
            "risk_flags": c.risk_flags,
            "verified_source": c.verified_source,
            "critical_flag_count": c.critical_flag_count,
        })

    def _holder_dict(h: Optional[HolderAnalysis]) -> Optional[str]:
        if h is None:
            return None
        return json.dumps({
            "top10_concentration": h.top10_concentration,
            "whale_percentage": h.whale_percentage,
            "creator_holding": h.creator_holding,
            "single_holder_dominant": h.single_holder_dominant,
            "creator_dominant": h.creator_dominant,
            "total_holders": h.total_holders,
        })

    def _liquidity_dict(liq: Optional[LiquidityAnalysis]) -> Optional[str]:
        if liq is None:
            return None
        return json.dumps({
            "total_liquidity_usd": liq.total_liquidity_usd,
            "liquidity_mcap_ratio": liq.liquidity_mcap_ratio,
            "lp_locked": liq.lp_locked,
            "low_liquidity": liq.low_liquidity,
            "pool_count": liq.pool_count,
        })

    def _honeypot_dict(hp: Optional[HoneypotResult]) -> Optional[str]:
        if hp is None:
            return None
        return json.dumps({
            "is_honeypot": hp.is_honeypot,
            "buy_tax": hp.buy_tax,
            "sell_tax": hp.sell_tax,
            "buy_blocked": hp.buy_blocked,
            "sell_blocked": hp.sell_blocked,
            "details": hp.details,
        })

    with _get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO token_scores
               (address, score, grade, is_honeypot, penalties,
                contract_json, holder_json, liquidity_json, honeypot_json, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                score.address,
                score.score,
                score.grade,
                score.honeypot.is_honeypot if score.honeypot else False,
                json.dumps(score.penalties),
                _contract_dict(score.contract),
                _holder_dict(score.holder),
                _liquidity_dict(score.liquidity),
                _honeypot_dict(score.honeypot),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


async def _run_analysis(address: str) -> SafetyScore:
    analyzer = ContractAnalyzer(RPC_URL, BASESCAN_API_KEY)
    holder_analyzer = HolderAnalyzer(RPC_URL)
    liquidity_checker = LiquidityChecker(RPC_URL)
    honeypot_detector = HoneypotDetector(RPC_URL)
    scorer = SafetyScorer()

    contract = await analyzer.analyze(address)
    holder = await holder_analyzer.analyze(address)
    liquidity = await liquidity_checker.analyze(address)
    honeypot = await honeypot_detector.detect(address)
    return scorer.score(address, contract, holder, liquidity, honeypot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_db()
    yield


app = FastAPI(
    title="Token Sentry API",
    description="Base token safety analysis and honeypot detection",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version=VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/analyze/{address}", response_model=AnalyzeResponse)
async def analyze_token(address: str, background_tasks: BackgroundTasks):
    """Trigger full token analysis. Returns immediately with cached result if available."""
    # Check cache first
    with _get_db() as conn:
        row = conn.execute(
            "SELECT score, grade, is_honeypot FROM token_scores WHERE address = ?",
            (address,)
        ).fetchone()
        if row:
            return AnalyzeResponse(
                address=address,
                score=row["score"],
                grade=row["grade"],
                is_honeypot=bool(row["is_honeypot"]),
            )

    # Run analysis
    try:
        score = await _run_analysis(address)
        _store_score(score)
        return AnalyzeResponse(
            address=address,
            score=score.score,
            grade=score.grade,
            is_honeypot=score.honeypot.is_honeypot if score.honeypot else False,
            scoring_method=getattr(score, "scoring_method", "rule_based"),
            ml_confidence=getattr(score, "ml_confidence", None),
        )
    except Exception as e:
        logger.error(f"Analysis failed for {address}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/tokens", response_model=TokenListResponse)
async def list_tokens(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    grade: Optional[str] = Query(None),
    is_honeypot: Optional[bool] = Query(None),
):
    """List analyzed tokens with optional filtering."""
    conditions = []
    params: list = []

    if grade:
        conditions.append("grade = ?")
        params.append(grade.upper())
    if is_honeypot is not None:
        conditions.append("is_honeypot = ?")
        params.append(1 if is_honeypot else 0)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    with _get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM token_scores {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT address, score, grade, is_honeypot, analyzed_at FROM token_scores {where} "
            f"ORDER BY analyzed_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return TokenListResponse(
        tokens=[
            TokenListItem(
                address=r["address"],
                score=r["score"],
                grade=r["grade"],
                is_honeypot=bool(r["is_honeypot"]),
                analyzed_at=r["analyzed_at"],
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.get("/tokens/{address}", response_model=TokenDetailSchema)
async def get_token(address: str):
    """Get full analysis breakdown for a token."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT * FROM token_scores WHERE address = ?", (address,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Token not found. POST /analyze/{address} first.")

    contract = None
    if row["contract_json"]:
        d = json.loads(row["contract_json"])
        contract = ContractAnalysisSchema(**d)

    holder = None
    if row["holder_json"]:
        d = json.loads(row["holder_json"])
        holder = HolderAnalysisSchema(**d)

    liquidity = None
    if row["liquidity_json"]:
        d = json.loads(row["liquidity_json"])
        liquidity = LiquidityAnalysisSchema(**d)

    honeypot = None
    if row["honeypot_json"]:
        d = json.loads(row["honeypot_json"])
        honeypot = HoneypotResultSchema(**d)

    return TokenDetailSchema(
        address=row["address"],
        score=row["score"],
        grade=row["grade"],
        penalties=json.loads(row["penalties"]),
        contract=contract,
        holder=holder,
        liquidity=liquidity,
        honeypot=honeypot,
        analyzed_at=row["analyzed_at"],
    )


@app.get("/tokens/{address}/score", response_model=SafetyScoreSchema)
async def get_token_score(address: str):
    """Get safety score only (lightweight)."""
    with _get_db() as conn:
        row = conn.execute(
            "SELECT address, score, grade, penalties FROM token_scores WHERE address = ?",
            (address,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Token not found. POST /analyze/{address} first.")

    return SafetyScoreSchema(
        address=row["address"],
        score=row["score"],
        grade=row["grade"],
        penalties=json.loads(row["penalties"]),
    )


@app.get("/watch/recent", response_model=RecentTokensResponse)
async def recent_tokens(limit: int = Query(20, ge=1, le=100)):
    """List recently detected new tokens from the watcher."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT address, detected_at FROM recent_tokens ORDER BY detected_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

    return RecentTokensResponse(
        tokens=[RecentTokenSchema(address=r["address"], detected_at=r["detected_at"]) for r in rows],
        count=len(rows),
    )
